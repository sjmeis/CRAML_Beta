# view for text exploration (n-gram)

import sys
from pathlib import Path
import pandas as pd
import logging

import dash
from dash import dcc
import dash_bootstrap_components as dbc
from dash import html
import dash_daq as daq
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash import dash_table, no_update

from server import app
from .utility import get_keywords, get_rule_files, get_ext_log, get_options

sys.path.append("classes")
from Text_Ex import Text_Ex

def get_filler(project):
    if project is None:
        return []

    children = []
    num_cols = len(get_keywords(project).keys())+1
    for i in range(0, num_cols):
        children.append(dbc.InputGroup([dbc.InputGroupText(""), 
                        dbc.Input(id="ig-{}".format(i), type="number")],
                        style={"display":"none"}))
    return children

def get_layout(arg, project):
    log = get_ext_log(project)
    if arg not in [x['pid'] for x in log]:
        arg = None
    else:
        logging.getLogger("messages").info("Preloaded with pid {}".format(arg))

    add_modal = html.Div(dbc.Modal(
                    [
                        dbc.ModalHeader("Add rule"),
                        dbc.ModalBody(
                            [
                                dbc.Label("Name:"),
                                dbc.Input(id="new_rule", type="text", debounce=True),
                                dbc.Label("Rule File:"),
                                dcc.Dropdown(id="rule-drop", options=get_rule_files(project),
                                        placeholder="Select a rules file..."),
                                dbc.Label("Info:"),
                                html.Div(id="modal-div", children=get_filler(project))
                            ]
                        ),
                        dbc.ModalFooter(
                            [
                                dbc.Button("OK", color="primary", id="ex_modal_ok"),
                                dbc.Button("Cancel", id="ex_modal_cancel"),
                            ]
                        ),
                    ],
                    id="ex-modal",
                    size="lg",
                    centered=True,
                    is_open=False,
                    keyboard=True
                )
                )

    ex_dialog = dcc.ConfirmDialog(id="ex-dialog", message=None, displayed=False)

    if arg is None:
        drop_dir = dcc.Dropdown(id="dir-drop", options=get_options(project, False), placeholder="Select an extracted directory...")
    else:
        drop_dir = dcc.Dropdown(id="dir-drop", options=get_options(project, False), value=arg)


    drop_keys = dcc.Dropdown(id="key-drop", options=[{"label":k, "value":k} for k in get_keywords(project).keys()], 
                placeholder="Select a keyword to explore...")

    chunk_switch = html.Div(children=[html.Div(html.P(id="left-p-cs", children="Word Chunks \t"), style={"display":"inline-block", "padding-right":"1rem"}), 
                html.Div(daq.BooleanSwitch(id="chunk-switch", on=False), style={"display":"inline-block"}),
                html.Div(html.P(id="right-p-cs", children="\t Sentence Chunks"), style={"display":"inline-block", "padding":"1rem"})], 
                style={"display":"inline-block", "padding":"1rem"})

    switch = html.Div(children=[html.Div(html.P(id="left-p-ex", children="Top-X\t"), style={"display":"inline-block", "padding":"1rem"}), 
            html.Div(daq.BooleanSwitch(id="ex-switch", on=False), style={"display":"inline-block"}),
            html.Div(html.P(id="right-p-ex", children="\tRandom-X"), style={"display":"inline-block", "padding":"1rem"})], 
            style={"display":"inline-block", "padding":"1rem", "padding-right":"2rem"})

    number = html.Div(children=[html.Div(html.P(id="left-p-ex-x", children="X:\t"), style={"display":"inline-block", "padding":"1rem"}),
            html.Div(daq.NumericInput(id="ex-x", min=0, max=1000, value=100, theme="dark", size=75), style={"display":"inline-block"})],
            style={"display":"inline-block", "padding":"1rem", "padding-right":"2rem"})

    run_button = html.Div(html.Button("Run!", id="ex-run"), style={"display":"inline-block", "padding-left":"5rem"})

    add_button = html.Div(html.Button("Add Selected", id="ex-add"), style={"display":"inline-block", "padding-left":"5rem"})

    ex_slide = html.Div(children=[html.Div(html.P(id="left-p-ex-p", children="Context Size:\t"), style={"display":"inline-block"}), 
                        html.Div(dcc.Slider(id="ex-slider", min=1, max=6, step=1, value=3, 
                            marks={x:str(x) for x in range(1,7)}, tooltip={"placement": "bottom", "always_visible": False}), 
                            style={"width":"50%", "display":"inline-block", "padding":"1rem", "vertical-align":"middle"})])

    ex_load = dcc.Loading(id="ex-load")

    table = dash_table.DataTable(
                id="ex-table",
                columns=[{"id":"chunk", "name":"chunk", "selectable":True}, 
                        {"id":"count", "name":"count", "selectable":False}],
                data=None,
                editable=False,
                row_deletable=False,
                style_cell = {
                    'font_size':'16px',
                    'text_align':'center',
                    'maxWidth':'500px',
                    'minWidth':'35px'
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
                },
                filter_action="native"
    )

    export = dbc.Button("Export", id="ngram-export")
    ngram_download = dcc.Download(id="ngram-download")

    hidden = html.Div(id="ex-hidden-div", children=None, style={"display":"none"})

    layout = [add_modal, ex_dialog, html.H1("Context Exploration"), html.H3("Dive into the extracted text."), html.Hr(), 
                drop_dir, drop_keys, chunk_switch, switch, number, run_button, add_button, ex_load, ex_slide, table, export, ngram_download, hidden]

    return layout

