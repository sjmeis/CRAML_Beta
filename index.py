#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Stephen Meisenbacher
# October 21, 2021
# index.py
# homepage for UI

import platform
import sys
from pathlib import Path
import time
import logging
import io
import queue
from datetime import datetime
import json

import easygui

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from flask import request

from server import app
from views import project, setup, sample, tags, rules, extract, validation, text_ex, train_nb, train_rf, dataset, data_ex, file_browser, pdf_to_text, metadata_maker, dc_login, dc_import

###################### GLOBAL DATA ###############################
PATH = Path(__file__).parent
NAME = "CRAML"
LOG_STREAM = io.StringIO()
q = queue.Queue()
####################################################################

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 5,
    "bottom": 5,
    "width": "25rem",
    "padding": "1rem 1rem",
    "padding-left":"2rem"
    #"background-color": "#f8f9fa",
}

CONTENT_STYLE = {
    #"position":"absolute",
    "margin-left": "-60rem",
    #"margin-right": "2rem",
    "margin-top":"-14rem",
    "padding": "2rem 1rem",
    #"width": "130rem"
    "width":"140%",
}

MESSAGE_STYLE = {
    "position":"fixed",
    "top": 0,
    "margin-top": "0rem",
    "margin-left": "-60rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
    #"width":"130rem",
    "width":"70%",
    "background":"rgb(25, 28, 35)",
    "zIndex":9999
}

message = html.Div([
    html.Hr(),
    html.H5("Message Center:", id="message-head"),
    dbc.ListGroup(id="message", 
        children=[dbc.ListGroupItem("[{}] INFO: Welcome to {}! Your messages will be displayed here.".format(datetime.now().strftime('%m/%d/%Y-%H:%M:%S'), NAME))]),
    html.Hr()],
    style=MESSAGE_STYLE)

sidebar = html.Div(
    [
        html.H2("{} Tool".format(NAME), className="display-4"),
        html.Hr(),
        html.P(
            "{} Navbar".format(NAME), className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("Home", href="/home", active="exact"),
                dbc.NavLink("Project", href="/project", active="exact"),
                dbc.NavLink("Setup", href="/setup", active="exact", disabled=True),
                dbc.NavLink("Sample", href="/sample", active="exact", disabled=True),
                dbc.NavLink("Tags", href="/tags", active="exact", disabled=True),
                dbc.NavLink("Rules", href="/rules", active="exact", disabled=True),
                dbc.NavLink("Extract", href="/extract", active="exact", disabled=True),
                dbc.NavLink("Context Exploration", href="/text_ex/", active="exact", disabled=True),
                dbc.NavLink("Validation", href="/validation/", active="exact", disabled=True),
                dbc.NavLink("Train (NB)", href="/train_nb", active="exact", disabled=True),
                dbc.NavLink("Train (RF)", href="/train_rf", active="exact", disabled=True),
                dbc.NavLink("Dataset Creation", href="/dataset", active="exact", disabled=True),
                dbc.NavLink("Dataset Exploration", href="/data_ex/", active="exact", disabled=True),
                dbc.NavLink("", href="#", disabled=True),
                dbc.NavLink("Exit", href="/shutdown", active="exact")
            ],
            vertical=True,
            pills=True,
        ),
        html.Hr(),
        html.P("Utilities"),
        dbc.Nav(
            [
                dbc.NavLink("File Explorer", href="/file_browser/", active="exact", disabled=True),
                dbc.NavLink("PDF-To-Text", href="/pdf_to_text", active="exact", disabled=True),
                dbc.NavLink("Metadata Maker", href="/metadata_maker", active="exact", disabled=True)
            ],
            vertical=True,
            pills=True
        ),
        html.Hr(),
        html.P("DocumentCloud Tools"),
        dbc.Nav(
            [
                dbc.NavLink("Login", href="/dc_login", active="exact"),
                dbc.NavLink("Import", href="/dc_import", active="exact", disabled=True)
            ],
            vertical=True,
            pills=True
        )
    ],
    style=SIDEBAR_STYLE,
    id="sidebar"
)

content = html.Div(id="page-content", style=CONTENT_STYLE, 
                    children=[html.H1("{}".format(NAME))])

tooltip = html.Div([dbc.Button("Help", id="help-button", outline=True, color="success", size="lg"),
                    dbc.Tooltip(id="tooltip", target="help-button", placement="bottom-start",
                                style={"font-size":16})],
                    style={"position":"fixed", "top":10, "right":10},
                    className="d-grid gap-2 col-1 mx-auto")

hidden_dir_divs = [html.Div(id="sample-dir-gui-hidden", style={"display":"none"}),
                    html.Div(id="setup-dir-gui-hidden", style={"display":"none"}),
                    html.Div(id="pdf-dir-gui-hidden", style={"display":"none"}),
                    html.Div(id="ret-dir-gui-hidden", style={"display":"none"})]

