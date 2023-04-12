# Author: Stephen Meisenbacher
# view for setup (db) page

import os
import json
import io
import base64
import pandas as pd
from lxml import etree
import csv
import zipfile
from pathlib import Path
from collections import defaultdict
import logging
import platform

import dash
from dash import dcc
import dash_bootstrap_components as dbc
from dash import html
import dash_daq as daq
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash import dash_table, no_update

from server import app
from .utility import get_settings, get_mongo_client

SETUP = defaultdict(lambda: defaultdict())

tabs_styles = {
    'height': '44px'
}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '5px',
    'fontWeight': 'bold',
    "display":"block"
}
tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': '#119DFF',
    'color': 'white',
    'padding': '5px'
}

def check_xml(data):
    doc = etree.ElementTree(etree.fromstring(data))
    root = doc.getroot()

    elements = []
    for child in root:
        for e in child:
            elements.append(e.tag)
        break

    return elements, None

def check_csv(decoded):
    line = io.StringIO(decoded.decode('utf-8')).readline()

    dialect = csv.Sniffer().sniff(line)
    delim = dialect.delimiter

    columns = [x.strip() for x in line.split(delim)]

    return columns, delim

def check_zip(decoded):
    with zipfile.ZipFile(io.BytesIO(decoded), 'r') as z:
        for subd in z.namelist():
            ext = os.path.splitext(subd)[1]
            if "xml" in ext.lower():
                with z.open(subd) as f:
                    return check_xml(f.read())
            else:
                with z.open(subd) as f:
                    return check_csv(f.read())

def get_dbs():
    client = get_mongo_client()    

    dbs = [db for db in client.list_database_names()]
    options = []
    for d in dbs:
        options.append({"label":d, "value":d})

    return options

def create_tab(x, name, disabled, INIT=None):
    if INIT is None:
        INIT = {"db":None, "collection":None, "fields":None, 
                "id":None, "extract":None}

    direct = html.Div(id="db-direct-div", children=[html.Div(html.P("Mongo collection for this data: "), 
                                        style={"display":"inline-block", "padding-right":"1rem"}),
                                html.Div(dcc.Dropdown(id="db-name-drop", 
                                                    placeholder="Select Mongo collection.",
                                                    value=INIT['db'],
                                                    options=get_dbs(),
                                                    style={"padding-left":"1rem", "padding-top":"1rem", "width":"50rem"}), 
                                style={"display":"inline-block"})],
                                style={"display":"inline-block"})

    db_table = dash_table.DataTable(
                id="setup-db-table",
                columns=[{"id":"collection", "name":"collection", "selectable":False},
                        {"id":"entries", "name":"entries", "selectable":False}],
                data=None,
                editable=False,
                row_deletable=False,
                row_selectable="single",
                style_cell = {
                    'font_size':'16px',
                    'text_align':'center',
                    'maxWidth':'500px',
                },
                fixed_rows={'headers': True},
                style_table={'max_height': 200, 'padding':'2rem'},
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
                sort_action='native',
                persistence=False
    )

    drop = dcc.Dropdown(id="tab-db-drop", 
                        options=[{"label":y, "value":y} for y in x],
                        placeholder="Identifier:",
                        value=INIT['id'],
                        style={"padding-top":"1rem"})

    ext_drop = dcc.Dropdown(id="tab-db-extdrop", 
                            options=[{"label":"None", "value":"None"}]+[{"label":y, "value":y} for y in x],
                            placeholder="Select field to extract:", value=INIT['extract'],
                            style={"padding-top":"1rem"})

    '''
    file_opt = html.Div(id="db-file-div",
                        children=[html.P("Extract field contains filename? ", id="db-filename-prompt",
                                    style={"display":"inline-block", "padding-left":"1rem"}),
                                dbc.Tooltip("Select if text is contained in individual files and metadata records the filename.", target="filename-prompt", style={"font-size":"16px"}),
                                daq.BooleanSwitch(id="db-file-switch", 
                                    on=INIT['file_extract'],
                                    label="",
                                    labelPosition="right",
                                    style={"display":"inline-block", "padding":"1rem"})], 
                        style={"display":"inline-block", "visibility":"hidden", "padding-right":"2rem"})

    file_dir = html.Div(id="db-file-dir-div", 
                        children=[html.Div(html.P("Location of these text files: "), 
                                        style={"display":"inline-block", "padding-right":"1rem"}),
                                html.Div(dbc.Input(id="db-file-dir", 
                                                    placeholder="Input (relative) parent directory.",
                                                    value=INIT['file_extract_dir'],
                                                    debounce=True, type="text", valid=None,
                                                    style={"width":"50rem"}), 
                                style={"display":"inline-block"}),
                                html.Div(dbc.Button("Browse", id="setup-db-file-dir-browse"), 
                                        style={"display":"inline-block"})],
                                style={"display":"inline-block", "visibility":"hidden"})
    '''

    all_switch = html.Div(children=[html.Div(html.P(children="None\t"), style={"display":"inline-block"}), 
        html.Div(daq.BooleanSwitch(id="db-tab-switch", on=False), style={"display":"inline-block"}),
        html.Div(html.P(children="\tAll"), style={"display":"inline-block"})], 
        style={"display":"inline-block", "padding":"1rem"})

    check = dcc.Checklist(id="db-tab-check",
                            options=[{"label":y, "value":y} for y in x], 
                            value=x, 
                            labelStyle={'display': 'inline-block', 'padding':'1rem'})

    if disabled == True:
        temp = dcc.Tab(id="tab", label=None,
                    children=[html.Hr(), direct, db_table, drop, ext_drop, #file_opt, file_dir,
                                all_switch, check], disabled=disabled, style={"display": "none"})
    else:
        temp = dcc.Tab(id="tab", label=name, style=tab_style, selected_style=tab_selected_style,
                    children=[html.Hr(), direct, db_table, drop, ext_drop, #file_opt, file_dir,
                            html.Hr(),html.H6("Fields to keep:"), all_switch, check])
    return temp

