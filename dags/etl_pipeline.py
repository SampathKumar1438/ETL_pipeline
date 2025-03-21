from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd

def extract():
    """Read CSV file and return a DataFrame."""
    df = pd.read_csv("/opt/airflow/dags/data/sales_data.csv")
    df.to_csv("/opt/airflow/dags/data/sales_data_cleaned.csv", index=False)
    print("Extracted data successfully!")

def transform():
    """Load and clean the extracted data."""
    df = pd.read_csv("/opt/airflow/dags/data/sales_data_cleaned.csv")
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df.to_csv("/opt/airflow/dags/data/sales_data_transformed.csv", index=False)
    print("Transformed data successfully!")

def load():
    """Load the transformed data into PostgreSQL via Airflow connection."""
    postgres_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = postgres_hook.get_conn()
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            product VARCHAR(50),
            price FLOAT,
            quantity INT,
            sale_date DATE
        )
    """)
    
    # Load data
    df = pd.read_csv("/opt/airflow/dags/data/sales_data_transformed.csv")
    for _, row in df.iterrows():
        cursor.execute(
            "INSERT INTO sales (product, price, quantity, sale_date) VALUES (%s, %s, %s, %s)",
            (row["product"], row["price"], row["quantity"], row["sale_date"])
        )
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Loaded data successfully!")

# Define Airflow DAG
default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 3, 22),
    "retries": 1,
}

dag = DAG(
    "etl_pipeline",
    default_args=default_args,
    schedule_interval="@daily",  # Run daily
    catchup=False
)

extract_task = PythonOperator(task_id="extract", python_callable=extract, dag=dag)
transform_task = PythonOperator(task_id="transform", python_callable=transform, dag=dag)
load_task = PythonOperator(task_id="load", python_callable=load, dag=dag)

extract_task >> transform_task >> load_task
