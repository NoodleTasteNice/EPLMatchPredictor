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

def read_from_duckdb(layer: str, table: str, partition: str = None, partition_val: str = None) -> pd.DataFrame:
    db_path = get_db_path(layer)
    with duckdb.connect(str(db_path)) as con:
        if partition:
            return con.execute(f"SELECT * FROM {table} WHERE {partition} = ?", [partition_val]).df()
        else:
            return con.execute(f"SELECT * FROM {table}").df()