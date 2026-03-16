"""
FinSight AI - SEC Filings Ingestion DAG
Triggers Lambda to fetch SEC filings for configured tickers.
Schedule: Daily at 6 AM UTC
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import boto3
import json

# Configuration
AWS_REGION = "us-east-1"
LAMBDA_FUNCTION = "finsight-ingest_sec"
TICKERS = ["AAPL", "MSFT", "GOOGL"]

def invoke_lambda(ticker, **context):
    """Invoke SEC ingestion Lambda for a ticker."""
    client = boto3.client('lambda', region_name=AWS_REGION)
    
    payload = {
        'ticker': ticker,
        'filing_types': ['10-K', '10-Q'],
        'limit': 5
    }
    
    print(f"Invoking {LAMBDA_FUNCTION} for {ticker}")
    print(f"Payload: {json.dumps(payload)}")
    
    response = client.invoke(
        FunctionName=LAMBDA_FUNCTION,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read().decode())
    print(f"Response: {json.dumps(result, indent=2)}")
    
    return result

def log_completion(**context):
    """Log pipeline completion."""
    print("=" * 50)
    print("SEC Ingestion Complete!")
    print(f"Tickers processed: {TICKERS}")
    print("=" * 50)

# DAG Definition
default_args = {
    'owner': 'finsight-ai',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='finsight_sec_ingestion',
    default_args=default_args,
    description='Ingest SEC filings via Lambda',
    schedule_interval='0 6 * * *',  # 6 AM UTC daily
    start_date=datetime(2026, 3, 1),
    catchup=False,
    tags=['finsight', 'ingestion', 'sec', 'production'],
) as dag:
    
    # Create a task for each ticker
    tasks = []
    for ticker in TICKERS:
        task = PythonOperator(
            task_id=f'ingest_{ticker.lower()}',
            python_callable=invoke_lambda,
            op_kwargs={'ticker': ticker},
        )
        tasks.append(task)
    
    # Completion task
    complete = PythonOperator(
        task_id='log_completion',
        python_callable=log_completion,
    )
    
    # All ingest tasks run in parallel, then completion
    tasks >> complete
