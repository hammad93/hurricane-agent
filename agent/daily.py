import pandas as pd

def transform_data(data):
    '''
    Parameters
    ----------
    data
    '''
    return data.to_dict(orient='records')

def create_report(data, chat, prompt):
    '''
    Parameters
    ----------
    data pandas.DataFrame
      - Based on this PostgreSQL query or similar
      - SELECT * FROM ingest_hash WHERE time >= NOW() - INTERVAL '24 hours';
    chat Object
      - A Python function (Object) that inputs 'message' and returns the response
      from the LLM
    prompt String Template
      - This template takes in the data after it's processed and generates a report
      from the LLM.
    '''
    result = {
        'BODY_TEXT': None,
        'BODY_HTML': None,
        'RECIPIENTS': 'daily@fluids.ai',
        'SUBJECT': 'fluids hurricane agent: Daily Reports'
    }
    return result