app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Store(id="project", storage_type='session', data={"project":None}),
    html.Div(dcc.Store(id="dc", storage_type='session', data={})),
    sidebar,
    dcc.Interval(id="flush-stream", interval=500),
    dcc.Interval(id="message-timer", interval=1000),
    html.Div([message, dcc.Loading(id="content-load", fullscreen=True, type="circle", style={"background":"rgba(0,0,0,0.5)"}), 
                content], 
            style={"position":"absolute", "vertical-align":"middle", "width":"50%", "left":"900px"}),
    tooltip,
    html.Div(id="index-hidden", style={"display":"none"})
]+hidden_dir_divs)

#def index_gui():
@app.callback(Output("ret-dir-gui-hidden", "children"),
            [Input("sample-dir-gui-hidden", "children"),
            Input("setup-dir-gui-hidden", "children"),
            Input("pdf-dir-gui-hidden", "children")])
def open_dir_gui(sample, setup, pdf):
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]
    
    called = None
    if which == "sample-dir-gui-hidden":
        if sample is None:
            raise PreventUpdate
        called = sample
    elif which == "setup-dir-gui-hidden":
        if setup is None:
            raise PreventUpdate
        called = setup
    elif which == "pdf-dir-gui-hidden":
        if pdf is None:
            raise PreventUpdate 
        called = pdf

    if called is None:
        raise PreventUpdate
    
    ret_dir = easygui.diropenbox(msg="Choose Data Directory for {}".format(called), title="{} Directory".format(called))

    return "{}:::{}".format(called, ret_dir)

@app.callback(Output("index-hidden", "children"),
                Input("flush-stream", "n_intervals"))
def stream_flush(n):
    global LOG_STREAM
    global q

    flush = LOG_STREAM.getvalue()
    LOG_STREAM.seek(0)
    LOG_STREAM.truncate(0)

    if flush is None or flush == "":
        raise PreventUpdate

    flush = flush.split('\n')
    if len(flush) > 0:
        for f in flush:
            if f != "":
                q.put(f)
        return ""
    else:
        raise PreventUpdate

@app.callback(Output("message", "children"),
                Input("message-timer", "n_intervals"),
                State("message", "children"))
def update_messages(n, current):
    global q
    MAX_MESSAGE = 5
    DURATION = 10

    # remove old messages
    temp = []
    for c in current:
        dt = datetime.strptime(c['props']['children'].split()[0][1:-1], '%m/%d/%Y-%H:%M:%S')
        level = c['props']['children'].split()[1][:-1]
        if (datetime.now() - dt).total_seconds() < DURATION:
            temp.append(c)
    current = temp

    if len(current) >= MAX_MESSAGE:
        raise PreventUpdate

    num_new = MAX_MESSAGE - len(current)
    new_messages = []
    for _ in range(0, num_new):
        try:
            m = q.get_nowait()
            m = "[{}] {}".format(datetime.now().strftime('%m/%d/%Y-%H:%M:%S'), m)
            level = m.split()[1][:-1]
            if "Navigate" in m:
                color = "secondary"
            elif level == "INFO":
                color = "info"
            elif level == "CRITICAL":
                m = m.replace("CRITICAL", "SUCCESS")
                color = "success"
            elif level == "WARNING":
                color = "warning"
            else:
                color = "danger"
            new_messages.append(dbc.ListGroupItem(m, color=color))
        except queue.Empty:
            break

    to_ret = current + new_messages
    if len(to_ret) == 0:
        to_ret = [dbc.ListGroupItem("[{}] INFO: No New Messages.".format(datetime.now().strftime('%m/%d/%Y-%H:%M:%S')))]

    return to_ret

@app.callback([Output("content-load", "children"),
                Output("page-content", "children"), 
                Output("sidebar", "children"),
                Output("tooltip", "children")], 
                [Input("url", "pathname"),
                Input("project", "data"),
                Input("dc", "data")])
