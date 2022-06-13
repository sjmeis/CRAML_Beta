# Author: Stephen Meisenbacher
# class for Full Extract Extrapolation
from re import sub
import sys
import pandas as pd
import swifter
from pathlib import Path
import random
import multiprocessing as mp
import logging
from contextlib import closing
import re
from pandarallel import pandarallel

pandarallel.initialize()

class Extrapolate:
    pid = None
    project = None
    basename = None
    files = None
    rule_files = None
    id = None

    def __init__(self, pid, basename, files, rfs, project, id):
        self.pid = pid
        self.project = project
        self.basename = basename
        self.files = files
        self.rule_files = rfs
        self.id = id

        logging.getLogger("messages").info("EXTRAPOLATE: init complete")

    def get_matches(self, row, rules, tags, rule_tags):
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

        ret_dict = {}
        if len(temp) > 0:
            top = max(temp, key=lambda x: x['match'])
            #return pd.Series({k:top[k] for k in tags})
            for k in tags:
                ret_dict['chunk'] = top['chunk']
                ret_dict['rule'] = top['rule']
                ret_dict[k] = top[k]
                ret_dict['indices'] = ';'.join([str(x) for x in matched_ones])
            if len(ret_dict.keys()) > 0:
                return pd.Series(ret_dict)
            else:
                return pd.Series({k:0 for k in tags})
        else:
            return pd.Series({k:0 for k in tags})
        #    for k in tags:
        #        ret_dict['chunk'] = top['chunk']
        #        ret_dict['rule'] = top['rule']
        #        ret_dict[k] = 0
        #        ret_dict['indices'] = ';'.join([str(x) for x in matched_ones])
        #    return pd.Series({k:0 for k in tags})
        

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

            #res = sub_df.swifter.progress_bar(False).apply(lambda x: self.get_matches(x, rules, tags, rule_tags), axis=1)
            data = sub_df.parallel_apply(lambda x: self.get_matches(x, rules, tags, rule_tags), axis=1)
            if data is None or len(data.index) == 0:
                continue
            
            if any(x in tags for x in sub_df.columns[2:]):
                to_add = [x for x in tags if x in sub_df.columns[2:]]
                sub_df = sub_df.join(data, how="left", lsuffix='_left', rsuffix='_right').fillna(0)
                for a in to_add:
                    sub_df[a] = sub_df.apply(lambda x: 1 if (x[a+'_left'] + x[a+'_right']) > 0 else 0, axis=1)
                    sub_df = sub_df.drop(columns=[a+'_left', a+'_right'])
            else:
                sub_df = sub_df.join(data, how="left").fillna(0)

        sub_df = sub_df.reset_index()
        return sub_df

    def extrapolate(self):
        logging.getLogger("messages").info("EXTRAPOLATE: extrapolation begun")

        all_data = []
        #with closing(mp.Pool(mp.cpu_count())) as pool:
        #    all_data = list(pool.map(self.__extra_helper__, self.files))
        for f in self.files:
            all_data.append(self.__extra_helper__(f))

        logging.getLogger("messages").info("EXTRAPOLATE: merging results")
        merged = pd.concat(all_data, ignore_index=True)
        del all_data
        merged = merged.sample(frac=1, random_state=42)

        name = Path(self.project) / "csv" / str(self.pid) / "{}_full.csv".format(self.basename)
        merged.to_csv(name.as_posix(), index=False)
        return name