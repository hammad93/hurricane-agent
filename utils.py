import json
import requests
import os
import agent.hourly
import test
import time
import re
import pandas as pd
import datetime
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import config
import agent
from fastapi import HTTPException, Response
import predict

def run_tts(timestamp=False):
    '''
    Runs the container on the web service that generates and uploads the 
    text to speech artificial intelligence through Azure.

    Input
    -----
    timestamp int (Optional)
        The unix timestamp associated with the run

    References
    ----------
    https://github.com/Azure-Samples/azure-samples-python-management/blob/main/samples/containerinstance/manage_container_group.py
    '''
    test.setup() # setups up environment
    if not timestamp: # if the timestamp isn't set
        timestamp = int(time.time())
    
    # Azure Service Principal Credentials
    tenant_id = os.environ['AZURE_TENANT_ID']
    client_id = os.environ['AZURE_CLIENT_ID']
    client_secret = os.environ['AZURE_CLIENT_SECRET']
    acr_secret = os.environ['AZURE_CONTAINER_REGISTRY_PWD']

    # Azure Resource Details
    subscription_id = '6fabfb83-efda-4669-a00e-8c928dcd4b18'
    resource_group = 'jupyter-lab_group'
    container_group_name = f'tts{timestamp}'
    image_id = "huraim.azurecr.io/hurricane-tts:latest"

    # Azure REST API Endpoint
    resource = "https://management.azure.com/"
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ContainerInstance/containerGroups/{container_group_name}?api-version=2021-07-01"

    # Body of the request
    container_instance_body = {
        # Add your container instance details here
        "location": "eastus",
        "properties": {
            "containers": [
                {
                    "name": container_group_name,
                    "properties": {
                        "image": image_id,
                        "resources": {
                            "requests": {
                                "cpu": 2,
                                "memoryInGb": 8
                            }
                        }
                    }
                }
            ],
            "osType": "Linux",
            "imageRegistryCredentials": [
            {
                "server": "huraim.azurecr.io",  # Replace with your registry server
                "username": "huraim",  # Replace with your registry username
                "password": acr_secret  # Replace with your registry password
            }
        ],
        "restartPolicy": "Never"  # Set the restart policy to Never
        }
    }

    # Function to create the container instance
    def create_container_instance(url, token, body):
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.put(url, headers=headers, json=body)
        return response

    # Main process
    access_token = get_access_token(tenant_id, client_id, client_secret)
    response = create_container_instance(url, access_token, container_instance_body)

    # Output the result
    print(response.status_code, response.json())

    # return metadata
    return {
        'timestamp': timestamp,
        'container-name': container_group_name,
        'request-body': container_instance_body,
        'request-response': response.json()
    }

def manage_containers():
    # Azure Service Principal Credentials
    tenant_id = os.environ['AZURE_TENANT_ID']
    client_id = os.environ['AZURE_CLIENT_ID']
    client_secret = os.environ['AZURE_CLIENT_SECRET']
    acr_secret = os.environ['AZURE_CONTAINER_REGISTRY_PWD']

    # Azure Resource Details
    subscription_id = '6fabfb83-efda-4669-a00e-8c928dcd4b18'
    resource_group = 'jupyter-lab_group'
    image_id = "huraim.azurecr.io/hurricane-tts:latest"
    token = get_access_token(tenant_id, client_id, client_secret)

    # list and select containers to delete
    containers_response = list_container_instances(subscription_id, resource_group, token)
    print(f"Container list response: {containers_response}")
    containers = [container['name'] for container in containers_response['value']]
    max_containers = 5
    tts_regex = 'tts[0-9]+' # match container names
    completed_containers = []
    for container in containers:
        status = request_container_status(subscription_id, resource_group, container, token)
        if re.fullmatch(tts_regex, container) and status in ['Terminated', 'Succeeded', 'Failed']:  # Check for the relevant status
            completed_containers.append(container)
    
    # delete conditions is FIFO on time, but if it's the same time, unknwon which it first deletes
    if len(completed_containers) > max_containers:
        # first in first out according to time, which is the unix time in the name
        fifo = sorted(completed_containers, key = lambda name: re.search("[0-9]+", name).group())[:-max_containers]
        print(f"Select containers to delete: {fifo}")
        # prune out containers
        for container in fifo:
            response_code = delete_container_instance(subscription_id, resource_group, container, token)
            print(f"Container instance deleted, response code: {response_code}")


