#!/usr/bin/env python3
# Author: Stephen Meisenbacher
# July 22, 2021
# Extract.py
# Class to implement extract.py

import os
import platform
import re
import pandas as pd
import numpy as np
from lxml import etree
from html import unescape
from bs4 import BeautifulSoup
import csv
import nltk
nltk.download("punkt", quiet=True)
from nltk.tokenize import word_tokenize, sent_tokenize
import logging

import zipfile
from pathlib import Path
if platform.system() == "Linux":
    import multiprocessing as mp
else:
    import multiprocess as mp
from contextlib import closing
from functools import partial

NUM_PROC = int(0.75 * mp.cpu_count())

# utility for quick cleaning text
def clean(text):
    if '&' in text:
        text = unescape(text.strip()) # remove html chars
    if '<' in text:
        text = BeautifulSoup(text, "lxml").text
    text = re.sub(r"www\S+", " ", text)
    text = re.sub(r"\b(?![ai])[a-zA-Z]\b", " ", text)
    text = re.sub(r"\d+", " ", text)
    text = " ".join(text.split()) # remove excess newlines
    text = text.replace(',','') # remove commas for easier csv readability
    text = text.replace(':','.').replace('*','.')
    text = text.replace(' .', '.')
    text = text.encode("ascii", "ignore").decode()
    # keyword specfic
    text = text.replace("-site", "site").replace(" site", "site")
    text = text.replace("-life", "life").replace(" life", "life")

    text = text.replace(" s "," ")

    return text

# generator to feed the pool workers xml entries
def generate_entries(xml, fields):
    xmls = [xml for _ in fields]
    for tup in zip(*xmls):
        temp = {fields[i]:y[1].text for i, y in enumerate(tup)}
        yield temp
        for z in tup:
            z[1].clear()

def get_context(text, keywords, n, MODE="word"):
    #n = 6
    if MODE == "word":
        text = re.sub(r'[^a-z0-9]+', ' ', text)
    else:
        text = re.sub(r'[^a-z0-9.!?]+', ' ', text)
        text = '. '.join(text.split('.'))
        if '?' in text:
            text = '? '.join(text.split('?'))
        if '!' in text:
            text = '! '.join(text.split('!'))
        text = text.replace('?', '.').replace('!', '.')

    if MODE == "word":
        words = text.split()
    else:
        #words = sent_tokenize(text)
        words = [x.strip() for x in text.split('.')]
        
    found_index = [i for i, w in enumerate(words) if any(k.strip() in w for k in keywords)]
    context = [" ".join(words[max(0, idx-n):min(idx+n+1, len(words))]) for idx in found_index]

    return '|'.join(context)

def _filter_helper_(arg):
    if any(a in arg[0] for a in arg[1]):
        return True
    else:
        return False

# filter the provided xml entries
# if the text contains keywords, find all sentences that do
def filter_data(entry, parent=None, sub_parent=None, KEYS=None, n=None, MODE=None):

    if parent is not None:
        if entry['filename'] == "":
            return None

        #if entry['filename'][0] == '[' and entry['filename'][-1] == ']':
        #    list_files = entry['filename'].strip('][').replace('\'', '').replace('\"', '').split(', ')
        if len(entry['filename'].split(';;')) > 1:
            list_files = entry['filename'].split(';;')
            temp_text = []
            for file in list_files:
                if sub_parent is not None:
                    filepath = Path(parent) / sub_parent / file
                elif 'parent' in entry:
                    filepath = Path(parent) / entry['parent'] / file
                else:
                    filepath = Path(parent) / file

                if filepath.is_file() == True:
                    with open(filepath.as_posix(), 'r') as f:
                        temp_text.append(f.read())
            if len(temp_text) > 0:
                text = " ".join(temp_text)
            else:
                return None
        else:
            if sub_parent is not None:
                    filepath = Path(parent) / sub_parent / entry['filename']
            elif 'parent' in entry:
                filepath = Path(parent) / entry['parent'] / entry['filename']
            else:
                filepath = Path(parent) / entry['filename']

            if filepath.is_file() == True:
                with open(filepath.as_posix(), 'r') as f:
                    text = f.read()
            else:
                return None
    else:
        text = entry["text"]

    if text is None or text == "":
        return None

    #keywords = global_keywords
    keywords = KEYS
    if any(w in text for w in keywords):
        # first roughly clean text
        text = clean(text)

        keep = []
        text = text.lower()
        args = ((text, k) for k in keywords)
        res = set(map(_filter_helper_, args))
        if True in res:
            context = get_context(text, keywords, n, MODE)
            keep.append(context)

        keep = list(set(keep)) # remove duplicates
        if parent is not None:
            return ":::".join([str(entry[x]) for x in entry.keys() if x != "filename"]+["|".join(keep)])
        else:
            return ":::".join([str(entry[x]) for x in entry.keys() if x != "text"]+["|".join(keep)])
    else:
        return None

