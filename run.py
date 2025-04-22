from typing import Union, List
import uvicorn
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import config
import db
import chatgpt
import pandas as pd
import traceback
import os
import redis
import test
import json
import httpx
import gc
import predict

app = FastAPI(
    title="fluids API",
    description="A 100% independent and non-profit weather API providing weather data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root(request: Request):
    return await reverse_proxy(config.local_django_url, request)

@app.get("/chat")
async def chat(request: Request):
    return await reverse_proxy(config.local_openwebui_url, request)

@app.get("/live-storms")
async def get_live_storms():
    """
    Retrieve live tropical storm data.

    Returns:
        list: A list of dictionaries containing the current live tropical storms
              with keys: id, time, lat, lon, and int.
    """
    gc.collect()
    data = db.query("SELECT * FROM hurricane_live")
    data['time'] = data['time'].astype(str)  # Convert 'time' column to string
    data = data.rename(columns={'int': 'wind_speed'})  # Rename 'int' column to 'wind_speed'
    storms = data.to_dict(orient="records")
    for storm in storms:
        # wind speed is in knots
        storm['wind_speed_mph'] = round(int(storm['wind_speed']) * 1.15078, 2)
        storm['wind_speed_kmph'] = round(int(storm['wind_speed']) * 1.852, 2)
    return storms

@app.get('/forecasts')
async def forecasts():
    '''
    Generates a linear model that is quick enough to do it in the API call.
    Reference predict.forecast_storm_with_great_circle
    '''
    gc.collect()
    data = db.query("SELECT * FROM forecasts_live")
    data['time'] = data['time'].astype(str)  # Convert 'time' column to string
    data = data.rename(columns={'int': 'wind_speed'})  # Rename 'int' column to 'wind_speed'
    result = {storm : data[data['id'] == storm].to_dict(orient='records') for storm in set(data['id'])}
    return result

async def reverse_proxy(local_url: str, request: Request):
    print(request.headers.get("Referer"))
    # Determine if the request is for a static file
    if request.url.path.startswith("/static/"):
        # Construct the URL for the static file
        file_path = request.url.path[len("/static/"):]  # Strip the "/static/" prefix
        target_url = f"http://localhost:8000/static/{file_path}"
    else:
        # Construct the full URL for the request
        target_url = f"{local_url}{request.url.path}"
    
    # Forward the request with the same query parameters and headers
    headers = request.headers.copy()
    async with httpx.AsyncClient() as client:
        response = await client.get(target_url, params=request.query_params, headers=headers)
    
    # Return the response from the local service
    return Response(content=response.content, media_type=response.headers.get('content-type'))

if __name__ == "__main__":
    # set things up according to tests
    test.setup()
    uvicorn.run(app, host="0.0.0.0", port=443, workers=1,
                ssl_keyfile='/root/privkey.pem', ssl_certfile='/root/fullchain.pem')