def delete_container_instance(subscription_id, resource_group, container_group_name, token):
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ContainerInstance/containerGroups/{container_group_name}?api-version=2021-07-01"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    response = requests.delete(url, headers=headers)
    return response.status_code

def request_container_status(subscription_id, resource_group, container_group_name, token):
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ContainerInstance/containerGroups/{container_group_name}?api-version=2021-07-01"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)
    return response.json().get('properties', {}).get('instanceView', {}).get('state')

def list_container_instances(subscription_id, resource_group, token):
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ContainerInstance/containerGroups?api-version=2021-07-01"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)
    return response.json()

def get_access_token(tenant_id, client_id, client_secret):
    '''
    Get access token from Azure
    '''
    resource = "https://management.azure.com/"
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'resource': resource
    }
    response = requests.post(url, data=payload).json()
    return response['access_token']

def web_screenshot(url = 'http://fluids.ai:7000/', out = 'screenshot.png'):
  import time
  from selenium import webdriver
  from selenium.webdriver.chrome.options import Options
  from selenium.webdriver.chrome.service import Service
  from webdriver_manager.chrome import ChromeDriverManager
  
  # Configure Selenium options
  options = Options()
  options.add_argument('--headless')  # Run in headless mode for a headless machine
  options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
  options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
  options.add_argument('--no-sandbox')  # Bypass OS security model, required in some environments
  
  # Initialize the Chrome driver
  driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
  
  # Navigate to the url
  driver.get(url)
  
  # Wait for the map to load fully. Adjust time as needed based on network speed and map complexity
  time.sleep(10)  # Sleep for 10 seconds (or more if needed)
  
  # Take and save a screenshot
  driver.save_screenshot(out)
  
  # Close the browser
  driver.quit()


def send_email(BODY_TEXT,
               BODY_HTML,
               SENDER,
               SENDERNAME,
               USERNAME_SMTP,
               PASSWORD_SMTP,
               HOST,
               PORT,
               RECIPIENTS,
               SUBJECT) :
  '''
  This function sends the email for the hourly agent
  Parameters
  ----------
  BODY_TEXT

  BODY_HTML

  SENDER

  SENDERNAME

  USERNAME_SMTP

  PASSWORD_SMTP

  HOST

  POST

  RECIPIENTS
    This is email is configured with a mailing list.

  SUBJECT
  '''
  # Create message container - the correct MIME type is multipart/alternative.
  msg = MIMEMultipart('alternative')
  msg['Subject'] = SUBJECT
  msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
  # Comment or delete the next line if you are not using a configuration set
  # msg.add_header('X-SES-CONFIGURATION-SET',CONFIGURATION_SET)

  # Record the MIME types of both parts - text/plain and text/html.
  part1 = MIMEText(BODY_TEXT, 'plain')
  part2 = MIMEText(BODY_HTML, 'html')

  # Attach parts into message container.
  # According to RFC 2046, the last part of a multipart message, in this case
  # the HTML message, is best and preferred.
  msg.attach(part1)
  msg.attach(part2)

  # Try to send the messages to the recipients
  # RECIPIENTS must be comma separated
  msg['To'] = RECIPIENTS
  try:
    server = smtplib.SMTP(HOST, PORT)
    server.ehlo()
    server.starttls()
    #stmplib docs recommend calling ehlo() before & after starttls()
    server.ehlo()
    server.login(USERNAME_SMTP, PASSWORD_SMTP)
    server.sendmail(SENDER, RECIPIENTS.split(';'), msg.as_string())
    server.close()
  # Display an error message if something goes wrong.
  except Exception as e:
    print ("Error: ", e)
  else:
    print (f"Email sent to {RECIPIENTS}")
  
  return BODY_HTML