@app.callback([Output("ex-load", "children"), Output("ex-table", "data")],
                Input("ex-run", "n_clicks"),
                [State("dir-drop", "value"), State("key-drop", "value"), 
                State("ex-switch", "on"), State("ex-x", "value"), State("ex-slider", "value"),
                State("chunk-switch", "on"), State("project", "data")])
def get_chunks(n_clicks, dir, key, mode, x, n, chunk, proj):

    if n_clicks is None or dir is None or key is None:
        if n_clicks is not None:
            logging.getLogger("messages").error("Missing information! Please fill all fields.")
        raise PreventUpdate

    keys = get_keywords(proj['project'])[key]

    if chunk == False:
        chunk = "word"
    else:
        chunk = "sentence"

    if mode == False:
        lr = Text_Ex(int(x), int(n), Path(proj['project']) / "csv" / dir, keys, "TOP", CHUNK=chunk)
    elif mode == True:
        lr = Text_Ex(int(x), int(n), Path(proj['project']) / "csv" / dir, keys, "RANDOM", CHUNK=chunk)

    data = lr.do_lr()
    logging.getLogger("messages").critical("TEXT EXTRACT complete, results displayed")
        
    return "", data

@app.callback([Output("modal-div", "children"), Output("ex-hidden-div", "children")],
                Input("rule-drop", "value"),
                State("project", "data"))
def update_rule_options(val, data):
    if val is None:
        raise PreventUpdate

    children = []
    path = Path(data['project']) / "rules" / "{}.csv".format(val)
    cols = pd.read_csv(path.as_posix()).columns
    for i, c in enumerate(cols[1:]):
        if c == "prio":
            children.append(dbc.InputGroup([dbc.InputGroupText(c), 
                            dbc.Input(
                                #id="ig-{}".format(i), 
                                id={'type':'number-input', 'index':i},
                                type="number")]))
        else:
            children.append(dbc.InputGroup([dbc.InputGroupText(c), dbc.Select(
                    #id="ig-{}".format(i),
                    id={'type':'number-input', 'index':i},
                    options=[
                        {"label": "0", "value": 0},
                        {"label": "1", "value": 1},
                    ]
                )]))

    fields = len(children)

    num_tot = len(get_keywords(data['project']).keys())+1
    for i in range(len(children), num_tot):
        children.append(dbc.InputGroup([dbc.InputGroupText(""), dbc.Input(id="ig-{}".format(i), type="number")], 
                        style={"display":"none"}))
    
    return children, fields


