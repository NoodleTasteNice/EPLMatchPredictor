import pandas as pd
from pathlib import Path
from src.storage.read_duckdb import read_from_duckdb
from src.storage.write_duckdb import append_to_duckdb

def migrate_stadiums_to_silver():
    stadiums_df = read_from_duckdb(layer="bronze", table="stadiums")

    stadiums_df = stadiums_df[['Team', 'Name', 'Capacity', 'Latitude', 'Longitude']].rename(columns={
        'Team': 'team',
        'Name': 'stadium_name',
        'Capacity': 'capacity',
        'Latitude': 'latitude',
        'Longitude': 'longitude'
    })

    append_to_duckdb(stadiums_df, layer="silver", table="stadiums")
    print(f"Migrated {len(stadiums_df)} stadiums to silver")

if __name__ == '__main__':
    migrate_stadiums_to_silver()