# Author: Stephen Meisenbacher
# view for extracting sample

import os
import sys
from pathlib import Path
from multiprocessing import Process, Queue
from datetime import datetime
import queue
import shutil
import logging
import pandas as pd

import time
import random

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
import dash_daq as daq
from dash.dependencies import Input, Output, State  
from dash.exceptions import PreventUpdate
from dash import dash_table

sys.path.append("classes")
from Extract import Extract
from Extrapolate import Extrapolate

from server import app
from .utility import get_settings, get_keywords, get_rules, get_rule_files, get_ext_log, update_ext_log

def get_layout(project):

    dialog = dcc.ConfirmDialog(id="es-dialog", message=None, displayed=False)
    del_dialog = dcc.ConfirmDialog(id="del-dialog", message=None, displayed=False)

    mode_switch = html.Div(children=[html.Div(html.P(children="Extract Sample \t"), style={"display":"inline-block", "padding-right":"1rem"}), 
                html.Div(daq.BooleanSwitch(id="es-mode-switch", on=False), style={"display":"inline-block"}),
                html.Div(html.P(children="\t Full Dataset Extraction"), style={"display":"inline-block", "padding":"1rem"})], 
                style={"padding":"1rem"})

    switch = html.Div(children=[html.Div(html.P(id="left-p-es", children="Word Chunks \t"), style={"display":"inline-block", "padding-right":"1rem"}), 
                html.Div(daq.BooleanSwitch(id="es-switch", on=False), style={"display":"inline-block"}),
                html.Div(html.P(id="right-p-es", children="\t Sentence Chunks"), style={"display":"inline-block", "padding":"1rem"})], 
                style={"display":"inline-block", "padding":"1rem"})

    n_input = html.Div(children=[daq.NumericInput(
                    id='es-n',
                    min=0,
                    max=20,
                    value=6,
                    label='N',
                    labelPosition='bottom',
                    style={"display":"inline-block"})], 
                style={"display":"inline-block", "padding":"1rem"})

    es_button = html.Div(dbc.Button("Extract!", id="es-button", size="lg"))

    columns = [{"id":"pid", "name":"pid", "type":"text", "presentation":"markdown"}] + \
        [{"id":x, "name":x, "type":"text"} for x in ["name", "start", "elapsed"]] + \
        [{"id":"status", "name":"status", "type":"text", "presentation":"markdown"}]

    table = dash_table.DataTable(
                id="es-table",
                columns=columns,
                data=get_ext_log(project, first=True),
                row_deletable=True,
                style_cell={
                    'font_size': '16px',
                    'text_align': 'center',
                    'maxWidth':'300px'
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
                    'color': 'white',
                    'whiteSpace':'normal',
                    'height':'auto'
                },
                markdown_options={"link_target": "_self"}
    )

    loading = dcc.Loading(id="es-loading")
    loading2 = dcc.Loading(id="es-loading-opt")

    interval = dcc.Interval(id="table-refresh", interval=3000)

    hidden_div = html.Div(id="es-hidden", style={"display":"none"})

    layout = [interval, dialog, del_dialog, html.H1("Extraction"), html.H3("Time to test out your keywords (+ rules)."),
                mode_switch, switch, n_input, es_button, html.Hr(), loading, loading2, table, hidden_div]

    return layout

q = Queue()

def start_proc(e, name, n, mode, q, CLASS, project, basename, id):
    pid = str(os.getpid())
    e.set_path(pid)
    os.makedirs(e.get_path())

    q.put([pid, name, datetime.now(), n, mode])
    extracted = e.extract()
    if CLASS == True:
        rules = get_rules(project)
        extra = Extrapolate(pid, basename, extracted, rules, project, id)
        saved = extra.extrapolate()
        logging.getLogger("messages").info("Extrapolation complete: saved to {}".format(saved.as_posix()))
    q.put([pid])

    return

def get_duration(start):
    diff = datetime.now() - start
    return round(diff.total_seconds(), 2)

@app.callback(Output("es-table", "data"), 
                [Input("table-refresh", "n_intervals"), Input("del-dialog", "cancel_n_clicks")],
                State("project", "data"))
def refresh(n, c, data):
    global q

    if n is None:
        raise PreventUpdate

    time.sleep(random.uniform(0, 0.1))

    rows = get_ext_log(data['project'])
    try:
        new = q.get(block=True, timeout=0.5)
        if len(new) != 1:
            new_data = {"pid":new[0], "name":new[1], "start":new[2].strftime("%m/%d/%Y, %H:%M:%S"), 
                        "elapsed": get_duration(new[2]), "status":"Running!", "n":new[3], "mode":new[4]}
            rows.append(new_data)
            logging.getLogger("messages").info("Extract Sample process {} ({}) started.".format(new_data['pid'], new_data['name']))
        else:
            to_del = new[0]
            for i, r in enumerate(rows):
                if r['pid'] == to_del:
                    r['elapsed'] = get_duration(datetime.strptime(r['start'], "%m/%d/%Y, %H:%M:%S"))
                    r['status'] = "Finished"
                    logging.getLogger("messages").critical("Extract Sample process {} ({}) finished!".format(r['pid'], r['name']))
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

    update_ext_log(new_rows, data['project'])

    return_rows = []
    for n in new_rows:
        if n['status'] == "Finished":
            n['status'] = "[{}]({})".format(n['status'], "/file_browser/{}".format(n['pid']))
            if "FULL EXTRACT" not in n['name']:
                n['pid'] = "[{}]({})".format(n['pid'], "/text_ex/{}".format(n['pid']))
            else:
                n['pid'] = "[{}]({})".format(n['pid'], "/validation/{}".format(n['pid']))
        temp = {x:n[x] for x in n if x != "n" and x != "mode"}
        return_rows.append(temp)

    return return_rows

