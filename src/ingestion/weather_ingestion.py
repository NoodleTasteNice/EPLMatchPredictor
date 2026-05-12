import requests
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
from src.utils.logger import get_logger
from src.storage.read_duckdb import read_from_duckdb
from src.storage.write_duckdb import append_to_duckdb
from src.processing.clean_fb_data import map_team_names, join_venue

logger = get_logger(__name__)

HISTORICAL_SEASONS = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']
CURRENT_SEASON = '2526'

def get_weather(lat, lon, date_str):

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
        "weather_key": f"{date_str}_{lat}_{lon}"
    }

def get_existing_keys(season):
    try:
        existing_df = read_from_duckdb(layer="bronze", table="weather", partition = 'season', partition_val = season)
        return set(existing_df['weather_key'].astype(str))
    except Exception as e:
        print(e)
        return set()
    
def process_season_weather(season: str):
    logger.info(f"Processing weather for season {season}")

    fixtures_df = read_from_duckdb(layer="bronze", table="fixtures", partition = 'season', partition_val = season)
    stadiums_df = read_from_duckdb(layer='bronze', table='stadiums')
    existing_keys = get_existing_keys(season)

    mapped_df = map_team_names(fixtures_df)
    combined_df = join_venue(mapped_df, stadiums_df)

    res = []
    for _, row in combined_df.iterrows():
        date_str = row['Date']
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        formatted_date = date_obj.strftime("%Y-%m-%d")
        lat, lon = row['Latitude'], row['Longitude']
        home_team = row['HomeTeam']
        away_team = row['AwayTeam']
        key = f"{formatted_date}_{lat}_{lon}"
        if key in existing_keys:
            continue

        logger.info(f"Fetching weather for {home_team} vs {away_team} on {date_str}")
        res.append(get_weather(lat, lon, formatted_date))
        time.sleep(0.1)

    if res:
        new_df = pd.DataFrame(res)
        new_df['season'] = season
        append_to_duckdb(new_df, layer="bronze", table="weather", key='weather_id')
        logger.info(f"Added {len(res)} new rows for season {season}")
    else:
        logger.info(f"No new weather data for season {season}")

def run_weather_ingestion(mode: str = 'current'):
    seasons = HISTORICAL_SEASONS if mode == 'historical' else [CURRENT_SEASON]
    for season in seasons:
        process_season_weather(season)

if __name__ == '__main__':
    run_weather_ingestion()