@app.callback([Output("ex-modal", "is_open"), Output("new_rule", "value"),
                Output("ex-dialog", "message"), Output("ex-dialog", "displayed")],
                [
                    Input("ex-add", "n_clicks"),
                    Input("ex_modal_ok", "n_clicks"),
                    Input("ex_modal_cancel", "n_clicks"),
                ],
                [State("ex-modal", "is_open"), State("ex-table", "active_cell"),
                State("ex-table", "derived_virtual_data"), State("new_rule", "value"),
                State("rule-drop", "value"), 
                State("project", "data"),
                State("ex-hidden-div", "children"),
                State({'type':'number-input', 'index':ALL}, 'value')],
                prevent_initial_call=True)
def add_rule(n1, n2, n3, is_open, active, data, rule_text, rule, proj, num_fields, igargs):

    if n1 is None and n2 is None and n3 is None:
        raise PreventUpdate

    if is_open == False and active is None:
        raise PreventUpdate

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    chunk = data[active['row']][active['column_id']]
    
    if is_open == False and which == "ex-add":
        return True, chunk, no_update, False

    if is_open == True:
        if which == "ex_modal_ok":
            if rule is None or any(x is None for x in igargs[:int(num_fields)]):
                logging.getLogger("messages").error("Please fill in all fields.")
                return True, chunk, "Please fill in all fields.", True
            else:
                args = [str(x) for x in igargs if x is not None]
                to_write = ','.join([rule_text]+args)+'\n'

                path = Path(proj['project']) / "rules" / "{}.csv".format(rule)
                with open(path.as_posix(), 'a') as out:
                    out.write(to_write)
                    
                logging.getLogger("messages").critical("Rule saved successfully to {}".format(rule))

                return False, None, no_update, False
        elif which == "ex_modal_cancel":
            logging.getLogger("messages").info("Rule add operation canceled.")
            return False, None, no_update, False
        else:
            raise PreventUpdate

    return False, None, no_update, False

@app.callback([Output("ex-slider", "max"), Output("ex-slider", "marks"),
                Output("chunk-switch", "disabled")],
                [Input("dir-drop", "value"), Input("chunk-switch", "on")],
                State("project", "data"))
def update_slider_max(value, on, data):
    if value is None:
        raise PreventUpdate

    log = get_ext_log(data['project'])
    find = [i for i, l in enumerate(log) if value == l['pid']][0]
    max_val = log[find]['n']

    if log[find]['mode'] == "word" and on == True:
        logging.getLogger("messages").warning("Extracted word mode results selected, but sentence mode is selected.")
        raise PreventUpdate
    elif log[find]['mode'] == "sentence" and on == False:
        logging.getLogger("messages").info("Extracted sentence mode results selected - sentence exploration activated.")
        max_val = 10
        return max_val, {x:str(x) for x in range(1,max_val+1)}, False
    elif log[find]['mode'] == "sentence":
        logging.getLogger("messages").info("Extracted sentence mode results selected - sentence exploration activated.")
        return max_val, {x:str(x) for x in range(1,max_val+1)}, False
    else:
        logging.getLogger("messages").info("Extracted word mode results selected - sentence exploration deactivated.")
        return max_val, {x:str(x) for x in range(1,max_val+1)}, True
      
@app.callback(Output("ngram-download", "data"),
                Input("ngram-export", "n_clicks"),
                [State("ex-table", "data"),
                State("key-drop", "value"),
                State("ex-slider", "value")])
def export_ngrams(n, data, key, x):
    if n is None:
        raise PreventUpdate

    if data is None:
        logging.getLogger("messages").error("No data to export!")
        raise PreventUpdate

    logging.getLogger("messages").info("Preparing ngrams for download.")
    to_export = pd.DataFrame.from_records(data)
    to_export = to_export[['chunk', 'count']]

    name = "ngram_{}_{}.csv".format(key, x)
    return dcc.send_data_frame(to_export.to_csv, name, index=False)