# utility for creating pandas df
def split_and_dict(rows, fields):
    to_df = []
    for r in rows:
        splitted = r.split(':::')
        to_df.append({fields[i]:x for i, x in enumerate(splitted)})
    return to_df

# for merging with new keywords
def merge_helper(row):
    if row['text1'] == "empty":
        return row['text2']
    else:
        if row['text2'] == "empty":
            return row['text1']
        else:
            return row['text1'] + '|' + row['text2']

# for global keyword access
def init_pool(k, m, n):
    global global_keywords
    global global_mode
    global global_n

    global_keywords = k
    global_mode = m
    global_n = n

class Extract:
    keywords = None
    filelist = None
    csv_dir = None
    settings = None
    MODE = "word"
    n = None
    EXTRACT = None
    FILE_EXTRACT = None

    def __init__(self, ext_list, csv_dir, fields, n, KEYS=None, SETTINGS=None, MODE="Word", FILE_EXT=False):

        self.MODE = MODE
        self.n = n
        self.FILE_EXTRACT = FILE_EXT

        # read in keywords (search terms)
        self.keywords = KEYS

        if SETTINGS is not None:
            self.settings = SETTINGS

        self.filelist = {}
        for x in self.settings.keys():
            if self.settings[x]['extract'] != "None":
                self.EXTRACT = self.settings[x]['extract']
                self.filelist[x] = {}
                self.filelist[x]["ext"] = self.settings[x]["ext"]
                self.filelist[x]["delim"] = self.settings[x]["delim"]
                self.filelist[x]["files"] = sorted([Path(f) for f in ext_list], reverse=True)
                self.filelist[x]["fields"] = self.settings[x]["fields"]
        self.csv_dir = Path(csv_dir)

        logging.getLogger("messages").info("EXTRACT: init complete, extract: {}, mode: {}, file_extract: {}".format(self.EXTRACT, self.MODE, self.FILE_EXTRACT))

    def set_path(self, pid):
        self.csv_dir = Path(self.csv_dir) / pid

    def get_path(self):
        return self.csv_dir

    def get_file_text(self, parent, filename):
        path = (Path(parent) / filename)
        if path.is_file() == True:
            with open(path.as_posix(), 'r') as f:
                text = f.read()
        else:
            text = ""
        return text

    def extract(self):
        saved = []
        with closing(mp.Pool(NUM_PROC, init_pool(self.keywords, self.MODE, self.n))) as pool:
            for x in self.filelist.keys():
                total_files = len(self.filelist[x]['files'])
                for idx, fname in enumerate(self.filelist[x]["files"]):
                    logging.getLogger("messages").info("EXTRACT: processing file {}/{} for input {} - {}".format(idx+1, total_files, x, fname.stem))
                    if "zip" in self.filelist[x]["ext"].lower():
                        with zipfile.ZipFile(Path(fname).as_posix(),'r') as z:
                            # go through all files in zip (should just be one)
                            for subd in z.namelist():
                                with z.open(subd) as f:
                                    fields = self.filelist[x]["fields"].copy()
                                    to_change = None
                                    if self.EXTRACT is not None:
                                        change = None
                                        for i, find in enumerate(fields):
                                            if find == self.EXTRACT:
                                                change = i
                                                break
                                        to_change = fields[change]
                                        fields[change] = "text"

                                    if "xml" in os.path.splitext(subd)[1]:
                                        if self.EXTRACT is not None:
                                            tags = tuple(t for t in self.filelist[x]["fields"] if t != to_change) + (to_change,)
                                            xml = etree.iterparse(f, events=('end',), tag=tags)
                                            rows = list(pool.imap_unordered(partial(filter_data, KEYS=self.keys), generate_entries(xml, fields), chunksize=10)) # start filter job
                                            rows = list(filter(None, rows)) # remove entries where nothing was found 
                                        else:
                                            tags = tuple(t for t in self.filelist[x]["fields"])
                                            xml = etree.iterparse(f, events=('end',), tag=tags)
                                            rows = list(generate_entries(xml, fields))
                                            rows = [":::".join(x) for x in rows] 
                                            rows = list(filter(None, rows)) 
                                        del xml
                                    else:
                                        data = pd.read_csv(f, dtype=str, delimiter=self.filelist[x]["delim"])[self.filelist[x]["fields"]]
                                        if self.EXTRACT is not None:
                                            if self.FILE_EXTRACT == False:
                                                data = data.rename(columns={to_change:"text"})
                                                data = data[fields]
                                                rows = data.to_dict('records')
                                                rows = pool.imap_unordered(partial(filter_data, KEYS=self.keys), rows, chunksize=10)
                                                rows = [row for row in rows]
                                                rows = list(filter(None, rows))
                                            else:
                                                sub_parent = None
                                                if total_files > 1:
                                                    data['parent'] = fname.stem
                                                    sub_parent = fname.stem
                                                    fields.append("parent")
                                                elif len(self.settings[x]['files']) > 1 and "sample" in fname.as_posix():
                                                    fields.append("parent")
                                                    data = pd.read_csv(fname, dtype=str, delimiter=self.settings[x]["delim"])[fields]

                                                data = data.rename(columns={to_change:"filename"})
                                                data['filename'] = data['filename'].fillna("")
                                                parent = self.settings[x]["file_extract_dir"]
                                                data = data[fields]
                                                rows = data.to_dict('records')
                                                rows = pool.imap_unordered(partial(filter_data, parent=parent, sub_parent=sub_parent, KEYS=self.keywords, n=self.n, MODE=self.MODE), rows, chunksize=10)
                                                rows = [row for row in rows]
                                                rows = list(filter(None, rows))
                                        else:
                                            rows = data.to_dict('records')
                                            rows = [":::".join(x) for x in rows]

                                    if self.FILE_EXTRACT == True:
                                        fields = [x for x in fields if x != "filename"]+["text"] 
                                    else: 
                                        fields = [x for x in fields if x != "text"]+["text"]
                                    # export to dataframe and then to csv
                                    fields = [x for x in fields if x != "text"]+["text"]
                                    to_df = split_and_dict(rows, fields)
                                    del rows
                                    df = pd.DataFrame(to_df, columns=fields)
                                    del to_df
                                    df = df.replace("", np.nan)
                                    df = df.dropna()
                                    save_name = self.csv_dir / (Path(fname).stem+".csv")
                                    df.to_csv(save_name, index=False, quoting=0)
                                    saved.append(save_name)
                                    del df
                    else:
                        fields = self.filelist[x]["fields"].copy()
                        to_change = None
                        if self.EXTRACT is not None:
                            change = None
                            for i, find in enumerate(fields):
                                if find == self.EXTRACT:
                                    change = i
                                    break
                            to_change = fields[change]
                            if self.FILE_EXTRACT == True:
                                fields[change] = "filename"
                            else:
                                fields[change] = "text"

                        if "xml" in os.path.splitext(fname.name)[1]:
                            with open(fname, 'rb') as f:
                                if self.EXTRACT is not None:
                                    tags = tuple(t for t in self.filelist[x]["fields"] if t != to_change) + (to_change,)
                                    xml = etree.iterparse(f, events=('end',), tag=tags)
                                    rows = list(pool.imap_unordered(partial(filter_data, KEYS=self.keys), generate_entries(xml, fields), chunksize=10)) # start filter job
                                    rows = list(filter(None, rows)) # remove entries where nothing was found 
                                else:
                                    tags = tuple(t for t in self.filelist[x]["fields"])
                                    xml = etree.iterparse(f, events=('end',), tag=tags)
                                    rows = list(generate_entries(xml, fields))
                                    rows = [":::".join(x) for x in rows] 
                                    rows = list(filter(None, rows)) 
                            del xml
                        else:
                            data = pd.read_csv(fname, dtype=str, delimiter=self.settings[x]["delim"])[self.filelist[x]["fields"]]
                            if self.EXTRACT is not None:
                                if self.FILE_EXTRACT == False:
                                    data = data.rename(columns={to_change:"text"})
                                    data = data[fields]
                                    rows = data.to_dict('records')
                                    rows = pool.imap_unordered(partial(filter_data, KEYS=self.keys), rows, chunksize=10)
                                    rows = [row for row in rows]
                                    rows = list(filter(None, rows))
                                else:
                                    sub_parent = None
                                    if total_files > 1:
                                        data['parent'] = fname.stem
                                        sub_parent = fname.stem
                                        fields.append("parent")
                                    elif len(self.settings[x]['files']) > 1 and "sample" in fname.as_posix():
                                        fields.append("parent")
                                        data = pd.read_csv(fname, dtype=str, delimiter=self.settings[x]["delim"])[fields]

                                    data = data.rename(columns={to_change:"filename"})
                                    data['filename'] = data['filename'].fillna("")
                                    parent = self.settings[x]["file_extract_dir"]
                                    data = data[fields]
                                    rows = data.to_dict('records')
                                    rows = pool.imap_unordered(partial(filter_data, parent=parent, sub_parent=sub_parent, KEYS=self.keywords, n=self.n, MODE=self.MODE), rows, chunksize=10)
                                    rows = [row for row in rows]
                                    rows = list(filter(None, rows))
                            else:
                                rows = data.to_dict('records')
                                rows = [":::".join(x) for x in rows]

                        # export to dataframe and then to csv
                        if self.FILE_EXTRACT == True:
                            fields = [x for x in fields if x != "filename"]+["text"] 
                        else: 
                            fields = [x for x in fields if x != "text"]+["text"]
                        to_df = split_and_dict(rows, fields)
                        del rows
                        df = pd.DataFrame(to_df, columns=fields)
                        del to_df
                        df = df.replace("", np.nan)
                        df = df.dropna()
                        save_name = self.csv_dir / (Path(fname).stem+".csv")
                        df.to_csv(save_name, index=False, quoting=0)
                        saved.append(save_name)
                        del df
                    
            pool.close()
            pool.join()
        return saved
