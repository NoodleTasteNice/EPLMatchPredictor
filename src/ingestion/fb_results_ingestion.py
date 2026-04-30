import pandas as pd
from pathlib import Path
import time
from src.utils.logger import get_logger

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

    # get target directory 
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    save_dir = root_dir / "data" / 'bronze'/ "raw_fb_data"

    # create the directory if it doesn't exist
    save_dir.mkdir(parents=True, exist_ok=True)

    # save the file
    file_path = save_dir / f"season_{season}.csv"
    results.to_csv(file_path, index=False)
    
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
