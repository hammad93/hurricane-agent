import update
import pickle
import numpy as np
import pandas as pd
import logging
import requests
import json
import datetime
from datetime import timedelta
from datetime import timezone
import config
from math import radians, cos, sin, asin, sqrt, atan2, degrees
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import timedelta
import db

def download_file(url) :
    response = requests.get(url)
    with open(f'/root/{url.split("/")[-1]}', "wb") as file:
        file.write(response.content)

def feature_extraction(timestep, previous):
    '''
    PURPOSE: Calculate the features for a machine learning model within the context of hurricane-net
    METHOD: Use the predictors and the calculation methodology defined in Knaff 2013
    INPUT:  timestep - current dictionary of features in the hurricane object format
            previous - previous timestep dictionary of features in the hurricane object format
    OUTPUT: Dictionary of features

    timestep = {
      'lat' : float,
      'long' : float,
      'max-wind' : float,
      'entry-time' : datetime
    }
    '''
    features = {
        'lat': timestep['lat'],
        'long': timestep['lon'],
        'max_wind': timestep['wind'],
        'delta_wind': (timestep['wind'] - previous[
            'wind']) /  # Calculated from track (12h)
                      ((timestep['time'] - previous[
                          'time']).total_seconds() / 43200),
        'min_pressure': timestep['pressure'],
        'zonal_speed': (timestep['lat'] - previous[
            'lat']) /  # Calculated from track (per hour)
                       ((timestep['time'] - previous[
                           'time']).total_seconds() / 3600),
        'meridonal_speed': (timestep['lon'] - previous[
            'lon']) /  # Calculated from track (per hour)
                           ((timestep['time'] - previous[
                               'time']).total_seconds() / 3600),
        'year': timestep['time'].year,
        'month': timestep['time'].month,
        'day': timestep['time'].day,
        'hour': timestep['time'].hour,
    }
    return features

def predict_json(project, model, instances, version=None):
    """Send json data to a deployed model for prediction.

    Args:
        project (str): project where the Cloud ML Engine Model is deployed.
        model (str): model name.
        instances ([Mapping[str: Any]]): Keys should be the names of Tensors
            your deployed model expects as inputs. Values should be datatypes
            convertible to Tensors, or (potentially nested) lists of datatypes
            convertible to tensors.
        version: str, version of the model to target.
    Returns:
        Mapping[str: any]: dictionary of prediction results defined by the
            model.
    """
    '''
    # Create the ML Engine service object.
    # To authenticate set the environment variable
    # GOOGLE_APPLICATION_CREDENTIALS=<path_to_service_account_file>
    service = googleapiclient.discovery.build('ml', 'v1')
    name = 'projects/{}/models/{}'.format(project, model)

    if version is not None:
        name += '/versions/{}'.format(version)

    response = service.projects().predict(
        name=name,
        body={'instances': instances}
    ).execute()

    if 'error' in response:
        raise RuntimeError(response['error'])

    return response
    '''
    # make request to hurricane ai
    headers = {"content-type": "application/json"}
    data = json.dumps({"instances" : instances})
    json_response = requests.post(f'http://localhost:9000/v1/models/{model}:predict',
                  data = data,
                  headers = headers)
    print(json_response.text)

    # return results
    return json.loads(json_response.text)["predictions"]


