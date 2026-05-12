import duckdb
import pandas as pd
from pathlib import Path

def get_db_path():
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    return root_dir / "data" / "gold" / "gold_football.db"

def build_dim_team(con, matches_df: pd.DataFrame):
    teams = pd.concat([
        matches_df[['home_team_alt']].rename(columns={'home_team_alt': 'team_name'}),
        matches_df[['away_team_alt']].rename(columns={'away_team_alt': 'team_name'})
    ]).drop_duplicates().reset_index(drop=True)

    teams.index = teams.index + 1
    teams.index.name = 'team_id'
    teams = teams.reset_index()

    con.execute("""
        CREATE TABLE IF NOT EXISTS dim_team (
            team_id   INTEGER PRIMARY KEY,
            team_name VARCHAR NOT NULL
        )
    """)
    con.execute("""
        INSERT INTO dim_team
        SELECT team_id, team_name FROM teams
        WHERE team_name NOT IN (SELECT team_name FROM dim_team)
    """)
    print(f"dim_team: {con.execute('SELECT COUNT(*) FROM dim_team').fetchone()[0]} rows")

def build_dim_referee(con, matches_df: pd.DataFrame):
    referees = matches_df[['referee']].drop_duplicates().dropna().reset_index(drop=True)
    referees.index = referees.index + 1
    referees.index.name = 'referee_id'
    referees = referees.reset_index().rename(columns={'referee': 'referee_name'})

    con.execute("""
        CREATE TABLE IF NOT EXISTS dim_referee (
            referee_id   INTEGER PRIMARY KEY,
            referee_name VARCHAR NOT NULL
        )
    """)
    con.execute("""
        INSERT INTO dim_referee
        SELECT referee_id, referee_name FROM referees
        WHERE referee_name NOT IN (SELECT referee_name FROM dim_referee)
    """)
    print(f"dim_referee: {con.execute('SELECT COUNT(*) FROM dim_referee').fetchone()[0]} rows")

def build_dim_date(con, matches_df: pd.DataFrame):
    dates = pd.to_datetime(matches_df['match_date']).dt.normalize().drop_duplicates().sort_values().reset_index(drop=True)

    date_df = pd.DataFrame({
        'date_id': dates.dt.strftime('%Y%m%d').astype(int),
        'full_date': dates,
        'year': dates.dt.year,
        'month': dates.dt.month,
        'month_name': dates.dt.strftime('%B'),
        'week': dates.dt.isocalendar().week.astype(int),
        'day_of_week': dates.dt.dayofweek + 1,  # 1=Monday, 7=Sunday
        'day_name': dates.dt.strftime('%A'),
        'is_weekend': dates.dt.dayofweek.isin([5, 6]),
        'quarter': dates.dt.quarter,
    })

    con.execute("""
        CREATE TABLE IF NOT EXISTS dim_date (
            date_id      INTEGER PRIMARY KEY,
            full_date    TIMESTAMP,
            year         INTEGER,
            month        INTEGER,
            month_name   VARCHAR,
            week         INTEGER,
            day_of_week  INTEGER,
            day_name     VARCHAR,
            is_weekend   BOOLEAN,
            quarter      INTEGER
        )
    """)
    con.execute("""
        INSERT INTO dim_date
        SELECT * FROM date_df
        WHERE date_id NOT IN (SELECT date_id FROM dim_date)
    """)
    print(f"dim_date: {con.execute('SELECT COUNT(*) FROM dim_date').fetchone()[0]} rows")

def build_fact_matches(con, matches_df: pd.DataFrame):
    team_map = con.execute("SELECT team_name, team_id FROM dim_team").df()
    team_map = dict(zip(team_map['team_name'], team_map['team_id']))

    referee_map = con.execute("SELECT referee_name, referee_id FROM dim_referee").df()
    referee_map = dict(zip(referee_map['referee_name'], referee_map['referee_id']))

    matches_df['home_team_id'] = matches_df['home_team_alt'].map(team_map)
    matches_df['away_team_id'] = matches_df['away_team_alt'].map(team_map)
    matches_df['referee_id'] = matches_df['referee'].map(referee_map)
    matches_df['date_id'] = pd.to_datetime(matches_df['match_date']).dt.strftime('%Y%m%d').astype(int)

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

    fact_df = matches_df[fact_cols]

    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_matches AS
        SELECT * FROM fact_df WHERE FALSE
    """)
    con.execute("""
        INSERT INTO fact_matches
        SELECT * FROM fact_df
        WHERE match_id NOT IN (SELECT match_id FROM fact_matches)
    """)
    print(f"fact_matches: {con.execute('SELECT COUNT(*) FROM fact_matches').fetchone()[0]} rows")

def run():
    db_path = get_db_path()
    print(f"Connecting to {db_path}")

    with duckdb.connect(str(db_path)) as con:
        matches_df = con.execute("SELECT * FROM matches").df()
        print(f"Loaded {len(matches_df)} rows from matches")

        build_dim_team(con, matches_df)
        build_dim_referee(con, matches_df)
        build_dim_date(con, matches_df)
        build_fact_matches(con, matches_df)

        print("\nStar schema built successfully:")
        print(f"  dim_team:     {con.execute('SELECT COUNT(*) FROM dim_team').fetchone()[0]} teams")
        print(f"  dim_referee:  {con.execute('SELECT COUNT(*) FROM dim_referee').fetchone()[0]} referees")
        print(f"  dim_date:     {con.execute('SELECT COUNT(*) FROM dim_date').fetchone()[0]} dates")
        print(f"  fact_matches: {con.execute('SELECT COUNT(*) FROM fact_matches').fetchone()[0]} matches")

if __name__ == '__main__':
    run()