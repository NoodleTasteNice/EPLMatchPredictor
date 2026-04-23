import pandas as pd
from pathlib import Path
import time

def get_results(season):

    url = f'https://www.football-data.co.uk/mmz4281/{season}/E0.csv'
    results = pd.read_csv(url)

    # keep relevant columns
    columns_to_keep = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'HTHG', 'HTAG', 
                       'HTR', 'Referee', 'HS', 'AS', 'HST', 'AST', 'HF', 'AF', 'HC', 'AC', 'HY', 
                       'AY', 'HR', 'AR']
    results = results[columns_to_keep]

    # rename for clarity
    results = results.rename(columns={
    'FTHG': 'FT Home Goals',
    'FTAG': 'FT Away Goals',
    'FTR': 'FT Result',
    'HTHG': 'HT Home Goals',
    'HTAG': 'HT Away Goals',
    'HTR': 'HT Result',
    'HS': 'Home Shots',
    'AS': 'Away Shots',
    'HST': 'Home SoT',
    'AST': 'Away SoT',
    'HC': 'Home Corners',
    'AC': 'Away Corners',
    'HF': 'Home Fouls',
    'AF': 'Away Fouls',
    'HY': 'Home Yellows',
    'AY': 'Away Yellows',
    'HR': 'Home Reds',
    'AR': 'Away Reds'
    })

    # get target directory 
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    save_dir = root_dir / "data" / "fb_data"

    # create the directory if it doesn't exist
    save_dir.mkdir(parents=True, exist_ok=True)

    # save the file
    file_path = save_dir / f"season_{season}.csv"
    results.to_csv(file_path, index=False)
    
    print(f"saved {season} data")

# # run once to get past 10 years of historical data
# seasons = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']

# for season in seasons:
#     get_results(season)
#     # sleep to avoid rate limits
#     time.sleep(6)

