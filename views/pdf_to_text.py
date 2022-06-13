# Author: Stephen Meisenbacher
# view for pdf-to-text utility

import os
from pathlib import Path
import tika
from tika import parser
import multiprocessing as mp
import logging
import json
import platform

from html import unescape
from bs4 import BeautifulSoup
import re

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_daq as daq

from server import app

tika.initVM()
NUM_PROCS = int(0.75 * mp.cpu_count())

def pdf_text(tup):
    file = tup[0]
    save_parent = tup[1]

    #print(file, flush=True)
    p = None
    while p is None:
        try:
            p = parser.from_file(file.as_posix())
        except RuntimeError:
            pass

    text = p['content']
    if text is not None:
        save = Path(save_parent) / "{}.txt".format(file.stem)
        with open(save, 'w') as out:
            out.write(text)
        return 1
    else:
        return 0

# utility for quick cleaning text
def clean(text, ABBREV):
    if '&' in text:
        text = unescape(text.strip())
    if '<' in text:
        text = BeautifulSoup(text, "lxml").text
    text = re.sub(r"www\S+", " ", text)
    text = re.sub(r"\b(?![ai])[a-zA-Z]\b", " ", text)
    text = re.sub(r"\d+", " ", text)
    text = text.replace(',',' ')
    text = text.replace(':',' ').replace('*',' ')
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r"[^0-9a-zA-Z\.\?\! ]+", " ", text)
    text = " ".join(text.split())
    text = text.replace(" .", ".")
    text = re.sub(r"\.{2,}", ".", text)

    # handle abbreviations
    text = " ".join([ABBREV.get(x.lower(), x) for x in text.split()])
    text = re.sub(r"(?<!\w)([A-Za-z])\.", r"\1", text)

    text = text.lower()

    return text

def __helper__(tup):
    global abbreviations
    #print(file, flush=True)

    file = tup[0]
    save_path = tup[1]

    text = None
    with open(file.as_posix(), 'r') as f:
        text = f.read()
        text = clean(text, abbreviations)

    save = Path(save_path) / file.name.replace(' ', '_')
    with open(save.as_posix(), 'w') as out:
        out.write(text)

    return 1

def pool_init(arg):
    global abbreviations
    abbreviations = arg

def get_layout():

    switch = html.Div(children=[html.Div(html.P("Already have TXT files?\t"), style={"display":"inline-block", "padding":"1rem"}), 
            html.Div(daq.BooleanSwitch(id="pdf-switch", on=False), style={"display":"inline-block"})], 
            style={"display":"inline-block", "padding":"1rem"})

    clean = html.Div(children=[html.Div(html.P("Clean Text?\t"), style={"display":"inline-block", "padding":"1rem"}), 
            html.Div(daq.BooleanSwitch(id="clean-switch", on=True), style={"display":"inline-block"})], 
            style={"display":"inline-block", "padding":"1rem"})

    direct = html.Div(dbc.Input(id="pdf-dir", 
                            placeholder="Input (relative) parent directory of files.",
                            debounce=True, 
                            type="text",
                            autocomplete=False),
                        style={"display":"inline-block", "width":"90%"})

    browse = html.Div(dbc.Button("Browse", id="pdf-dir-browse"), style={"display":"inline-block"})

    run = html.Div(dbc.Button("Run!", id="run-clean", size="lg"), style={"padding":"1rem"})

    clean_loading = dcc.Loading(id="clean-load")

    layout = [html.H1("PDF-To-Text"), html.H4("Get your PDFs converted to cleaned text."), html.Hr(),
                switch, clean, direct, browse, run, clean_loading]

    return layout


@app.callback([Output("pdf-dir", "valid"), Output("pdf-dir", "invalid")],
                Input("pdf-dir", "value"),
                State("pdf-switch", "on"))
def validate_pdf_dir(path, on):
    if path is None:
        raise PreventUpdate

    if on == True:
        doc = "Text"
    else:
        doc = "PDF"

    if Path(path).is_dir() == True:
        logging.getLogger("messages").info("Valid {} directory! ({})".format(doc, path))
        return True, False
    else:
        logging.getLogger("messages").error("Invalid {} directory: {}".format(doc, path))
        return False, True

