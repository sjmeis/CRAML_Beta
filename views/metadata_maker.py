# Author: Stephen Meisenbacher
# view for metadata maker

import pandas as pd
from pathlib import Path
import logging

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_daq as daq

from server import app

def get_dirs(project):
    options = []

    if (Path(project) / "data" / "cleaned").is_dir() == True:
        for d in (Path(project) / "data" / "cleaned").iterdir():
            if d.is_dir():
                num_files = len([x for x in d.rglob("*.txt")])
                options.append({"label":"{} [{} files]".format(d.name, num_files), "value":d.name})
        return options
    else:
        logging.getLogger("messages").warning("No cleaned text directories available.")
        return []

def get_layout(project):

    name = html.Div(dbc.Input(id="meta-name", type="text", placeholder="Choose the metadata file name."),
                    style={"padding":"1rem"})

    dir_select = dcc.Dropdown(id="text-dir-select",
                                placeholder="Select which cleaned text directories to include.",
                                options=get_dirs(project),
                                multi=True)

    total = html.P(id="total-files", children="Total files: 0", style={"padding":"1rem"})

    go = html.Div(dbc.Button("Go!", id="make-meta"), style={"padding":"1rem"})
    load = dcc.Loading(id="meta-load")

    layout = [html.H1("Metadata Maker"), html.H4("Prepare your local cleaned text files for CRAML."),
                html.Hr(), name, dir_select, total, go, load]

    return layout

@app.callback(Output("total-files", "children"),
                Input("text-dir-select", "value"),
                State("project", "data"))
def update_total(values, data):
    if values is None or len(values) == 0:
        return "Total files: 0"

    total = 0
    for v in values:
        search = Path(data['project']) / "data" / "cleaned" / v
        total += len([x for x in search.rglob("*.txt")])

    return "Total files: {}".format(total)

@app.callback(Output("meta-load", "children"),
                Input("make-meta", "n_clicks"),
                [State("text-dir-select", "value"), State("meta-name", "value"),
                State("project", "data")])
def make_meta(n, values, name, data):
    if n is None:
        raise PreventUpdate

    if name is None:
        logging.getLogger("messages").error("No filename inputted!")
        raise PreventUpdate

    name = name.split('.')[0]

    rows = []
    for v in values:
        for i, f in enumerate((Path(data['project']) / "data" / "cleaned" / v).rglob("*.txt")):
            rows.append({"id":"{}_{}".format(v, i), "filename":f.name})

    meta = pd.DataFrame(rows)
    save_path = Path(data['project']) / "data" / "{}.csv".format(name)
    meta.to_csv(save_path.as_posix(), index=False)

    logging.getLogger("messages").critical("Created requested metadata file - saved to {}".format(save_path.as_posix()))

    return " "