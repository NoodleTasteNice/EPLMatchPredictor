from thefuzz import process
import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger
from src.storage.write_duckdb import append_to_duckdb
from src.storage.read_duckdb import read_from_duckdb

logger = get_logger(__name__)

historical_seasons = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']
current_season = '2526'

def map_team_names(fixtures_df, stadiums_df):

    manual_overrides = {
    'Man United': 'Manchester United',
    'Man City': 'Manchester City',
    }

    stadium_teams = stadiums_df['Team'].tolist()
    
    def find_best_match(team_name):
        if team_name in manual_overrides:
            return manual_overrides[team_name]
        
        match, score = process.extractOne(team_name, stadium_teams)
        if score >= 80:  
            return match
        logger.warning(f"low confidence match: '{team_name}' to '{match}' (score: {score})")
        return None 
    
    fixtures_df['mapped_home_team'] = fixtures_df['HomeTeam'].apply(find_best_match)
    fixtures_df['mapped_away_team'] = fixtures_df['AwayTeam'].apply(find_best_match)

    return fixtures_df

def join_venue(fixtures_df, stadiums_df):
    # only keep relevant columns from stadiums df
    stadiums_df = stadiums_df[['Team', 'Name', 'Latitude', 'Longitude']]

    result = fixtures_df.merge(
        stadiums_df,
        left_on='mapped_home_team',
        right_on='Team',
        how='left'
    )

    unmatched = result[result['mapped_home_team'].isna()]
    if not unmatched.empty:
        logger.error(f"{len(unmatched)} teams with no match: {unmatched['HomeTeam'].tolist()}")

    result.drop(['Team'], axis=1, inplace=True)
    
    return result

def rename_columns(df):
    column_renaming = {
        'HomeTeam': 'home_team',
        'AwayTeam': 'away_team',
        'FTHG': 'ft_home_goals',
        'FTAG': 'ft_away_goals',
        'FTR': 'ft_result',
        'HTHG': 'ht_home_goals',
        'HTAG': 'ht_away_goals',
        'HTR': 'ht_result',
        'HS': 'home_shots',
        'AS': 'away_shots',
        'HST': 'home_sot',
        'AST': 'away_sot',
        'HC': 'home_corners',
        'AC': 'away_corners',
        'HF': 'home_fouls',
        'AF': 'away_fouls',
        'HY': 'home_yellows',
        'AY': 'away_yellows',
        'HR': 'home_reds',
        'AR': 'away_reds',
        'Latitude': 'latitude',
        'Longitude': 'longitude',
        'Name': 'stadium_name',
        'mapped_away_team': 'away_team_alt',
        'mapped_home_team': 'home_team_alt',
        'Referee': 'referee'
    }
    df = df.rename(columns=column_renaming)
    return df

def standardise_dates(df):
    # standardise with weather data to YYYY-MM-DD
    df['match_date'] = pd.to_datetime(df['Date'], dayfirst=True)
    df = df.drop(columns=['Date'])
    return df

def clean_season(season, stadiums_df):
    logger.info(f"cleaning fixtures for {season} season")

    df = read_from_duckdb(layer='bronze', table='fixtures', partition='season', partition_val=season)

    # map team names
    df = map_team_names(df, stadiums_df)

    # rename columns 
    df = rename_columns(df)

    # standardise dates
    df = standardise_dates(df)

    df['match_id'] = df['match_date'].dt.strftime('%Y-%m-%d') + '_' + df['home_team_alt'] + '_' + df['away_team_alt']
    target_order = [
        'home_team', 'away_team', 'ft_home_goals', 'ft_away_goals', 
        'ft_result', 'ht_home_goals', 'ht_away_goals', 'ht_result', 
        'referee', 'home_shots', 'away_shots', 'home_sot', 
        'away_sot', 'home_fouls', 'away_fouls', 'home_corners', 
        'away_corners', 'home_yellows', 'away_yellows', 'home_reds', 
        'away_reds', 'home_team_alt', 'away_team_alt', 'match_date', 
        'season', 'match_id'
    ]

    # Reorder before saving
    df = df[target_order]

    append_to_duckdb(df, layer="silver", table="fixtures", key='match_id')
    logger.info(f"saved to duckdb")

def run(mode='current'):
    stadiums_df = read_from_duckdb(layer='bronze', table='stadiums')
    seasons = historical_seasons if mode == 'historical' else [current_season]

    for season in seasons:
        clean_season(season, stadiums_df)

if __name__ == '__main__':
    run()
