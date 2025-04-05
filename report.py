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
import agent

# Setup logs
logging.basicConfig(filename='report.log', level=logging.DEBUG)

SENDER = 'husmani@fluids.ai'
SENDERNAME = 'Hurricane AI'

# SMTP Credentials
credentials_df = pd.read_csv('/root/credentials.csv')
credentials = credentials_df.iloc[0]
USERNAME_SMTP = credentials['user']
PASSWORD_SMTP = credentials['pass']

HOST = credentials['host']
PORT = int(credentials['port'])

# The HTML body of the email.
data = update.nhc()
global_data = update.global_pipeline()
command_line = False if len(sys.argv) < 2 else sys.argv[1] # e.g. python report.py push
if global_data['unique'] or command_line == 'push': # command line to push the email even if not new
  # Run forecasts
  predict.global_forecast()
  # Send email
  BODY_TEXT, BODY_HTML = agent.hourly.create_report(data, global_data, predict, config.current_forecasts_api)
  BODY_HTML = utils.send_email(BODY_TEXT, BODY_HTML, SENDER, SENDERNAME, USERNAME_SMTP, PASSWORD_SMTP, HOST, PORT, RECIPIENTS = 'hourly@fluids.ai', SUBJECT = 'HURAIM Hourly Reports')
  top_of_the_hour = datetime.datetime.now().replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H")
  # Create blog post
  wp.create_post(
    f'fluids Hourly Weather Report: {top_of_the_hour}00 Zulu',
    BODY_HTML
    )
else :
  print('Data ingested is not new.')

