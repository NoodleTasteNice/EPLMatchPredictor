import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)

def calculate_rest_days(df):
    df = df.sort_values('match_date').reset_index(drop=True)
    df['match_date'] = pd.to_datetime(df['match_date'])

    # stack home and away into one long table
    home_games = df[['match_date', 'home_team']].rename(columns={'home_team': 'team'})
    away_games = df[['match_date', 'away_team']].rename(columns={'away_team': 'team'})
    all_games = pd.concat([home_games, away_games]).sort_values('match_date').reset_index(drop=True)

    # days since last game regardless of home or away
    all_games['rest_days'] = (
        all_games.groupby('team')['match_date']
        .transform(lambda x: x.diff().dt.days)
    )

    # first game of season defaults to 7
    all_games['rest_days'] = all_games['rest_days'].fillna(7)

    # merge back for home team
    home_rest = all_games.rename(columns={'team': 'home_team', 'rest_days': 'home_rest_days'})[['match_date', 'home_team', 'home_rest_days']]
    away_rest = all_games.rename(columns={'team': 'away_team', 'rest_days': 'away_rest_days'})[['match_date', 'away_team', 'away_rest_days']]

    df = df.merge(home_rest, on=['match_date', 'home_team'], how='left')
    df = df.merge(away_rest, on=['match_date', 'away_team'], how='left')

    return df

def calculate_rolling_form(df):
    df = df.sort_values('match_date').reset_index(drop=True)

    # points from each team's perspective
    # home team: H=3, D=1, A=0
    # away team: A=3, D=1, H=0
    home_games = df[['match_date', 'home_team', 'ft_result', 'ft_home_goals', 'home_sot']].copy()
    home_games.columns = ['match_date', 'team', 'ft_result', 'goals_scored', 'sot']
    home_games['team_points'] = home_games['ft_result'].map({'H': 3, 'D': 1, 'A': 0})

    away_games = df[['match_date', 'away_team', 'ft_result', 'ft_away_goals', 'away_sot']].copy()
    away_games.columns = ['match_date', 'team', 'ft_result', 'goals_scored', 'sot']
    away_games['team_points'] = away_games['ft_result'].map({'H': 0, 'D': 1, 'A': 3})

    all_games = pd.concat([home_games, away_games]).sort_values('match_date').reset_index(drop=True)

    # rolling points sum over last 5 games 
    all_games['rolling_points'] = (
        all_games.groupby('team')['team_points']
        .transform(lambda x: x.shift(1).rolling(5, min_periods=1).sum())
    )

    # rolling goals over last 5 games
    all_games['rolling_goals'] = (
        all_games.groupby('team')['goals_scored']
        .transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    )

    # rolling shots on target over last 5 games
    all_games['rolling_sot'] = (
        all_games.groupby('team')['sot']
        .transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    )

    # merge back for home team
    home_form = all_games.rename(columns={
        'team': 'home_team',
        'rolling_points': 'home_rolling_points',
        'rolling_goals': 'home_rolling_goals',
        'rolling_sot': 'home_rolling_sot'
    })[['match_date', 'home_team', 'home_rolling_points', 'home_rolling_goals', 'home_rolling_sot']]

    # merge back for away team
    away_form = all_games.rename(columns={
        'team': 'away_team',
        'rolling_points': 'away_rolling_points',
        'rolling_goals': 'away_rolling_goals',
        'rolling_sot': 'away_rolling_sot'
    })[['match_date', 'away_team', 'away_rolling_points', 'away_rolling_goals', 'away_rolling_sot']]

    df = df.merge(home_form, on=['match_date', 'home_team'], how='left')
    df = df.merge(away_form, on=['match_date', 'away_team'], how='left')

    return df

def create_features(df):
    # sort by date for rolling calculations
    df = df.sort_values('match_date').reset_index(drop=True)

    df = calculate_rest_days(df)
    df = calculate_rolling_form(df)

    rolling_cols = [
    'home_rolling_points',
    'away_rolling_points', 
    'home_rolling_goals',
    'away_rolling_goals',
    'home_rolling_sot',
    'away_rolling_sot'
]
    df[rolling_cols] = df[rolling_cols].fillna(0)

    df['total_goals'] = df['ft_home_goals'].astype(int) + df['ft_away_goals'].astype(int)

    logger.info("feature engineering complete")
    return df

def get_h2h(all_seasons_df):
    # calculate h2h on the full historical dataset
    df = all_seasons_df.sort_values('match_date').reset_index(drop=True)

    # create same key regardless of who is home or away
    df['h2h_key'] = df.apply(
        lambda x: '_'.join(sorted([x['home_team'], x['away_team']])), axis=1
    )

    # get the first team alphabetically in each fixture
    df['team_a'] = df['h2h_key'].str.split('_').str[0]

    # number of wins team a has regardless of whether team a is home or not 
    df['team_a_win'] = (
        ((df['home_team'] == df['team_a']) & (df['ft_result'] == 'H')) |
        ((df['away_team'] == df['team_a']) & (df['ft_result'] == 'A'))
    ).astype(int)

    # get win rate for team a
    df['h2h_team_a_win_rate'] = (
        df.groupby('h2h_key')['team_a_win']
        .transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
    )

    # express team a win rate from current home teams perspective
    # if home team is a then use same win rate else use the inverse
    df['h2h_home_win_rate'] = df.apply(
        lambda x: x['h2h_team_a_win_rate'] if x['home_team'] == x['team_a']
        else 1 - x['h2h_team_a_win_rate'],
        axis=1
    )

    # fill any nulls with average
    df['h2h_home_win_rate'] = df['h2h_home_win_rate'].fillna(0)
    df['h2h_team_a_win_rate'] = df['h2h_team_a_win_rate'].fillna(0)

    df = df.drop(columns=['h2h_key', 'team_a_win', 'team_a', 'h2h_team_a_win_rate'])

    return df