#@app.get("/forecast-live-storms")
def forecast_live_storms(model='all'):
    """
    Get a weather storm forecast using different versions of OpenAI's GPT models.

    This FastAPI endpoint uses the chat completion feature from OpenAI to forecast weather storms.
    It can either use a single specified model or a list of pre-defined models to get multiple forecasts.

    Parameters:
    -----------
    model : str, optional
        The specific GPT model to use for the forecast. 
        Default is 'all', which uses all available models ['gpt-3.5-turbo', 'gpt-4'].
    
    Returns:
    --------
    list[dict]
        A list of forecast data as dictionaries. Each dictionary contains the forecast information and
        the model used for that particular forecast. 

    Raises:
    -------
    HTTPException:
        If an error occurs while fetching or processing the forecast data.
        
    Notes:
    ------
    - Uses a global `cache` dictionary to store the forecast data.
    - Fetches current live storms to feed into the language models for forecasting.
    """
    # Generate all available forecasts from the framework
    if model == 'all' :
        #available_models = ['gpt-35-turbo', 'gpt-4']
        available_models = ['live']
    else :
        available_models = [model]
    forecast = []
    for _model in available_models :
        try:
            # We use the script to get current live storms and feed it into the LLM
            preprocessed = chatgpt.chatgpt_forecast_live(model_version=_model)
            if _model == 'live' :
                preprocessed['model'] = 'gpt-35-turbo'
            else:    
                preprocessed['model'] = _model
            preprocessed['time'] = preprocessed['time'].apply(lambda x: x.isoformat())
            print(preprocessed.head())
            # finish prepropossing by transforming to final data structure
            # list of dict's
            processed = preprocessed.to_dict(orient="records")
            # note that we use extend to reduce dimensionality of data model
            forecast.extend(processed)
        except Exception as e:
            return traceback.print_exc()
    # set in cache
    global r
    r.set('forecasts', json.dumps(forecast))
    return json.loads(r.get('forecasts'))

#@app.get('/latest-tts', response_model=list)
def latest_tts():
    """
    Retrieve the latest text-to-speech (TTS) output.

    This endpoint queries the Redis database to fetch the latest TTS output
    based on a predefined key. The data is stored as a JSON string in Redis,
    representing a list of dictionaries. Each dictionary contains details of a
    TTS file, including filename, storm identifier, timestamp, and language.

    Returns:
        list: A list of dictionaries, each containing details of a TTS file.

    Raises:
        HTTPException: If there is an error in fetching data from Redis or if
        the data is not found.
    """
    try:
        global r
        latest_key = config.redis_latest_audio_key
        result = r.get(latest_key)
        if result is None:
            raise HTTPException(status_code=404, detail="Latest TTS data not found")
        
        # Parse the JSON string into a Python object
        tts_data = json.loads(result.decode('utf-8'))
        return tts_data
    except redis.RedisError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding JSON data from Redis")

#@app.get('/get-audio/{filename}', response_class=Response)
def get_audio(filename: str):
    """
    Retrieve an audio file in .wav format.

    This endpoint queries the Redis database to fetch an audio file based on
    the provided filename. The filename is used as the key in Redis.

    Parameters:
        filename (str): The filename of the audio file to retrieve.

    Returns:
        Response: A response object containing the audio file in binary format.

    Raises:
        HTTPException: If there is an error in fetching the audio file from Redis
        or if the file is not found.
    """
    try:
        # download audio first
        db.download_file_s3(filename, config.s3_tts_bucket, config.s3_tts_save_dir)
        # read in audio
        with open(config.s3_tts_save_dir + filename, "rb") as f:
            audio_data = f.read()
        # respond as wav format
        return Response(content=audio_data, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

