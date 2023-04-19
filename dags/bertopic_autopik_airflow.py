#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 26 12:00:42 2022

@author: hojun
"""

import airflow
from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
# from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from utils.slack_alert import SlackAlert
from functions import  data, training_bertopic, training_vectorizers
# from functions import  prepare_user_or_pik_data
from airflow.models.baseoperator import chain
from datetime import datetime, timedelta




slack = SlackAlert("#airflow-monitor", "xoxb-2654232235489-4145809392837-oy7FLFexlTrHAFbhHZ2ZDKIO")

default_args = {
    "owner": 'airflow',
    'email_on_failure' : False,
    'email_on_retry' : False,
    'email' : 'hojun.seo@pikurate.com',
    'retries': 0,
    'retry_delay' : timedelta(minutes=5),
    'on_success_callback': slack.success_msg,
    'on_failure_callback': slack.fail_msg


}

with DAG(
    dag_id='bertopic_autopik_airflow',
    start_date=datetime(2022, 9 , 28),
    schedule_interval="0 */2 * * *",  ##meaning every 2 hours. https://crontab.guru/ 매새벽3시에돌린다 (UTC타임)
    default_args=default_args,
    catchup=False,
    
) as dag:





    task_clear_bento = BashOperator(   ##이전 bentoml model들을 모두 지운다
            task_id="clear_bento",         ##
            bash_command=
            """ 
                bentoml delete bertopic_autopik_bento --yes; bentoml models delete bertopic_autopik_model --yes; echo "Job continued"  
            """
            )
    
    
    
    # task_db_data_fetching = PythonOperator(
    #         task_id='db_data_fetching',
    #         python_callable=data.db_data_fetching,
    #         op_kwargs={
    #             'default_path' : '/opt/airflow/dags/data',
    #             'hostname' : 'dev-postgres.c5dkkbujxodg.ap-northeast-2.rds.amazonaws.com',
    #             'dbname' : 'pikurateqa',
    #             'username' : 'postgres',
    #             'password' : 'wXVcn64CZsdM27',
    #             'portnumber' : 5432
    #         })
    
    
    
    ##raw data를 정제된 link_cat_pik으로 만들어준다
    task_data_process = PythonOperator(
        task_id="raw_data_preprocess",
        python_callable=data.raw_data_preprocess,
        op_kwargs={
            "path": '/opt/airflow/dags/data', ##실제 DB에서가져오는 raw data
        }
    )
    
    
    task_save_processed_data = PythonOperator(  ##없으나 마나한 태스크지만 에어플로우에서 제대로 저장되지 않는 이상현상이 발견 된 적이 있기 때문에 넣었다
        task_id="save_processed_data",
        python_callable=data.check_data,
        op_kwargs={
            "df": '/opt/airflow/dags/data/link_cat_pik.csv', ##실제 DB에서가져오는 raw data
            'processed_data_path': '/opt/airflow/dags/data/processed_data.csv'
        }
    )


    task_train_bertopic = PythonOperator(  ##없으나 마나한 태스크지만 에어플로우에서 제대로 저장되지 않는 이상현상이 발견 된 적이 있기 때문에 넣었다
        task_id="train_bertopic",
        python_callable=training_bertopic.train_bertopic_save,
        op_kwargs={
            "data_path":  '/opt/airflow/dags/data/processed_data.csv', ##실제 DB에서가져오는 raw data
            'embedding_model': 'paraphrase-multilingual-MiniLM-L12-v2',
            'min_topic_size': 40,
            'n_gram_range': (1,2),
            'top_n_words': 20,
            'bertopic_model_save_path':  "/opt/airflow/dags/data/paraphrase-multilingual-MiniLM-L12-v2_40_20",
            'bento_model_save_path': "bertopic_autopik_model"
        }
    )


    task_train_vectorizers = PythonOperator(  ##없으나 마나한 태스크지만 에어플로우에서 제대로 저장되지 않는 이상현상이 발견 된 적이 있기 때문에 넣었다
        task_id="train_vectorizers",
        python_callable=training_vectorizers.train_vectorizers_save,
        op_kwargs={
            'data_path': '/opt/airflow/dags/data',
            'pikurate_whole_data_name': 'processed_data'
        }
    )


    
    task_create_bento = BashOperator(   ##이전 bentoml model들을 모두 지운다
        task_id="create_bento",         ##
        bash_command=
        
        """ 
            cd /opt/airflow/dags/bentoml/auto_pik_bento; bentoml build
        """
        )
    
        
        
    
    
    task_serve_bentoml = BashOperator(
        task_id="serve_bentoml",
        bash_command=
        # fuser -k 3000/tcp; bentoml serve -p 3001 pik_recommender_bento:latest --production
        """ 
            fuser -k 7171/tcp; bentoml serve -p 7171 bertopic_autopik_bento:latest --production
        """
        )
        
    
    



    
    # task_clear_bento >> task_db_data_fetching >> task_data_process >> task_save_processed_data >> task_train_bertopic >> task_train_vectorizers >> task_create_bento >> task_serve_bentoml
    task_clear_bento >> task_data_process >> task_save_processed_data >> task_train_bertopic >> task_train_vectorizers >> task_create_bento >> task_serve_bentoml
