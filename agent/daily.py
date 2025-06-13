import pandas as pd
import datetime
import logging
import markdown

def transform_data(data):
    '''
    Parameters
    ----------
    data
    '''
    return data.to_dict(orient='records')

def unit_tests(tests):
    results = tests()
    logging.info(results)
    if False in [test[0] for test in results]:
      return False, "❌"
    else:
      return True, "✅"

def create_report(data, tests, chat, prompt):
    '''
    Parameters
    ----------
    data pandas.DataFrame
      - Based on this PostgreSQL query or similar
      - SELECT * FROM ingest_hash WHERE time >= NOW() - INTERVAL '24 hours';
    tests Object
      - A Python function (Object) that runs unit tests with no input
    chat Object
      - A Python function (Object) that inputs 'message' and returns the response
      from the LLM
    prompt String Template
      - This template takes in the data after it's processed and generates a report
      from the LLM.
    '''
    message = prompt.substitute(daily_data=transform_data(data), timestamp=datetime.datetime.now())
    logging.info(message)
    llm_output = chat(message)
    logging.info(llm_output)
    BODY_TEXT = llm_output['result']
    BODY_HTML = markdown.markdown(BODY_TEXT)
    test_results = unit_tests(tests)
    result = {
        'BODY_TEXT': BODY_TEXT,
        'BODY_HTML': BODY_HTML,
        'RECIPIENTS': 'daily@fluids.ai',
        'SUBJECT': f'fluids hurricane agent: Daily Reports. Unit Tests: {test_results[1]}'
    }
    return result