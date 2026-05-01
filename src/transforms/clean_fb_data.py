from thefuzz import process
import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)

historical_seasons = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']
current_season = '2526'
manual_overrides = {
    'Man United': 'Manchester United',
    'Man City': 'Manchester City',
}


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
    'Name': 'name'
}

def map_team_names(fixtures_df, stadiums_df):

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
    df = df.rename(columns=column_renaming)
    return df

def standardise_dates(df):
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    df = df.rename(columns={'Date': 'match_date'})
    return df

def clean_season(season, stadiums_df):
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent

    source_path = root_dir / "data" / "bronze" / "raw_fb_data" / f"season_{season}.csv"
    save_path = root_dir / "data" / "silver" / "cleaned_fb_data" / f"season_{season}.csv"
    save_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"cleaning fixtures for {season} season")

    df = pd.read_csv(source_path)

    # map team names and join stadium
    df = map_team_names(df, stadiums_df)

    # rename columns 
    df = rename_columns(df)

    # standardise dates
    df = standardise_dates(df)

    df.to_csv(save_path, index=False)
    logger.info(f"saved to silver/cleaned_fb_data/season_{season}.csv")

def run(mode='current'):
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    stadium_path = root_dir / "data" / "bronze" / "stadiums" / "stadiums.csv"
    stadiums_df = pd.read_csv(stadium_path)

    seasons = historical_seasons if mode == 'historical' else [current_season]

    for season in seasons:
        clean_season(season, stadiums_df)

if __name__ == '__main__':
    run()