@app.callback(Output("es-dialog", "displayed"),
                Input("es-button", "n_clicks"),
                [State("es-mode-switch", "on"), State("es-switch", "on"), 
                State("es-n", "value"), State("project", "data")])
def do_es(n, mode, switch, n_input, data):
    global q

    if n is None:
        raise PreventUpdate

    settings = get_settings(data['project'])
    if settings is None:
        logging.getLogger("messages").error("No settings found. Please visit the setup tab first.")
        return False

    keywords = get_keywords(data['project'])
    all_keys = []
    for k in keywords.keys():
        all_keys.extend(keywords[k])
    all_keys = list(set(all_keys))

    for k in settings.keys():
        if settings[k]['extract'] != "None":
            if switch == False:
                MODE = "word"
            else:
                MODE = "sentence"

            if mode == False:
                name = "[SAMPLE EXTRACT] parent: {} ({}), fields: {}, extract: {}, mode: {} (n={})".format(settings[k]["parent"], \
                    settings[k]["ext"], len(settings[k]["fields"]), settings[k]["extract"], MODE, n_input)
                ext_list = [x for x in (Path(data['project']) / "sample").rglob("*{}".format(settings[k]['ext']))]
                e = Extract(ext_list=ext_list, csv_dir=(Path(data['project']) / "csv"), 
                            n=n_input, fields=settings[k]["fields"], KEYS=all_keys, SETTINGS=settings, MODE=MODE,
                            FILE_EXT=settings[k]['file_extract'])
                p = Process(target=start_proc, args=(e, name, n_input, MODE, q, False, data['project'], k, settings[k]['id']))

            else:
                name = "[FULL EXTRACT] parent: {} ({}), fields: {}, extract: {}, mode: {} (n={})".format(settings[k]["parent"], \
                    settings[k]["ext"], len(settings[k]["fields"]), settings[k]["extract"], MODE, n_input)
                ext_list = [Path(x) for x in settings[k]['files']]
                e = Extract(ext_list=ext_list, csv_dir=(Path(data['project']) / "csv"), 
                            n=n_input, fields=settings[k]["fields"], KEYS=all_keys, SETTINGS=settings, MODE=MODE,
                            FILE_EXT=settings[k]['file_extract'])
                p = Process(target=start_proc, args=(e, name, n_input, MODE, q, True, data['project'], k, settings[k]['id']))

            p.start()

    return False

@app.callback(Output("es-loading", "children"),
                Input("del-dialog", "submit_n_clicks"),
                [State("es-hidden", "children"), State("project", "data")])
def save_del(n, delete, data):
    if n is None or n == 0:
        raise PreventUpdate

    log = get_ext_log(data['project'])
    delete = delete.split(",")
    for p in delete:
        del_path = Path(data['project']) / "csv" / p
        if del_path.is_dir() == True:
            shutil.rmtree(del_path.as_posix())
            logging.getLogger("messages").info("Removed Extract results for process {}".format(p))
        else:
            logging.getLogger("messages").info("Removed log results for process {}".format(p))

    deleted = []
    for l in log:
        if l['pid'] in delete:
            if l['status'] != "Removed":
                l['status'] = "Removed"
                deleted.append(l)

    new_log = deleted + [x for x in log if x['pid'] not in delete]

    update_ext_log(new_log, data['project'])

    return " "

@app.callback([Output("del-dialog", "message"), Output("del-dialog", "displayed")],
                [Input("es-hidden", "children")])
def display_dialog(pid):
    return "Are you sure you want to delete {}?".format(pid), True

@app.callback(Output("es-hidden", "children"),
              [Input("es-table", "data_previous"), Input("es-table", "data_timestamp")],
              [State("es-table", "data")])
def show_removed_rows(previous, ts, current):

    if previous is None:
        raise PreventUpdate
    else:
        really_delete = [r['pid'] for r in previous if r not in current and r["status"] == "Removed"]
        try:  
            deleted = [r["pid"].split(']')[0].split('[')[1] for r in previous if r not in current and r["status"].split(']')[0].split('[')[1] == "Finished"]
        except IndexError:
            deleted = []
            pass

        return ",".join(really_delete+deleted)

@app.callback(Output("es-loading-opt", "children"),
                [Input("es-mode-switch", "on"), Input("es-switch", "on"),
                Input("es-n", "value")],
                prevent_initial_call=True)
def inform_update(on, on2, n):
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if which == "es-mode-switch":
        if on == False:
            logging.getLogger("messages").info("Option update: extraction performed from Sample.")
        else:
            logging.getLogger("messages").info("Option update: extraction performed on full data.")
    elif which == "es-switch":
        if on2 == False:
            logging.getLogger("messages").info("Option update: extracting word chunks of context size {}".format(n))
        else:
            logging.getLogger("messages").info("Option update: extracting sentence chunks of context size {}".format(n))
    else:
        logging.getLogger("messages").info("Option update: context size changed to {}".format(n))

    return " "