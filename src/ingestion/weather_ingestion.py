import requests
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

def get_weather(lat, lon, match_date):
    date_str = match_date.strftime("%Y-%m-%d")

    if lat is None or lon is None:
        logger.warning(f"no location provided for match on {date_str}")
        return {
            "location": None,
            "match_date": date_str,
            "temp_min": None,
            "temp_max": None,
            "precipitation_mm": None,
            "windspeed_kmh": None,
        }
            
    # get weather for that date
    weather_url = "https://archive-api.open-meteo.com/v1/archive"
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str,
        "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum,windspeed_10m_max",
        "timezone": "Europe/London"
    }
        
    r = requests.get(weather_url, params=weather_params).json()
    
    return {
        "coordinates": (lat, lon),
        "match_date": date_str,
        "temp_min": r["daily"]["temperature_2m_min"][0],
        "temp_max": r["daily"]["temperature_2m_max"][0],
        "precipitation_mm": r["daily"]["precipitation_sum"][0],
        "windspeed_kmh": r["daily"]["windspeed_10m_max"][0],
    }
    
def get_all_historical_weather(season):
    res = []

    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    target_dir = root_dir / "data" / 'silver' / "mapped_fb_data" / f'season_{season}.csv'
    save_dir = root_dir / "data" / 'bronze' / "weather_data" / f'season_{season}.csv'
    save_dir.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(target_dir)
    print(f"read {season} file")
    for id, row in df.iterrows():
        home = row['HomeTeam']
        away = row['AwayTeam']
        lat = row['Latitude']
        lon = row['Longitude']
        date = pd.to_datetime(row['Date'], dayfirst=True)
        print(f'processing {home} vs {away} on {date}')

        # get the weather for the location
        res.append(get_weather(lat, lon, date))
        time.sleep(0.1)
    
    weather_df = pd.DataFrame(res)
    weather_df.to_csv(save_dir, index=False)
    logger.info(f"saved weather data for {season} season")

if __name__ == '__main__':
    seasons = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']
    for season in seasons:
        get_all_historical_weather(season)