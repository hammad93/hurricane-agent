feature_scaler_path='https://github.com/apatel726/HurricaneDissertation/raw/master/hurricane_ai/scaler/feature_scaler.pkl'
forecast_model='https://storage.googleapis.com/cyclone-ai.appspot.com/model_2021_09_23_03_27/saved_model.pb'
forecast_chatgpt='https://raw.githubusercontent.com/hammad93/hurricane-net/main/hurricane_net_chatgpt.py'
forecast_model_dir='/root/forecast/1'
credentials_dir='/root/credentials.csv'
api_url='https://nfc.ai:1337/'
chatgpt_forecast_api=f'{api_url}forecast-live-storms'
current_forecasts_api=f'{api_url}forecasts'
live_storms_api=f'{api_url}live-storms'
redis_latest_audio_key = 'latest_audio_metadata'
s3_tts_bucket = 'hurricane-tts'
s3_tts_save_dir = '/root/'
forecasts_live_table = 'forecasts_live'
forecasts_archive_table = 'forecasts_archive'
daily_ingest_sql_path = 'docs/daily_ingest.sql'