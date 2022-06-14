# Author: Stephen Meisenbacher
# view for sample page

from pathlib import Path
import random
import shutil
import os
import pandas as pd
import logging
import platform

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_daq as daq

from server import app
from .utility import get_settings

random.seed(42)

def sample_dir(dir, n, ext, project, SINGLE=False, SUBD=False, FILES=None, FIELDS=None):
    path = Path(project) / "sample"

    if path.is_dir() == False:
        os.makedirs(path.as_posix())

    save = Path(project) / "sample"
    if SINGLE == True:
        if SUBD == True:
            sample = None
            check = [Path(x).resolve() for x in FILES]
            for d in Path(dir).iterdir():
                if d.resolve() in check:
                    parent = d.stem
                    data = pd.read_csv(d)[FIELDS]
                    data['parent'] = parent
                    if sample is None:
                        sample = data.sample(frac=n/100)
                    else:
                        data = data.sample(frac=n/100)
                        sample = pd.concat([sample, data], ignore_index=True)
        else:
            data = pd.read_csv(dir)[FIELDS]
            sample = data.sample(frac=n/100)

        save = save / "sample.csv"
        sample.to_csv(save.as_posix(), index=False)
        return len(sample.index)
    else:
        all_dir = Path(dir).rglob("*{}".format(ext))
        files = [x for x in all_dir if x.is_file()]

        num = int(len(files) * (n/100))
        sample = random.sample(files, num)

        for f in sample:
            shutil.copy2(f.as_posix(), save.as_posix())
        return len(sample)

def get_layout(project):
    settings = get_settings(project)
    init_val = None
    if settings is not None:
        for k in settings:
            if settings[k]['extract'] != "None":
                init_val = settings[k]['parent']
                break

    dialogs= [dcc.ConfirmDialog(id="clear-confirm", message="Are you sure you wish to clear the sample directory?", displayed=False), 
                dcc.ConfirmDialog(id="sample-success", message=None,displayed=False)]

    loading = dcc.Loading(id="sample-loading")

    switch = html.Div(children=[html.Div(html.P(id="left-p-switch", children="Sample from single file (from setup)\t"), style={"display":"inline-block", "padding":"1rem"}),
            dbc.Tooltip("Select to sample text from a single file (i.e. where the extract field contains filenames).", target="left-p-switch", style={"font-size":"16px"}), 
            html.Div(daq.BooleanSwitch(id="sample-switch", on=True), style={"display":"inline-block"}),
            html.Div(html.P(id="right-p", children="\tSample from parent directory"), style={"display":"inline-block", "padding":"1rem"}),
            dbc.Tooltip("Select to sample text from a parent directory containing all the text data files.", target="right-p", style={"font-size":"16px"})], 
            style={"display":"inline-block"})

    direct = dbc.Input(id="sample-dir", 
                            placeholder="Input (relative or absolute) parent directory of text data files. Or hit Browse.",
                            value=init_val,
                            debounce=True, 
                            type="text",
                            autocomplete=False,
                            style={"padding-bottom":"1rem", "display":"inline-block", "width":"90%"})

    browse = html.Div(dbc.Button("Browse", id="sample-dir-browse"), style={"display":"inline-block"})

    dir_browse = html.Div([direct, browse])

    slider = html.Div([html.P("Sample Rate:"),
                        dcc.Slider(id="sample-slider", min=0, max=100, step=5, value=10, 
                        marks={x:str(x) for x in range(0,101,5)})], 
                        style={"padding":"2rem"})

    sample = dbc.Button("Sample", id="sample-button")
    clear = dbc.Button("Clear", id="clear-button")
    buttons = html.Div(dbc.ButtonGroup([sample, clear], size="lg", className="me-1"), style={"width":"80%"})

    layout = dialogs+[loading, html.H1("Sample"), html.H4("Create a sample to build training data."), 
                html.Hr(), switch, dir_browse, slider, buttons]

    return layout

@app.callback([Output("sample-dir", "valid"), Output("sample-dir", "invalid")],
                Input("sample-dir", "value"), State("project", "data"))
def validate_sample_dir(path, data):
    if path is None:
        raise PreventUpdate

    if Path(path).is_dir() == True:
        logging.getLogger("messages").info("Valid directory! ({})".format(path))
        return True, False
    else:
        logging.getLogger("messages").error("Invalid directory: {}".format(path))
        return False, True

