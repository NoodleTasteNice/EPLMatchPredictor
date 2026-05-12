import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger
from src.storage.read_duckdb import read_from_duckdb
from src.features.feature_calculation import create_features, get_h2h
from src.storage.save_to_schema import save_to_star_schema
from src.storage.read_duckdb import get_db_path

logger = get_logger(__name__)

HISTORICAL_SEASONS = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']
CURRENT_SEASON = '2526'

ROLLING_COLS = [
    'home_rolling_points', 'away_rolling_points',
    'home_rolling_goals', 'away_rolling_goals',
    'home_rolling_sot', 'away_rolling_sot'
]

COLS_TO_DROP = ['stadium_name', 'latitude', 'longitude', 'ft_result', 'ht_result', 'capacity', 'weather_key', 'team']

def load_season(season: str) -> pd.DataFrame:
    fixtures_df = read_from_duckdb(layer="silver", table="fixtures", partition='season', partition_val=season)
    weather_df = read_from_duckdb(layer="bronze", table="weather", partition='season', partition_val=season)
    stadiums_df = read_from_duckdb(layer='silver', table='stadiums')
    weather_df['match_date'] = pd.to_datetime(weather_df['match_date']).astype('datetime64[ns]')   

    merged = fixtures_df.merge(stadiums_df, left_on='home_team_alt', right_on='team', how='left')
    merged = merged.merge(weather_df, on=['match_date', 'latitude', 'longitude', 'season'], how='left')
    
    missing = merged['temp_max'].isna().sum()
    if missing > 0:
        logger.warning(f"Season {season}: {missing} fixtures missing weather data")

    return merged

def build_season_features(season: str) -> pd.DataFrame:
    df = load_season(season)
    df = df.sort_values('match_date').reset_index(drop=True)
    df = create_features(df)
    df[ROLLING_COLS] = df[ROLLING_COLS].fillna(0)
    df['total_goals'] = df['ft_home_goals'].astype(int) + df['ft_away_goals'].astype(int)
    df['result_encoded'] = df['ft_result'].map({'H': 1, 'D': 0, 'A': -1})
    return df

def build_matches(seasons: list[str]) -> pd.DataFrame:
    all_dfs = [build_season_features(season) for season in seasons]
    df = pd.concat(all_dfs)
    return df.sort_values('match_date').reset_index(drop=True)

def save_matches(df: pd.DataFrame):
    save_to_star_schema(df, str(get_db_path("gold")))

def run(mode: str = 'current'):
    if mode == 'historical':
        combined_df = build_matches(HISTORICAL_SEASONS)
        combined_df = get_h2h(combined_df)
        combined_df = combined_df.drop(columns = COLS_TO_DROP)
        save_matches(combined_df)

    else:
        historical_df = read_from_duckdb(layer="gold", table="matches")
        current_df = build_season_features(CURRENT_SEASON)
        combined_df = pd.concat([historical_df, current_df]).sort_values('match_date').reset_index(drop=True)
        combined_df = get_h2h(combined_df)
        combined_df = combined_df.drop(columns = COLS_TO_DROP)
        save_matches(combined_df[combined_df['season'] == CURRENT_SEASON].copy())

if __name__ == '__main__':
    run()



