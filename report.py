import pandas as pd
import logging
import predict
import update
import datetime
import config
import chat
import os
import utils
import test
import wp
import sys
import db
import fire
import hurricane_net as hn
import requests
import time

from agent import hourly
from agent import daily
from agent import five_min

# Setup logs
logging.basicConfig(
    handlers=[
        logging.FileHandler( # outputs to log file with timestamp
          f'{config.agent_log_path}/report-{int(time.time())}.log'),
        logging.StreamHandler()
    ],
    level=logging.DEBUG,
    format=config.agent_log_format
)

class Report(object):
  def __init__(self):
    self.SENDER = os.environ['SMTP_USER']
    self.SENDERNAME = 'Hurricane AI'
    # SMTP Credentials
    self.USERNAME_SMTP = os.environ['SMTP_USER']
    self.PASSWORD_SMTP = os.environ['SMTP_PASS']
    self.HOST = os.environ['SMTP_HOST']
    self.PORT = int(os.environ['SMTP_PORT'])
  
  def email(self, report):
    utils.send_email(report['BODY_TEXT'],
                      report['BODY_HTML'],
                      self.SENDER,
                      self.SENDERNAME,
                      self.USERNAME_SMTP,
                      self.PASSWORD_SMTP,
                      self.HOST,
                      self.PORT,
                      report['RECIPIENTS'],
                      report['SUBJECT'])

  def hourly(self, command =''):
    # Execute data pipeline
    data = update.nhc()
    logging.info(data)
    global_data = update.global_pipeline()
    logging.info(global_data)
    
    # Send notification, minimizing duplicate emails
    if global_data['unique'] or command == 'push': # command line to push the email even if not new
      # Run forecasts
      predict.global_forecast()
      # Send email
      hourly_report = hourly.create_report(data, global_data, predict, config.current_forecasts_api)
      logging.info(hourly_report)
      self.email(hourly_report)
      
      # Create blog post
      top_of_the_hour = datetime.datetime.now().replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H")
      wp.create_post(f'fluids Hourly Weather Report: {top_of_the_hour}00 Zulu', hourly_report['BODY_HTML'])
    else :
      logging.info('Data ingested is not new.')
  
  def daily(self):
    logging.info('Starting daily agent through Report class.')
    # Query PostgreSQL for the data ingested in the last 24 hours
    with open(config.daily_ingest_sql_path) as file:
      query = file.read()
    logging.info(query)
    sql_data = db.query(query)
    daily_data = {
      'sql_data': sql_data.to_dict(orient='records'),
      'live-storms': requests.get(config.live_storms_api).json(),
      'forecasts': requests.get(config.current_forecasts_api).json()
    }
    logging.info(daily_data)
    # Open up prompt template from hurricane_net repository
    template = hn.prompt.daily_report
    daily_report = daily.create_report(data=daily_data, chat=chat.chat, prompt=template, tests=test.tests)
    logging.info(daily_report)
    self.email(daily_report)
    logging.info('Daily agent is done.')

  def five_min(self):
    logging.info('Started 5 Minute AI Agent through Report class.')
    # get live storms and forecasts
    storms = chat.get_live_storms()
    forecasts = chat.get_forecasts()
    data = {
      'storms': storms,
      'forecasts': forecasts
    }
    prompts = chat.get_prompts(storms[['id', 'time', 'lat', 'lon', 'wind_speed']])
    five_min_report = five_min.create_report(data=data, chat=chat, prompts=prompts, db=db, config=config)
    if five_min_report:
      logging.info(five_min_report)
      self.email(five_min_report)
    logging.info('5 Minute Agent is done.')

if __name__ == '__main__':
  agent = Report()
  fire.Fire(agent)
