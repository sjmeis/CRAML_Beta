# Author: Stephen Meisenbacher
# view for dataset exploration

from pathlib import Path
import pandas as pd
import sqlite3
import logging

import dash
from dash import dcc
import dash_bootstrap_components as dbc
from dash import html
import dash_daq as daq
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash import dash_table

from server import app
from .utility import get_pipeline_log

def get_options(project):
    if project is None:
        return []

    log = get_pipeline_log(project)

    options = []
    for l in log:
        if l['status'] == "Finished":
            if l['db_table'] != "None":
                name = "{} ({} - {})".format(l['name'], Path(l['save']).name, l['db_table'])
            else:
                name = "{} (csv)".format(l['name'])
            options.append({"label":name, "value":l['pid']})
        
    return options

def get_data(save, table, mode, x):
    if Path(save).suffix == ".csv":
        if mode == "first":
            data = pd.read_csv(save).head(n=x)
        else:
            data = pd.read_csv(save).sample(n=x)
    else:      
        con = sqlite3.connect(save)
        if mode == "first":
            data = pd.read_sql_query("SELECT * from {} LIMIT {}".format(table, x), con)
        else:
            data = pd.read_sql_query("SELECT * from {} ORDER BY RANDOM() LIMIT {}".format(table, x), con)
    
    return data.columns, data.to_dict('records')

def get_layout(arg, project):
    log = get_pipeline_log(project)
    if arg not in [x['pid'] for x in log]:
        arg = None

    if arg is None:
        drop_dir = dcc.Dropdown(id="dex-dir-drop", options=get_options(project), placeholder="Select a dataset...")
    else:
        drop_dir = dcc.Dropdown(id="dex-dir-drop", options=get_options(project), value=arg)

    switch = html.Div(children=[html.Div(html.P(id="left-p-dex", children="First-X\t"), style={"display":"inline-block", "padding":"1rem"}), 
            html.Div(daq.BooleanSwitch(id="dex-switch", on=False), style={"display":"inline-block"}),
            html.Div(html.P(id="right-p-dex", children="\tRandom-X"), style={"display":"inline-block", "padding":"1rem"})], 
            style={"display":"inline-block", "padding":"1rem", "padding-right":"2rem"})

    number = html.Div(children=[html.Div(html.P(id="left-p-dex-x", children="X:\t"), style={"display":"inline-block", "padding":"1rem"}),
            html.Div(daq.NumericInput(id="dex-x", min=0, max=1000, value=50, theme="dark", size=75), style={"display":"inline-block"})],
            style={"display":"inline-block", "padding":"1rem", "padding-right":"2rem"})

    run_button = html.Div(html.Button("Go!", id="dex-run"), style={"display":"inline-block", "padding-left":"5rem"})

    dex_load = dcc.Loading(id="dex-load", fullscreen=True)

    table = dash_table.DataTable(
                id="dex-table",
                columns=None,
                data=None,
                editable=False,
                row_deletable=False,
                style_cell = {
                    'font_size':'16px',
                    'text_align':'center',
                    'maxWidth':'300px',
                    'minWidth':'75px'
                },
                fixed_rows={'headers': True},
                style_table={'max_height': 700},
                style_as_list_view=True,
                style_header={
                    'backgroundColor':'rgb(30, 30, 30)',
                    'color':'white'
                },
                style_data={
                    'backgroundColor':'rgb(50, 50, 50)',
                    'color':'white',
                    'whiteSpace':'normal',
                    'height':'auto'
                }
    )

    layout = [html.H1("Dataset Exploration"), html.H3("Look into your created datasets."), html.Hr(), 
                drop_dir, switch, number, run_button, dex_load, table]

    return layout

@app.callback([Output("dex-load", "children"), Output("dex-table", "columns"),
                Output("dex-table", "data")],
                Input("dex-run", "n_clicks"),
                [State("dex-dir-drop", "value"),
                State("dex-switch", "on"), State("dex-x", "value"),
                State("project", "data")])
def get_chunks(n_clicks, pid, switch, x, proj):
    if n_clicks is None:
        raise PreventUpdate

    if pid is None:
        logging.getLogger("messages").error("No data chosen!")
        raise PreventUpdate

    log = get_pipeline_log(proj['project'])
    save = None
    for l in log:
        if l['pid'] == pid:
            save = l['save']
            table = l['db_table']

    if switch == True:
        mode = "random"
    else:
        mode = "first"

    logging.getLogger("messages").info("Fetching data ({}-{}) from {}".format(mode.upper(), x, table))
    columns, data = get_data(save, table, mode, x)
    columns = [{"id":x, "name":x, "selectable":False} for x in columns]
    logging.getLogger("messages").critical("Results displayed.")

    return "", columns, data
