# Author: Stephen Meisenbacher
# November 23, 2021
# Train.py
# class for extrapolate + all things training

import os
import sys
import pandas as pd
import re
import swifter
from pathlib import Path
import random
import multiprocessing as mp
import pickle
import logging
from contextlib import closing
from pandarallel import pandarallel

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import  TfidfVectorizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from pure_sklearn.map import convert_estimator
import nltk
nltk.download("stopwords", quiet=True)
from nltk.corpus import stopwords

pandarallel.initialize()

def get_labels(data):
    labels = []
    for _, row in data.iterrows():
        labels.append(row[2:].to_numpy().astype('float32'))

    return np.stack(labels, axis=0)

def get_matches(text, neg_sample, rules, classes, rule_tags):
    temp = []
    splitted = text.split('|')
    for r in rules:
        match = []
        plus = 0
        for x in splitted:
            if "REGEX" in r:
                regex = re.compile(r.split(':::')[1])
                if re.search(regex, x):
                    match.append((x,1))
                    plus += 1
                elif plus > 0 and neg_sample == True:
                    if not any(ru in x for ru in rules):
                        match.append((x,0))
                        plus -= classes
            else:
                if r in x:
                    match.append((x,1))
                    plus += 1
                elif plus > 0 and neg_sample == True:
                    if not any(ru in x for ru in rules):
                        match.append((x,0))
                        plus -= classes
        random.shuffle(match)
        for m in match:
            if m[1] == 1:
                temp.append({**{"chunk":m[0], "rule": r, "match":rule_tags[r]['prio']},**rule_tags[r]['encoding']})
            else:
                temp.append({**{"chunk":m[0], "rule": r, "match":rule_tags[r]['prio']},**{k:0 for k in rule_tags[r]['encoding'].keys()}})
    
    return temp

