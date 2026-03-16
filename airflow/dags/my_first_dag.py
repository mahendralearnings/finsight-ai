"""
My First DAG - Hello FinSight!
"""
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

#task fucntions 
def say_hello():
    print("Hello from FinSight AI!")
    print(f"Current time: {datetime.now()}")

def say_goodbye():
    print("Pipeline complete! Goodbye!")


#craetion of DAG Object

with DAG(
    dag_id='my_first_dag',
    description='My first Airflow DAG',
    start_date=datetime(2026, 3, 1),
    schedule_interval=None, #manuel trigger only
    catchup=False,  #Catchup=False is important in production — it prevents Airflow from running all historical dates when you deploy a new DAG
    tags=['learning'],
) as dag:
    
    # Tasks Definitions
    
    task_hello = PythonOperator(
        task_id='say_hello',  # Unique ID within this DAG
        python_callable=say_hello,  ## Function to call
    )
    
    task_date = BashOperator(
        task_id='print_date',  
        bash_command='echo "Today is $(date)"',
    )
    
    task_goodbye = PythonOperator(
        task_id='say_goodbye',
        python_callable=say_goodbye,
    )
    
    task_hello >> task_date >> task_goodbye
