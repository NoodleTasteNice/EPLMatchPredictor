from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime
from src.ingestion.fb_results_ingestion import run_ingestion
from src.ingestion.weather_ingestion import run_weather_ingestion

with DAG(
    dag_id='ingestion',
    start_date=datetime(2025, 8, 1),
    schedule_interval='0 10 * * 2',
    catchup=False,
) as dag:

    ingest_fixtures_task = PythonOperator(
        task_id='ingest_fixtures',
        python_callable=run_ingestion,
        op_kwargs={'mode': 'current'}
    )

    ingest_weather_task = PythonOperator(
        task_id='ingest_weather',
        python_callable=run_weather_ingestion,
        op_kwargs={'mode': 'current'}
    )

    trigger_bronze_to_silver = TriggerDagRunOperator(
        task_id='trigger_bronze_to_silver',
        trigger_dag_id='bronze_to_silver',
        wait_for_completion=False,
    )

    ingest_fixtures_task >> ingest_weather_task >> trigger_bronze_to_silver