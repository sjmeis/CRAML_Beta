# Author: Stephen Meisenbacher
# class for Full Extract Extrapolation

import sys
import pandas as pd
import numpy as np
import swifter
from pathlib import Path
import multiprocessing as mp
import logging
from contextlib import closing
from pandarallel import pandarallel

from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

pandarallel.initialize()

class Extrapolate:
    pid = None
    project = None
    basename = None
    files = None
    rule_files = None
    id = None
    THRESHOLD = None
    model = None
    EMBED = False
    KEYWORDS = None

    def __init__(self, pid, basename, files, rfs, project, id, THRESHOLD=None, EMBED=False, KEYWORDS=None):
        self.pid = pid
        self.project = project
        self.basename = basename
        self.files = files
        self.rule_files = rfs
        self.id = id
        self.THRESHOLD = THRESHOLD
        self.EMBED = EMBED
        if self.EMBED == True:
            self.KEYWORDS = KEYWORDS
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device="cpu")
            self.class_vectors = self.create_class_vectors(self.rule_files)
            logging.getLogger("messages").info("EXTRAPOLATE (EMBED): init complete")
        else:
            logging.getLogger("messages").info("EXTRAPOLATE: init complete")

    def get_matches(self, row, rules, tags, rule_tags):
        import pandas as pd
        import re
        import random
        from collections import OrderedDict

        text = row['text']

        temp = []
        splitted = text.split('|')
        matched_indices = []
        matched_ones = []
        for r in rules:
            match = []
            for idx, x in enumerate(splitted):
                found_match = False
                if "REGEX" in r:
                    regex = re.compile(r.split(':::')[1])
                    if re.search(regex, x):
                        match.append((x,1))
                elif r in x:
                    match.append((x,1))
                    found_match = True

                if found_match == True:
                    matched_indices.append(idx)
            random.shuffle(match)
            for m, z in zip(match, matched_indices):
                if m[1] == 1:
                    if any(rule_tags[r]['encoding'][code] == 1 for code in rule_tags[r]['encoding']):
                        matched_ones.append(z)
                    temp.append({**{"chunk":m[0], "rule": r, "match":int(rule_tags[r]['prio'])},**rule_tags[r]['encoding']})
                else:
                    temp.append({**{"chunk":m[0], "rule": r, "match":int(rule_tags[r]['prio'])},**{k:0 for k in rule_tags[r]['encoding'].keys()}})
        
        matched_ones = sorted(list(set(matched_ones)))

        ret_dict = OrderedDict()
        if len(temp) > 0:
            top = max(temp, key=lambda x: x['match'])
            #return pd.Series({k:top[k] for k in tags})
            for k in tags:
                #ret_dict['chunk'] = top['chunk']
                #ret_dict['rule'] = top['rule']
                #ret_dict['indices'] = ';'.join([str(x) for x in matched_ones])
                ret_dict[k] = top[k]
            if len(ret_dict.keys()) > 0:
                return pd.Series(ret_dict)
            else:
                return pd.Series({k:0 for k in tags})
        else:
            return pd.Series({k:0 for k in tags})
        
    def create_class_vectors(self, rule_files):
        class_vectors = {}
        for r in rule_files:
            df = pd.read_csv(r)
            tags = df.columns[2:].to_list()
            for t in tags:
                rules = df[df[t] == 1]["rule"].to_list()
                embeddings = self.model.encode(rules)
                avg = np.mean(embeddings, axis=0)
                class_vectors[t] = avg
                
        return class_vectors
    
    def embed_sim(self, class_vector, class_keywords, THRESHOLD, text):    
        text = [x for x in text.split('|') if any(y in x for y in class_keywords)]
        if len(text) == 0:
            return ""
        
        text_encode = self.model.encode(text)
        sim_scores = cos_sim(class_vector, text_encode)[0]
        if any(x > THRESHOLD for x in sim_scores):
            evidence = [text[i] for i, x in enumerate(sim_scores) if x > THRESHOLD]
            return "|".join(evidence)
        else:
            return ""

    def __extra_helper_embed__(self, fname): 
        sub_df = pd.read_csv(fname).set_index(self.id)

        if len(sub_df.index) == 0:
            return None

        for c in self.class_vectors: 
            class_vector = self.class_vectors[c]
            class_keywords = self.KEYWORDS[c]
            
            evidence = sub_df["text"].apply(lambda x: self.embed_sim(class_vector, class_keywords, self.THRESHOLD, x))
            mask = [True if x != "" else False for x in evidence]
            evidence = [x for x in evidence if x != ""]
            temp = sub_df[mask].copy()
            temp = temp.drop(["text"], axis=1)
            temp["{}_evidence".format(c)] = evidence
            temp[c] = 1
            data = temp[[c, "{}_evidence".format(c)]]
            del temp
            
            sub_df = sub_df.join(data, how="left").fillna(0)
            sub_df[c] = sub_df[c].astype(int)
            del data
            
        sub_df = sub_df.reset_index()
        return sub_df

    def __extra_helper__(self, fname):
        #print("Processing {}...".format(fname.stem), flush=True)
        sub_df = pd.read_csv(fname).set_index(self.id)

        if len(sub_df.index) == 0:
            return None

        for r in self.rule_files:
            rule_data = pd.read_csv(r)
            rules = rule_data['rule'].to_list()
            tags = rule_data.columns[2:].to_list()
            rule_tags = {}
            for _, row in rule_data.iterrows():
                rule_tags[row['rule']] = {}
                rule_tags[row['rule']]['encoding'] = row[2:].to_dict()
                rule_tags[row['rule']]['prio'] = row['prio']

            data = sub_df.swifter.progress_bar(False).apply(lambda x: self.get_matches(x, rules, tags, rule_tags), axis=1)
            #data = sub_df.parallel_apply(lambda x: self.get_matches(x, rules, tags, rule_tags), axis=1)
            if data is None or len(data.index) == 0:
                continue
            elif data.index.name != self.id:
                data.set_index(self.id)
            
            if any(x in tags for x in sub_df.columns[2:]):
                to_add = [x for x in tags if x in sub_df.columns[2:]]
                sub_df = sub_df.join(data, how="left", lsuffix='_left', rsuffix='_right').fillna(0)
                for a in to_add:
                    sub_df[a] = sub_df.apply(lambda x: 1 if (x[a+'_left'] + x[a+'_right']) > 0 else 0, axis=1)
                    sub_df[a] = sub_df[a].astype(int)
                    sub_df = sub_df.drop(columns=[a+'_left', a+'_right'])
            else:
                new_cols = [x for x in data.columns if x not in sub_df.columns]
                data = data[new_cols]
                for n in new_cols:
                    data[n] = data[n].astype(int)
                sub_df = sub_df.join(data, how="left").fillna(0)
                #non_rule = [x for x in sub_df.columns if x != "rule"]
                #sub_df[non_rule] = sub_df[non_rule].fillna(0)

        sub_df = sub_df.reset_index()
        return sub_df

    def extrapolate(self):
        logging.getLogger("messages").info("EXTRAPOLATE: extrapolation begun")

        all_data = []
        #with closing(mp.Pool(mp.cpu_count())) as pool:
        #    all_data = list(pool.map(self.__extra_helper__, self.files))
        for f in self.files:
            if self.EMBED == True:
                all_data.append(self.__extra_helper_embed__(f))
            else:
                all_data.append(self.__extra_helper__(f))

        logging.getLogger("messages").info("EXTRAPOLATE: merging results")
        merged = pd.concat(all_data, ignore_index=True)
        del all_data
        merged = merged.sample(frac=1, random_state=42)

        name = Path(self.project) / "csv" / str(self.pid) / "{}_full.csv".format(self.basename)
        merged.to_csv(name.as_posix(), index=False)
        return name