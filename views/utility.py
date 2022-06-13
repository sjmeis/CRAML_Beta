# Author: Stephen Meisenbacher
# utility functions

import os
import json
from pathlib import Path
import psutil
from datetime import datetime
import pandas as pd
import logging
import platform
import subprocess

import zlib
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d

def open_file(path):
    logging.getLogger("messages").info("Opening {}".format(path.as_posix()))
    if platform.system() == "Darwin":
        subprocess.call(('open', path))
    elif platform.system() == "Windows":
        os.startfile(path)
    else:
        subprocess.call(('xdg-open', path))

def get_duration(start):
    diff = datetime.now() - start
    return round(diff.total_seconds(), 2)

def get_settings(project):
    path = Path(project) / "settings.json"

    if path.is_file() == False:
        return None
    else:
        with open(path.as_posix(), 'r') as f:
            settings = json.load(f)
        return settings

def get_keywords(project):
    if project is None:
        return {}

    path = Path(project) / "keywords.json"

    if path.is_file():
        with open(path.as_posix(), 'r') as f:
            KEYWORDS = json.load(f)
    else:
        with open(path.as_posix(), 'w') as out:
            json.dump({}, out, indent=3)
        KEYWORDS = {}
    return KEYWORDS

def save_keywords(project, keywords):
    save_path = (Path(project) / "keywords.json").as_posix()
    with open(save_path, 'w') as out:
            json.dump(keywords, out, indent=3)
    logging.getLogger("messages").info("Keywords written to {}".format(save_path))

def get_rules(project):
    if project is None:
        return []

    path = Path(project) / "rules"

    if path.is_dir():
        files = path.rglob("*csv")
        files = [x for x in files]
    else:
        os.makedirs(path.as_posix())
        files = []
    return files

def get_rule_files(project):
    options = []
    path = Path(project) / "rules"
    for f in path.rglob("*csv"):
        options.append({"label":f.stem, "value":f.stem})
    return options

def get_ext_log(project, first=False):
    if project is None:
        return []

    path = Path(project) / "logs" / "ext_procs.json"

    if path.is_file() == False:
        with open(path.as_posix(), 'w') as out:
            json.dump([], out)
        log = []
    else:
        with open(path.as_posix(), 'r') as f:
            log = json.load(f)

    if first == True:
        new_log = []
        procs = [p.pid for p in psutil.process_iter(attrs=["pid"])]

        for l in log:
            if l['status'] != "Finished" and l['status'] != "Removed":
                if int(l['pid']) not in procs:
                    l['status'] = "Finished"
                    l['elapsed'] = str(l['elapsed'])+'+'
            new_log.append(l)
        log = new_log
        update_ext_log(log, project)

    return log

def update_ext_log(new_data, project):
    with open((Path(project) / "logs" / "ext_procs.json").as_posix(), 'w') as out:
        json.dump(new_data, out, indent=3)

def get_ex_log_train(project):
    if project is None:
        return {}

    path = Path(project) / "logs" / "ext_procs.json"

    if path.is_file() == False:
        with open(path.as_posix(), 'w') as out:
            json.dump([], out)
        return []
    else:
        with open(path.as_posix(), 'r') as f:
            log = json.load(f)
        return {item['pid']:item for item in log}

def get_nb_log(project, first=False):
    if project is None:
        return []

    path = Path(project) / "logs" / "nb_train_procs.json"

    if path.is_file() == False:
        with open(path.as_posix(), 'w') as out:
            json.dump([], out)
        log = []
    else:
        with open(path.as_posix(), 'r') as f:
            log = json.load(f)

    if first == True:
        new_log = []
        procs = [p.pid for p in psutil.process_iter(attrs=["pid"])]

        for l in log:
            if l['status'] != "Finished" and l['status'] != "Removed":
                if int(l['pid']) not in procs:
                    l['status'] = "Finished"
                    l['elapsed'] = str(l['elapsed'])+'+'
            new_log.append(l)
        update_nb_log(new_log, project)
        for l in new_log:
            del l['log']
        log = new_log

    return log

def update_nb_log(d, project):
    with open((Path(project) / "logs" / "nb_train_procs.json").as_posix(), 'w') as out:
        json.dump(d, out, indent=3)

def get_rf_log(project, first=False):
    if project is None:
        return []

    path = Path(project) / "logs" / "rf_train_procs.json"

    if path.is_file() == False:
        with open(path.as_posix(), 'w') as out:
            json.dump([], out)
        log = []
    else:
        with open(path.as_posix(), 'r') as f:
            log = json.load(f)

    if first == True:
        new_log = []
        procs = [p.pid for p in psutil.process_iter(attrs=["pid"])]

        for l in log:
            if l['status'] != "Finished" and l['status'] != "Removed":
                if int(l['pid']) not in procs:
                    l['status'] == "Finished"
                    l['elapsed'] = str(l['elapsed'])+'+'
            new_log.append(l)
        update_rf_log(new_log, project)
        for l in new_log:
            del l['log']
        log = new_log

    return log

def update_rf_log(d, project):
    with open((Path(project) / "logs" / "rf_train_procs.json").as_posix(), 'w') as out:
        json.dump(d, out, indent=3)

def get_train_logs(project):
    if project is None:
        return []

    rf_path = Path(project) / "logs" / "rf_train_procs.json"
    nb_path = Path(project) / "logs" / "nb_train_procs.json"

    rf = []
    nb = []
    if rf_path.is_file() == True:
        with open(rf_path.as_posix(), 'r') as f:
            rf = json.load(f)

    if nb_path.is_file() == True:
        with open(nb_path.as_posix(), 'r') as f:
            nb = json.load(f)

    all_logs = rf+nb
    all_logs = [x for x in all_logs if x['status'] == "Finished"]
    return all_logs

def get_options(project, FULL=False):
    if project is None:
        return []

    log = get_ext_log(project)

    options = []
    for l in log:
        if l['status'] != "Finished":
            continue

        if FULL == False and "FULL EXTRACT" in l['name']:
            continue
        elif FULL == True and "SAMPLE EXTRACT" in l['name']:
            continue

        path = Path(project) / "csv" / l['pid']
        if path.is_dir():
            info = "pid: {}, {}".format(l['pid'], l['name'])
            for file in path.rglob("*.csv"):
                cols = pd.read_csv(file).columns
                if "text" in cols:
                    options.append({"label":info, "value":l['pid']})
                else:
                    options.append({"label":info, "value":l['pid'], "disabled":True})
                break
    return list(reversed(options))

def get_pipeline_log(project, first=False):
    if project is None:
        return []

    path = Path(project) / "logs" / "pipe_procs.json"

    if path.is_file() == False:
        with open(path.as_posix(), 'w') as out:
            log = json.dump([], out)
        log = []
    else:
        with open(path.as_posix(), 'r') as f:
            log = json.load(f)

    if first == True:
        new_log = []
        procs = [p.pid for p in psutil.process_iter(attrs=["pid"])]

        for l in log:
            if l['status'] != "Finished" and l['status'] != "Removed":
                if int(l['pid']) not in procs:
                    l['status'] = "Finished"
                    l['elapsed'] = str(l['elapsed'])+'+'
            new_log.append(l)
        log = new_log

    return list(reversed(log))

def update_pipe_log(d, project):
    with open((Path(project) / "logs" / "pipe_procs.json").as_posix(), 'w') as out:
            json.dump(d, out, indent=3)

def p_encode(p):
    return b64e(zlib.compress(p.encode(), 9)).decode()
def p_decode(b):
    return zlib.decompress(b64d(b.encode())).decode()