def render_page_content(pathname, data, dc):
    time.sleep(0.1)
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    # check dc login
    if len(dc.keys()) > 0:
        dc_disabled = False
    else:
        dc_disabled = True

    with open((Path("assets") / "tooltip.json").as_posix(), 'r') as f:
        tips = json.load(f)
        search = pathname.split('/')[1]
        if search in tips:
            tip = tips[search]['tip']
            name = tips[search]['name']
        else:
            tip = tips['home']['tip']
            name = "Help"
        tip = html.Div([html.H6(name), html.Hr(), tip])

    if data['project'] is not None and pathname != "/shutdown":
        sidebar = [
                    html.H2("{} Tool".format(NAME), className="display-4"),
                    html.P("Current Project: \t", style={"display":"inline-block", "padding-right":"0.5rem"}),
                    html.P(data['project'].split('/')[-1], 
                            style={"display":"inline-block", "font-weight": "bold"}),
                    html.Hr(),
                    html.P(
                        "{} Navbar".format(NAME), className="lead"
                    ),
                    dbc.Nav(
                        [
                            dbc.NavLink("Home", href="/home", active="exact"),
                            dbc.NavLink("Project", href="/project", active="exact"),
                            dbc.NavLink("Setup", href="/setup", active="exact"),
                            dbc.NavLink("Sample", href="/sample", active="exact"),
                            dbc.NavLink("Tags", href="/tags", active="exact"),
                            dbc.NavLink("Rules", href="/rules", active="exact"),
                            dbc.NavLink("Extract", href="/extract", active="exact"),
                            dbc.NavLink("Context Exploration", href="/text_ex/", active="exact"),
                            dbc.NavLink("Validation", href="/validation/", active="exact"),
                            dbc.NavLink("Train (NB)", href="/train_nb", active="exact"),
                            dbc.NavLink("Train (RF)", href="/train_rf", active="exact"),
                            dbc.NavLink("Dataset Creation", href="/dataset", active="exact"),
                            dbc.NavLink("Dataset Exploration", href="/data_ex/", active="exact"),
                            dbc.NavLink("", href="#", disabled=True),
                            dbc.NavLink("Exit", href="/shutdown", active="exact")
                        ],
                        vertical=True,
                        pills=True,
                    ),
                    html.Hr(),
                    html.P("Utilities"),
                    dbc.Nav(
                        [
                            dbc.NavLink("File Explorer", href="/file_browser/", active="exact"),
                            dbc.NavLink("PDF-To-Text", href="/pdf_to_text", active="exact"),
                            dbc.NavLink("Metadata Maker", href="/metadata_maker", active="exact")
                        ],
                        vertical=True,
                        pills=True
                    ),
                    html.Hr(),
                    html.P("DocumentCloud Tools"),
                    dbc.Nav(
                        [
                            dbc.NavLink("Login", href="/dc_login", active="exact"),
                            dbc.NavLink("Import", href="/dc_import", active="exact", disabled=dc_disabled)
                        ],
                        vertical=True,
                        pills=True
                    )
                ]
    else:
        sidebar = [
                    html.H2("{} Tool".format(NAME), className="display-4"),
                    html.Hr(),
                    html.P(
                        "{} Navbar".format(NAME), className="lead"
                    ),
                    dbc.Nav(
                        [
                            dbc.NavLink("Home", href="/home", active="exact"),
                            dbc.NavLink("Project", href="/project", active="exact"),
                            dbc.NavLink("Setup", href="/setup", active="exact", disabled=True),
                            dbc.NavLink("Sample", href="/sample", active="exact", disabled=True),
                            dbc.NavLink("Tags", href="/tags", active="exact", disabled=True),
                            dbc.NavLink("Rules", href="/rules", active="exact", disabled=True),
                            dbc.NavLink("Extract", href="/extract", active="exact", disabled=True),
                            dbc.NavLink("Context Exploration", href="/text_ex/", active="exact", disabled=True),
                            dbc.NavLink("Validation", href="/validation/", active="exact", disabled=True),
                            dbc.NavLink("Train (NB)", href="/train_nb", active="exact", disabled=True),
                            dbc.NavLink("Train (RF)", href="/train_rf", active="exact", disabled=True),
                            dbc.NavLink("Dataset Creation", href="/dataset", active="exact", disabled=True),
                            dbc.NavLink("Dataset Exploration", href="/data_ex/", active="exact", disabled=True),
                            dbc.NavLink("", href="#", disabled=True),
                            dbc.NavLink("Exit", href="/shutdown", active="exact")
                        ],
                        vertical=True,
                        pills=True,
                    ),
                    html.Hr(),
                    html.P("Utilities"),
                    dbc.Nav(
                        [
                            dbc.NavLink("File Explorer", href="/file_browser/", active="exact", disabled=True),
                            dbc.NavLink("PDF-To-Text", href="/pdf_to_text", active="exact", disabled=True),
                            dbc.NavLink("Metadata Maker", href="/metadata_maker", active="exact", disabled=True)
                        ],
                        vertical=True,
                        pills=True
                    ),
                    html.Hr(),
                    html.P("DocumentCloud Tools"),
                    dbc.Nav(
                        [
                            dbc.NavLink("Login", href="/dc_login", active="exact", disabled=True),
                            dbc.NavLink("Import", href="/dc_import", active="exact", disabled=True)
                        ],
                        vertical=True,
                        pills=True
                    )
                ]

    if which == "dc":
        return " ", no_update, sidebar, no_update

    if pathname == "/home" or pathname == "/":
        if pathname == "/home" and which == "project":
            logging.getLogger("messages").info("Home!")
        layout = [html.H1("{} Homepage".format(NAME)), html.H3("Navigate the sidebar to begin!")]
    elif pathname == "/project":
        if which != "project":
            logging.getLogger("messages").info("Navigated to Projects page.")
        layout = project.get_layout()
    elif pathname == "/setup":
        logging.getLogger("messages").info("Navigated to Setup page.")
        layout = setup.get_layout(data['project'])
    elif pathname == "/sample":
        logging.getLogger("messages").info("Navigated to Sample page.")
        layout = sample.get_layout(data['project'])
    elif pathname == "/tags":
        logging.getLogger("messages").info("Navigated to Tags page.")
        layout = tags.get_layout(data['project'])
    elif pathname == "/rules":
        logging.getLogger("messages").info("Navigated to Rules page.")
        layout = rules.get_layout(data['project'])
    elif pathname == "/extract":
        logging.getLogger("messages").info("Navigated to Extract page.")
        layout = extract.get_layout(data['project'])
    elif pathname.startswith('/text_ex/'):
        arg = pathname.split('/')[-1]
        logging.getLogger("messages").info("Navigated to Context Exploration page.")
        if arg == "text_ex" or arg == "":
            layout = text_ex.get_layout(None, data['project'])
        else:
            layout = text_ex.get_layout(arg, data['project'])
    elif pathname.startswith('/validation/'):
        arg = pathname.split('/')[-1]
        logging.getLogger("messages").info("Navigated to Validation page.")
        if arg == "validation" or arg == "":
            layout = validation.get_layout(data['project'], None)
        else:
            layout = validation.get_layout(data['project'], arg)
    elif pathname == "/train_nb":
        logging.getLogger("messages").info("Navigated to Train (NB) page.")
        layout = train_nb.get_layout(data['project'])
    elif pathname == "/train_rf":
        logging.getLogger("messages").info("Navigated to Train (RF) page.")
        layout = train_rf.get_layout(data['project'])
    elif pathname == "/dataset":
        logging.getLogger("messages").info("Navigated to Dataset Creation page.")
        layout = dataset.get_layout(data['project'])
    elif pathname.startswith('/data_ex/'):
        arg = pathname.split('/')[-1]
        logging.getLogger("messages").info("Navigated to Data Exploration page.")
        if arg == "data_ex" or arg == "":
            layout = data_ex.get_layout(None, data['project'])
        else:
            layout = data_ex.get_layout(arg, data['project'])
    elif pathname == "/shutdown":
        logging.getLogger("messages").warning("Server Shutdown. OK to exit.")
        time.sleep(1)
        shutdown_server()
        layout = [html.H1("Goodbye!"), html.H3("You can now exit the browser.")]
    elif pathname.startswith("/file_browser/"):
        arg = pathname.split('/')[-1]
        logging.getLogger("messages").info("Navigated to File Browser")
        if arg == "file_browser" or arg == "":
            layout = file_browser.get_layout(data['project'], None)
        else:
            layout = file_browser.get_layout(data['project'], arg)
    elif pathname == "/pdf_to_text":
        logging.getLogger("messages").info("Navigated to PDF-To-Text Utility")
        layout = pdf_to_text.get_layout()
    elif pathname == "/metadata_maker":
        logging.getLogger("messages").info("Navigated to Metadata Maker")
        layout = metadata_maker.get_layout(data['project'])
    elif pathname == "/dc_login":
        logging.getLogger("messages").info("Navigated to DocumentCloud Login")
        layout = dc_login.get_layout(dc)
    elif pathname == "/dc_import":
        logging.getLogger("messages").info("Navigated to DocumentCloud Import")
        layout = dc_import.get_layout(dc)
    else:
        logging.getLogger("messages").error("Page does not exist. Turn back!")
        layout = [
                html.H1("404: Not Found", className="text-danger"),
                html.Hr(),
                html.P("The pathname {} was not recognized...".format(pathname)),
        ]
    
    return " ", layout, sidebar, tip

#####################################################

def set_log():
    global LOG_STREAM

    # set up logger
    logger = logging.getLogger("messages")
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler(stream=LOG_STREAM)
    sh.setLevel(logging.INFO)
    #formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%m/%d/%Y-%H:%M:%S')
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    sh.setFormatter(formatter)
    logger.addHandler(sh)

def server():
    global app
    set_log()
    app.run_server(debug=False, threaded=True, #host=socket.gethostbyname(socket.gethostname()),
        port=8011, dev_tools_ui=False, dev_tools_props_check=False)

def server_dev():
    global app
    set_log()
    app.run_server(debug=True, threaded=True)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dev":
        #index_gui()
        server_dev()
