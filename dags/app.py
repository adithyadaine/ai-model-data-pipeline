from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from typing import List, Dict, Any
from huggingface_hub import list_models
import requests
import logging  

# 1. DAG Configuration

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 20),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

# Create the DAG
dag = DAG(
    'huggingface_model_etl',
    default_args=default_args,
    description='ETL pipeline for Hugging Face models',
    schedule='@daily',
    catchup=False,
    tags=['etl', 'huggingface', 'postgres'],
)

# 2. EXTRACT: Fetch Data from Hugging Face
def extract_model_data(**kwargs):
    """
    EXTRACT PHASE: Pull raw model data from the hugging Face API.
    Returns the top 50 models by download count
    """
    print("EXTRACT PHASE: Fetching models from Hugging Face Hub")
    
    try:
        # Fetch latest 50 models sorted by last modified date
        models = list_models(sort="lastModified", direction=-1, limit=50, cardData=True)
        
        # Fetch top 50 models by download count
        # models = list_models(sort="downloads", direction=-1, limit=50)

        # Fetch latest 50 models by creation date
        # models = list_models(sort="created", direction=-1, limit=50)
        
        raw_models = [{
            "model_id": m.id,
            "author": m.author if m.author else None,
            "pipeline_tag": m.pipeline_tag if m.pipeline_tag else None,
            "tags": m.tags if m.tags else [],
            "last_modified": str(m.lastModified),
        } for m in models]
        
        # Push raw models to XCom for downstream tasks
        kwargs['ti'].xcom_push(key='raw_models', value=raw_models)
        print(f"EXTRACT COMPLETE: Retrieved {len(raw_models)} raw model records")
        return "Extract completed successfully"
    
    except Exception as e:
        print(f"Error in EXTRACT phase: {e}")
        kwargs['ti'].xcom_push(key='raw_models', value=[])
        return "Extract failed" 
    
# Create the extract task
extract_task = PythonOperator(
    task_id='extract_huggingface_models',
    python_callable=extract_model_data,
    dag=dag,
)
        
# 3. TRANSFORM: Process and Clean Data
def transform_model_data(**kwargs):
    """
    TRANSFORM PHASE: Clean and structure the raw model data.
    """
    ti = kwargs['ti']
    raw_models = ti.xcom_pull(key='raw_models', task_ids='extract_huggingface_models') or []
    print(f"TRANSFORM PHASE: Processing {len(raw_models)} raw records")
    
    transformed_data = []
    seen = set()
    
    # Process ALL models first
    for m in raw_models:
        mid = m.get('model_id')
        if not mid or mid in seen:
            continue
        seen.add(mid)
        
        transformed_data.append({
            "model_id": mid,
            "author": m.get('author') or 'N/A',
            "pipeline_tag": m.get('pipeline_tag') or 'N/A',
            "tags": m.get('tags') or [],
            "last_modified": m.get('last_modified'),
        })
    
    ti.xcom_push(key='transformed_models', value=transformed_data)
    print(f"TRANSFORM COMPLETE: Processed {len(transformed_data)} cleaned records")
    return "Transform completed successfully"
    
# Create the transform task
transform_task = PythonOperator(
    task_id='transform_model_data',
    python_callable=transform_model_data,
    dag=dag,
)

# 4. LOAD: Insert Data into Postgres
def load_to_postgres(**kwargs):
    """
    LOAD PHASE: Insert the transformed model data into a Postgres database.
    """
    ti = kwargs['ti']
    transformed_data = ti.xcom_pull(key='transformed_models', task_ids='transform_model_data')
    
    if not transformed_data:
        print("LOAD ERROR: No transformed data to load")
        return "No data to load"
    
    postgres_hook = PostgresHook(postgres_conn_id='model_connection')
    
    # Create table if not exists
    create_table_query = """
    CREATE TABLE IF NOT EXISTS ai_models (
        model_id VARCHAR(255) PRIMARY KEY,
        author VARCHAR(255),
        pipeline_tag VARCHAR(255),
        tags TEXT[],
        last_modified TIMESTAMP
    );
    """
    postgres_hook.run(create_table_query)
    
    # Insert data
    insert_query = """
    INSERT INTO ai_models (model_id, author, pipeline_tag, tags, last_modified)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (model_id) DO UPDATE
    SET author = EXCLUDED.author,
        pipeline_tag = EXCLUDED.pipeline_tag,
        tags = EXCLUDED.tags,
        last_modified = EXCLUDED.last_modified;
    """
    try:
        for model in transformed_data:
            postgres_hook.run(insert_query, parameters=(
                model['model_id'],
                model['author'],
                model['pipeline_tag'],
                model['tags'],
                model['last_modified']
            ))
            
        print(f"LOAD COMPLETE: Loaded {len(transformed_data)} records.")
        return f"loaded {len(transformed_data)} models"
    
    except Exception as e:
        print(f"Error in LOAD phase: {e}")
        raise
    
# Create the load task
load_task = PythonOperator(
    task_id='load_to_postgres',
    python_callable=load_to_postgres,
    dag=dag,
)

# 5. ETL Task Dependencies
    
# Extract must run before transform and load
extract_task >> transform_task >> load_task