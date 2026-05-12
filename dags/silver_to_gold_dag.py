from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from src.features.feature_engineering import run as build_features

with DAG(
    dag_id='silver_to_gold',
    start_date=datetime(2025, 8, 1),
    schedule_interval=None,  # only triggered by bronze_to_silver DAG
    catchup=False,
) as dag:

    build_features_task = PythonOperator(
        task_id='build_features',
        python_callable=build_features,
        op_kwargs={'mode': 'current'}
    )