@app.callback(Output("pdf-dir", "placeholder"),
                [Input("pdf-switch", "on"), Input("clean-switch", "on")])
def pdf_switch(on, on2):
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]
  
    if which == "pdf-switch":
        if on == True:
            logging.getLogger("messages").info("Option update: now inputting text files to be cleaned.")
            return "Input (relative) parent directory of .txt files."
        else:
            logging.getLogger("messages").info("Option update: now inputting PDF files to be extracted and cleaned.")
            return "Input (relative) parent directory of .pdf files."
    else:
        if on2 == True:
            logging.getLogger("messages").info("Option update: text will be cleaned.")
            return no_update
        else:
            logging.getLogger("messages").info("Option update: text will not be cleaned.")
            return no_update

@app.callback(Output("clean-load", "children"),
                Input("run-clean", "n_clicks"),
                [State("pdf-switch", "on"), State("clean-switch", "on"),
                State("pdf-dir", "value"), State("pdf-dir", "valid"),
                State("project", "data")])
def do_clean(n, pdf, text, dir, valid, data):
    global NUM_PROCS
    if n is None:
        raise PreventUpdate

    if dir is None or valid == False:
        logging.getLogger("messages").error("Invalid file directory: {}".format(dir))
        raise PreventUpdate

    if (Path(data['project']) / "data").is_dir() == False:
        os.makedirs((Path(data['project']) / "data").as_posix())

    if pdf == False:
        files = [x for x in Path(dir).rglob("*.pdf")]
        save_path = Path(data['project']) / "data" / "text"

        if len(files) > 0:
            logging.getLogger("messages").info("Found {} PDF files to be processed. This may take a bit.".format(len(files)))
        else:
            logging.getLogger("messages").error("No PDF files found!")
            return " "

        if save_path.is_dir() == False:
            os.makedirs(save_path.as_posix())

        parent = files[0].parent.as_posix().split('/')[-1]
        save_path = save_path / parent
        files = [(x, save_path) for x in files]

        if save_path.is_dir() == False:
            os.makedirs(save_path.as_posix())

        with mp.Pool(NUM_PROCS) as pool:
            res = pool.map(pdf_text, files)
            res = [x for x in res]
        logging.getLogger("messages").critical("Extracted {} PDF files to text - saved to {}".format(sum(res), save_path.as_posix()))

        dir = save_path
    elif pdf == False and text == False:
        logging.getLogger("messages").error("Both options switched - nothing to do!")
        raise PreventUpdate

    save_path = Path(data['project']) / "data" / "cleaned"
    if save_path.is_dir() == False:
        os.makedirs(save_path.as_posix())

    files = [x for x in Path(dir).rglob("*.txt")]
    parent = files[0].parent.as_posix().split('/')[-1]
    save_path = save_path / parent
    files = [(x, save_path) for x in files]

    if save_path.is_dir() == False:
            os.makedirs(save_path.as_posix())

    logging.getLogger("messages").info("Found {} text files to be cleaned. This should go quickly.".format(len(files))) 

    with open((Path("assets") / "abbrev.json").as_posix(), 'r')as f:
        abbrev = json.load(f)

    with mp.Pool(NUM_PROCS, initializer=pool_init, initargs=(abbrev,)) as pool:
        res = pool.map(__helper__, files)
        res = [x for x in res]
    logging.getLogger("messages").critical("Cleaned {} text files - saved to {}".format(sum(res), save_path.as_posix()))      

    return " "

@app.callback(Output("pdf-dir-gui-hidden", "children"),
                Input("pdf-dir-browse", "n_clicks"))
def call_gui(n):
    if n is None:
        raise PreventUpdate

    if platform.system() == "Darwin":
        logging.getLogger("messages").error("Browse feature not supported on Mac.")
        raise PreventUpdate

    return "PDF/Text"

@app.callback(Output("pdf-dir", "value"),
                Input("ret-dir-gui-hidden", "children"))
def fill_dir(data):
    if data is None:
        raise PreventUpdate

    if "PDF/Text" in data:
        ret = data.split(':::')[-1]
        if ret != "":
            return ret
        else:
            raise PreventUpdate
    else:
        raise PreventUpdate