# Author: Stephen Meisenbacher
# November 27, 2021
# Pipeline.py
# Python class for encapsulation of extraction, processing, classification process (generalized)

import json
import os
import pickle
import pandas as pd
import numpy as np
import swifter
from pathlib import Path
from datetime import datetime
import sqlite3
from Extract import Extract
import multiprocessing as mp
from contextlib import closing
from functools import partial
import json
import logging

from nltk.corpus import stopwords

######## GLOBAL DATA #########
stop = stopwords.words("english")
N = 13
center = int(N / 2)
NUM_PROC = int(0.75 * mp.cpu_count())
##############################

def key_index(text, keywords):
    global center

    found = []
    for k in keywords:
        found.extend([i for i, x in enumerate(text.split()) if k in x])

    found = [(x, abs(center - x)) for x in found]
    if found:
        middle = min(found, key=lambda x:x[1])[0]
    else:
        middle = int(len(text.split()) / 2)

    return middle

def append_qual(text, qualifiers):
    global keywords

    found = []
    for q in qualifiers:
        found.extend([x for x in text.split() if q == x])

    if found:
        found = sorted(found)
        prefix = "_".join(found)+"_"
    else:
        prefix = ""

    text = " ".join([prefix+x if x not in qualifiers else x for x in text.split()])

    return text

def proc(keywords, qualifiers, keep, text):
    global stop
    TRIM = 2

    trimmed = []
    for t in text.split('|'):
        # first remove stopwords (for richer text chunks)
        t = " ".join([x for x in t.split() if x not in stop])
        main_index = key_index(t, keywords) # find index of "center" keyword
        t = append_qual(t, qualifiers) # append qualifers

        # trim
        lower = max(0, main_index-TRIM)
        upper = min(len(text), main_index+TRIM)
        new_t = t.split()[lower:upper+1]
        new_t = [x for x in new_t if x not in qualifiers]
        keeps = [x for x in t.split()[:lower]+t.split()[upper+1:] if x in keep]
        t = keeps + new_t
        trimmed.append(" ".join(t))

    return "|".join(trimmed)

def classify(keys, CLASSIFIER, text):
    #global CLASSIFIER

    total = 0
    to_pred = [] #text.split('|')
    for chunk in text.split('|'):
        if any(x in chunk for x in keys):
            to_pred.append(chunk)
    if len(to_pred) > 0:
        pred = CLASSIFIER['clf'].predict(to_pred)
        total += sum(pred)
    return 1 if total > 0 else 0

def init_pool(classifier):
    global CLASSIFIER
    CLASSIFIER = classifier

def _proc_helper_(keys, qual, keep, texts):
    global NUM_PROC

    proc_func = partial(proc, keys, qual, keep)
    with closing(mp.Pool(NUM_PROC)) as pool:
        res = pool.map(proc_func, texts)
        pool.close()
        pool.join()
    return res

def _class_helper_(classifier, keys, texts):
    global NUM_PROC
    #global CLASSIFIER

    class_func = partial(classify, keys, classifier) 
    #with closing(mp.Pool(NUM_PROC, init_pool(classifier['clf']))) as pool:
    with closing(mp.Pool(NUM_PROC)) as pool:
        res = pool.map(class_func, texts)
        pool.close()
        pool.join()
    return res
    
def _merge_helper_(id, con):
    cursor = con.cursor()
    cursor.execute("select id from jobs where id={};".format(id))
    res = cursor.fetchall()
    cursor.close()
    if len(res) > 0:
        return 0
    else:
        return 1

