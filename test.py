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
  return tests()

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