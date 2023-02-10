#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 13:59:38 2022

@author: hojun
"""
from random import choice
from random import random
from random import randint
import torch
import bentoml
import numpy as np
from bentoml.io import Text, JSON, NumpyNdarray, Multipart, File, PandasDataFrame
import typing
from sklearn.metrics.pairwise import cosine_similarity
import pydantic
import requests_toolbelt
import pandas as pd
import json
import pickle
from typing import Any
import io
from typing import List
import torch
import pydantic
import requests_toolbelt
from typing import Any
import io
from sklearn.metrics.pairwise import cosine_distances
from sklearn.cluster import AgglomerativeClustering
import re
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from scipy.sparse import *




df = pd.read_csv("/home/hojun/auto_pik_creator/dags/data/link_cat_pik_quicklinkbox.csv")

    
with open("/home/hojun/auto_pik_creator/dags/data/user_lang_dict.json") as f:
    user_lang_dict = json.load(f)
 
with open("/home/hojun/auto_pik_creator/dags/data/pik_lang_dict.json") as f:
    pik_lang_dict = json.load(f)

with open("/home/hojun/auto_pik_creator/dags/data/link_lang_dict.json") as f:
    link_lang_dict = json.load(f)
    
with open('/home/hojun/auto_pik_creator/dags/data/pik_status_dict.json') as f:
    pik_status_dict = json.load(f)


with open('/home/hojun/auto_pik_creator/dags/data/count_vectorizer', 'rb') as f:
    count_vectorizer = pickle.load(f)

with open('/home/hojun/auto_pik_creator/dags/data/tfidf_transformer', 'rb') as f:
    tfidf_transformer = pickle.load(f)

with open('/home/hojun/auto_pik_creator/dags/data/feature_names', 'rb') as f:
    feature_names = pickle.load(f)

model = BERTopic.load("/home/hojun/auto_pik_creator/dags/data/bertopic_paraphrase-multilingual-MiniLM-L12-v2_40_20")



def filtering_users(data, user_colname, user_list: List):
    '''
    Parameters
    ----------
    data : Pandas dataframe
        DESCRIPTION.
    user_colname : string
        DESCRIPTION.
    user_list : List
        DESCRIPTION.

    Returns
    -------
    data : TYPE
        DESCRIPTION.

    '''
    for user in user_list:
        data = data[data[user_colname] != user]
    return data




def preprocess(document: str) -> str:
   
    ##https://m.blog.naver.com/PostView.naver?isHttpsRedirect=true&blogId=realuv&logNo=220699272999
    pattern =r'[^가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9 ]' 
    # pattern =r'[^가-힣ㄱ-ㅎㅏ-ㅣ]' ##숫자와 영어를뺴고싶은경우
    document = re.sub(pattern=pattern, repl=' ', string=document)
    
    # remove empty space
    document = document.strip()

    # make empty spcae size as only one
    document = ' '.join(document.split())
    
    return document

##invalid 데이터 필터링아웃하기
def filter_data(dataframe, cols):
    '''
    Purpose:
        filtering non-character values
        filtering invalid characters
    '''
    dataframe.dropna(axis=0, how='any', inplace=True, subset = cols)
    dataframe = dataframe.dropna(axis=0, how='any', subset= cols)
    for col in cols:
        dataframe[col] = [preprocess(str(text)) for text in dataframe[col]]
        dataframe = dataframe[dataframe[col] != ' ']
        dataframe = dataframe[dataframe[col] != 'nan']        
        dataframe = dataframe[dataframe[col] != ''] 
        dataframe = dataframe[dataframe[col] != '\n'] 
    return dataframe



df = filter_data(df, ['link_title'])



# https://docs.bentoml.org/en/latest/concepts/runner.html
##custom runner building
model_file = "/home/hojun/auto_pik_creator/dags/data/bertopic_paraphrase-multilingual-MiniLM-L12-v2_40_20"
class bertopik_runnable(bentoml.Runnable):
    SUPPORTED_RESOURCES = ("nvidia.com/gpu",)


    def __init__(self, model_file):
        self.model = BERTopic.load(model_file)  ##this model should the bertopic model

    @bentoml.Runnable.method(batchable=True, batch_dim=0)
    def predict(self, input: List):
        return self.model.transform(input)
#1
# bertopik_run = bertopik_runnable(model_file)
# bertopik_runner.predict(test_albert_data)

#2
bertopik_runner = bentoml.Runner(
    bertopik_runnable,
    name="bertopik_runner",
    runnable_init_params={
        "model_file": model_file,
    }
)
# bertopik_runner.init_local()
# result = bertopik_runner.predict.run(test_albert_data[0])
svc = bentoml.Service("bertopic_autopik_model", runners=[bertopik_runner])

    




def link_id_topic(results, list_of_docs_id):

    '''link id 와 topic 그룹을 정렬'''
    link_id_results = []
    for link_id, content in list(zip(list_of_docs_id, results[0])):
        link_id_results.append((link_id, content))
    return link_id_results
        


def get_keywords_and_groups(link_id_results, model, topk):
 
    groups_dict={}
    keywords_dict = {}
    keywords_by_category = []
    all_keywords_tracked = []
    outlier_links_dict = {}
    
    for linkid, topic in link_id_results:
        if topic != -1:
            for (keyword, importance) in model.get_topic(topic):
                
                keywords_by_category.append(keyword)
                all_keywords_tracked.append(keyword)   ##모든링크의 키워드를 다 한곳에 모아놓은 것
                
            keywords_dict[linkid] = keywords_by_category[:topk] ##각 링크마다 키워드 20개씩 추출한 것
            groups_dict[linkid] = topic
            keywords_by_category=[]  ##This is keyword with link_id of the links brought in
    
        
        if topic == -1:
            # outlier_links_dict[linkid] = model.get_topic(topic)
            outlier_links_dict[linkid] = topic
    return keywords_dict, groups_dict, outlier_links_dict, all_keywords_tracked




'''This is to get pik title'''


def tf_idf_to_quicklink_keywords(count_vectorizer, tfidf_transformer, quicklink_keywords):

    keywords_joined = ' '.join(quicklink_keywords)
    tf_idf_vector = tfidf_transformer.transform(count_vectorizer.transform([keywords_joined]))
    
    return tf_idf_vector


    
def sort_coo(coo_matrix):
    tuples = zip(coo_matrix.col, coo_matrix.data)
    return sorted(tuples, key=lambda x: (x[1], x[0]), reverse=True)


# sorted_keywords=sort_coo(tf_idf_vector.tocoo())



def extract_topn_from_vector(feature_names, sorted_items, topn=10):
    """get the feature names and tf-idf score of top n items"""
    
    #use only topn items from vector
    sorted_items = sorted_items[:topn]
    score_vals = []
    feature_vals = []
    
    # word index and corresponding tf-idf score
    for idx, score in sorted_items:
        
        #keep track of feature name and its corresponding score
        score_vals.append(round(score, 3))
        feature_vals.append(feature_names[idx])
    #create a tuples of feature,score
    #results = zip(feature_vals,score_vals)
    results= {}
    for idx in range(len(feature_vals)):
        results[feature_vals[idx]]=score_vals[idx]
    
    return results








# user_id = '49'
## This is modification of above to inlcude language condition
input_spec = Multipart(user_id=Text())
output_spec = Multipart(category_titles=JSON(), link_by_category=JSON(), outlier_links_dict=JSON(), pik_title=Text())
@svc.api(input=input_spec, output=output_spec)
def predict(user_id) -> dict:
    
    user_quicklinkbox_data = df[df['user_id'] == int(user_id)]
    list_of_docs = list(user_quicklinkbox_data['link_title'])
    # list_of_docs_id = user_quicklinkbox_data['link_id']
    list_of_docs_url = user_quicklinkbox_data['url']
    results = bertopik_runner.run(list_of_docs)  ##링크들을 카테고리로 나눈 결과와 그 키워드들 

    link_id_results = link_id_topic(results, list_of_docs_url) 
    keywords_dict, groups_dict, outlier_links_dict, all_keywords_tracked = get_keywords_and_groups(link_id_results, model, 20)  ##20의 자리는topk  키워드 갯수 
    
    # word_count_vector, tf_idf_vector, feature_names = tf_idf(link_cat_pik['link_title'])
    tf_idf_vector = tf_idf_to_quicklink_keywords(count_vectorizer, tfidf_transformer, all_keywords_tracked)
    sorted_keywords=sort_coo(tf_idf_vector.tocoo())
    keywords=extract_topn_from_vector(feature_names,sorted_keywords, 20)

    category_titles = {i:title_candidates[0] for i, title_candidates in keywords_dict.items()}  ##각 링크들이 카테고리로 나누어졌을 때 그 카테고리 명 topk 1을 뽑은 것
    link_by_category = groups_dict  ##각 링크들이 속한 카테고리 번호를 먹인것 
    pik_title_candidate = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[0]  ##키워드들의 키워드로 가장 순위가 높은 것을 뽑아서 픽의 제목으로 쓰자.
    pik_title = pik_title_candidate[0]
    
    return {'category_titles':category_titles, 'link_by_category':link_by_category, 'outlier_links_dict':outlier_links_dict, 'pik_title':pik_title}


