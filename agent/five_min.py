import pandas as pd
import datetime
import logging

def create_report(data, tests, chat, prompts, db):
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
    forecasted = set(data['forecasts']['id'])
    todos = [id for id in storm_ids if id not in forecasted]
    todo = todos[0] # only do one at a time
    for p in prompts:
        if p[1]['storm_id'] == todo:
            prompt = p[0]
    logging.info(prompt)
    llm_output = chat(prompt)
    logging.info(llm_output)
    return False