class Pipeline:
    # class attributes
    project = None
    
    csv_dir = None
    data_dir = None
    main_dir = None
    rules_dir = None
    file_mapping = {}
    tags = None
    settings = None
    project_settings = None
    keep_text = False
    n = None
    MODE = "word"

    db_path = None
    db_name = None
    db_table = None
    con = None # db connection
    db_fields = None
    csv_save = None

    #cols = None
    #dtypes = None
    convert_c = None
    convert_t = None

    all_keywords = []
    proc_keywords = {}
    all_qualifiers = []
    proc_qualifiers = {}
    proc_keep = {}

    classifiers = {}

    # class functions
    def __init__(self, SETTINGS, project_settings):
        #print("Setting up...")

        self.project = SETTINGS['project']

        self.n = SETTINGS['n']
        self.MODE = SETTINGS['mode']

        if SETTINGS['main_dir']:
            self.main_dir = Path(SETTINGS['main_dir'])
            #self.create_mapping()
        else:
            self.main_dir = None
        self.data_dir = Path(SETTINGS['data_dir'])
        self.csv_dir = Path(SETTINGS['csv_dir'])
        self.rules_dir = Path(SETTINGS['rules_dir'])
        self.settings = SETTINGS
        self.project_settings = project_settings
        self.keep_text = SETTINGS['keep_text']
        
        self.tags = SETTINGS['tags']
        self.convert_t = {k:int for k in self.tags}

        # read in class-specific keywords for preproc
        self.proc_keywords = SETTINGS['proc_keywords']
        for k in self.proc_keywords.keys():
            self.all_keywords.extend(self.proc_keywords[k])
        self.all_keywords = list(set(self.all_keywords))

        # read in qualifiers
        # not current used
        '''
        self.proc_qualifiers = SETTINGS['qualifiers']
        for k in self.proc_qualifiers.keys():
            self.all_qualifiers.extend(self.proc_qualifiers[k])
        self.all_qualifiers = list(set(self.all_qualifiers))

        # read in keeps
        self.proc_keep = SETTINGS['proc_keep']
        '''

        # open classifiers
        clf = SETTINGS['clf']
        for c in clf.keys():
            self.classifiers[c] = {}
            self.classifiers[c]['clf'] = pickle.load(open(clf[c]['clf'], 'rb'))
            self.classifiers[c]['preproc'] = clf[c]['preproc']

        # init db / save
        if SETTINGS['do_db'] == True:
            path = Path(self.project) / "db"

            if path.is_dir() == False:
                os.makedirs("{}/db".format(self.project))

            self.db_fields = SETTINGS['db_fields']
            self.db_path = (path / "{}.db".format(SETTINGS['db_name'])).as_posix()
            self.db_table = SETTINGS['db_table']
            
            self.init_db()
        else:
            path = Path(self.project) / "db"
            if path.is_dir() == False:
                os.makedirs("{}/db".format(self.project))
                
            self.csv_save = SETTINGS['csv_save']

        logging.getLogger("messages").info("PIPELINE: init complete")

    def create_mapping(self):
        '''
        for f in self.main_dir.rglob("*.txt"):
            # find corresponding tagged directory
            date = datetime.strptime(f.stem[-7:], "%Y-%m")
            search_string = '_'+date.strftime("%Y%m")
            # obtain all matching tagged data
            zips = self.data_dir.rglob("*{}*.zip".format(search_string))
            zips = [t for t in zips]
            self.file_mapping[f.as_posix()] = zips
        '''
        pass
    
    def init_db(self):
        self.con = sqlite3.connect(self.db_path)

        # reset db
        cursor = self.con.cursor()
        cursor.execute("DROP TABLE IF EXISTS {}".format(self.db_table))

        # new db
        fields_string = ", ".join(self.db_fields)
        rules_string = ", ".join(list(map(lambda x: x.lower()+" INTEGER NOT NULL", self.tags)))
        create = "CREATE TABLE {} ({}, {})".format(self.db_table, fields_string, rules_string)
        cursor.execute(create)

        self.con.commit()
        logging.getLogger("messages").info("PIPELINE: {} table created".format(self.db_table))

    def get_data(self, csv):
        if self.main_dir is not None:
            all_dfs = []
            logging.getLogger("messages").info("PIPELINE: getting data from {} main files".format(len(self.settings['main']['files'])))
            for f in self.settings['main']['files']:
                temp_df = pd.read_csv(f, delimiter=self.settings['main']['delim'], 
                                encoding='latin-1', usecols=self.settings['main']['fields'])
                all_dfs.append(temp_df)

            complete_df = pd.concat(all_dfs, ignore_index=True)

            if self.settings['extract']['id'] is not None:
                complete_df = complete_df.rename(columns={self.settings['main']['id']:'id'})
                complete_df = complete_df.set_index('id')     
            complete_df.columns = map(str.lower, complete_df.columns)
        else:
            complete_df = None

        # load all csv data
        data = []
        cols = [x if x != self.settings['extract']['text'] else "text" for x in self.settings['extract']['fields']]

        logging.getLogger("messages").info("PIPELINE: getting data from {} extract files".format(len(csv)))
        for c in csv:
            temp_df = pd.read_csv(c, usecols=cols)
            data.append(temp_df)
        if self.settings['extract']['id'] is not None:
            df = pd.concat(data, axis=0, ignore_index=True)
            df = df.rename(columns={self.settings['extract']['id']:'id'}).set_index('id')

        return complete_df, df

    def preproc(self, tag, texts):
        #print("Preprocessing {}...".format(tag), flush=True)
        return _proc_helper_(self.proc_keywords[tag], self.proc_qualifiers[tag], self.proc_keep[tag], texts)

    def do_class(self, tag, texts):
        #print("Classifying {}...".format(tag), flush=True)
        return _class_helper_(self.classifiers[tag], self.proc_keywords[tag], texts)

    def merge_store(self, complete, csv):
        #print("Merging and storing to DB... ", end="", flush=True)
        logging.getLogger("messages").info("PIPELINE: merging and storing")

        if complete is None:
            merged_df = csv
        else:
            merged_df = complete.join(csv, how="left").fillna(0).astype(self.convert_t)

        # revert back to original column names
        merged_df.index.name = self.settings['extract']['id']
        if self.keep_text == True:
            merged_df = merged_df.rename(columns={'text':self.settings['extract']['text']})
           
        # check for already existing ids in db
        if self.settings['do_db'] == True:
            new_con = sqlite3.connect(self.db_path)
            include = []
            for tup in merged_df.itertuples():
                id = tup[0]
                cursor = new_con.cursor()
                cursor.execute("select {} from {} where {}={};".format(self.settings['extract']['id'], 
                                self.db_table, self.settings['extract']['id'], id))
                res = cursor.fetchall()
                if len(res) > 0:
                    include.append(0)
                else:
                    include.append(1)
                cursor.close()
            
            merged_df['include'] = include

            merged_df = merged_df[merged_df['include'] == 1]
            merged_df = merged_df.drop(['include'], axis=1)

        merged_df = merged_df[~merged_df.index.duplicated(keep='first')]

        if self.settings['do_db'] == True:
            logging.getLogger("messages").info("PIPELINE: saved to DB ({})".format(self.db_table))
            merged_df.to_sql(self.db_table, con=self.con, if_exists="append")
        else:
            logging.getLogger("messages").info("PIPELINE: saved to CSV ({})".format(self.csv_save))
            merged_df.to_csv(self.csv_save)
        #print("Finished.")

    def do_pipeline(self):
        #to_do = [f for f in self.data_dir.rglob("*{}".format(self.settings['extract']['ext']))]
        to_do = self.settings['extract']['files']

        yield "Extracting"
        logging.getLogger("messages").info("PIPELINE: extraction started")
        e = Extract(to_do, self.csv_dir, self.settings['extract']['fields'], 
                    self.n, SETTINGS=self.project_settings, KEYS=self.all_keywords, MODE=self.MODE,
                    FILE_EXT=self.settings['file_extract'])
        csv_files = e.extract()

        yield "Retrieving Data"
        complete, csv = self.get_data(csv_files)

        tags_to_class = self.tags

        for idx, t in enumerate(tags_to_class):
            logging.getLogger("messages").info("PIPELINE: classifying tag {}/{} ({})".format(idx+1, len(tags_to_class), t))
            #if self.classifiers[t]["preproc"] == True:
            #    csv['trimmed'] = self.preproc(t, csv['text'])
            #    csv[t] = self.do_class(t, csv['trimmed'])
            #else:
            yield "Classifying {}".format(t)
            csv[t] = self.do_class(t, csv['text'])

        if self.keep_text == False:
            csv = csv.drop(columns=['text', 'trimmed'], axis=1, errors='ignore')

        yield "Storing"
        self.merge_store(complete, csv)

        del complete
        del csv
        yield "Pipeline Complete."
