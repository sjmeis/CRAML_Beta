# Author: Stephen Meisenbacher
# view for dataset creation, i.e. full pipeline run

import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
from multiprocessing import Process, Queue
import queue
import shutil
import sqlite3
import logging

import time
import random

import dash
from dash import dcc
import dash_bootstrap_components as dbc
from dash import html
import dash_daq as daq
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash import dash_table

from server import app
from .utility import get_duration, get_settings, get_keywords, get_rule_files, get_train_logs, get_pipeline_log, update_pipe_log

sys.path.append("classes")
from Pipeline import Pipeline

def get_clfs(tag, display, project, idx):
    logs = get_train_logs(project)
    t_clf = []
    for x in logs:
        for y in x['log']['results']:
            if y['class'] == tag:
                t_clf.append((y['name'], y['F1']))    
    options = [{"label":"{} (F1: {})".format(x[0], x[1]), "value":x[0]} for x in t_clf]
    if display == True:
        style = {"padding":"1rem"}
    else:
        style = {"display":"none"}

    return html.Div(
            [
                dbc.Label(tag, html_for="dropdown"),
                dcc.Dropdown(
                    #id="{}-dropdown".format(tag),
                    id={'type':'clf-dropdown', 'index':idx},
                    options=options,
                    placeholder="Select classifier for {}".format(tag),
                    persistence="session"
                ),
            ],
            #className="mb-3",
            style=style
        )

def get_rules(project):
    return html.Div([
        dcc.Dropdown(
            id='pipe-rule-drop',
            options=get_rule_files(project),
            value=None,
            placeholder="Select rule files to use.",
            multi=True,
            persistence="session"
        ),
        html.Div(id='rule-drop-output')
    ], style={"padding":"2rem"})

def get_class(tags, project):
    keys = get_keywords(project).keys()
    if tags is None:
        return [html.Div("No rules / tags selected. Start at the Rules tab.")]+\
                [get_clfs(x, False, project, i) for i, x in enumerate(get_keywords(project).keys())]
    else:
        drops = []
        for i, t in enumerate(keys):
            if t in tags:
                drops.append(get_clfs(t, True, project, i))
            else:
                 drops.append(get_clfs(t, False, project, i))
        return drops

def get_save():
    switch1 = html.Div(children=[html.Div(html.P(children="Keep Text? \t"), style={"display":"inline-block", "padding-right":"1rem"}), 
                html.Div(daq.BooleanSwitch(id="keep-switch", on=True, persistence="session"), style={"display":"inline-block"})], 
                style={"display":"inline-block", "padding":"2rem"})

    switch2 = html.Div(children=[html.Div(html.P(children="Save to Database? \t"), style={"display":"inline-block", "padding-right":"1rem"}), 
                html.Div(daq.BooleanSwitch(id="db-switch", on=False, persistence="session"), style={"display":"inline-block"})], 
                style={"display":"inline-block", "padding":"2rem"})

    db = html.Div(id="save-div",
                children=[html.Div(children=[html.Div([dbc.Label("Database Name"),
                                            dbc.Input(id="db-name-input", 
                                            placeholder="Input database file name",
                                            debounce=True, type="text", 
                                            persistence="session",
                                            style={"padding-top":"1rem", "width":"35rem", "display":"inline-block"})],
                                            style={"display":"inline-block", "padding":"1rem"}),
                                        html.Div([dbc.Label("Table Name"),
                                        dbc.Input(id="db-table-input", 
                                            placeholder="Input database table name",
                                            debounce=True, type="text", 
                                            persistence="session",
                                            style={"padding-top":"1rem", "width":"35rem", "display":"inline-block"})],
                                            style={"display":"inline-block", "padding":"1rem"}),
                                        dbc.Alert(
                                            "Table already exists - will be overwritten if you continue.",
                                            color="danger",
                                            id="dup-alert",
                                            is_open=False,
                                            dismissable=True
                                        )
                                        ], 
                                    style={"display":"inline-block"})], 
                style={"display":"inline-block", "padding":"1rem"})

    fields = html.Div(id="fields-group", children=None)

    return html.Div(children=[switch1, switch2, db, html.Hr(), 
            html.H5(id="pipe-h5", children="Please select field types for database."), fields])

