import pandas as pd
import requests

def transform_data(data):
    '''
    Parameters
    ----------
    data
    '''
    return pd.DataFrame(data)

def create_report(data):
    '''
    data is based on this query or similar
    SELECT * FROM ingest_hash
    WHERE time >= NOW() - INTERVAL '24 hours';
    '''
    result = {
        'BODY_TEXT': None,
        'BODY_HTML': None,
        'RECIPIENTS': 'daily@fluids.ai',
        'SUBJECT': 'fluids hurricane agent: Daily Reports'
    }
    return result

def chat(message, token, base_url, model = '/data/phi-4.gguf'):
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