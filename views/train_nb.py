# Author: Stephen Meisenbacher
# view for nb training

import sys
import os
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
from multiprocessing import Process, Queue
import queue
import shutil
from collections import OrderedDict
import logging

import time
import random

import dash
from dash import dcc
import dash_bootstrap_components as dbc
from dash import html
import dash_daq as daq
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash import dash_table

from server import app
from .utility import get_duration, get_rule_files, get_ex_log_train, get_nb_log, update_nb_log, get_options

sys.path.append("classes")
from Train import Train

def get_layout(project):

    modal = html.Div(
        [
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Results")),
                    dbc.ModalBody(children=html.Pre(id="nb-modal-body", children=None)),
                    dbc.ModalFooter(
                        dbc.Button(
                            "Close", id="nb-modal-close", className="ms-auto", n_clicks=0
                        )
                    ),
                ],
                id="nb-modal",
                is_open=False,
                size="lg",
                zindex=99999,
                centered=True
            ),
        ]
    )

    dialog = dcc.ConfirmDialog(id="nb-dialog", message=None, displayed=False)
    del_dialog = dcc.ConfirmDialog(id="nb-del-dialog", message=None, displayed=False)

    drop_dir = dcc.Dropdown(id="nb-dir-drop", options=get_options(project, False), placeholder="Select an extracted directory...")

    drop_rules = dcc.Dropdown(id="nb-rule-drop", options=get_rule_files(project), 
                    placeholder="Select a rules file to train on...")

    switch = html.Div(children=[html.Div(html.P(id="left-p-nb", children="Negative sampling: Off\t"), style={"display":"inline-block", "padding-right":"1rem"}), 
                html.Div(daq.BooleanSwitch(id="nb-switch", on=False), style={"display":"inline-block"}),
                html.Div(html.P(id="right-p-nb", children="\tOn"), style={"display":"inline-block", "padding":"1rem-left"})], 
                style={"display":"inline-block", "padding":"1rem"})

    slider = html.Div(children=[html.Div(html.P(id="left-p-nb2", children="Sample Rate (%):\t"), style={"display":"inline-block"}),
                        html.Div(dcc.Slider(id="nb-slider", min=1, max=100, step=1, value=10, 
                        marks={x:str(x) for x in [1,5,10,15,20,25,50,100]},
                        tooltip={"placement": "bottom", "always_visible": False}),
                        style={"width":"50%", "display":"inline-block", "vertical-align":"middle"})], 
                        style={"padding":"1rem"})

    nb_button = dbc.Button("Train!", id="nb-button")
    res_button = dbc.Button("Show Results", id="nb-res-button")
    buttons = html.Div(dbc.ButtonGroup([nb_button, res_button], size="lg", className="me-1"), style={"width":"50%"})

    columns = [{"id":x, "name":x, "type":"text"} for x in ["name", "start", "elapsed", "status"]]

    table = dash_table.DataTable(
                id="nb-table",
                columns=columns,
                data=get_nb_log(project, first=True),
                row_deletable=True,
                row_selectable="single",
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
                }
    )

    loading = dcc.Loading(id="nb-loading")

    interval = dcc.Interval(id="nb-table-refresh", interval=2000)

    hidden_div = html.Div(id="nb-hidden", style={"display":"none"})

    layout = [modal, dialog, del_dialog, html.H1("Naive Bayes Training"), html.H3("Train a simple text classifier."), html.Hr(),
                drop_dir, drop_rules, switch, slider, buttons, html.Hr(), table, loading, interval, hidden_div]

    return layout

q = Queue()
def start_proc(project, parent, rule, samp, neg, q):
    local_log = {}

    pid = str(os.getpid())
    if neg == True:
        name = "{}_{}_neg".format(Path(rule).stem, samp)
    else:
        name = "{}_{}".format(Path(rule).stem, samp)
    local_log['settings'] = {}
    local_log['settings']['parent'] = parent.as_posix()
    local_log['settings']['rule_file'] = rule.as_posix()
    local_log['settings']['sample_rate'] = samp/100.0
    local_log['settings']['neg_sample'] = neg

    train = Train(pid, name, parent, rule, samp/100.0, neg, project)

    path = Path(project) / "train" / str(pid)
    os.makedirs(path.as_posix())
    path = path / "clf"
    os.makedirs(path.as_posix())

    start = datetime.now()
    q.put([pid, name, start, "Extrapolating training data..."])
    train_file = train.extrapolate()
    local_log['train_file'] = train_file.as_posix()
    q.put([pid, name, None, "Training..."]) 
    local_log['results'] = []
    for res in train.train_nb(train_file):
        local_log['results'].append(res)
    q.put([pid, local_log])

    return

@app.callback(Output("nb-dialog", "displayed"),
                Input("nb-button", "n_clicks"),
                [State("nb-dir-drop", "value"), State("nb-rule-drop", "value"),
                State("nb-slider", "value"), State("nb-switch", "on"),
                State("project", "data")])
