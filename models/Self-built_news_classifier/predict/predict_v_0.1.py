import pandas as pd
import numpy as np
import time
import os
import sys
sys.path.append("F:\paper\code\getCnki\handle_data")
from tool.BAGGING import BAGGING
import jieba
jieba.load_userdict("F:\paper\data\important\cover_name.txt")
import multiprocessing as mp
import threading
from tool.toolBox import DATA,TOOl
from tool.model import Model
from tool.get_different_mindf import GetData
from tool.BAGGING import kfold
DATA = DATA()
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score
from sklearn import metrics
import warnings
import pickle
from scipy.sparse import csr_matrix
import multiprocessing as mlp
import copy
from bidict import bidict
warnings.filterwarnings("ignore")
#file_handle = open("exp.txt","a")
sample_size = 10
vote_num = 5
process_num = sample_size
def trans_num(x):
        if x > 0:
            return 1
        elif x < 0:
            return -1
        else:
            return 0
"""
org has always represented the initial training sample in this sample

"""
def predict(min_df,org,seed,n_split = sample_size,model_method = "train"):
    global sample_size,vote_num,process_num
    gd = GetData(min_df = min_df,cut_method="global")
    kf = kfold(org,n_split)
    grand_org = kf.train_data[seed]
    test_data = kf.test_data[seed]
    

    all_data = gd.data
#all_data = pd.read_pickle("/Users/qianyuyang/Desktop/paper/data/important/sentence_target_cut_already.pkl")
    all_data = all_data.drop_duplicates(["sentence"])
    all_data["id"] = all_data.index
    ##################################################################################################################
    #Process the overall tf-idf matrix here
    
    all_tf = TfidfVectorizer()
    #############################################
    all_tf_parse_matrix = all_tf.fit_transform(all_data.text.tolist())
    #######This step can be omitted to reflect the superiority of the coefficient matrix##############
    word_news_parse_matrix = csr_matrix((np.array([1] * len(all_tf_parse_matrix.data)),all_tf_parse_matrix.indices,all_tf_parse_matrix.indptr),shape = all_tf_parse_matrix.shape)
    all_word_list = all_tf.get_feature_names()

    """
    Here we first separate the test set and training set test_org and grand_org
    """
    #grand_org = ud["train_data"][seed]
    #test_data = ud["test_data"][seed]
    test_data = TOOl().clean(min_df = min_df,org = test_data)
    org_pool = []
    word_vector_sum = pd.DataFrame()
    for vote in range(vote_num):
        """
        Here, the training set and the validation set train_org, test_org are divided according to the training set
        """
        test_org = grand_org.sample(int(0.2 * len(grand_org)),replace = False)
        train_org = grand_org[grand_org.id.isin(test_org.id.tolist()) == False]
        if not os.path.exists("min_df = %s/para_dict"%min_df):
            os.mkdir("min_df = %s/para_dict"%min_df)
        param_dict = dict()
        with open("min_df = %s/para_dict/para_dict_%s.pkl"%(min_df,seed),"wb") as f:
                pickle.dump(param_dict,f)
        
        for line_standard in range(10,0,-1):
            line_standard = round(line_standard * 0.1,1)
            
            print("_____________________________________\n")
            print("the line standard is %s\n"%line_standard)
            print("_____________________________________\n")
            
            """
            Each vote of each seed needs to perform parameter learning to obtain the best step size. This step is to load the performance of the previous different steps in the current sample/vote on the validation set
            """
            with open("min_df = %s/para_dict/para_dict_%s.pkl"%(min_df,seed),"rb") as f:
                param_dict = pickle.load(f)
            ad = copy.deepcopy(all_data)
            org = copy.deepcopy(train_org)
            torg = copy.deepcopy(test_org)
            org = TOOl().clean(min_df = min_df,org = org)
            
            m = Model(org = org,line_standard = line_standard,min_df = min_df)
            k = m.result
            org = k["prediction"]
            word_vec = k["word_vector"]
            """
            This will show the total number of negative news
            """
            print("_____%s_________"%len(org[org.label == -1]))
            
            td = pd.merge(torg,org[["sentence","label"]],on = "sentence",how = "left")
            
            td = td.dropna(axis = 0,subset=["label_x","label_y"])
        
            f1s = f1_score(td.label_x,td.label_y,average = "macro")
            
            param_dict[line_standard] = f1s
            with open("min_df = %s/para_dict/para_dict_%s.pkl"%(min_df,seed),"wb") as f:
                pickle.dump(param_dict,f)
        stat = pickle.load(open("min_df = %s/para_dict/para_dict_%s.pkl"%(min_df,seed),"rb"))
        best_key = max(stat,key = stat.get)
        """
        After getting the best step size, there is an optimization that throws the validation set back for training with all grand_org
        """
        again_result = Model(org = TOOl().clean(min_df = min_df,org = grand_org),line_standard = best_key,min_df = min_df,method = model_method).result
        iteration_word_vector = again_result["word_vector"]
        org_pool.append(again_result["prediction"])
        if  len(word_vector_sum) == 0:

            word_vector_sum = iteration_word_vector.sort_values("word")
        else:
            word_vector_sum.score = word_vector_sum.score + iteration_word_vector.sort_values("word").score
    seed_org = copy.deepcopy(org_pool[0])
    seed_org["label"] = 0
    for i in range(vote_num):
        
        seed_org["label"] = seed_org["label"] + org_pool[i]["label"]
    seed_org["label"] = seed_org["label"].apply(trans_num)
    seed_org.to_pickle("predict_%s_%s.pkl"%(min_df,seed))
    word_vector_sum.to_pickle("word_vector_%s_%s.pkl"%(min_df,seed))
    if not os.path.exists("min_df = %s/para_dict"%min_df):
        os.mkdir("min_df = %s/para_dict"%min_df)
    return seed_org,word_vector_sum,test_data