def get_fields(project, keep):
    i = 0
    children = []
    settings = get_settings(project)
    for k in settings:
        if settings[k]['extract'] != "None":
            children.append(dbc.Label("Extracted Data:"))
        else:
            children.append(dbc.Label("Metadata:"))
        
        for f in settings[k]['fields']:
            init_val = None
            if settings[k]['extract'] != "None" and f == settings[k]['extract']:
                init_val = "TEXT"

            if f == settings[k]['extract'] and keep == False:
                continue

            if init_val is not None:
                temp = dbc.InputGroup([
                            #dbc.RadioButton(id={'type':'field-radio', 'index':i}),
                            dbc.InputGroupText(id={'type':'field-text', 'index':i}, children=f),
                            dbc.Select(id={'type':'field-drop', 'index':i},
                                options=[
                                    {"label": "INTEGER", "value": "INTEGER", "disabled":True},
                                    {"label": "REAL", "value": "REAL", "disabled":True},
                                    {"label": "TEXT", "value": "TEXT"}
                                ],
                                value = init_val,
                                persistence="session"
                            )
                            ])
            else:
                temp = dbc.InputGroup([
                        #dbc.RadioButton(id={'type':'field-radio', 'index':i}),
                        dbc.InputGroupText(id={'type':'field-text', 'index':i}, children=f),
                        dbc.Select(id={'type':'field-drop', 'index':i},
                            options=[
                                {"label": "INTEGER", "value": "INTEGER"},
                                {"label": "REAL", "value": "REAL"},
                                {"label": "TEXT", "value": "TEXT"}
                            ],
                            placeholder="Select data type for {}".format(f),
                            persistence="session"
                        )
                        ])
            i += 1
            children.append(temp)

    return [html.P(id="fields-p", children="Primary Key: None")] + children

def get_extra():
    switch = html.Div(children=[html.Div(html.P(id="left-p-d", children="Word Chunks \t"), style={"display":"inline-block", "padding-right":"1rem"}), 
                html.Div(daq.BooleanSwitch(id="d-switch", on=False), style={"display":"inline-block"}),
                html.Div(html.P(id="right-p-d", children="\t Sentence Chunks"), style={"display":"inline-block", "padding":"1rem"})], 
                style={"display":"inline-block", "padding":"1rem"})

    n_input = html.Div(children=[daq.NumericInput(
                    id='d-n',
                    min=0,
                    max=20,
                    value=6,
                    label='N',
                    labelPosition='bottom',
                    style={"display":"inline-block"})], 
                style={"display":"inline-block", "padding":"2rem"})

    return [switch, n_input]

def get_layout(project):

    dialog = dcc.ConfirmDialog(id="pipe-dialog", message=None, displayed=False)
    del_dialog = dcc.ConfirmDialog(id="pipe-del-dialog", message=None, displayed=False)

    tabs = dcc.Tabs(id="pipeline-tabs", value=None, children=[
                dcc.Tab(label="1. Rules", value="Rules", id="pipeline-tab-rules", children=get_rules(project)),
                dcc.Tab(label="2. Extrapolate", value="Extrapolate", id="pipeline-tab-extra", children=get_extra()),                
                dcc.Tab(label="3. Save", value="Save", id="pipeline-tab-save", children=get_save()),
                dcc.Tab(label="4. Classifiers", value="Classifiers", id="pipeline-tab-class", 
                        children=dbc.Form(id="class-form", children=get_class(None, project)))
            ])

    columns = [{"id":"name", "name":"name", "type":"text", "presentation":"markdown"}]+\
            [{"id":x, "name":x, "type":"text"} for x in ["start", "elapsed", "status"]]
    table = dash_table.DataTable(
                id="pipe-table",
                columns=columns,
                data=get_pipeline_log(project, first=True),
                row_deletable=True,
                style_cell = {
                    'font_size': '16px',
                    'text_align': 'center'
                },
                fixed_rows={'headers': True},
                style_table={'max_height': 700},
                style_as_list_view=True,
                style_header={
                    'backgroundColor': 'rgb(30, 30, 30)',
                    'color': 'white'
                },
                style_data={
                    'backgroundColor': 'rgb(50, 50, 50)',
                    'color': 'white'
                },
                markdown_options={"link_target": "_self"}
    )

    loading = dcc.Loading(id="pipe-loading")
    interval = dcc.Interval(id="pipe-table-refresh", interval=2000)

    button = dbc.Button("Run!", id="pipe-button")

    hidden = html.Div(id="pipeline-hidden", style={"display":"none"})
    hidden2 = html.Div(id="pipeline-hidden2", style={"display":"none"})

    layout = [dialog, del_dialog, html.H1("Dataset Creation"), html.H3("Time to create your very own dataset."), 
                html.Hr(), html.H4("Setup"), tabs, html.Hr(), button, table, loading, interval, hidden, hidden2]

    return layout

