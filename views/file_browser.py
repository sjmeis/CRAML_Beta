# Author: Stephen Meisenbacher
# view for browsing files of a given output directory

import os
from pathlib import Path
import logging
import pandas as pd

import platform
import subprocess
from multiprocessing import Process

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State, MATCH
from dash.exceptions import PreventUpdate
import dash_daq as daq

from server import app
from .utility import get_ext_log, get_nb_log, get_rf_log, get_pipeline_log, open_file

def highlight(val):
    if val == True:
        color = "yellow"
    else:
        color = ""
    return "background-color: %s" % color

def gen_excel(parent, pid, value):
    path = Path(parent) / pid / value
    if 'xlsx' in value and path.is_file() == False:
        name = value.split('.')[0]+'.csv'
        csv_path = Path(parent) / pid / name
        data = pd.read_csv(csv_path).sample(frac=0.1)

        indices = data['indices'].tolist()
        split_chunk = data['text'].str.split('|', expand=True)

        split_chunk.style.apply(lambda x: highlight(x, indices), axis=1)
        all_temps = []
        for index, row in split_chunk.iterrows():
            if str(indices[index]) != 'nan':
                idxs = [int(x) for x in indices[index].split(';')]
                #temp = [True if i in idxs else False for i, _ in enumerate(row)]
                temp = ["True;;"+x if i in idxs else x for i, x in enumerate(row)]
            else:
                #temp = [False for x in row]
                temp = [x for x in row]
            all_temps.append(temp)
        mask = pd.DataFrame(all_temps)
        mask = mask.fillna("")

        #mask.style.applymap(highlight).to_excel(path.as_posix(), index=False, header=True)
        print("styling")
        styled = mask.style.applymap(lambda x: 'background-color: %s' % 'yellow' if "True;;" in x else '')

        writer = pd.ExcelWriter(path.as_posix(), engine="xlsxwriter")
        #split_chunk.style.apply(styled, axis=None)
        print("saving")
        styled.to_excel(writer, engine="xlsxwriter")
        print("here")
        writer.save()

        #split_chunk.to_excel(path.as_posix(), engine="openpyxl", index=False, header=True)

        #cols = [x for x in data.columns if x != "text" and x != "indices"]
        #data = data[cols]

        #excel = pd.concat([data, split_chunk], axis=1)
        #writer = pd.ExcelWriter(path.as_posix())
        #excel.style.apply(lambda x: highlight(x, indices), axis=1, subset=split_chunk.columns)
        #excel.to_excel(writer, index=False, header=True)
        #writer.save()
        logging.getLogger("messages").critical("Excel report saved to: {}".format(path.as_posix()))

    #logging.getLogger("messages").info("Opening {}".format(path.as_posix()))
    #if platform.system() == "Darwin":
    #    subprocess.call(('open', path))
    #elif platform.system() == "Windows":
    #    os.startfile(path)
    #else:
    #    subprocess.call(('xdg-open', path))

def get_options(project):
    options = []

    # get all logs
    for e in get_ext_log(project):
        if e['status'] == "Finished":
            e_path = (Path(project) / "csv").as_posix()
            options.append({"label":"[EXTRACT SAMPLE] pid:{}, {} --- {}".format(e['pid'], e['name'], e_path), "value":e['pid']})
    for n in get_nb_log(project):
        if n['status'] == "Finished":
            options.append({"label":"[TRAIN NB] pid: {}, {} --- {}".format(n['pid'], n['name'], n['log']['settings']['parent']), "value":n['pid']})
    for r in get_rf_log(project):
        if r['status'] == "Finished":
            options.append({"label":"[TRAIN RF] pid: {}, {} --- {}".format(r['pid'], r['name'], r['log']['settings']['parent']), "value":r['pid']})

    return options

def get_layout(project, arg):
    if arg is not None:
        if (Path(project) / "csv" / arg).is_dir() == False:
            arg = None

    dirs = dcc.Dropdown(
        id="filedir-drop",
        options=get_options(project),
        value=arg,
        clearable=False
    )

    loading = dcc.Loading(id="fb-load")
    loading2 = dcc.Loading(id="excel-load")

    layout = [html.H1("File Explorer"), html.H4("Browse the files for a given output directory."),
                dirs, html.Div(id="files-ex-div", style={"padding":"2rem"}), loading, loading2]

    return layout

@app.callback(Output("files-ex-div", "children"),
                Input("filedir-drop", "value"),
                State("filedir-drop", "options"))
def update_explorer(value, options):
    if value is None:
        raise PreventUpdate

    logging.getLogger("messages").info("Listing files for {}".format(value))

    parent = [x['label'] for x in options if value in x['label']][0].split(' --- ')[-1]

    files = os.listdir((Path(parent) / value).as_posix())
    filelist = []
    xls = 0
    for idx, x in enumerate(files):
        #filelist.append(html.Li(x, id={'type':'file', 'index':idx}))
        if 'xlsx' in x:
            filelist.append(dbc.Button(x, id={'type':'file', 'index':idx}, color="success"))
            continue
        else:
            filelist.append(dbc.Button(x, id={'type':'file', 'index':idx}))

        if "full" in x:
            name = x.split('.')[0]+'.xlsx'
            if (Path(parent) / value / name).is_file() == True:
                continue
            filelist.append(dbc.Button(name, id={'type':'file', 'index':len(files)+xls}, color="success"))
            xls += 1

    #return html.Ul(filelist)
    return dbc.ButtonGroup(filelist, vertical=True)

@app.callback([Output({"type":"file", "index":MATCH}, "hidden")],
                Input({"type":"file", "index":MATCH}, "n_clicks"),
                [State({"type":"file", "index":MATCH}, "children"),
                State("filedir-drop", "value"), State("filedir-drop", "options")])
def open_file(n, value, pid, options):
    if n is None or value is None:
        raise PreventUpdate

    logging.getLogger("messages").info("Generating Excel report: {}".format(value))

    parent = [x['label'] for x in options if pid in x['label']][0].split(' --- ')[-1]
    p = Process(target=gen_excel, args=(parent, pid, value))
    p.start()

    raise PreventUpdate