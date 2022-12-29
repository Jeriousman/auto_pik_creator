#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug  5 14:31:37 2022

@author: hojun
"""

import os
import pandas as pd
from typing import List
import pickle
import re
import pandas as pd
from typing import List
import json
import psycopg2


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
    # remove URL pattern 
    # 안녕https://m.naver.com하세요 -> 안녕하세요
    # pattern = r'(http|https|ftp)://(?:[-\w.]|[\w/]|[\w\?]|[\w:])+'
    # document = re.sub(pattern=pattern, repl='', string=document)

    # # remove tag pattern
    # # 안녕<tag>하세요 -> 안녕하세요
    # pattern = r'<[^>]*>'
    # document = re.sub(pattern=pattern, repl='', string=document)

    # # remove () and inside of ()
    # # 안녕(parenthese)하세요 -> 안녕하세요
    # pattern = r'\([^)]*\)'
    # document = re.sub(pattern=pattern, repl='', string=document)

    # # remove [] and inside of []
    # # 안녕[parenthese]하세요 -> 안녕하세요
    # pattern = r'\[[^\]]*\]'
    # document = re.sub(pattern=pattern, repl='', string=document)

    # # remove special chars without comma and dot
    # # 안녕!!@@하세요, 저는 !@#호준 입니다. -> 안녕하세요, 저는 호준 입니다.
    # pattern = r'[^\w\s - .|,]'
    # document = re.sub(pattern=pattern, repl='', string=document)

    # # remove list characters
    # # 안녕12.1하세요 -> 안녕하세요
    # pattern = r'[0-9]*[0-9]\.[0-9]*'
    # document = re.sub(pattern=pattern, repl='', string=document)

    # # remove korean consonant and vowel
    # # 안녕ㅏ하ㅡㄱ세요 -> 안녕하세요
    # pattern = r'([ㄱ-ㅎㅏ-ㅣ]+)'
    # document = re.sub(pattern=pattern, repl='', string=document)

    # # remove chinese letter
    # # 안녕山하세요 -> 안녕하세요
    # pattern = r'[一-龥]*'
    # document = re.sub(pattern=pattern, repl='', string=document)
    
    ##https://m.blog.naver.com/PostView.naver?isHttpsRedirect=true&blogId=realuv&logNo=220699272999
    pattern =r'[^가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9 ]' 
    # pattern =r'[^가-힣ㄱ-ㅎㅏ-ㅣ]' ##숫자와 영어를뺴고싶은경우
    document = re.sub(pattern=pattern, repl=' ', string=document)
    
    # 영어 소문자로 변환
    # document = document.lower()

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
    dataframe = dataframe.dropna(axis=0, how='any', subset = cols)
    dataframe.dropna(axis=0, how='any', inplace=True, subset = cols)
    # dataframe = dataframe.dropna(subset= cols)
    for col in cols:
        dataframe[col] = [preprocess(str(text)) for text in dataframe[col]]
        dataframe = dataframe[dataframe[col] != ' ']
        dataframe = dataframe[dataframe[col] != 'nan']        
        dataframe = dataframe[dataframe[col] != ''] 
        dataframe = dataframe[dataframe[col] != '\n'] 
    return dataframe

def check_data(**kwargs):
    # data = ti.xcom_pull(key='data', task_ids=['raw_data_preprocess'])
    df = kwargs.get('df', '/opt/airflow/dags/data/link_cat_pik.csv') 
    processed_data_path = kwargs.get('processed_data_path', '/opt/airflow/dags/data/processed_data.csv') 
    data = pd.read_csv(open(df,'rU'), encoding='utf-8', engine='c')
    # data=data.dropna(subset=['link_title', 'pik_title'])
    data=data.dropna(subset=['link_title'])
    data=data.dropna(subset=['pik_title'])
    
    data.to_csv(processed_data_path, index=False)
    print('processed_data shape is: ', data.shape)
    





def db_data_fetching(**kwargs):
    
    default_path = kwargs.get('default_path', '/opt/airflow/dags/data')
    hostname = kwargs.get('hostname', 'dev-postgres.c5dkkbujxodg.ap-northeast-2.rds.amazonaws.com')    
    dbname = kwargs.get('dbname', 'pikurateqa') 
    username = kwargs.get('username', 'postgres')
    password = kwargs.get('password', 'wXVcn64CZsdM27')
    portnumber = kwargs.get('portnumber', 5432)

    conn = psycopg2.connect(host=hostname, dbname=dbname, user=username, password=password, port=portnumber)
    cur = conn.cursor()

    # export to csv
    fid = open(f'{default_path}/category.csv', 'w')
    sql = "COPY (select * from piks_category where is_deleted=false) TO STDOUT WITH CSV HEADER"
    cur.copy_expert(sql, fid)
    fid.close()


    # export to csv
    fid = open(f'{default_path}/pik.csv', 'w')
    sql = "COPY (select * from piks_pik where is_deleted=false) TO STDOUT WITH CSV HEADER"
    cur.copy_expert(sql, fid)
    fid.close()


    # export to csv
    fid = open(f'{default_path}/user.csv', 'w')
    sql = "COPY (select * from users_user) TO STDOUT WITH CSV HEADER"
    cur.copy_expert(sql, fid)
    fid.close()


    # export to csv
    fid = open(f'{default_path}/link.csv', 'w')
    sql = "COPY (select * from linkhub_link where is_deleted=false) TO STDOUT WITH CSV HEADER"
    cur.copy_expert(sql, fid)
    fid.close()


    # export to csv
    fid = open(f'{default_path}/user_friends.csv', 'w')
    sql = "COPY (SELECT id, from_user_id, to_user_id, is_deleted FROM users_following) TO STDOUT WITH CSV HEADER"
    cur.copy_expert(sql, fid)
    fid.close()

    # export to csv
    fid = open(f'{default_path}/user_detail_info.csv', 'w')
    sql = "COPY (select * from users_user_detail_record) TO STDOUT WITH CSV HEADER"
    cur.copy_expert(sql, fid)
    fid.close()






def raw_data_preprocess(**kwargs):
    
    
    '''
    raw_data_path:
    artifical_user_list_path: Non-natural users should be removed from recommendation.
    processed_data_saving_path: A path to save processed pandas dataframe that will be constantly used.
    '''
    
    
    
    #model_name = kwargs.get('model_name', 'sentence-transformers/distilbert-multilingual-nli-stsb-quora-ranking')
    path = kwargs.get('path', '/opt/airflow/dags/data')    
    

 
        
        
        
    link = pd.read_csv(open(f'{path}/link.csv','rU'), encoding='utf-8', engine='c')
    pik = pd.read_csv(f'{path}/pik.csv', engine='python')
    category = pd.read_csv(f'{path}/category.csv', engine='python')
    user = pd.read_csv(f'{path}/user.csv', engine='python')
    with open(f'{path}/artificial_user_list', 'rb') as f:
        artificial_users = pickle.load(f)

    link.rename(columns = {'title':'link_title', 'id':'link_id'}, inplace=True)
    link = link[((link['is_deleted'] == 'f') | (link['is_deleted'] == False) | (link['is_deleted'] == 'false')) & ((link['is_draft'] == 'f') | (link['is_draft'] == False) | (link['is_draft'] == 'false'))]  ##

    pik.rename(columns = {'title':'pik_title', 'id':'pik_id'}, inplace=True)
    pik_quicklinkbox = pik[((pik['is_deleted'] == 'f') | (pik['is_deleted'] == False)) & ((pik['is_default'] == 't') | (pik['is_default'] == True)) & ((pik['is_draft'] == 'f') | (pik['is_draft'] == False))]
    pik = pik[((pik['is_deleted'] == 'f') | (pik['is_deleted'] == False)) & ((pik['is_draft'] == 'f') | (pik['is_draft'] == False))]

    category.rename(columns = {'title': 'cat_title', 'id':'category_id'}, inplace = True)
    category = category[((category['is_deleted'] == 'f') | (category['is_deleted'] == False))]   ##& ((category['is_initial'] == 'f') | (category['is_initial'] == False)) & ((category['is_default'] == 'f') | (category['is_default'] == False))]

    user.rename(columns = {'id':'user_id'}, inplace = True)
    user = user[((user['is_superuser'] == 'f') | (user['is_superuser'] == False)) & ((user['is_active'] == 't') | (user['is_active'] == True))]

    link.columns
    link.drop(['picture_id', 'default_logo', 'position', 'search_vector', 'old_id', 'platform', 'curating_point', 'next_obj', 'previous_obj', 'imported', 'is_deleted', 'is_draft'], axis =1, inplace=True)
    pik.columns
    pik.drop(['is_official', 'search_vector', 'old_id', 'is_onboard', 'platform', 'pik_photo_id', 'is_draft', 'is_deleted', 'is_default'], axis=1, inplace=True)
    pik_quicklinkbox.columns
    pik_quicklinkbox.drop(['is_official', 'search_vector', 'old_id', 'is_onboard', 'platform', 'pik_photo_id', 'is_draft', 'is_deleted', 'is_default'], axis=1, inplace=True)
    category.columns
    category.drop(['position',  'old_id', 'platform', 'next_obj', 'previous_obj', 'is_initial', 'is_deleted', 'is_default'], axis=1, inplace=True)
    user.columns
    user.drop(['password', 'email', 'full_name', 'date_joined', 'profile_photo_id', 'phone_number', 'default_logo', 'hashtag_updated', 'active_badge', 'old_id',\
            'first_name', 'last_name', 'responded', 'is_skipped', 'is_onboard', 'has_feed_keywords', 'is_superuser', 'is_active'], axis=1, inplace=True)

    category = pd.merge(category, user, how = 'inner', left_on ='user_id', right_on='user_id', suffixes=('_cat', '_user'))
        
    ##pik_info와 cat_info 병합
    cat_pik = pd.merge(category, pik, how = 'inner', left_on = 'pik_id', right_on = 'pik_id', suffixes=('_cat', '_pik'))
    cat_pik_quicklinkbox = pd.merge(category, pik_quicklinkbox, how = 'inner', left_on = 'pik_id', right_on = 'pik_id', suffixes=('_cat', '_pik'))
    cat_pik.columns
    cat_pik_quicklinkbox.columns

    link_cat_pik = pd.merge(link, cat_pik, how='inner', left_on='category_id', right_on='category_id', suffixes=('_link', '_catpik'))
    link_cat_pik.sort_values(['user_id', 'pik_id', 'category_id', 'link_id'], ascending = True, inplace=True)  
    link_cat_pik_quicklinkbox = pd.merge(link, cat_pik_quicklinkbox, how='inner', left_on='category_id', right_on='category_id', suffixes=('_link', '_catpik'))
    link_cat_pik_quicklinkbox.sort_values(['user_id', 'pik_id', 'category_id', 'link_id'], ascending = True, inplace=True)  


    def dropNa_dropArtificialUser(data, artificial_users, dropna=True, drop_artificial=True, integering=True):
        if drop_artificial:
        # from glob import glob
            slug1 = data['slug'][data['pik_id'] == 3085].iloc[0]
            slug2 = data['slug'][data['pik_id'] == 3186].iloc[0]
            slug3 = data['slug'][data['pik_id'] == 3188].iloc[0]
            
            ##특정 string이 포함된 행을 df에서찾기
            dummy1 = data[data['slug'].str.contains(slug1)]
            dummy2 = data[data['slug'].str.contains(slug2)]
            dummy3 = data[data['slug'].str.contains(slug3)]
            
            ## 추출한 행을 df에서제거하기
            data = data[~data.index.isin(dummy1.index)]
            data = data[~data.index.isin(dummy2.index)]
            data = data[~data.index.isin(dummy3.index)]
            
            ##제거된것을확인
            data[data['slug'] == slug1]
            data[data['slug'] == slug2]
            data[data['slug'] == slug3]
            
            # data.drop(['description', 'memo', 'url', 'is_draft_link', 'link_create_time', 'id_cat', 'created_cat', 'id_user', 'id_pik', 'slug', 'language', 'is_draft_catpik', 'created_pik'], axis=1, inplace=True)
            
        if integering:
            data = data.astype({'pik_id' :'int', 'link_id':'int', 'category_id':'int'}) 
        # link_cat_pik.dropna(axis=0, how='any', inplace=True, subset = 'link_title')
        # link_cat_pik.dropna(axis=0, how='any', inplace=True, subset = 'pik_title')
        # ti.xcom_push(key='data', value =  link_cat_pik)

        if dropna:
            data = filtering_users(data, 'user_id', artificial_users)      
            data = filter_data(data,  ['link_title'])
            data = filter_data(data,  ['pik_title'])

        user_lang_dict = {str(k):str(v) for k,v in zip(data['user_id'], data['language_code'])} ##모든유저를 검색할 수 있도록
        pik_lang_dict = {k:v for k,v in zip(data['pik_id'], data['language_code'])}
        link_lang_dict = {k:v for k,v in zip(data['link_id'], data['language_code'])}
        pik_status_dict = {k:v for k,v in zip(data['pik_id'], data['status'])}
        
        return user_lang_dict, pik_lang_dict, link_lang_dict, pik_status_dict, data


    user_lang_dict, pik_lang_dict, link_lang_dict, pik_status_dict, link_cat_pik = dropNa_dropArtificialUser(link_cat_pik, artificial_users, dropna=True, drop_artificial=True, integering=True)
    _, _, _, _, link_cat_pik_quicklinkbox = dropNa_dropArtificialUser(link_cat_pik_quicklinkbox, artificial_users, dropna=True, drop_artificial=False, integering=True)

    with open(f"{path}/user_lang_dict.json", "w") as f:  ##For bento_service.py
        json.dump(user_lang_dict, f)
        
    with open(f"{path}/pik_lang_dict.json", "w") as f:   ##For bento_service.py
        json.dump(pik_lang_dict, f)

    with open(f"{path}/link_lang_dict.json", "w") as f:   ##For bento_service.py
        json.dump(link_lang_dict, f)
    
    with open(f"{path}/pik_status_dict.json", "w") as f:   ##For bento_service.py
        json.dump(pik_status_dict, f)
    
    link_cat_pik.to_csv(f'{path}/link_cat_pik.csv', index=False)
    link_cat_pik_quicklinkbox.to_csv(f'{path}/link_cat_pik_quicklinkbox.csv', index=False)
    