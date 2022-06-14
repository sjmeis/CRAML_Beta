# Author: Stephen Meisenbacher
# view for setup page

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
from .utility import get_settings

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

def create_tab(i, x, name, disabled, INIT=None):
    if INIT is None:
        INIT = {"parent":None, "id":None, "ext":None, 
                "extract":None, "file_extract":None, "file_extract_dir":None}

    direct = html.Div([html.Div(html.P("Parent directory for this data: "), 
                                        style={"display":"inline-block", "padding-right":"1rem"}),
                                html.Div(dbc.Input(id="tab-{}-dir".format(i), 
                                                    placeholder="Input (relative) parent directory.",
                                                    value=INIT['parent'],
                                                    debounce=True, type="text", valid=None,
                                                    style={"width":"50rem"}), 
                                style={"display":"inline-block"})],
                                style={"display":"inline-block"})

    browse = html.Div(dbc.Button("Browse", id="setup-data-dir-browse-{}".format(i)), style={"display":"inline-block"})

    extension = html.Div([html.Div(html.P("Input file type: "), 
                                    style={"display":"inline-block", "padding-left":"1rem"}),
                            html.Div(dcc.Dropdown(id="ext-{}-drop".format(i), 
                                                searchable=False,
                                                placeholder="Select file type.",
                                                options=[
                                                    {"label":"Text File (.txt)", "value":".txt"},
                                                    {"label":"CSV File (.csv)", "value":".csv"},
                                                    {"label":"XML File (.xml)", "value":".xml"},
                                                    {"label":"Zip File (.zip)", "value":".zip"}
                                                ],
                                                value=INIT['ext'],
                                                style={"padding-left":"1rem", "padding-top":"1rem", "width":"25rem"}), 
                            style={"display":"inline-block", "verticalAlign":"bottom"})],
                            style={"padding":"2rem", "display":"inline-block"})

    file_table = dash_table.DataTable(
                id="setup-table-{}".format(i),
                columns=[{"id":"filename", "name":"filename", "selectable":False}, 
                        {"id":"size", "name":"size", "selectable":False}],
                data=None,
                editable=False,
                row_deletable=False,
                row_selectable="multi",
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

    all_button = dbc.Button("Select All Files", id="setup-all-button-{}".format(i))

    drop = dcc.Dropdown(id="tab-{}-drop".format(i), 
                        options=[{"label":y, "value":y} for y in x],
                        placeholder="Identifier:",
                        value=INIT['id'],
                        style={"padding-top":"1rem"})

    ext_drop = dcc.Dropdown(id="tab-{}-extdrop".format(i), 
                            options=[{"label":"None", "value":"None"}]+[{"label":y, "value":y} for y in x],
                            placeholder="Select field to extract:", value=INIT['extract'],
                            style={"padding-top":"1rem"})

    file_opt = html.Div(id="file-div-{}".format(i),
                        children=[html.P("Extract field contains filename? ", id="filename-prompt",
                                    style={"display":"inline-block", "padding-left":"1rem"}),
                                dbc.Tooltip("Select if text is contained in individual files and metadata records the filename.", target="filename-prompt", style={"font-size":"16px"}),
                                daq.BooleanSwitch(id="file-{}-switch".format(i), 
                                    on=INIT['file_extract'],
                                    label="",
                                    labelPosition="right",
                                    style={"display":"inline-block", "padding":"1rem"})], 
                        style={"display":"inline-block", "visibility":"hidden", "padding-right":"2rem"})

    file_dir = html.Div(id="file-dir-div-{}".format(i), 
                        children=[html.Div(html.P("Location of these text files: "), 
                                        style={"display":"inline-block", "padding-right":"1rem"}),
                                html.Div(dbc.Input(id="file-{}-dir".format(i), 
                                                    placeholder="Input (relative) parent directory.",
                                                    value=INIT['file_extract_dir'],
                                                    debounce=True, type="text", valid=None,
                                                    style={"width":"50rem"}), 
                                style={"display":"inline-block"}),
                                html.Div(dbc.Button("Browse", id="setup-file-dir-browse-{}".format(i)), 
                                        style={"display":"inline-block"})],
                                style={"display":"inline-block", "visibility":"hidden"})

    all_switch = html.Div(children=[html.Div(html.P(id="left-p", children="None\t"), style={"display":"inline-block"}), 
        html.Div(daq.BooleanSwitch(id="tab-{}-switch".format(i), on=True), style={"display":"inline-block"}),
        html.Div(html.P(id="right-p", children="\tAll"), style={"display":"inline-block"})], 
        style={"display":"inline-block", "padding":"1rem"})

    check = dcc.Checklist(id="tab-{}-check".format(i),
                            options=[{"label":y, "value":y} for y in x], 
                            value=x, 
                            labelStyle={'display': 'inline-block', 'padding':'1rem'})

    if disabled == True:
        temp = dcc.Tab(id="tab-{}".format(i), label=None,
                    children=[direct, browse, extension, file_table, all_button, drop, ext_drop, file_opt, file_dir,
                                all_switch, check], disabled=disabled, style={"display": "none"})
    else:
        temp = dcc.Tab(id="tab-{}".format(i), label=name, style=tab_style, selected_style=tab_selected_style,
                    children=[direct, browse, extension, file_table, all_button, drop, ext_drop, file_opt, file_dir,
                            html.Hr(),html.H6("Fields to keep:"), all_switch, check])
    return temp

def get_layout(project):
    global SETUP

    settings = get_settings(project)
    if settings is not None:
        SETUP = settings

        children = []
        for i, x in enumerate(settings):
            init_d = {"parent":settings[x]['parent'], "id":settings[x]['id'], "ext":settings[x]['ext'],
                        "extract":settings[x]['extract'], "file_extract":settings[x]['file_extract'],
                        "file_extract_dir":settings[x]['file_extract_dir']}
            children.append(create_tab(i, settings[x]['fields'], x, False, INIT=init_d))

        if len(children) == 1:
            children.append(create_tab(1, [], "", True))

        tabs = dcc.Tabs(id="tabs", value="tab-content", style=tabs_styles, children=children, persistence_type="memory")
        logging.getLogger("messages").info("Pre-filled settings with existing setup.")
    else:
        tabs = dcc.Tabs(id="tabs", value="tab-content", style=tabs_styles,
                children=[create_tab(0, [], "", True), create_tab(1, [], "", True)], persistence_type="memory")

    upload = html.Div([dcc.Upload(id="input-upload",   
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select Files'),
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=False
            )
        ]
        )

    loading = dcc.Loading(id="setup-loading")

    setup_div0 = html.Div(id="setup-div0", style={"display":"none"})
    setup_div1 = html.Div(id="setup-div1", style={"display":"none"})

    dialog = dcc.ConfirmDialog(id="setup-dialog", displayed=False)
    submit = dbc.Button("Submit", id="submit-button")
    clear = dbc.Button("Clear", id="settings-clear-button")
    set_buttons = html.Div(dbc.ButtonGroup([submit, clear], size="lg", className="me-1"), style={"width":"80%"})

    content = [dialog, upload, html.Hr(), loading, tabs, set_buttons, setup_div0, setup_div1]

    top = [html.H1("Setup"), html.H4("Please upload example input files"), html.Hr(),
    html.Div(children=[html.Div(html.P(id="left-p", children="1 input file type\t"), style={"display":"inline-block", "padding":"1rem"}),
            dbc.Tooltip("Metadata and data are contained in single files.", target="left-p", style={"font-size":"16px"}), 
            html.Div(daq.BooleanSwitch(id="setup-switch", on=False), style={"display":"inline-block"}),
            html.Div(html.P(id="right-p", children="\t2 input file types"), style={"display":"inline-block", "padding":"1rem"}),
            dbc.Tooltip("Metadata is located in separate files from the text data.", target="right-p", style={"font-size":"16px"})], 
            style={"display":"inline-block"})]

    layout = top + [html.Div(id="setup-content", children=content)]

    return layout

@app.callback(Output("input-upload", "multiple"),
                Input("setup-switch", "on"))
def switch(on):
    if on == True:
        logging.getLogger("messages").info("Option updated: 2 input files now expected.")
        return True
    else:
        logging.getLogger("messages").info("Option updated: 1 input file now expected.")
        return False 

for idx in [0,1]:
    @app.callback([Output("tab-{}-drop".format(idx), "options"), Output("tab-{}-extdrop".format(idx), "options")],
                Input("tab-{}-check".format(idx), "value")
            )
    def update_check(values):
        return [{"label":v, "value":v} for v in values], [{"label":"None", "value":"None"}]+[{"label":v, "value":v} for v in values]

    @app.callback(Output("setup-div{}".format(idx), "children"), 
                Input("tab-{}-drop".format(idx), "value"),
                State("tab-{}".format(idx), "label")
            )
    def update_drop(id, name):
        if id is None or name is None:
            raise PreventUpdate

        if name in SETUP:
            SETUP[name]["id"] = id
        else:
            SETUP[name] = {}
            SETUP[name]["id"] = id
        return None

    @app.callback(Output("tab-{}-check".format(idx), "value"),
                [Input("tab-{}-switch".format(idx), "on"), 
                Input("tab-{}-check".format(idx), "options")])
    def switch_update(on, values):
        ctx = dash.callback_context
        which = ctx.triggered[0]['prop_id'].split('.')[0]

        if "switch" in which:
            if on == True:
                return [x['value'] for x in values]
            else:
                return [] 
        else:
            return [x['value'] for x in values]

    @app.callback([Output("tab-{}-dir".format(idx), "valid"), Output("tab-{}-dir".format(idx), "invalid"),
                Output("setup-table-{}".format(idx), "data"), Output("ext-{}-drop".format(idx), "value")], 
                [Input("tab-{}-dir".format(idx), "value"), Input("ext-{}-drop".format(idx), "value")],
                [State("tab-{}".format(idx), "label"), State("tab-{}-drop".format(idx), "value"),
                State("tab-{}-check".format(idx), "value"), State("tab-{}-extdrop".format(idx), "value")]
            )
    def validate_dir(direct, extension, name, id, values, ext):
        global SETUP

        ctx = dash.callback_context
        which = ctx.triggered[0]['prop_id'].split('.')[0]

        if direct is None or direct == "" or Path(direct).is_dir() == False:
            if direct is not None:
                logging.getLogger("messages").error("Directory {} is invalid.".format(direct))
            return False, True, None, None
        else:
            if name not in SETUP:
                SETUP[name] = {}
            SETUP[name]["parent"] = direct

            if "tab" in which:
                ext_search = SETUP[name]['ext']
            elif "ext" in which:
                ext_search = extension
                SETUP[name]['ext'] = extension
            else:
                ext_search = extension

            # get all files under directory
            filenames = [x for x in Path(direct).rglob("*{}".format(ext_search))]
            sizes = ["{} MB".format(round(os.path.getsize(x)/(1024*1024),2)) for x in filenames]
            filenames = [x.name for x in filenames]
            data = pd.DataFrame(zip(filenames, sizes), columns=["filename", "size"])

            if "tab" in which:
                logging.getLogger("messages").info("Valid directory!")
                return True, False, data.to_dict('records'), SETUP[name]['ext']
            elif "ext" in which:
                return True, False, data.to_dict('records'), no_update
            else:
                return True, False, data.to_dict('records'), no_update

    @app.callback(Output("file-{}-dir".format(idx), "valid"),
                    Input("file-{}-dir".format(idx), "value"),
                    State("tab-{}".format(idx), "label"))
    def validate_file_dir(direct, name):
        if direct is None or direct == "" or Path(direct).is_dir() == False:
            if direct is not None:
                logging.getLogger("messages").error("Directory {} is invalid.".format(direct))
            return False
        else:
            logging.getLogger("messages").info("Valid directory!")
            return True

    @app.callback(
        [Output("setup-table-{}".format(idx), "selected_rows")],
        [Input("setup-all-button-{}".format(idx), "n_clicks"), 
        Input("setup-table-{}".format(idx), "data")],
        [State("setup-table-{}".format(idx), "derived_virtual_data"),
        State("project", "data"), State("setup-table-{}".format(idx), "selected_rows")]
    )
    def select_all(n, data, selected_rows, proj, already):
        ctx = dash.callback_context
        which = ctx.triggered[0]['prop_id'].split('.')[0]

        if which == "setup-all-button-{}".format(idx):
            if n is None:
                raise PreventUpdate

            if selected_rows is None:
                return [[]]
            else:
                return [[j for j in range(len(selected_rows))]]
        else:
            if data is None or already is not None:
                raise PreventUpdate

            preselect = []
            settings = get_settings(proj['project'])
            if settings is None:
                raise PreventUpdate

            filenames = [x['filename'] for x in data]
            for k in settings:
                if settings[k]['extract'] != "None":
                    options = [Path(x).name for x in settings[k]["files"]]
                    preselect = [i for i, x in enumerate(filenames) if x in options]
            return [preselect]

    @app.callback([Output("file-{}-switch".format(idx), "label"), 
                    Output("file-div-{}".format(idx), "style"), 
                    Output("file-dir-div-{}".format(idx), "style")],
                    [Input("tab-{}-extdrop".format(idx), "value"), 
                    Input("file-{}-switch".format(idx), "on")])
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

@app.callback([Output('setup-loading', 'children'), Output('tabs', 'children'), Output('tabs', 'value')],
             [Input('input-upload', 'contents'), Input("settings-clear-button", "n_clicks")],
              [State('input-upload', 'filename'), State("project", "data")])
def update_output(contents, n, filenames, data):
    global SETUP
    
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if which == "settings-clear-button":
        if n is None:
            raise PreventUpdate
        else:
            SETUP = {}
            logging.getLogger("messages").info("Settings cleared!")
            return " ", [create_tab(0, [], "", True), create_tab(1, [], "", True)], None
    else:
        if contents is None:
            raise PreventUpdate

        if filenames is not None:
            all_cols = []
            names = []

            if type(filenames) is list:
                logging.getLogger("messages").info("2 files uploading...")
                for k, tup in enumerate(zip(filenames, contents)):
                    f = tup[0]
                    c = tup[1]

                    _, content_string = c.split(',')

                    #name = os.path.splitext(f)[0]
                    name = "{}_{}".format(data['project'].split('/')[-1], k)
                    if name not in SETUP:
                        SETUP[name] = {}
                    logging.getLogger("messages").info("Processing {}...".format(name))
                    names.append(name)
                    ext = os.path.splitext(f)[1]
                    SETUP[name]["ext"] = ext
                    decoded = base64.b64decode(content_string)
                    if "zip" in ext.lower():
                        columns, delim = check_zip(decoded)
                        all_cols.append(columns)
                        SETUP[name]["delim"] = delim
                    elif "xml" not in ext.lower():
                        columns, delim = check_csv(decoded)
                        all_cols.append(columns)
                        SETUP[name]["delim"] = delim
                    else:
                        columns, delim = check_xml(decoded)
                        all_cols.append(columns)
                        SETUP[name]["delim"] = delim
            else:
                logging.getLogger("messages").info("File uploading...")
                _, content_string = contents.split(',')

                #name = os.path.splitext(filenames)[0]
                name = "{}_0".format(data['project'].split('/')[-1])
                if name not in SETUP:
                    SETUP[name] = {}
                logging.getLogger("messages").info("Processing {}...".format(name))
                names.append(name)
                ext = os.path.splitext(filenames)[1]
                SETUP[name]["ext"] = ext
                decoded = base64.b64decode(content_string)
                if "zip" in ext.lower():
                    columns, delim = check_zip(decoded)
                    all_cols.append(columns)
                    SETUP[name]["delim"] = delim
                elif "xml" not in ext.lower():
                    columns, delim = check_csv(decoded)
                    all_cols.append(columns)
                    SETUP[name]["delim"] = delim
                else:
                    columns, delim = check_xml(decoded)
                    all_cols.append(columns)
                    SETUP[name]["delim"] = delim

            children = []
            for j, x in enumerate(all_cols):
                children.append(create_tab(j, x, names[j], False))

            if len(children) == 1:
                children.append(create_tab(1, [], "", True))

            logging.getLogger("messages").info("Upload success!")

            return "", children, no_update
        else:
            raise PreventUpdate

@app.callback(Output("setup-dialog", "displayed"),
                Input("submit-button", "n_clicks"),
                [State("tab-0-dir", "valid"), State("tab-1-dir", "valid"),
                State("tab-0-drop", "value"), State("tab-1-drop", "value"),
                State("tab-0-check", "value"), State("tab-1-check", "value"),
                State("tab-0", "label"), State("tab-1", "label"),
                State("tab-0-extdrop", "value"), State("tab-1-extdrop", "value"),
                State("file-0-switch", "on"), State("file-1-switch", "on"),
                State("file-0-dir", "value"), State("file-1-dir", "value"),
                State("file-0-dir", "valid"), State("file-1-dir", "value"),
                State("project", "data"),
                State("setup-table-0", "selected_rows"), State("setup-table-0", "data"),
                State("setup-table-1", "selected_rows"), State("setup-table-1", "data")])
def save_setup(n, v1, v2, d1, d2, c1, c2, l1, l2, e1, e2, fs1, fs2, fd1, fd2, fv1, fv2, data, selected_rows_0, table_data_0, selected_rows_1, table_data_1):
    global SETUP

    if n is None:
        raise PreventUpdate

    if e1 is None:
        e1 = "None"
    if e2 is None:
        e2 = "None"

    if (e1 == "None" and e2 == "None") or (e1 != "None" and e2 != "None"):
        logging.getLogger("messages").error("One input must have a text field to be extracted.")
        return False
    elif v1 == False or d1 is None:
        return False, ""
    elif (v2 == False or d2 is None) and l2 is not None:
        return False, ""
    else:
        if l2 is None:
            if e1 == "None":
                logging.getLogger("messages").error("One input must have a text field to be extracted.")
                return False
            if selected_rows_0 is None:
                logging.getLogger("messages").error("No extract files selected.")
                return False
        else:
            if e2 == "None":
                if selected_rows_0 is None:
                    logging.getLogger("messages").error("No extract files selected ({}).".format(l1))
                    return False
            if e1 == "None":
                if selected_rows_1 is None:
                    logging.getLogger("messages").error("No extract files selected ({}).".format(l2))
                    return False

        SETUP[l1]["fields"] = c1
        SETUP[l1]["id"] = d1
        SETUP[l1]["extract"] = e1

        if l2 is None:
            if e1 == "None" and selected_rows_0 is None:
                logging.getLogger("messages").error("No extract files selected.")
                return False
        else:
            SETUP[l2]["fields"] = c2
            SETUP[l2]["id"] = d2
            SETUP[l2]["extract"] = e2

        if l1 is not None:
            files =[(Path(SETUP[l1]["parent"]) / table_data_0[j]['filename']).as_posix() for j in selected_rows_0]
            SETUP[l1]["files"] = files
        if l2 is not None:
            files =[(Path(SETUP[l2]["parent"]) / table_data_1[j]['filename']).as_posix() for j in selected_rows_1]
            SETUP[l2]["files"] = files

        if e1 != "None":
            if fs1 == True:
                if fv1 == False:
                    logging.getLogger("messages").error("Invalid file directory. ({})".format(l1))
                    return False
                else:
                    SETUP[l1]["file_extract"] = True
                    SETUP[l1]["file_extract_dir"] = fd1
            else:
                SETUP[l1]["file_extract"] = False
        elif e2 != "None" and l2 is not None:
            if fs2 == True:
                if fv2 == False:
                    logging.getLogger("messages").error("Invalid file directory. ({})".format(l2))
                    return False
                else:
                    SETUP[l1]["file_extract"] = True
                    SETUP[l1]["file_extract_dir"] = fd2
            else:
                SETUP[l2]["file_extract"] = False            

        save_path = (Path(data['project']) / "settings.json").as_posix()
        with open(save_path, 'w') as out:
            json.dump(SETUP, out, indent=3)

        logging.getLogger("messages").critical("Setup saved to {}".format(save_path))
        return False

@app.callback(Output("setup-dir-gui-hidden", "children"),
                [Input("setup-data-dir-browse-0", "n_clicks"),
                Input("setup-data-dir-browse-1", "n_clicks"),
                Input("setup-file-dir-browse-0", "n_clicks"),
                Input("setup-file-dir-browse-1", "n_clicks")])
def call_gui(n, n2, n3, n4):
    if n is None and n2 is None and n3 is None and n4 is None:
        raise PreventUpdate
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if platform.system() == "Darwin":
        logging.getLogger("messages").error("Browse feature not supported on Mac.")
        raise PreventUpdate

    if "data" in which:
        return "Setup Data {}".format(which.split('-')[-1])
    elif "file" in which:
        return "Setup File {}".format(which.split('-')[-1])
    else:
        raise PreventUpdate

@app.callback([Output("tab-0-dir", "value"), Output("tab-1-dir", "value"),
                Output("file-0-dir", "value"), Output("file-1-dir", "value")],
                Input("ret-dir-gui-hidden", "children"))
def fill_dir(data):
    if data is None:
        raise PreventUpdate

    ret = data.split(':::')[-1]
    if "Setup Data 0" in data:
        if ret != "":
            return ret, no_update, no_update, no_update
    if "Setup Data 1" in data:
        if ret != "":
            return no_update, ret, no_update, no_update
    if "Setup File 0" in data:
        if ret != "":
            return no_update, no_update, ret, no_update
    if "Setup File 1" in data:
        if ret != "":
            return no_update, no_update, no_update, ret
    raise PreventUpdate

@app.callback([Output("tab-0-check", "options"),
                Output("tab-1-check", "options")],
                [Input("setup-table-0", "selected_rows"), Input("setup-table-1", "selected_rows")],
                [State("setup-table-0", "data"), State("setup-table-1", "data"),
                State("tab-0-dir", "value"), State("tab-1-dir", "value")],
                prevent_initial_call=True)
def common_cols(sel_0, sel_1, data_0, data_1, dir_0, dir_1):
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if which == "setup-table-0":
        if sel_0 is None or len(sel_0) == 0:
            raise PreventUpdate

        sel_files = [x['filename'] for i, x in enumerate(data_0) if i in sel_0]
        intersection = pd.read_csv((Path(dir_0) / sel_files[0]).as_posix(), nrows=2).columns
        if len(sel_files) > 1:
            for s in sel_files[1:]:
                temp = pd.read_csv((Path(dir_0) / s).as_posix(), nrows=2).columns
                intersection = intersection & temp

        return [{"label":x, "value":x} for x in intersection], no_update

    elif which == "setup-table-1":
        if sel_1 is None or len(sel_1) == 0:
            raise PreventUpdate

        sel_files = [x['filename'] for i, x in enumerate(data_1) if i in sel_1]
        intersection = pd.read_csv(Path(dir_1 / sel_files[0]).as_posix(), nrows=2).columns
        if len(sel_files) > 1:
            for s in sel_files[1:]:
                temp = pd.read_csv((Path(dir_1) / s).as_posix(), nrows=2).columns
                intersection = intersection & temp

        return no_update, [{"label":x, "value":x} for x in intersection]