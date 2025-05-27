from string import Template
from datetime import timedelta
import dateutil
import concurrent.futures
import time
import requests
import pandas as pd
import openai
import json
import os
import config

import test
test.setup()


def storm_forecast_prompts_sequentially(data, hours = [6, 12, 24, 48, 72, 96, 120]):
  prompt = Template('''Please provide  a forecast for $future hours in the future from the most recent time from the storm.
  This forecast should be based on historical knowledge which includes but is not limited to storms with similar tracks and
  intensities, time of year of the storm, geographical coordinates, and climate change that may have occured since your
  previous training.
  The response will be a JSON object with these attributes:
      "lat" which is the predicted latitude in decimal degrees.
      "lon" which is the predicted longitude in decimal degrees.
      "wind_speed" which is the predicted maximum sustained wind speed in knots.

  Table 1. The historical records the includes columns representing measurements for the storm.
  - The wind_speed column is in knots representing the maxiumum sustained wind speeds.
  - The lat and lon are the geographic coordinates in decimal degrees.
  - time is sorted and the most recent time is the first entry.
  $data
  ''')
  reflection_prompt = Template('''Please quality check the response. The following are requirements,
  - The responses are numbers and not ranges.
  - They align with other forecast hours provided.
  This is an aggregated forecast produced by you and included for reference,
  $forecast
  
  Response with either "True" or "False" based on the quality check. If it's False, provide a more accurate forecast for the original
  $future hours in the future. This prompt is given every time and it's possible that the original response is accurate.
  ''')
  return [
    {
      "forecast_hour" : hour,
      "prompt" : prompt.substitute(future=hour, data=data),
      "reflection" : reflection_prompt
    }
        for hour in hours
  ]

def msg_to_obj(text, delimiters = ('{', '}')):
  # Find the indices of the first and last curly braces in the text
  if delimiters == '```':
      start_index = text.find(delimiters) + 3
      end_index = text.rfind(delimiters)
  else :
      start_index = text.find(delimiters[0])
      end_index = text.rfind(delimiters[1]) + 1

  # Extract the JSON string from the text
  json_string = text[start_index:end_index]
  print(json_string)
  return json_string

def chatgpt_forecast_live(model_version):
    '''
    This will pull in the live storms across the globe and engineer
    prompts that will allow us to ingest forecasts from ChatGPT

    Returns
    -------
    list(pd.DataFrame) A list of DataFrames that have the columns
        id, time, lat, lon, and wind_speed
    '''
    # get the current live tropical storms around the globe
    live_storms = get_live_storms()
    live_storms_cleaned = live_storms.drop(columns=['wind_speed_mph', 'wind_speed_kph'])
    prompts = get_prompts(live_storms_cleaned)
    # capture the forecast from ChatGPT
    # do this concurrently because each prompt is independent
    with concurrent.futures.ThreadPoolExecutor() as executor:
      forecasts = list(executor.map(lambda p: chatgpt_forecast(*p),
                                    [(prompt, model_version) for prompt in prompts]))
    return pd.concat(forecasts, ignore_index=True).drop(columns=['forecast'])

def chatgpt_forecast(prompt, model_version, retries=10):
    '''
    Given the prompt, this will pass it to the version of ChatGPT defined.
    It's meant for forecasts of global tropical storms but can have a range of options.

    Input
    -----
    prompt String
        The initial message to pass to ChatGPT
    system String
        The system message based on the current OpenAI API
    model_version String
        Which model to use

    Returns
    -------
    pd.DataFrame

    References
    ----------
    https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart?tabs=command-line&pivots=programming-language-python
    '''
    openai.api_type = "azure"
    openai.api_version = "2023-05-15" 
    openai.api_base = os.getenv('OPENAI_API_BASE')
    openai.api_key = os.getenv('OPENAI_API_KEY')
    while retries > 0 :
        response = openai.ChatCompletion.create(
            engine=model_version,
            messages=[
                    {"role": "system", "content": "Please act as an expert forecaster and a helpful assistant. Responses should be based on historical data and forecasts must be as accurate as possible. Provided are live data from official source including NOAA and NASA."},
                    {"role": "user", "content": prompt[0]},
                ]
            )
        text = response["choices"][0]["message"]["content"]
        print(text)
        # Parse the JSON string into a Python object
        try:
            cleaned = transform_chatgpt_forecasts(text, prompt[1])
            return pd.DataFrame(cleaned)
        except Exception as e:
            retries = retries - 1
            print(f"Retries left: {retries}, error message: {e}")
