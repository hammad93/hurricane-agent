import config
import pandas as pd
import requests
import os
import utils

def ai_pipeline():
  '''
  Starts and manages the processes with artificial intelligence including,
  - Forecasts
  - Text to speech
  '''
  # chatgpt forecasts
  forecasts = requests.get(config.chatgpt)
  print(f'ChatGPT forecasts: {forecasts.content}')
  
  # text to speech
  tts_metadata = utils.run_tts()
  print(f'TTS Metadata: {tts_metadata}')

  # cleanup pipeline run
  utils.manage_containers()

def setup():
  '''
  Setup environment variables and other conditions similar to
  production
  '''
  passwords = pd.read_csv(config.credentials_dir)
  def get_var(var, col):
    return passwords[passwords['user'] == var].iloc[0][col]
  os.environ["OPENAI_API_KEY"] = get_var('openai', 'pass')
  os.environ["OPENAI_API_BASE"] = get_var('openai', 'host')

  # https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-on-premises-apps
  os.environ['AZURE_CLIENT_ID'] = get_var('azure_client', 'pass')
  os.environ['AZURE_TENANT_ID'] = get_var('azure_tenant', 'pass')
  os.environ['AZURE_CLIENT_SECRET'] = get_var('azure_key', 'pass')
  os.environ['AZURE_CONTAINER_REGISTRY_PWD'] = get_var('acr_key', 'pass')
  os.environ['AZURE_REDIS_KEY'] = get_var('redis', 'pass')
  os.environ['AZURE_REDIS_HOST'] = get_var('redis', 'host')
  os.environ['AZURE_REDIS_PORT'] = str(int(get_var('redis', 'port')))
  os.environ['WP_PASS'] = get_var('user', 'pass')
  os.environ['AWS_ACCESS_KEY_ID'] = get_var('AWS_ACCESS_KEY_ID', 'pass')
  os.environ['AWS_SECRET_ACCESS_KEY'] = get_var('AWS_SECRET_ACCESS_KEY', 'pass')
  os.environ['OPENWEBUI_TOKEN'] = get_var('openwebui', 'pass')

def tests():
  '''
  Failed tests can be done assessed with,
  >>> if False in [x[0] for x in tests()]
  '''
  def test_ok(url):
    response = requests.get(url)
    if not response.ok:
      return False, response
    else:
      return True, response.text
  results = []
  # check to see if fluids.ai is up
  results.append(test_ok(config.fluids_url))
  # check if live forecasts are up
  results.append(test_ok(config.current_forecasts_api))
  # check to see if live tracking is up
  results.append(test_ok(config.live_storms_api))
  # check to see if the 3D map is up
  results.append(test_ok(config.map_url))
  
  return results