def predict_universal(data = None) :
    # get the update
    if data :
        raw = data
    else :
        raw = update.nhc()

    # read in the scaler
    download_file(config.feature_scaler_path)
    with open('/root/feature_scaler.pkl', 'rb') as f :
        scaler = pickle.load(f)

    # generate predictions
    results = []
    for storm in raw :
        print(f'Processing {storm["id"]}. . . ')

        # create prescale data structure
        df = pd.DataFrame(storm['entries']).sort_values('time', ascending = False)

        # set reference time and geometric pattern recognition
        reference = df['time'].max().replace(tzinfo = timezone.utc)
        reference_count = 0
        print(f"Reference time is: {reference}")
        while reference.hour not in [0, 6, 12, 18] : # not a regular timezone
            reference_count += 1
            reference = df.iloc[reference_count]['time']
            print(f"Reference time is: {reference}")
        input = df[df['time'].isin(
            [reference - timedelta(hours = delta)
             for delta in [0, 6, 12, 18, 24, 30]])
        ].sort_values('time', ascending = False).reindex()

        # flag for if input is not long enough
        if (len(input) < 6) :
            logging.warning(
                f"{storm['id']}"
                f" does not have enough data, does not follow the input"
                f" pattern for the AI, or an unknown error. Skipping.")
            results.append({'error': f'{storm["id"]} did not have enough records'})
            continue

        # generate input
        input = [list(feature_extraction(input.iloc[i + 1], input.iloc[i]).values())
                 for i in range(5)]

        # scale our input
        input = np.expand_dims(scaler.transform(input), axis = 0)

        # get our prediction
        prediction_json = predict_json('cyclone-ai', 'hurricane', input.tolist())
        prediction = prediction_json[0]
        
        # inverse transform the prediction
        lat = [output[0] for output in scaler.inverse_transform(
            [[lat[0], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] for lat in
             prediction])]
        lon = [output[1] for output in scaler.inverse_transform(
            [[0, lon[0], 0, 0, 0, 0, 0, 0, 0, 0, 0] for lon in
             prediction])]
        wind = [output[2] for output in scaler.inverse_transform(
            [[0, 0, wind[0], 0, 0, 0, 0, 0, 0, 0, 0] for wind in
             prediction])]

        output = dict()
        for index, value in enumerate([12, 18, 24, 30, 36]):
            output[reference + timedelta(hours = value)] = {
                'lat': lat[index],
                'lon': lon[index],
                'max_wind(mph)': wind[index] * 1.15078
            }
        output['id'] = storm['id']
        results.append(output)
        print(f'Done with {storm["id"]}, results:\n{output}')

    return results

