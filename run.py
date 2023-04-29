from typing import Union, List
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import config
import db
import hurricane_net_chatgpt
import pandas as pd

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


class StormData(BaseModel):
    id: str = Field(..., description="Storm ID")
    time: str = Field(..., description="ISO8601 timestamp")
    lat: float = Field(..., description="Latitude in decimal degrees")
    lon: float = Field(..., description="Longitude in decimal degrees")
    wind_speed: int = Field(..., description="Maximum sustained wind speed in knots")

@app.get("/live-storms", response_model=List[StormData])
async def get_live_storms() -> List[StormData]:
    """
    Retrieve live tropical storm data.

    Returns:
        list: A list of dictionaries containing the current live tropical storms
              with keys: id, time, lat, lon, and int.
    """
    data = db.query("SELECT * FROM hurricane_live")
    data['time'] = data['time'].astype(str)  # Convert 'time' column to string
    data = data.rename(columns={'int': 'wind_speed'})  # Rename 'int' column to 'wind_speed'
    storms = data.to_dict(orient="records")
    return storms

@app.get("/chatgpt_forecast_storm_live", response_model=List[StormData])
async def chatgpt_forecast_storm_live() -> List[StormData]:
    '''
    '''
    forecast = chatgpt.chatgpt_forecast_live()
    return forecast.to_dict(orient="records")


if __name__ == "__main__":
    # Set ChatGPT password
    passwords = pd.read_csv(config.credentials_dir)
    os.environ["OPENAI_API_KEY"] = passwords[passwords['user'] == 'openai'].iloc[0]['pass']
    uvicorn.run("run:app", host="0.0.0.0", port=1337, reload=True)
