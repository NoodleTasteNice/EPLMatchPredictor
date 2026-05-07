# dags/historical_backfill_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
sys.path.insert(0, '/Users/regan/Desktop/EPLMatchPredictor')

from src.ingestion.fb_results_ingestion import run_ingestion
from src.transforms.clean_fb_data import run as run_clean
from src.ingestion.weather_ingestion import run_weather_ingestion
from src.transforms.feature_engineering import run as run_features
from src.modelling.train_model import train

HISTORICAL_SEASONS = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']

def ingest_historical():
    run_ingestion(mode='historical')

def clean_historical():
    run_clean(mode='historical')

def run_weather_ingestion_historical():
    run_weather_ingestion(mode='historical')

def build_features_historical():
    run_features(mode='historical')

with DAG(
    dag_id='historical_backfill',
    start_date=datetime(2024, 1, 1),
    schedule=None, 
    catchup=False,
    tags=['historical'],
) as dag:

    t1 = PythonOperator(
        task_id='ingest_historical_fixtures',
        python_callable=ingest_historical,
    )

    t2 = PythonOperator(
        task_id='clean_historical_fixtures',
        python_callable=clean_historical,
    )

    t3 = PythonOperator(
        task_id='ingest_historical_weather',
        python_callable=run_weather_ingestion_historical,
    )

    t4 = PythonOperator(
        task_id='build_historical_features',
        python_callable=build_features_historical,
    )

    t1 >> t2 >> t3 >> t4 