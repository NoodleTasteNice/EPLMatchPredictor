import pandas as pd
import duckdb

def upsert_dim_team(con, df: pd.DataFrame):
    teams = pd.concat([
        df[['home_team_alt']].rename(columns={'home_team_alt': 'team_name'}),
        df[['away_team_alt']].rename(columns={'away_team_alt': 'team_name'})
    ]).drop_duplicates()

    con.execute("""
        INSERT INTO dim_team (team_name)
        SELECT team_name FROM teams
        WHERE team_name NOT IN (SELECT team_name FROM dim_team)
    """)
    print(f"dim_team: {con.execute('SELECT COUNT(*) FROM dim_team').fetchone()[0]} rows")

def upsert_dim_referee(con, df: pd.DataFrame):
    referees = df[['referee']].drop_duplicates().dropna()
    referees = referees.rename(columns={'referee': 'referee_name'})

    con.execute("""
        INSERT INTO dim_referee (referee_name)
        SELECT referee_name FROM referees
        WHERE referee_name NOT IN (SELECT referee_name FROM dim_referee)
    """)
    print(f"dim_referee: {con.execute('SELECT COUNT(*) FROM dim_referee').fetchone()[0]} rows")

def upsert_dim_date(con, df: pd.DataFrame):
    dates = pd.to_datetime(df['match_date']).dt.normalize().drop_duplicates().sort_values().reset_index(drop=True)

    date_df = pd.DataFrame({
        'date_id': dates.dt.strftime('%Y%m%d').astype(int),
        'full_date': dates,
        'year': dates.dt.year,
        'month': dates.dt.month,
        'month_name': dates.dt.strftime('%B'),
        'week': dates.dt.isocalendar().week.astype(int),
        'day_of_week': dates.dt.dayofweek + 1,
        'day_name': dates.dt.strftime('%A'),
        'is_weekend': dates.dt.dayofweek.isin([5, 6]),
        'quarter': dates.dt.quarter,
    })

    con.execute("""
        INSERT INTO dim_date
        SELECT * FROM date_df
        WHERE date_id NOT IN (SELECT date_id FROM dim_date)
    """)
    print(f"dim_date: {con.execute('SELECT COUNT(*) FROM dim_date').fetchone()[0]} rows")

def insert_fact_matches(con, df: pd.DataFrame):
    team_map = dict(zip(*con.execute("SELECT team_name, team_id FROM dim_team").df().values.T))
    referee_map = dict(zip(*con.execute("SELECT referee_name, referee_id FROM dim_referee").df().values.T))

    df['home_team_id'] = df['home_team'].map(team_map)
    df['away_team_id'] = df['away_team'].map(team_map)
    df['referee_id'] = df['referee'].map(referee_map)
    df['date_id'] = pd.to_datetime(df['match_date']).dt.strftime('%Y%m%d').astype(int)

    fact_cols = [
        'match_id', 'date_id', 'season',
        'home_team_id', 'away_team_id', 'referee_id',
        'ft_home_goals', 'ft_away_goals',
        'ht_home_goals', 'ht_away_goals',
        'home_shots', 'away_shots',
        'home_sot', 'away_sot',
        'home_fouls', 'away_fouls',
        'home_corners', 'away_corners',
        'home_yellows', 'away_yellows',
        'home_reds', 'away_reds',
        'temp_min', 'temp_max', 'precipitation_mm', 'windspeed_kmh',
        'home_rest_days', 'away_rest_days',
        'home_rolling_points', 'away_rolling_points',
        'home_rolling_goals', 'away_rolling_goals',
        'home_rolling_sot', 'away_rolling_sot',
        'total_goals', 'result_encoded',
        'h2h_home_win_rate'
    ]

    fact_df = df[fact_cols]
    con.execute("""
        INSERT INTO fact_matches
        SELECT * FROM fact_df
        WHERE match_id NOT IN (SELECT match_id FROM fact_matches)
    """)
    print(f"fact_matches: {con.execute('SELECT COUNT(*) FROM fact_matches').fetchone()[0]} rows")

def save_to_star_schema(df: pd.DataFrame, db_path: str):
    with duckdb.connect(db_path) as con:
        upsert_dim_team(con, df)
        upsert_dim_referee(con, df)
        upsert_dim_date(con, df)
        insert_fact_matches(con, df)