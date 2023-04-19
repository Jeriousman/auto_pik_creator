#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec  9 09:35:56 2022

@author: hojun
"""

import pandas as pd
import time
import numpy as np
from bertopic import BERTopic
import torch
from transformers import BertTokenizer, BertModel, XLMRobertaTokenizer, XLMRobertaModel, AutoTokenizer, AutoModel, Trainer, TrainingArguments
import bentoml
from transformers import pipeline
from typing import List







def train_bertopic_save(**kwargs):
    
    data_path = kwargs.get('data_path', '/opt/airflow/dags/data/processed_data.csv')  
    embedding_model = kwargs.get('embedding_model', 'paraphrase-multilingual-MiniLM-L12-v2')  
    min_topic_size = kwargs.get('min_topic_size', 40)  
    n_gram_range = kwargs.get('n_gram_range', (1,2))  
    top_n_words = kwargs.get('top_n_words', 20)  
    bertopic_model_save_path = kwargs.get('bertopic_model_save_path', f"/opt/airflow/dags/data/{embedding_model}_{min_topic_size}_{top_n_words}")  
    bento_model_save_path = kwargs.get('bento_model_save_path', "bertopic_autopik_model")  
    
     
    data = pd.read_csv(data_path, engine='python')
    model = BERTopic(embedding_model=embedding_model, min_topic_size=min_topic_size, n_gram_range=n_gram_range, top_n_words=top_n_words)
    
    
    ''' Training'''
    # list_of_docs = list(link_cat_pik['link_title'][:-10])
    
    start = time.time()
    # topics, probs = model.fit_transform(list_of_docs)
    topics, probs = model.fit_transform(list(data['link_title']))
    end = time.time()
    print('the BERTopic took', end - start, 'seconds')
    model.save(bertopic_model_save_path)
    saved_model = bentoml.picklable_model.save_model(bento_model_save_path, model)
    print(f"Model saved: {saved_model}")    