def predict_singular(data = None) :
    # get the update
    if data :
        raw = data
    else :
        raw = update.nhc()

    # read in the scaler
    download_file('model_artifacts/universal/feature_scaler.pkl')
    with open('/root/feature_scaler.pkl', 'rb') as f :
        scaler = pickle.load(f)

    # generate predictions
    results = []
    for storm in raw:
        print(f'Processing {storm["id"]}. . . ')

        # create prescale data structure
        df = pd.DataFrame(storm['entries']).sort_values('time', ascending=False)
        # set reference time and geometric pattern recognition
        reference = df['time'].max().replace(tzinfo=timezone.utc)
        reference_count = 0
        print(f"Reference time is: {reference}")
        while reference.hour not in [0, 6, 12, 18]:  # not a regular timezone
            reference_count += 1
            reference = df.iloc[reference_count]['time']
            print(f"Reference time is: {reference}")
        input = df[df['time'].isin(
            [reference - timedelta(hours=delta)
             for delta in [0, 24, 48, 72, 96, 120]])
        ].sort_values('time', ascending=False).reindex()
        # if input is not long enough
        if (len(input) < 6):
            logging.warning(
                f"{storm['id']}"
                f" does not have enough data, does not follow the input"
                f" pattern for the AI, or an unknown error. Skipping.")
            continue
        input = [list(feature_extraction(input.iloc[i + 1], input.iloc[i]).values())
                 for i in range(5)]

        # scale our input
        input = np.expand_dims(scaler.transform(input), axis=0)

        # get our prediction
        prediction = predict_json(
            'cyclone-ai', 'universal', input.tolist())[
            "predictions"][0]["time_distributed"]
        print(prediction)

        # inverse transform the prediction
        lat = [output[0] for output in scaler.inverse_transform(
            [[lat[0], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] for lat in
             prediction])]
        lon = [output[1] for output in scaler.inverse_transform(
            [[0, lon[0], 0, 0, 0, 0, 0, 0, 0, 0, 0] for lon in
             prediction])]
        wind = [output[2] for output in scaler.inverse_transform(
            [[0, 0, wind[0], 0, 0, 0, 0, 0, 0, 0, 0] for wind in
             prediction])]

        output = dict()
        for index, value in enumerate([24, 48, 72, 96, 120]):
            output[reference + timedelta(hours=value)] = {
                'lat': lat[index],
                'long': lon[index],
                'max_wind(mph)': wind[index] * 1.15078
            }
        output['id'] = storm['id']
        results.append(output)
        print(f'Done with {storm["id"]}, results:\n{output}')

    return results

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth using the Haversine formula.
    """
    # Radius of the Earth in kilometers
    R = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Compute differences
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Haversine formula to calculate the distance
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    
    # Distance in kilometers
    distance = R * c
    return distance

def destination_point(lat, lon, bearing, distance):
    """
    Calculate a new point given an initial point, a bearing, and a distance.
    """
    R = 6371.0  # Radius of the Earth in kilometers
    
    # Convert lat, lon, and bearing to radians
    lat = radians(lat)
    lon = radians(lon)
    bearing = radians(bearing)
    
    # Calculate the new latitude
    new_lat = asin(sin(lat) * cos(distance / R) + cos(lat) * sin(distance / R) * cos(bearing))
    
    # Calculate the new longitude
    new_lon = lon + atan2(sin(bearing) * sin(distance / R) * cos(lat), cos(distance / R) - sin(lat) * sin(new_lat))
    
    # Convert the new latitude and longitude back to degrees
    new_lat = degrees(new_lat)
    new_lon = degrees(new_lon)
    
    return new_lat, new_lon

def bearing(lat1, lon1, lat2, lon2):
    """
    Calculate the bearing from point A (lat1, lon1) to point B (lat2, lon2).
    """
    # Convert latitudes and longitudes to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Calculate the bearing
    dlon = lon2 - lon1
    y = sin(dlon) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
    
    # Convert the bearing to degrees
    initial_bearing = atan2(y, x)
    initial_bearing = degrees(initial_bearing)
    
    # Normalize to 0-360 degrees
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing

def forecast_storm_with_great_circle(data):
    """
    Takes in a list of dictionaries representing storm data, and returns a forecast for 1, 2, and 3 days out,
    incorporating great-circle calculations for latitude and longitude.
    """
    # Convert the data to a pandas DataFrame
    df = pd.DataFrame(data)
    
    # Convert 'time' column to datetime
    df['time'] = pd.to_datetime(df['time'])
    
    # Ensure lat/lon and wind_speed are floats
    df['lat'] = df['lat'].astype(float)
    df['lon'] = df['lon'].astype(float)
    df['wind_speed'] = df['wind_speed'].astype(float)
    
    # Sort by time
    df = df.sort_values(by='time')

    # Return empty data if there's only one record
    if len(df) < 2 :
        return []
    
    # Extract the most recent and second-most recent data
    recent_data = df.iloc[-1]
    previous_data = df.iloc[-2]
    
    # Prepare time values in seconds
    time_values = np.array([(previous_data['time'] - df['time'].min()).total_seconds(), 
                            (recent_data['time'] - df['time'].min()).total_seconds()]).reshape(-1, 1)
    
    # Calculate the great-circle distance and bearing between the two points
    distance = haversine(previous_data['lat'], previous_data['lon'], recent_data['lat'], recent_data['lon'])
    angle = bearing(previous_data['lat'], previous_data['lon'], recent_data['lat'], recent_data['lon'])
    
    # Create a linear model for distance over time
    distance_values = np.array([0, distance])  # Start with 0 distance at the earlier point
    distance_model = LinearRegression().fit(time_values, distance_values)
    
    # Create a linear model for wind_speed over time
    wind_speed_values = np.array([previous_data['wind_speed'], recent_data['wind_speed']], dtype=float)
    wind_model = LinearRegression().fit(time_values, wind_speed_values)
    
    # Define the forecast times: 1 day, 2 days, and 3 days out (in seconds)
    forecast_times = [
        (recent_data['time'] + timedelta(hours=6) - df['time'].min()).total_seconds(),
        (recent_data['time'] + timedelta(hours=12) - df['time'].min()).total_seconds(),
        (recent_data['time'] + timedelta(days=1) - df['time'].min()).total_seconds(),
        (recent_data['time'] + timedelta(days=2) - df['time'].min()).total_seconds(),
        (recent_data['time'] + timedelta(days=3) - df['time'].min()).total_seconds()
    ]
    
    # Calculate the forecasts
    forecasts = []
    for t in forecast_times:
        # Predict the distance and wind speed at each forecast time
        predicted_distance = distance_model.predict([[t]])[0]
        wind_speed_forecast = wind_model.predict([[t]])[0]
        forecast_time = df['time'].min() + timedelta(seconds=t)
        
        # Check if it's a valid forecast
        if wind_speed_forecast < 0 : # wind speed is negative
            slope = wind_model.coef_[0]
            intercept = wind_model.intercept_
            zero_time = -intercept/slope
            # redefine variables to valid forecast
            forecast_time = df['time'].min() + timedelta(seconds=zero_time)
            wind_speed_forecast = wind_model.predict([[zero_time]])[0]
            # print some logs
            print(str(wind_speed_forecast))
            print(f"f(x) = {slope}x + {intercept}, f({zero_time}) = {wind_speed_forecast}")
        
        # Use the distance and bearing to calculate the new lat/lon
        forecast_lat, forecast_lon = destination_point(recent_data['lat'], recent_data['lon'], angle, predicted_distance)
        # finalize data structure
        forecast = {
            'forecast_time': forecast_time.isoformat(),
            'time': recent_data['time'].isoformat(),
            'lat': forecast_lat,
            'lon': forecast_lon,
            'wind_speed': wind_speed_forecast,
            'source': 'Linear Model by fluids'
        }
        forecasts.append(forecast)
        if wind_speed_forecast < 1: # storm has dissapated (wind speed is 0)
            break
    
    return forecasts

def global_forecast():
    '''
    Parameters
    ----------
    data dictionary
        The global live storms and their data

    Table: forecasts_live
        Columns:
        - model: The unique identifier for the model
        - id: The storm ID
        - forecast_time: The time in the future, relative to the time variable, in ISO 8601
        - time: Time of the observation in ISO 8601 time format e.g. +6 hours and this is the starting value
        - trans_time: Transaction time of when the observation was requested or ingested
        - hash: The hash ID for the observation hierarchy
        - lat: The latitude ISO 6709
        - lon: The longitude ISO 6709
        - int: The wind intensity in knots
        - metadata: JSON object of arbitrary size or structure
    '''
    data = pd.DataFrame(requests.get(config.live_storms_api).json())
    
    forecasts = {}
    for storm in set(data['id']):
        entries = data[data['id'] == storm]
        forecast = forecast_storm_with_great_circle(entries.to_dict(orient='records'))
        print(forecast)
        forecasts[storm] = forecast
    
    # vectorize and archive data in the raw form
    vector = update.upload_hash(forecasts)

    # for updating the database, we need to make sure the data hasn't already been processed (is unique)
    print(f"Unique?: {vector['unique']}")
    if vector['unique'] :
        # Post process for the expected row values of the forecasts_live table
        forecast_table =[]
        for forecast in forecasts.keys():
            print(forecast)
            for storm in forecasts[forecast]:
                print(storm)
                forecast_table.append({
                    'model': storm['source'],
                    'id': forecast,
                    'forecast_time': storm['forecast_time'],
                    'time': storm['time'],
                    'trans_time': datetime.datetime.now().isoformat(),
                    'hash': vector['hash'],
                    'lat': storm['lat'],
                    'lon': storm['lon'],
                    'int': float(storm['wind_speed'])
                })
        # process database and SQL for archiving forecasts
        engine = db.get_engine()
        metadata = update.MetaData()
        metadata.reflect(bind=engine)
        table = metadata.tables[config.forecasts_archive_table]
        db.query(q = (table.insert(), forecast_table), write = True)
        # process database and SQL for live forecasts
        engine = db.get_engine()
        metadata = update.MetaData()
        metadata.reflect(bind=engine)
        table_name = config.forecasts_live_table
        table = metadata.tables[table_name]
        # reset live table
        db.query(q = (f'DELETE FROM {table_name}',), write = True)
        db.query(q = (table.insert(), forecast_table), write = True)


    