class Train:
    pid = None
    project = None
    basename = None
    parent = None
    rule_file = None
    rules = None
    tags = None
    classes = None
    rule_tags = None
    sample = None
    neg_sample = False

    N_ESTIMATORS = None
    min_samples_split = None
    min_samples_leaf = None

    def __init__(self, pid, basename, parent, rf, sample, neg_sample, project, N_ESTIMATORS=None, min_samples_split=None, min_samples_leaf=None):
        self.pid = pid
        self.project = project
        self.basename = basename
        self.parent = Path(parent)
        self.rule_file = Path(rf)

        rule_data = pd.read_csv(self.rule_file)
        self.rules = rule_data['rule'].to_list()
        self.tags = rule_data.columns[2:].to_list()
        self.classes = len(self.tags)
        self.rule_tags = {}
        for _, row in rule_data.iterrows():
            self.rule_tags[row['rule']] = {}
            self.rule_tags[row['rule']]['encoding'] = row[2:].to_dict()
            self.rule_tags[row['rule']]['prio'] = row['prio']

        self.sample = float(sample)
        self.neg_sample = neg_sample

        self.N_ESTIMATORS = N_ESTIMATORS
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf

        logging.getLogger("messages").info("TRAIN: init complete")

    def __extra_helper__(self, fname):
        #print("Processing {}...".format(fname.stem), flush=True)
        sub_df = pd.read_csv(fname)
        
        if len(sub_df.index) == 0:
            return None
        else:
            sub_df = sub_df.sample(frac=self.sample, random_state=42)

        #res = sub_df['text'].swifter.progress_bar(False).apply(lambda x: self.get_matches(x))
        res = sub_df['text'].parallel_apply(lambda x: get_matches(x, self.neg_sample, self.rules, self.classes, self.rule_tags))
        del sub_df
        res = [x for s in res for x in s]
        data = pd.DataFrame(res)
        del res
        if len(data.index) == 0:
            return None
        else:
            data = data.sort_values("match", ascending=False).reset_index(drop=True)
            data = data.drop_duplicates("chunk").sample(frac=1).reset_index(drop=True)
            return data

    def extrapolate(self):
        logging.getLogger("messages").info("TRAIN: extrapolation begun")

        path = Path(self.parent).rglob("*.csv")
        files = [f for f in path]

        all_data = []
        #with closing(mp.Pool(mp.cpu_count())) as pool:
        #    all_data = list(pool.map(self.__extra_helper__, files))
        for f in files:
            all_data.append(self.__extra_helper__(f))

        merged = pd.concat(all_data, ignore_index=True)
        del all_data
        merged = merged.sort_values("match", ascending=False).reset_index(drop=True)
        merged = merged.sample(frac=1, random_state=42).reset_index(drop=True)
        merged = merged.drop(columns=["match"])

        if (Path(self.project) / "train" / str(self.pid)).is_dir() == False:
            os.makedirs((Path(self.project) / "train" / str(self.pid)).as_posix())

        name = Path(self.project) / "train" / str(self.pid) / self.basename
        merged.to_csv(name.as_posix(), index=False)
        return name

    def train_nb(self, train_file):
        # get training data
        data = pd.read_csv(train_file)
        classes = self.tags

        # split data
        train, test = train_test_split(data, random_state=42, test_size=0.2)
        X_train = train['chunk']
        X_test = test['chunk']

        # setup
        nb_pipeline = Pipeline([
                    ('tfidf', TfidfVectorizer(stop_words=stopwords.words('english'))),
                    ('clf', OneVsRestClassifier(MultinomialNB())),
                ])

        # train
        for c in classes:
            logging.getLogger("messages").info("TRAIN: nb training on {}".format(c))

            nb_pipeline.fit(X_train, train[c])
            pred = nb_pipeline.predict(X_test)
            acc = accuracy_score(test[c], pred)
            prec = precision_score(test[c], pred, zero_division=0)
            rec = recall_score(test[c], pred, zero_division=0)
            f1 = f1_score(test[c], pred, zero_division=0)

            name = "NB_{}-{}".format(self.sample, c)
            save_path = Path(self.project) / "train" / str(self.pid) / "clf" / name
            pickle.dump(nb_pipeline, open(save_path, 'wb'))
            logging.getLogger("messages").info("TRAIN: classifer saved to {}".format(save_path.as_posix()))

            yield {"class":c, "name":save_path.as_posix(), "Accuracy":round(acc,3), "Precision":round(prec,3), 
                    "Recall":round(rec,3), "F1":round(f1,3)}

    def train_rf(self, train_file):
        data = pd.read_csv(train_file)
        classes = self.tags

        # split data
        train, test = train_test_split(data, random_state=42, test_size=0.2)
        X_train = train['chunk']
        y_train = train.iloc[:,1:]
        X_test = test['chunk']
        y_test = np.array(test.iloc[:,1:])

        rf_pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(stop_words=stopwords.words('english'))),
                ('scale', StandardScaler(with_mean=False)),
                ('clf', RandomForestClassifier(n_estimators=self.N_ESTIMATORS, criterion="gini", 
                min_samples_leaf=self.min_samples_leaf, min_samples_split=self.min_samples_split, n_jobs=-1, random_state=42)),
            ])

        for c in classes:
            logging.getLogger("messages").info("TRAIN: rf training on {}".format(c))

            rf_pipeline.fit(X_train, train[c])
            pure_clf = convert_estimator(rf_pipeline)
            pred = pure_clf.predict(X_test)
            acc = accuracy_score(test[c], pred)
            prec = precision_score(test[c], pred, zero_division=0)
            rec = recall_score(test[c], pred, zero_division=0)
            f1 = f1_score(test[c], pred, zero_division=0)

            name = "RF_{}-{}".format(self.sample, c)
            save_path = Path(self.project) / "train" / str(self.pid) / "clf" / name
            pickle.dump(pure_clf, open(save_path, 'wb'))
            logging.getLogger("messages").info("TRAIN: classifer saved to {}".format(save_path.as_posix()))

            yield {"class":c, "name":save_path.as_posix(), "Accuracy":round(acc,3), "Precision":round(prec,3), 
                    "Recall":round(rec,3), "F1":round(f1,3)}