def get_layout(project):
    global SETUP

    settings = get_settings(project)
    if settings is not None:
        SETUP = settings

        children = []
        for x in settings:
            if "db" in settings[x]:
                init_d = {"db":settings[x]['db'], "dollection":settings[x]['collection'], "id":settings[x]['id'],
                            "extract":settings[x]['extract'], "fields":settings[x]['fields']}
                children.append(create_tab(settings[x]['fields'], x, False, INIT=init_d))
            else:
                children.append(create_tab(settings[x]['fields'], x, False))

        tabs = dcc.Tabs(id="tabs-db", value="tab-content", style=tabs_styles, children=children, persistence_type="memory")
        logging.getLogger("messages").info("Pre-filled settings with existing setup.")
    else:
        tabs = dcc.Tabs(id="tabs-db", value="tab-content", style=tabs_styles,
                children=[create_tab([], "Mongo DB Setup", False)], persistence_type="memory")

    loading = dcc.Loading(id="setup-db-loading")

    setup_div0 = html.Div(id="setup-db-div", style={"display":"none"})

    dialog = dcc.ConfirmDialog(id="setup-db-dialog", displayed=False)
    submit = dbc.Button("Submit", id="submit-db-button")
    clear = dbc.Button("Clear", id="settings-clear-db-button")
    set_buttons = html.Div(dbc.ButtonGroup([submit, clear], size="lg", className="me-1"), style={"width":"80%"})

    content = [dialog, html.Hr(), loading, tabs, set_buttons, setup_div0]

    layout = [html.H1("Setup (DB)"), html.H4("Connect your data stored in a Mongo DB"), html.Hr(), html.Div(id="setup-db-content", children=content)]

    return layout

@app.callback(Output("setup-db-table", "data"),
                Input("db-name-drop", "value"))
