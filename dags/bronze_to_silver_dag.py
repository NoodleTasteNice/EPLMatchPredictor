from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime
from src.processing.clean_fb_data import run as clean_fixtures

with DAG(
    dag_id='bronze_to_silver',
    start_date=datetime(2025, 8, 1),
    schedule_interval=None, 
    catchup=False,
) as dag:

    clean_fixtures_task = PythonOperator(
        task_id='clean_fixtures',
        python_callable=clean_fixtures,
        op_kwargs={'mode': 'current'}
    )

    trigger_silver_to_gold = TriggerDagRunOperator(
        task_id='trigger_silver_to_gold',
        trigger_dag_id='silver_to_gold',
        wait_for_completion=True,
    )

    clean_fixtures_task >> trigger_silver_to_gold