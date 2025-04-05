import json
import requests
import os
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


def send_email(data,
               global_data,
               SENDER,
               SENDERNAME,
               USERNAME_SMTP,
               PASSWORD_SMTP,
               HOST,
               PORT,
               RECIPIENTS= 'hourly@fluids.ai',
               SUBJECT = 'HURAIM Hourly Reports') :
  '''
  This function sends the email for the hourly agent
  Parameters
  ----------
  data

  global_data

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
  # The email body for recipients with non-HTML email clients.
  BODY_TEXT = ("HURAIM Hourly Reports\r\n"
             "This email has an attached HTML document. Please reply "
             "for troubleshooting."
  )
  # get current forecasts to report
  current_forecasts = requests.get(config.current_forecasts_api).json()
  BODY_HTML = """<html>
  <head></head>
  <body>
    <h1>Hurricane Artificial Intelligence using Machine Learning Hourly Reports</h1><br>
    This experimental academic weather report was generated using the software available at <br>
    https://github.com/apatel726/HurricaneDissertation <br>
    https://github.com/hammad93/hurricane-deploy <br>
    <h2>Atlantic Tropical Storms and Hurricanes</h2>"""
  for storm in data :
      # get the prediction for this storm
      try :
        prediction = predict.predict_universal([storm])[0]
        print(prediction)
      except Exception as error :
        prediction = {
          'error' : error
        }
      
      # add to HTML
      html = f"""
      <h2>{storm['id']} ({storm['name']})</h2>
      """

      # storm metadata
      html += f"""<h3>
      As of {str(storm['entries'][-1]['time'])}<br>
      Wind : {round(1.150779 * storm['entries'][-1]['wind'])} mph, {storm['entries'][-1]['wind']} Knots<br>
      Pressure : {storm['entries'][-1]['pressure']} mb<br>
      Location : (lat, lon) ({storm['entries'][-1]['lat']}, {storm['entries'][-1]['lon']}<br>)
      </h3>"""

      # print the informative error
      if 'error' in prediction.keys() :
        html += f"""
        <h3><p style="color:red">Errors in running forecast,</p></h3>
        <pre>
        {prediction['error']}
        </pre>
          """

      else :
          # put the predictions
          html += """
            <table>
              <tr>
                <th><b>Time</b></th>
                <th><b>Wind (mph)</b></th>
                <th><b>Coordinates (Decimal Degrees)</b></th>
              <tr>
          """
          for value in prediction :
              # datetime object keys are predictions
              if isinstance(value, datetime.datetime) :
                  html += f"""
              <tr>
                <th>{value.isoformat()}</th>
                <th>{prediction[value]['max_wind(mph)']:.2f}</th>
                <th>{prediction[value]['lat']:.2f}, {prediction[value]['lon']:.2f}</th>
              <tr>            
                  """
          html += "</table>"
      BODY_HTML += html
  BODY_HTML += "<h2>Global Storms</h2>"
  BODY_HTML += global_data['dataframe'].to_html()
  BODY_HTML += f"""
  {str(current_forecasts)}
  </body>
  </html>
              """

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