@app.callback([Output("sample-loading", "children"), 
                Output("sample-success", "displayed")],
                Input("sample-button", "n_clicks"),
                [State("sample-dir", "valid"), State("sample-dir", "value"), 
                State("sample-slider", "value"), State("sample-switch", "on"),
                State("project", "data")])
def sample(n, valid, dir, value, on, data):
    if n is None:
        raise PreventUpdate

    settings = get_settings(data['project'])
    if settings is None:
        logging.getLogger("messages").error("Setup not performed. Do that first!")
        return " ", False

    if on == False:
        for k in settings:
            if settings[k]['extract'] != "None" and Path(settings[k]["files"][0]).is_file() == False:
                logging.getLogger("messages").error("Sample file is not located in the specified directory.")
                return " ", False

    save_path = Path(data['project']) / "sample"
    if valid == False:
        logging.getLogger("messages").error("Please fill in valid directory information.")
        return " ", False
    elif dir is None:
        logging.getLogger("messages").error("No directory given.")
        return " ", False
    elif on == False:
        SUBD = False
        FILES = None
        FIELDS = None
        for k in settings:
            if settings[k]['extract'] != "None":
                FIELDS = settings[k]['fields']
                if len(settings[k]['files']) > 1:
                    dir = Path(settings[k]['files'][0]).parent.as_posix()
                    SUBD = True
                    FILES = settings[k]['files']
                else:
                    dir = settings[k]['files'][0]
                break

        num_sampled = sample_dir(dir, value, None, data['project'], SINGLE=True, SUBD=SUBD, FILES=FILES, FIELDS=FIELDS)
        message = "Sample file [{} row(s)] created - saved to {}".format(num_sampled, (save_path / "sample.csv").as_posix())
        logging.getLogger("messages").critical(message)
        return " ", False
    else:
        ext = None
        for k in settings:
            if settings[k]['extract'] != "None":
                ext = settings[k]['ext']
                break

        num_sampled = sample_dir(dir, value, ext, data['project'])
        message = "Sample directory ({} files) created - saved to {}".format(num_sampled, save_path.as_posix())
        logging.getLogger("messages").info(message)
        return " ", False

@app.callback(Output("clear-confirm", "displayed"),
                [Input("clear-button", "n_clicks"), Input("clear-confirm", "submit_n_clicks")],
                State("project", "data"))
def clear_confirm(n1, n2, data):
    if n1 is None and n2 is None:
        raise PreventUpdate
    
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if which == "clear-button" and n1 > 0:
        return True
    elif which == "clear-confirm" and n2 > 0:
        if len(list((Path(data['project']) / "sample").glob("*"))) == 0:
            logging.getLogger("messages").error("Sample directory already empty.")
            raise PreventUpdate

        for f in (Path(data['project']) / "sample").glob("*"):
            if f.is_file():
                f.unlink()
        logging.getLogger("messages").info("Sample directory cleared!")
        return False

@app.callback(Output("sample-switch", "style"),
                Input("sample-switch", "on"),
                State("project", "data"))
def guide_switch(on, data):
    settings = get_settings(data['project'])
    if settings is None:
        logging.getLogger("messages").warning("Setup not complete. Turn back!")
        raise PreventUpdate

    file_extract = False
    for k in settings:
        if settings[k]['extract'] != "None" and settings[k]['file_extract'] == True:
            file_extract = True

    if file_extract == True:
        if on == False:
            logging.getLogger("messages").info("Recommended sample options met.")
        else:
            logging.getLogger("messages").warning("Switch option is set to ON, even though you chose File Extract mode in Setup.")
    else:
        if on == False:
            logging.getLogger("messages").warning("Switch option is set to OFF, recommended setting os ON with current setup.")
        else:
            logging.getLogger("messages").info("Recommended sample options met.")

    return {"display":"inline-block"}

@app.callback(Output("sample-dir-gui-hidden", "children"),
                Input("sample-dir-browse", "n_clicks"))
def call_gui(n):
    if n is None:
        raise PreventUpdate

    if platform.system() == "Darwin":
        logging.getLogger("messages").error("Browse feature not supported on Mac.")
        raise PreventUpdate

    return "Sample"

@app.callback(Output("sample-dir", "value"),
                Input("ret-dir-gui-hidden", "children"))
def fill_dir(data):
    if data is None:
        raise PreventUpdate

    if "Sample" in data:
        ret = data.split(':::')[-1]
        if ret != "":
            return ret
        else:
            raise PreventUpdate
    else:
        raise PreventUpdate