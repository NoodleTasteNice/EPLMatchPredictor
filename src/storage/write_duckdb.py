import duckdb
import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)

def get_db_path(layer: str) -> Path:
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    db_dir = root_dir / "data" / layer
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / f"{layer}_football.db"

def write_to_duckdb(df: pd.DataFrame, layer: str, table: str, partition_col: str, partition_val: str):
    db_path = get_db_path(layer)
    with duckdb.connect(str(db_path)) as con:
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} AS
            SELECT * FROM df WHERE FALSE
        """)
        old_count = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {partition_col} = ?", [partition_val]).fetchone()[0]
        con.execute(f"DELETE FROM {table} WHERE {partition_col} = ?", [partition_val])
        con.execute(f"INSERT INTO {table} SELECT * FROM df")
        new_count = len(df)
    
    logger.info(f"Updated {table}: {old_count} rows replaced with {new_count} rows.")

def append_to_duckdb(df: pd.DataFrame, layer: str, table: str, key: str = None):
    db_path = get_db_path(layer)

    with duckdb.connect(str(db_path)) as con:

        con.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} AS
            SELECT * FROM df WHERE FALSE
        """)

        old_rows = con.execute(f"""SELECT COUNT(*) from {table}""").fetchone()[0]

        if key == None:
            con.execute(f"INSERT INTO {table} SELECT * FROM df")
        else:
            # insert only new rows
            con.execute(f"""
                INSERT INTO {table}
                SELECT df.*
                FROM df
                LEFT JOIN {table} t ON df.{key} = t.{key}
                WHERE t.{key} IS NULL
            """)

        new_rows = con.execute(f"""SELECT COUNT(*) from {table}""").fetchone()[0]
        rows_added = new_rows - old_rows

    logger.info(f"Appended {rows_added} rows to {table}")