def do_nb(n, dir, rule, samp, neg, data):
    global q
    if n is None or rule is None:
        raise PreventUpdate

    p = Process(target=start_proc, args=(data['project'], Path(data['project']) / "csv" / dir, 
                Path(data['project']) / "rules" / "{}.csv".format(rule), int(samp), neg, q))
    p.start()

    return False

@app.callback(Output("nb-table", "data"), 
                Input("nb-table-refresh", "n_intervals"),
                State("project", "data"))
def refresh(n, data):
    global q

    if n is None:
        raise PreventUpdate

    time.sleep(random.uniform(0, 0.2))

    rows = get_nb_log(data['project'])
    try:
        new = q.get(block=True, timeout=0.5)
        if len(new) != 2:
            if new[2] is not None:
                new_data = {"pid":new[0], "name":new[1], "start":new[2].strftime("%m/%d/%Y, %H:%M:%S"), 
                            "elapsed": get_duration(new[2]), "status":new[3], "log":None}
                rows.append(new_data)
                logging.getLogger("messages").info("Train NB process {} ({}) started.".format(new_data['pid'], new_data['name']))
            else:
                to_up = None
                new_data = None
                for i, r in enumerate(rows):
                    if r['pid'] == new[0]:
                        new_data = {"pid":new[0], "name":new[1], "start":r['start'], 
                            "elapsed": get_duration(datetime.strptime(r['start'], "%m/%d/%Y, %H:%M:%S")), "status":new[3], "log":None}
                        to_up = i
                        break
                rows[to_up] = new_data
        else:
            to_del = new[0]
            for i, r in enumerate(rows):
                if r['pid'] == to_del:
                    r['elapsed'] = get_duration(datetime.strptime(r['start'], "%m/%d/%Y, %H:%M:%S"))
                    r['status'] = "Finished"
                    r['log'] = new[1]
                    logging.getLogger("messages").critical("Train NB process {} ({}) finished!".format(r['pid'], r['name']))
                    to_del = (i, r)
                    break
            rows[to_del[0]] = to_del[1]
    except queue.Empty:
        if len(rows) == 0:
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

    update_nb_log(new_rows, data['project'])

    return_rows = []
    for r in new_rows:
        del r['log']
        return_rows.append(r)

    return return_rows

@app.callback(Output("nb-loading", "children"),
                Input("nb-del-dialog", "submit_n_clicks"),
                [State("nb-hidden", "children"), State("project", "data")])
def save_del(n, delete, data):
    if n is None or n == 0:
        raise PreventUpdate

    log = get_nb_log(data['project'])
    delete = delete.split(",")

    pids = [x.split(':::')[0] for x in delete]

    for p in pids:
        del_path = Path(data['project']) / "train" / p
        if del_path.is_dir() == True:
            shutil.rmtree(del_path.as_posix())
            logging.getLogger("messages").info("Removed Train results for process {}".format(p))
        else:
            logging.getLogger("messages").info("Removed log results for process {}".format(p))

    deleted = []
    for l in log:
        if l['pid'] in pids:
            if l['status'] != "Removed":
                l['status'] = "Removed"
                deleted.append(l)

    new_log = deleted + [x for x in log if x['pid'] not in pids]

    update_nb_log(new_log, data['project'])

    return " "

@app.callback([Output("nb-del-dialog", "message"), Output("nb-del-dialog", "displayed")],
                [Input("nb-hidden", "children")])
def display_dialog(delete):
    names = ','.join([x.split(':::')[1] for x in delete.split(',')])
    return "Are you sure you want to delete {}?".format(names), True

@app.callback(Output("nb-hidden", "children"),
              [Input("nb-table", "data_previous"), Input("nb-table", "data_timestamp")],
              [State("nb-table", "data")])
def show_removed_rows(previous, ts, current):
    if previous is None:
        raise PreventUpdate
    else:
        really_delete = [r['pid']+':::'+r['name'] for r in previous if r not in current and r["status"] == "Removed"]
        deleted = [r["pid"]+':::'+r['name'] for r in previous if r not in current and r["status"] == "Finished"]
        return ",".join(really_delete+deleted)

@app.callback([Output("nb-modal-body", "children"), Output("nb-modal", "is_open")],
            [Input("nb-res-button", "n_clicks"), Input("nb-modal-close", "n_clicks")],
            [State("nb-table", "selected_rows"), State("nb-table", "data"),
            State("nb-modal", "is_open"), State("project", "data")])
def show_results(n, n2, select, data, is_open, proj):
    if n is None or n == 0:
        raise PreventUpdate

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if select is None or len(select) == 0:
        raise PreventUpdate

    if which == "nb-modal-close":
        if n2 == 0:
            raise PreventUpdate
        else:
            return None, False
    else:
        pid = data[select[0]]['pid']
        log = get_nb_log(proj['project'])
        to_display = None
        for l in log:
            if l['pid'] == pid:
                to_display = OrderedDict(l)
                break

        return json.dumps(to_display, indent=3), True