import pandas as pd
import datetime
import logging
import pprint
from sqlalchemy import MetaData, Table
import datetime

def create_report(data, chat, prompts, db, config):
    '''
    Parameters
    ----------
    data pandas.DataFrame
      - Based on this PostgreSQL query or similar
      - SELECT * FROM ingest_hash WHERE time >= NOW() - INTERVAL '24 hours';
    chat Object
      - A Python function (Object) that inputs 'message' and returns the response
      from the LLM
    prompt LangChain PromptTemplate
      - This template takes in the data after it's processed and generates a report
      from the LLM.
    
    '''
    storm_ids = set(data['storms']['id'])
    forecasts_data = data['forecasts']
    forecasted = set(forecasts_data[forecasts_data['model'] != 'Linear Model by fluids']['id'])
    todos = [id for id in storm_ids if id not in forecasted]
    logging.info(f"Live: {storm_ids}\nForecasted: {forecasted}\nPending forecasts for {todos}")
    todo = todos[0] # only do one at a time
    for p in prompts:
        if p[1]['storm_id'] == todo:
            prompt = p[0]
    logging.info(prompt)
    llm_output = chat.chat(prompt)
    response = llm_output['result']
    logging.info(pprint.pprint(response))
    forecasts = chat.msg_to_obj(response, delimiters=('[',']'))
    forecasts_hash = hash(str(forecasts))
    forecasts_start = list(forecasts_data[forecasts_data['id'] == todo].sort_values(by='time', ascending=False)['time'])[0]
    forecast_table = []
    for forecast in forecasts:
      forecast_table.append({
          'model': config.gpt_model,
          'id': todo,
          'forecast_time': forecasts_start + datetime.timedelta(hours=forecast['forecast']),
          'time': forecasts_start,
          'trans_time': datetime.datetime.now().isoformat(),
          'hash': forecasts_hash,
          'lat': forecast['lat'],
          'lon': forecast['lon'],
          'int': float(forecast['wind_speed'])
      })
    # process database and SQL for archiving forecasts
    engine = db.get_engine()
    metadata = MetaData()
    metadata.reflect(bind=engine)
    table = metadata.tables[config.forecasts_archive_table]
    db.query(q = (table.insert(), forecast_table), write = True)
    # process database and SQL for live forecasts
    engine = db.get_engine()
    metadata = MetaData()
    metadata.reflect(bind=engine)
    table_name = config.forecasts_live_table
    table = metadata.tables[table_name]
    db.query(q = (table.insert(), forecast_table), write = True)
    return False

