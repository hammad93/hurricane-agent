import pandas as pd

def transform_data(data):
    '''
    Parameters
    ----------
    data
    '''
    return pd.DataFrame(data)

def create_report(data):
    '''
    data is based on this query or similar
    SELECT * FROM ingest_hash
    WHERE time >= NOW() - INTERVAL '24 hours';
    '''
    result = {
        'BODY_TEXT': None,
        'BODY_HTML': None,
        'RECIPIENTS': 'daily@fluids.ai',
        'SUBJECT': 'fluids hurricane agent: Daily Reports'
    }
    return result