def transform_chatgpt_forecasts(text, metadata):
    '''
    Cleans the response from ChatGPT
    '''
    # the current data structure is a list of dictionaries
    json_object = json.loads(msg_to_obj(text, delimiters = '```'))
    result = [
      {
        **forecast,
        'time' : dateutil.parser.parse(metadata['latest_time']) + timedelta(hours = forecast['forecast']),
        'id' : metadata['storm_id']
      } for forecast in json_object]
    return result

def get_live_storms():
    '''
    Upon calling this function, the live tropical storms around the global
    will be returned in a JSON format. Each of the storms returned will have
    the historical records along with in.

    Returns
    -------
    df pandas.DataFrame
        The records include the columns id, time, lat, lon, wind_speed
    '''
    # make the request for live data
    response = requests.get(f"{config.api_url}live-storms")
    if response :
        data = response.json()
    else :
        print(f'There was an error getting live storms, {response.content}')
        return response
    return pd.DataFrame(data)

def get_prompts(df, historical_limit = 5, forecast_times = [12, 24, 36, 48, 72]):
    '''
    Utilizing the current global tropical storms, we will generate prompts
    for a LLM such as ChatGPT to provide forecasts. This function will
    generate prompts for each storm

    Intput
    ------
    df pd.DataFrame
        The records include the columns id, time, lat, lon, wind_speed.
    historical_limit int
        When creating the prompts, this limits the historical limits.
    '''
    unique_storms = set(df['id'])
    prompts = []
    # apply each storm to the prompt template
    for storm in unique_storms:
        current_storm = df[df['id'] == storm].drop(columns=['id']).sort_values(by='time', ascending=False)
        # because it's sorted by latest, it's the first row
        current_storm_latest = current_storm.iloc[0]['time']
        prompt = f'''
Please provide forecasts for {str(forecast_times)} hours in the future from the most recent time in Table 1.
These forecasts should be based on historical knowledge which includes but is not limited to storms with similar tracks and intensities, time of year of the storm, geographical coordinates, and climate change that may have occured since your previous training.
The response will be a list of JSON objects with these attributes:
    "forecast" which is the hour ahead you're forecasting as an integer, e.g. 12 for 12 hours in the future
    "lat" which is the predicted latitude WGS 84
    "lon" which is the predicted longitude WGS 84
    "wind_speed" which is the predicted maximum sustained wind speed in knots.
There should be {len(forecast_times)} JSON objects in this list each corresponding to the forecast times {str(forecast_times)} hours in the future.
Please delimit the JSON response with ``` before and after the data.

Table 1.
- The wind_speed column is in knots representing the maxiumum sustained wind speeds.
- The lat and lon are the geographic coordinates
- time is sorted and the most recent time is the first entry.
- We have limited the history to {historical_limit} records.
- All coordinates are decimal degrees and follow WGS 84.
In JSON,
{current_storm.head(historical_limit).to_json(indent=2, orient='records')}
        '''
        prompts.append((prompt, {
          'latest_time': current_storm_latest,
          'forecast_times': forecast_times,
          'storm_id': storm
        }))
        print(prompt)
    return prompts

