
import pandas as pd
import pickle
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from scipy.sparse import *

def tf_idf(data, max_df=0.85, smooth_idf=True, use_idf=True):
    ##making TF
    ##우리가 가지고 있는 전체문장으로 tf-idf를 트레이닝한다.
    if isinstance(data, pd.Series):
        print('It is pandas.Series type')
        data = data.tolist()
    else:
        pass
    cv=CountVectorizer(max_df=max_df)    
    word_count_vector = cv.fit_transform(data)
    # list(cv.vocabulary_.keys())[:10]
    # feature_names=cv.get_feature_names()
    feature_names=cv.get_feature_names_out()
    
    ##making IDF
    tfidf_transformer = TfidfTransformer(smooth_idf=smooth_idf, use_idf=use_idf)
    tfidf_transformer.fit(word_count_vector)    
        
    
    return cv, tfidf_transformer, feature_names

def train_vectorizers_save(**kwargs):
    data_path = kwargs.get('data_path', '/opt/airflow/dags/data')  
    pikurate_whole_data_name = kwargs.get('pikurate_whole_data_name', 'processed_data')  

    data = pd.read_csv(f"{data_path}/{pikurate_whole_data_name}.csv", engine='python')
    
    count_vectorizer, tfidf_transformer, feature_names = tf_idf(data['link_title'])

    with open(f'{data_path}/count_vectorizer', 'wb') as f:
        pickle.dump(count_vectorizer, f)

    with open(f'{data_path}/tfidf_transformer', 'wb') as f:
        pickle.dump(tfidf_transformer, f)

    with open(f'{data_path}/feature_names', 'wb') as f:
        pickle.dump(feature_names, f)