q = Queue()

def start_proc(tags, MODE, n_input, keep, db, db_name, db_table, classifiers, field_types, field_text, project, q, file_ext):
    pipeline_settings = {}
    settings = get_settings(project)

    # general
    pipeline_settings['tags'] = tags
    pipeline_settings['mode'] = MODE
    pipeline_settings['n'] = n_input
    pipeline_settings['keep_text'] = keep
    pipeline_settings['do_db'] = db
    pipeline_settings['file_extract'] = file_ext
    if db == True:
        pipeline_settings['db_name'] = db_name.strip().split('.')[0]
        pipeline_settings['db_table'] = db_table.strip()

    # clfs
    pipeline_settings['clf'] = {}
    for c in classifiers:
        tag = c.split('-')[-1]
        pipeline_settings['clf'][tag] = {}
        pipeline_settings['clf'][tag]['clf'] = c
        pipeline_settings['clf'][tag]['preproc'] = False # for now!

    # tag keywords
    pipeline_settings['proc_keywords'] = {}
    keywords = get_keywords(project)
    for k in keywords:
        if k in tags:
            pipeline_settings['proc_keywords'][k] = keywords[k]

    # dirs
    pipeline_settings['project'] = project

    rules_dir = "{}/rules/".format(project)
    pipeline_settings['rules_dir'] = rules_dir
    main_dir = None
    data_dir = None
    for s in settings:
        if settings[s]['extract'] == "None":
            main_dir = settings[s]['parent']
            pipeline_settings['main'] = {}
            pipeline_settings['main']['delim'] = settings[s]['delim']
            pipeline_settings['main']['fields'] = settings[s]['fields']
            pipeline_settings['main']['files'] = settings[s]['files']
            pipeline_settings['main']['id'] = settings[s]['id']
        else:
            data_dir = settings[s]['parent']
            pipeline_settings['extract'] = {}
            pipeline_settings['extract']['id'] = settings[s]['id']
            pipeline_settings['extract']['ext'] = settings[s]['ext']
            pipeline_settings['extract']['fields'] = settings[s]['fields']
            pipeline_settings['extract']['files'] = settings[s]['files']
            pipeline_settings['extract']['text'] = settings[s]['extract']
    pipeline_settings['main_dir'] = main_dir
    pipeline_settings['data_dir'] = data_dir

    # db fields
    if db == True:
        id_key = None
        main_key = None
        fields = []
        for k in settings:
            for f in settings[k]['fields']:
                if f == settings[k]['id'] and settings[k]['extract'] != "None":
                    id_key = f 
                elif f == settings[k]['id']:
                    main_key = f
        fields = []
        primary_key = None
        for x,y in zip(field_text, field_types):
            if x == id_key:
                primary_key = "{} {} PRIMARY KEY".format(x, y)
            elif x == main_key:
                continue
            else:
                fields.append("{} {}".format(x, y))
        pipeline_settings['db_fields'] = [primary_key]+fields

    pid = str(os.getpid())
    csv_dir = (Path(project) / "csv" / pid).as_posix()
    os.makedirs(csv_dir)
    pipeline_settings['csv_dir'] = csv_dir

    # save
    if db == True:
        save = (Path(project) / "db" / "{}.db".format(pipeline_settings['db_name'])).as_posix()
        table = pipeline_settings['db_table']
    else:
        save = (Path(project) / "db" / "{}.csv".format(pid)).as_posix()
        pipeline_settings['csv_save'] = save
        table = "None"
        
    pipe = Pipeline(pipeline_settings, settings)
    name = "{}: ".format(pid) + ", ".join(tags)

    q.put([pid, name, datetime.now(), "Running!", save, table])
    for stat in pipe.do_pipeline():
        q.put([pid, name, None, stat, save, table])
    q.put([pid])

    return

@app.callback(Output("pipe-dialog", "displayed"),
                Input("pipe-button", "n_clicks"),
                [State("pipeline-hidden", "children"),
                State("d-switch", "on"), State("d-n", "value"),
                State("keep-switch", "on"), State("db-switch", "on"),
                State("db-name-input", "value"), State("db-table-input", "value"),
                State("project", "data"),
                State({"type":"clf-dropdown", "index":ALL}, "value"),
                State({"type":"field-drop", "index":ALL}, "value"),
                State({"type":"field-text", "index":ALL}, "children")])