def chat(message, token=os.environ["OPENWEBUI_TOKEN"], base_url = config.base_url, model = config.gpt_model):
    url = f'{base_url}/api/chat/completions'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = {
      "model": model,
      "messages": [
        {
          "role": "user",
          "content": message
        }
      ]
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    result['result'] = result['choices'][0]['message']['content']
    return result


def chatgpt_reflection_forecast_concurrent(model='gpt-3.5-turbo'):
  # get the live storms first
  live_storms = get_live_storms()
  # validate the live data
  if len(live_storms) < 1 :
    return 'No storms currently around the world.'

  # generate prompts for one of the storms
  # some storms have long history so we have to set a threshold
  max_historical_track = 4 * 7 # days, approx if 6 hour interval
  tag = int(time.time()) # a unique tag to track the data
  final_results = []
  for storm in set(live_storms['id']):
    # get the storm from the live data and sort by time
    storm_data = live_storms.query(f"id == '{storm}'").sort_values(by='time', ascending=False).iloc[:max_historical_track]
    # clean the data to prepare to use it for the prompt
    storm_data_input = storm_data.drop(columns=['id', 'wind_speed_mph', 'wind_speed_kph']).to_json(indent=2, orient='records')
    print(storm_data_input)
    prompts = storm_forecast_prompts_sequentially(storm_data_input)

    # execute prompts concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
      results = list(executor.map(
          lambda p: chatgpt(*p),
            [
              (prompt["prompt"],
                model,
                5,
                f"{tag}_{storm}_{index}",
                {
                  'forecast_hour': prompt['forecast_hour']
                })
              for index, prompt in enumerate(prompts)
              ]
          )
      )
    # execute reflection prompts
    forecast_string = pd.DataFrame([{**result['json'],
                                    'forecast_hour': result['metadata']['forecast_hour']
                                   } for result in results]).to_json(indent=2, orient='records')
    with concurrent.futures.ThreadPoolExecutor() as executor:
      results_reflection = list(executor.map(
          lambda p: chatgpt(*p),
            [
              (prompt["reflection"].substitute(future=prompt['forecast_hour'], forecast=forecast_string),
                model,
                5,
                f"{tag}_{storm}_{index}",
                {
                  'forecast_hour': prompt['forecast_hour']
                })
              for index, prompt in enumerate(prompts)
              ]
          )
      )

    # add iteration to final results
    base_time = list(storm_data['time'])[0] # sorted desc this is the most recent
    final_results.append([{
          **result['json'], # dictionary unpacking
          'id': storm,
          'time': dateutil.parser.parse(base_time) + timedelta(hours=result['metadata']['forecast_hour']),
          'metadata': result['metadata']
      } for result in results_reflection if result['json']]
    )

  # return the forecast after reflection
  return final_results

def chatgpt(prompt, model_version="gpt-3.5-turbo", retries=5, id=None, metadata=False):
    '''
    Given the prompt, this will pass it to the version of ChatGPT defined.
    It's meant for forecasts of global tropical storms but can have a range of options.

    Input
    -----
    prompt String
        The initial message to pass to ChatGPT
    system String
        The system message based on the current OpenAI API
    model_version String
        Which model to use
    id String
        The thread id, will be created if none exist.
    retries int
        The amount of times to try the prompt again

    Returns
    -------
    pd.DataFrame
    '''
    global config
    openai.api_key = os.environ.get('OPENAI_API_KEY')

    # generate chat or message
    basic = [{"role": "system", "content": "Please act as a weather forecaster and a helpful assistant. Data provided are real time and from official sources including NOAA."},
      {"role": "user", "content": prompt}
    ]
    if id :
      print(id)
      # create chats object if it doesn't exist
      if not config.get('chats', False):
        config['chats'] = {}
      # create id if it doesn't exist
      if not config['chats'].get(id, False) :
        print(f'Adding id, {id} to chat.')
        config['chats'][id] = basic
      chat = config['chats'][id]
    else :
      chat = basic

    json_object = False
    
    # we retry until we get a parsable json
    while json_object is False and retries > 1:
      response = openai.ChatCompletion.create(
          model=model_version,
          messages=chat
      )
      text = response["choices"][0]["message"]["content"]
      print(text)

      json_string = msg_to_json(text)
      print(json_string)
      # Parse the JSON string into a Python object
      try :
        json_object = json.loads(json_string)
      except Exception as e :
        # this could be a QA check that results in True so we flag it here,
        if config['chats'].get(id, False) and text[:4].lower() == 'true':
          # get the previous message response, if there is one
          prev = config['chats'][id][-1]['content']
          # set it as a json_object
          try :
            json_object = json.loads(msg_to_json(prev))
          except :
            print(f"Couldn't parse JSON even though it passed, {prev}")
        print(f"Couldn't parse JSON in the response. Retries: {retries}, {e}")
      retries = retries - 1

    if id and config['chats'].get(id, False) :
      print(f"Adding response to chat history {id}.")
      config['chats'][id] += [{"role": "user", "content": prompt},
      {"role": "assistant", "content": text}]

    # update metadata with model run version
    version = {'model': model_version}
    return {
        "text" : text,
        "json" : json_object,
        "metadata" : version if not metadata else {**metadata, **version}
    }
#setup()
