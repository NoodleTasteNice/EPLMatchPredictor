# dags/weekly_update_dag.py
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

CURRENT_SEASON = '2526'

def ingest_current():
    run_ingestion()

def clean_current():
    run_clean()

def ingest_weather_current():
    run_weather_ingestion()

def build_features_current():
    run_features()

def retrain():
    train()

with DAG(
    dag_id='weekly_update',
    start_date=datetime(2024, 1, 1),
    schedule='0 6 * * 1', 
    catchup=False,
    tags=['weekly'],
) as dag:

    t1 = PythonOperator(
        task_id='ingest_current_fixtures',
        python_callable=ingest_current,
    )

    t2 = PythonOperator(
        task_id='clean_current_fixtures',
        python_callable=clean_current,
    )

    t3 = PythonOperator(
        task_id='ingest_current_weather',
        python_callable=ingest_weather_current,
    )

    t4 = PythonOperator(
        task_id='build_current_features',
        python_callable=build_features_current,
    )

    t5 = PythonOperator(
        task_id='retrain_model',
        python_callable=retrain,
    )

    t1 >> t2 >> t3 >> t4 >> t5