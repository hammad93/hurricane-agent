import pandas as pd
import logging
import predict
import update
import datetime
import config
import os
import utils
import test
import wp
import sys
import db
import fire

from agent import hourly
from agent import daily

# Setup logs
logging.basicConfig(filename='report.log', level=logging.DEBUG)

class Report(object):
  def __init__(self):
    self.SENDER = 'husmani@fluids.ai'
    self.SENDERNAME = 'Hurricane AI'
    # SMTP Credentials
    self.credentials_df = pd.read_csv(config.credentials_dir)
    self.credentials = self.credentials_df.iloc[0]
    self.USERNAME_SMTP = self.credentials['user']
    self.PASSWORD_SMTP = self.credentials['pass']
    self.HOST = self.credentials['host']
    self.PORT = int(self.credentials['port'])
  
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
    global_data = update.global_pipeline()
    
    # Send notification, minimizing duplicate emails
    if global_data['unique'] or command == 'push': # command line to push the email even if not new
      # Run forecasts
      predict.global_forecast()
      # Send email
      hourly_report = hourly.create_report(data, global_data, predict, config.current_forecasts_api)
      self.email(hourly_report)
      
      # Create blog post
      top_of_the_hour = datetime.datetime.now().replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H")
      wp.create_post(f'fluids Hourly Weather Report: {top_of_the_hour}00 Zulu', hourly_report['BODY_HTML'])
    else :
      print('Data ingested is not new.')
  
  def daily(self):
    with open(config.daily_ingest_sql_path) as file:
      query = file.read()
    daily_data = db.query(query)
    daily.create_report(daily_data)

if __name__ == '__main__':
  agent = Report()
  fire.Fire(agent)