def do_pipeline(n, tags, mode, n_input, keep, db, db_name, db_table, data, drop_args, field_types, field_text):
    global q
    if n is None:
        raise PreventUpdate

    if tags is None:
        logging.getLogger("messages").error("No tags selected.")
        return False

    if db == True and (db_name is None or db_table is None):
        logging.getLogger("messages").error("Missing database info.")
        return False

    if db == True and any(x is None for x in field_types):
        logging.getLogger("messages").error("Please enter a type for all database fields.")
        return False

    tags = [x.strip() for x in tags.split(',')]
    num_clfs = sum(1 for x in drop_args if x is not None)
    if len(tags) != num_clfs:
        logging.getLogger("messages").error("Please choose a classifier for every selected tag.")
        return False

    if mode == True:
        MODE = "sentence"
    else:
        MODE = "word"

    settings = get_settings(data['project'])
    for s in settings:
        if settings[s]['extract'] != "None":
            file_ext = settings[s]['file_extract']
            break

    # clfs
    classifiers = None
    if any(x is None for x in drop_args if x in tags):
        raise PreventUpdate
    else:
        classifiers = [x for x in drop_args]

    p = Process(target=start_proc, args=(tags, MODE, n_input, keep, db, db_name, db_table,
                    classifiers, field_types, field_text, data['project'], q, file_ext))
    p.start()

    return False

@app.callback(Output("pipe-table", "data"), 
                Input("pipe-table-refresh", "n_intervals"),
                State("project", "data"))
def refresh(n, data):
    global q

    if n is None:
        raise PreventUpdate

    time.sleep(random.uniform(0, 0.2))

    rows = get_pipeline_log(data['project'])
    try:
        new = q.get(block=True, timeout=0.5)
        if len(new) != 1:
            if new[2] is not None:
                new_data = {"pid":new[0], "name":new[1], "start":new[2].strftime("%m/%d/%Y, %H:%M:%S"), 
                            "elapsed": get_duration(new[2]), "status":new[3], "save":new[4], "db_table":new[5]}
                rows.append(new_data)
                logging.getLogger("messages").info("Pipeline process {} ({}) started.".format(new_data['pid'], new_data['name']))
            else:
                to_up = None
                new_data = None
                for i, r in enumerate(rows):
                    if r['pid'] == new[0]:
                        new_data = {"pid":new[0], "name":new[1], "start":r['start'], 
                            "elapsed": get_duration(datetime.strptime(r['start'], "%m/%d/%Y, %H:%M:%S")), 
                            "status":new[3], "save":new[4], "db_table":new[5]}
                        to_up = i
                        break
                rows[to_up] = new_data
        else:
            to_del = new[0]
            for i, r in enumerate(rows):
                if r['pid'] == to_del:
                    r['elapsed'] = get_duration(datetime.strptime(r['start'], "%m/%d/%Y, %H:%M:%S"))
                    r['status'] = "Finished"
                    logging.getLogger("messages").critical("Pipeline process {} ({}) finished!".format(r['pid'], r['name']))
                    to_del = (i, r)
                    break
            rows[to_del[0]] = to_del[1]
    except queue.Empty:
        if rows is None or len(rows) == 0:
            raise PreventUpdate
        else:
            pass

    new_rows = []
    for r in rows:
        if r['status'] != "Finished" and r['status'] != "Removed":
            r['elapsed'] = get_duration(datetime.strptime(r['start'], "%m/%d/%Y, %H:%M:%S"))
            new_rows.append(r)
        else:
            new_rows.append(r)

    update_pipe_log(new_rows, data['project'])

    return_rows = []
    for r in new_rows:
        del r['save']
        del r['db_table']
        if r['status'] == "Finished":
            r['name'] = "[{}]({})".format(r['name'], "/data_ex/{}".format(r['pid']))
        return_rows.append(r)

    return return_rows

@app.callback([Output("rule-drop-output", "children"), Output("pipeline-hidden", "children")],
                Input("pipe-rule-drop", "value"),
                State("project", "data"))
def update_rule_message(val, data):
    if val is None or len(val) == 0:
        return "Tags: None", None
    else:
        tags = []
        for v in val:
            rule_path = Path(data['project']) / "rules" / "{}.csv".format(v)
            temp = pd.read_csv(rule_path.as_posix()).columns[2:].tolist()
            tags.extend(temp)
        tags = list(set(tags))
        tags = ", ".join(tags)
        return "Tags: {}".format(tags), tags

