import pandas as pd
from pathlib import Path
import time
from src.utils.logger import get_logger
from src.storage.write_duckdb import write_to_duckdb, append_to_duckdb

logger = get_logger(__name__)

HISTORICAL_SEASONS = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']
CURRENT_SEASON = '2526'

def get_results(season):

    url = f'https://www.football-data.co.uk/mmz4281/{season}/E0.csv'
    results = pd.read_csv(url)

    # keep relevant columns
    columns_to_keep = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'HTHG', 'HTAG', 
                       'HTR', 'Referee', 'HS', 'AS', 'HST', 'AST', 'HF', 'AF', 'HC', 'AC', 'HY', 
                       'AY', 'HR', 'AR']
    results = results[columns_to_keep]

    results["match_id"] = (
        results["Date"].astype(str) +
        results["HomeTeam"] +
        results["AwayTeam"]
    )

    results['season'] = season
    
    append_to_duckdb(results, layer='bronze', table='fixtures', key='match_id')
    logger.info(f"saved {season} data")

def run_ingestion(mode='current'):
    if mode == 'historical':
        logger.info("Starting historical backfill")
        for season in HISTORICAL_SEASONS:
            get_results(season)
            time.sleep(2)
    else:
        logger.info(f"Running update for season {CURRENT_SEASON}")
        get_results(CURRENT_SEASON)

if __name__ == '__main__':
    run_ingestion()
