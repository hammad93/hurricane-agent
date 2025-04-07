import datetime
import requests

def init_report():
  # The email body for recipients with non-HTML email clients.
  BODY_TEXT = ("HURAIM Hourly Reports\r\n"
             "This email has an attached HTML document. Please reply "
             "for troubleshooting."
  )
  BODY_HTML = """<html>
  <head></head>
  <body>
    <h1>Hurricane Artificial Intelligence using Machine Learning Hourly Reports</h1><br>
    This experimental academic weather report was generated using the software available at <br>
    https://github.com/apatel726/HurricaneDissertation <br>
    https://github.com/hammad93/hurricane-deploy <br>
    <h2>Atlantic Tropical Storms and Hurricanes</h2>"""
  return BODY_TEXT, BODY_HTML

def nhc_report(data, predict):
  '''
  Parameters
  ----------
  data
    The NHC data
  predict
    The predict class
  '''
  BODY_HTML = ""
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
  
  return BODY_HTML

def forecasts(API):
  '''
  Parameters
  ----------
  API
    The URL to get the current forecasts
  '''
  # get current forecasts to report
  current_forecasts = requests.get(API).json()
  BODY_HTML = f"""
  {str(current_forecasts)}
  </body>
  </html>
              """
  return BODY_HTML

def global_report(global_data):
  '''
  Parameters
  ----------
  global_data
    The storms around the globe.
  '''
  BODY_HTML = "<h2>Global Storms</h2>"
  BODY_HTML += global_data['dataframe'].to_html()
  return BODY_HTML

def create_report(data, global_data, predict, forecasts_api):
  '''
  Parameters
  ----------
  data
    The NHC data
  global_data
    The storms around the world
  predict
    The predict class
  forecasts_api
    The URL where the current forecasts are
  '''
  BODY_TEXT, BODY_HTML = init_report()
  BODY_HTML += nhc_report(data, predict)
  BODY_HTML += global_report(global_data)
  BODY_HTML += forecasts(forecasts_api)

  result = {
     'BODY_TEXT': BODY_TEXT,
     'BODY_HTML': BODY_HTML,
     'RECIPIENTS': 'hourly@fluids.ai',
     'SUBJECT': 'fluids hurricane agent: HURAIM Hourly Reports'
  }
  return result