@app.callback(Output("pipeline-tab-class", "children"),
                Input("pipeline-tabs", "value"),
                [State("pipeline-hidden", "children"), State("project", "data")])
def update_class_opts(val, tags, data):
    if val == "Classifiers":
        if tags is None:
            return html.Div("No rules / tags selected. Start at the Rules tab.") 
        else:
            tags = tags.split(',')
            return get_class([x.replace(' ', '') for x in tags], data['project'])
    else:
        raise PreventUpdate

@app.callback(Output("save-div", "style"),
                Input("db-switch", "on"))
def switch_div(on):
    if on == True:
        logging.getLogger("messages").info("Option update: database save options now available.")
        return {"display":"inline-block", "padding":"1rem"}
    else:
        logging.getLogger("messages").info("Option update: database save options deactivated.")
        return {"display":"none"}

@app.callback([Output("fields-group", "children"), Output("pipe-h5", "children")],
                [Input("db-switch", "on"), Input("keep-switch", "on")],
                State("project", "data"))
def update_fields(on, keep, data):
    if on == False:
        return None, "Output will be saved to CSV."
    else:
        return get_fields(data['project'], keep), "Please select field types for database."

@app.callback(Output("fields-p", "children"),
                Input("fields-group", "children"),
                State("project", "data"))
def update_p(fields, data):
    settings = get_settings(data['project'])
    keys = [settings[x]['id'] for x in settings]
    if len(keys) == 1:
        p = "Key: {}".format(keys[0])
    else:
        p = "Keys: {}".format(', '.join(keys))
    return p

@app.callback(Output("dup-alert", "is_open"),
                Input("db-table-input", "value"),
                [State("db-name-input", "value"),
                State("project", "data")])
def validate_db(table, name, data):
    if name is None:
        raise PreventUpdate

    db_path = Path(data['project']) / "db" / "{}.db".format(name)
    if db_path.is_file() == True:
        con = sqlite3.connect(db_path.as_posix())
        cur = con.cursor()
        cur.execute("select count(name) from sqlite_master where type=\'table\' and name=\'{}\'".format(table))
        if cur.fetchone()[0] == 1:
            logging.getLogger("messages").warning("Database + table already exist -- continuing will overwrite.")
            return True
        else:
            return False
    else:
        return False

@app.callback(Output("pipe-loading", "children"),
                Input("pipe-del-dialog", "submit_n_clicks"),
                [State("pipeline-hidden2", "children"), State("project", "data")])
def save_del(n, delete, data):
    if n is None or n == 0:
        raise PreventUpdate

    log = get_pipeline_log(data['project'])
    delete = delete.split(";")

    pids = [x.split(':::')[0] for x in delete]

    for p in pids:
        del_path = Path(data['project']) / "csv" / p
        if del_path.is_dir() == True:
            shutil.rmtree(del_path.as_posix())
            logging.getLogger("messages").info("Removed Pipeline results for process {}".format(p))
        else:
            logging.getLogger("messages").info("Removed log results for process {}".format(p))

    deleted = []
    for l in log:
        if l['pid'] in pids:
            if l['status'] != "Removed":
                l['status'] = "Removed"
                deleted.append(l)

    new_log = deleted + [x for x in log if x['pid'] not in pids]

    update_pipe_log(new_log, data['project'])

    return " "

@app.callback([Output("pipe-del-dialog", "message"), Output("pipe-del-dialog", "displayed")],
                [Input("pipeline-hidden2", "children")])
def display_dialog(delete):
    names = ','.join([x.split(':::')[1] for x in delete.split(';')])
    return "Are you sure you want to delete {}? Any database results will be preserved, but pipeline files will be deleted.".format(names), True

@app.callback(Output("pipeline-hidden2", "children"),
              [Input("pipe-table", "data_previous"), Input("pipe-table", "data_timestamp")],
              [State("pipe-table", "data")])
def show_removed_rows(previous, ts, current):
    if previous is None:
        raise PreventUpdate
    else:
        really_delete = [r['pid']+':::'+r['name'] for r in previous if r not in current and r["status"] == "Removed"]
        time.sleep(1)
        deleted = [r["pid"]+':::'+r['name'] for r in previous if r not in current and r["status"] == "Finished"]
        return ";".join(list(set(really_delete+deleted)))