def update_db_table(val):
    if val is None:
        raise PreventUpdate

    client = get_mongo_client()
    collections = [c for c in client[val].list_collection_names()]

    data = []
    for name in collections:
        c = client[val][name]
        data.append({"collection":c.name, "entries":c.estimated_document_count()})

    return data

@app.callback([Output("tab-db-drop", "options"), Output("tab-db-extdrop", "options"),
                Output("db-tab-check", "options"), Output("setup-db-div", "children")],
                [Input("setup-db-table", "selected_rows"), Input("db-tab-check", "value")],
                [State("setup-db-table", "data"), State("db-name-drop", "value")],
                prevent_initial_call=True)
def common_cols(sel, values, data, db):
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if which == "setup-db-table":
        if sel is None or len(sel) == 0 or db is None:
            raise PreventUpdate

        sel_col = [x['collection'] for i, x in enumerate(data) if i in sel]
        client = get_mongo_client()
        collection = client[db].get_collection(sel_col[0])
        doc = collection.find_one()

        cols = [{"label":x, "value":x} for x in doc.keys()]

        return cols, cols, cols, ""
    else:
       return [{"label":v, "value":v} for v in values], [{"label":"None", "value":"None"}]+[{"label":v, "value":v} for v in values], no_update, no_update

@app.callback([Output("db-file-switch", "label"), 
                Output("db-file-div", "style"), 
                Output("db-file-dir-div", "style")],
                [Input("tab-db-extdrop", "value"), 
                Input("db-file-switch", "on")])
def file_switch_label(extdrop, on):
    no_show = {"display":"none", "visibility":"hidden", "padding":"1rem"}
    if extdrop is None or extdrop == "None":
        return "", no_show, no_show

    style = {"display":"inline-block", "padding":"1rem"}
    if on == True:
        logging.getLogger("messages").info("Option updated: \"{}\" field denotes the name of a file with text to be extracted.".format(extdrop))
        return no_update, style, style
    else:
        logging.getLogger("messages").info("Option updated: \"{}\" field contains text to be extracted.".format(extdrop))
        return no_update, style, no_show

@app.callback(Output("db-tab-check", "value"),
            Input("db-tab-switch", "on"),
            State("db-tab-check", "options"))
def switch_update(on, values):
    #ctx = dash.callback_context
    #which = ctx.triggered[0]['prop_id'].split('.')[0]

    #if "switch" in which:
    if on == True:
        return [x['value'] for x in values]
    else:
        return []
    #else:
    #    return [x['value'] for x in values]

@app.callback(Output("setup-db-dialog", "displayed"),
                Input("submit-db-button", "n_clicks"),
                [State("tab-db-drop", "value"),
                State("db-tab-check", "value"), 
                State("tab-db-extdrop", "value"),
                #State("db-file-switch", "on"),
                #State("db-file-dir", "value"),
                State("project", "data"),
                State("db-name-drop", "value"), 
                State("setup-db-table", "data"),
                State("setup-db-table", "selected_rows")])
def save_setup(n, d1, c1, e1, proj, db, data, sel):
    global SETUP

    l1 = "Mongo"

    if n is None:
        raise PreventUpdate

    if e1 is None:
        logging.getLogger("messages").error("No extract field selected!")
        raise PreventUpdate

    if d1 is None:
        return False, ""
    else:
        collection = [x['collection'] for i, x in enumerate(data) if i in sel][0]

        SETUP[l1]['db'] = db
        SETUP[l1]['collection'] = collection

        SETUP[l1]["fields"] = c1
        SETUP[l1]["id"] = d1
        SETUP[l1]["extract"] = e1

        #if fs1 == True:
        #    SETUP[l1]["file_extract"] = True
        #    SETUP[l1]["file_extract_dir"] = fd1          

        save_path = (Path(proj['project']) / "settings.json").as_posix()
        with open(save_path, 'w') as out:
            json.dump(SETUP, out, indent=3)

        logging.getLogger("messages").critical("Setup saved to {}".format(save_path))
        return False