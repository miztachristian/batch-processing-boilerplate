import logging

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.sensors.sftp_sensor import SFTPSensor
from airflow.contrib.sensors.gcs_sensor import GoogleCloudStorageObjectSensor
from airflow.contrib.operators.sftp_operator import SFTPOperator
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.operators.dataflow_operator import DataFlowPythonOperator
from airflow.contrib.operators.file_to_gcs import FileToGoogleCloudStorageOperator
from airflow.contrib.operators.gcs_to_gcs import GoogleCloudStorageToGoogleCloudStorageOperator
from datetime import datetime, timedelta

#
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2019, 1, 1),
    'email': ['tansudasli@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
}

PROJECT = "sandbox-236618"
REGION = "europe-west1"
ZONE = "europe-west1-a"
INGESTION_BUCKET_NAME = "sandbox-datalake-123"
BEAM_BUCKET_NAME = "beam-pipelines-123"
BEAM_FILE_NAME = "average-prices-by-product-enhanced"



with DAG('product-analytics', default_args=default_args, schedule_interval=timedelta(minutes=10)) as dag:

    # TODO: not implemented
    # listen customers FTP server folder w/ sensor
    # define sftp-default connection in Airflow UI
    # t1 = SFTPSensor(
    #     task_id='listen-sftp-server',
    # )

    # TODO: not implemented
    # copy from sftp to gcp storage's incoming folder
    # scenario will start right from here !
    # t2 = SFTPOperator(
    #     task_id='transfer-to-incoming',
    # )

    # Listen incoming folder w/ sensor
    template_fields = [INGESTION_BUCKET_NAME, '/incoming/sales_transactions_*']
    t3 = GoogleCloudStorageObjectSensor(
        task_id='listen-incoming-file',
        default_args=template_fields
    )

    # TODO: better file structure can be defined, such as monthly aggregation datalake/sales/05/sales_transactions_*
    # copy from gcs to datalake for raw data storing
    template_fields = (INGESTION_BUCKET_NAME, 'incoming/sales_transactions_*',
                       INGESTION_BUCKET_NAME, 'datalake/sales_transactions_*')
    t4 = GoogleCloudStorageToGoogleCloudStorageOperator(
        task_id='copy-to-datalake',
        default_args=template_fields,
        move_object=False
    )

    # copy from gcs to process for analytical calculations
    template_fields = (INGESTION_BUCKET_NAME, 'incoming/sales_transactions_*',
                       INGESTION_BUCKET_NAME, 'processing/sales_transactions_*')
    t5 = GoogleCloudStorageToGoogleCloudStorageOperator(
        task_id='move-to-processing',
        default_args=template_fields,
        move_object=True
    )

    # git clone average-prices-by-product-enhanced.py file ?????
    # deploy to GCP dataflow as a beam job, and check GCP dataflow job status
    options = {'autoscalingAlgorithm': 'BASIC',
               'maxNumWorkers': '50',
               # 'start': '{{ds}}',
               'partitionType': 'DAY'}
    dataflow_default_options = {'project': PROJECT,
                                'region': REGION,
                                'zone': ZONE,
                                'stagingLocation': 'gs://' + BEAM_BUCKET_NAME + '/staging',
                                'tempLocation': 'gs://' + BEAM_BUCKET_NAME + '/temp'}
    template_fields = [options, dataflow_default_options, BEAM_FILE_NAME]
    t6 = DataFlowPythonOperator(
        task_id='deploy-averages-prices-by-product-job',
        default_args=template_fields,
        py_file=''
    )

    # Listen output folder w/ sensor
    template_fields = [INGESTION_BUCKET_NAME, '/output/sales_transactions_*']
    t7 = GoogleCloudStorageObjectSensor(
        task_id='listen-output-file',
        default_args=template_fields
    )

    # TODO: not implemented
    # transfer output file to SFTP server
    # t8 = SFTPOperator(
    #     task_id='transfer-to-sftp-server',
    #     bash_command=''
    # )

    # t3 >> t2 >> t1
    t4 >> t3
    t5 >> t4
    t7 >> t6 >> t3
    # t8 >> t7


