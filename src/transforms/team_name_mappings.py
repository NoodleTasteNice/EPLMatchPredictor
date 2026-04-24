# src/transforms/team_name_normaliser.py
from thefuzz import process
import pandas as pd
import logging
from src.utils.logger import get_logger
from pathlib import Path


logger = get_logger(__name__)

def map_team_names(fixtures_df, stadiums_df):

    stadium_teams = stadiums_df['Team'].tolist()
    
    def find_best_match(team_name):
        match, score = process.extractOne(team_name, stadium_teams)
        if score >= 80:  
            return match
        logger.warning(f"low confidence match: '{team_name}' to '{match}' (score: {score})")
        return None 
    
    fixtures_df['mapped_team'] = fixtures_df['HomeTeam'].apply(find_best_match)
    
    result = fixtures_df.merge(
        stadiums_df,
        left_on='mapped_team',
        right_on='Team',
        how='left'
    )
    
    return result

def run_mapping(season, stadiums_df):
    # get target directory 
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    target_file_dir = root_dir / "data" / 'bronze' / "raw_fb_data" / f"season_{season}.csv"

    # read file
    data = pd.read_csv(target_file_dir)

    # clean the file
    cleaned_data = map_team_names(data, stadiums_df)

    # save the file
    file_path = root_dir / "data" / 'silver' / "mapped_fb_data" / f"season_{season}.csv"
    cleaned_data.to_csv(file_path, index=False)
    
    print(f"saved {season} season data")

def clean_historical_data():
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    stadium_file_dir = root_dir / "data" / 'bronze' / "stadiums" / f"stadiums.csv"

    # read stadiums file
    stadiums_df = pd.read_csv(stadium_file_dir)

    # clean each season 
    seasons = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']

    for season in seasons:
        run_mapping(season, stadiums_df)

if __name__ == '__main__':
    clean_historical_data()
