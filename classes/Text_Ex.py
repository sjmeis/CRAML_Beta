# Author: Stephen Meisenbacher
# November 22, 2021
# Text_Ex.py
# class for learn_rules.py

import pandas as pd
import logging

import nltk
nltk.download("punkt", quiet=True)
from nltk.tokenize import word_tokenize, sent_tokenize

from pathlib import Path
#import multiprocessing
import multiprocess as mp
import swifter
from contextlib import closing

from collections import Counter

def left_trim(x, n):
    return max(0, int(len(x.split())/2) - n)
def right_trim(x,n):
    return min(len(x), int(len(x.split())/2) + n) + 1

def left_trim_sent(x, n):
    return max(0, int(len(sent_tokenize(x))/2) - n)
def right_trim_sent(x,n):
    return min(len(x), int(len(sent_tokenize(x))/2) + n) + 1

def get_context_new(text, n, mode, keys):
    chunks = text.split('|')
    chunks = [x for x in chunks if any(k in x for k in keys)]
    if mode == "word":
        chunks = list(map(lambda x: " ".join(x.split()[left_trim(x,n):right_trim(x,n)]), chunks))
    else:
        chunks = list(map(lambda x: " ".join(sent_tokenize(x)[left_trim_sent(x,n):right_trim_sent(x,n)]), chunks))
    local_counts = Counter(chunks)
    return local_counts

class Text_Ex:

    x = None # top-/random-x
    n = None
    parent = None
    keywords = None
    mode = None
    chunk = None

    def __init__(self, x, n, parent, keywords, mode, CHUNK="word"):
        self.x = x
        self.n = n
        self.parent = parent
        self.keywords = keywords
        self.mode = mode
        self.chunk = CHUNK
        self.num_procs = int(0.75 * mp.cpu_count())
        logging.getLogger("messages").info("TEXT EXTRACT: init complete")


    def _helper_(self, fname):
        df = pd.read_csv(fname)
        counts = df["text"].swifter.progress_bar(False).apply(get_context_new, args=[self.n, self.chunk, self.keywords]).to_list()
        return counts

    def do_lr(self):
        path = Path(self.parent).rglob("*.csv")
        files = [x for x in path]
        global_counts = Counter()
        logging.getLogger("messages").info("TEXT EXTRACT: running on {} file(s)".format(len(files)))
        with closing(mp.Pool(self.num_procs)) as pool:
            all_counts = pool.map(self._helper_, files)
            flat = [i for s in all_counts for i in s]
            for c in flat:
                global_counts.update(c)

        logging.getLogger("messages").info("TEXT EXTRACT: counting complete, sampling...")
        df = pd.DataFrame.from_dict(global_counts, orient='index', columns=['count']).reset_index().sort_values(by=['count'], ascending=False)
        df = df.rename(columns={"index":"chunk"})
        if self.mode == "RANDOM":
            sample_frac = float(self.x / len(df.index))
            df = df.sample(frac=sample_frac)
        elif self.mode == "TOP":
            df = df.head(self.x)
        
        return df.to_dict('records')



