import requests
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

HISTORICAL_SEASONS = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']
CURRENT_SEASON = '2526'

def get_weather(lat, lon, match_date):
    date_str = match_date.strftime("%Y-%m-%d")

    if lat is None or lon is None:
        logger.warning(f"no location provided for match on {date_str}")
        return {
            "latitude": None,
            "longitude": None,
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
        "latitude": lat,
        "longitude": lon,
        "match_date": date_str,
        "temp_min": r["daily"]["temperature_2m_min"][0],
        "temp_max": r["daily"]["temperature_2m_max"][0],
        "precipitation_mm": r["daily"]["precipitation_sum"][0],
        "windspeed_kmh": r["daily"]["windspeed_10m_max"][0],
    }

def process_season_weather(season):
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent

    source_file = root_dir / "data" / "silver" / "cleaned_fb_data" / f"season_{season}.csv"
    save_path = root_dir / "data" / "bronze" / "weather_data" / f"season_{season}.csv"
    save_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source_file)

    # Incremental load, load existing weather if it exists to avoid re-fetching
    if save_path.exists():
        existing_weather_df = pd.read_csv(save_path)
        # create a unique key to check for existing records
        existing_keys = set(existing_weather_df['match_date'].astype(str) + 
                            existing_weather_df['home_team'].astype(str) +
                            existing_weather_df['away_team'].astype(str))
    else:
        existing_weather_df = pd.DataFrame()
        existing_keys = set()

    res = []
    new_count = 0

    for _, row in df.iterrows():
        date_obj = pd.to_datetime(row['match_date'])
        date_str = date_obj.strftime("%Y-%m-%d")
        home_team, away_team = row['home_team'], row['away_team']
        lat, lon = row['latitude'], row['longitude']
        
        key = f"{date_str}{home_team}{away_team}"
        
        if key in existing_keys:
            continue
        
        logger.info(f"Fetching weather for {row['home_team']} vs {row['away_team']} on ({date_str})")
        weather_data = get_weather(lat, lon, date_obj)
        
        if weather_data:
            res.append(weather_data)
            new_count += 1
            time.sleep(0.1) 

    if res:
        new_weather_df = pd.DataFrame(res)
        final_df = pd.concat([existing_weather_df, new_weather_df]).drop_duplicates()
        final_df.to_csv(save_path, index=False)
        logger.info(f"Added {new_count} rows for season {season}")
    else:
        logger.info(f"No new weather data for season {season}")

def run_weather_ingestion(mode='current'):
    if mode == 'historical':
        for season in HISTORICAL_SEASONS:
            process_season_weather(season)
    else:
        process_season_weather(CURRENT_SEASON)

if __name__ == '__main__':
    run_weather_ingestion()


