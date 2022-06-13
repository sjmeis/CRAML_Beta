# Author: Stephen Meisenbacher
# view for importing text from DC documents

import logging
from documentcloud import DocumentCloud
import subprocess
import time
from pathlib import Path
import json
import requests
import zipfile
from io import BytesIO

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_daq as daq

## Diskcache
from dash.long_callback import DiskcacheLongCallbackManager
import diskcache
cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

from .utility import p_decode
from server import app

def get_auth_header(access):
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
            'Authorization': "Bearer {}".format(access)}

def get_dc_projects(dc):
    client = DocumentCloud(dc['user'], p_decode(dc['passw']))
    projects = client.projects.all()
    options = []
    for p in projects:
        #label = "{} ({} documents)".format(p.title, len(p.document_ids))
        options.append({"label":p.title, "value":p.id})
    logging.getLogger("messages").info("Imported {} projects from DocumentCloud.".format(len(options)))
    return options

def get_layout(dc):

    dirs = dcc.Dropdown(
        id="dc-import-drop",
        options=get_dc_projects(dc),
        clearable=False
    )

    run = dbc.Button("Run!", id="run-dc-import", size="lg")
    cancel = dbc.Button("Cancel", id="cancel-dc-import", size="lg")
    buttons = dbc.ButtonGroup([run, cancel], style={"padding":"1rem"})

    progress = dbc.Progress(id="dc-import-progress", value=0, animated=True, label="0%", striped=True,
                            style={"height": "75px", "display":"none"})

    loading = dcc.Loading(id="dc-import-load")
    dummy = html.Div(id="dc-import-hidden", style={"display":"none"})

    layout = [html.H1("DocumentCloud Import"), html.H4("Import text from your DocumentCloud project documents."),
                dirs, buttons, progress, loading, dummy]
    return layout

@app.long_callback(output=[Output("dc-import-hidden", "children")],
                inputs=[Input("run-dc-import", "n_clicks"),
                        State("dc-import-drop", "value"), 
                        State("dc", "data"),
                        State("project", "data")],
                progress=[Output("dc-import-progress", "style"),
                            Output("dc-import-progress", "value"), 
                            Output("dc-import-progress", "label")],
                progress_default=[{"font-size":"100%", "height": "75px", "display":"none"}, no_update, no_update],
                cancel=[Input("cancel-dc-import", "n_clicks")],
                manager=long_callback_manager,
                prevent_initial_call=True)
def import_text(set_progress, n, value, data, proj):
    if n is None or n == 0:
        return [no_update]

    if value is None:
        logging.getLogger("messages").error("No project selected.")

    logging.getLogger("messages").info("Import started, this may take a while...")

    #proj_data = json.dumps({"proj_id":value})
    #args = ["--token", data['ACCESS'], "--refresh_token", data['REFRESH'], "--data", proj_data]
    #cmd = ["python3", (Path("classes") / "TextExport.py").as_posix()] + args

    #proc = subprocess.Popen(cmd)
    #while proc.poll() is None:
    #    time.sleep(1)

    set_progress([{"font-size":"100%", "height": "75"}, 100, "Gathering Documents..."])

    # use API to get doc_ids
    url = "https://api.www.documentcloud.org/api/projects/{}/documents".format(value)
    start_params = {"per_page":100}
    docs = []
    end = False
    while end == False:
        response = None
        success = False
        while success == False:
            try:
                r = requests.get(url, params=start_params, headers=get_auth_header(data['ACCESS']), timeout=30)
            except requests.exceptions.Timeout:
                continue

            if r.ok:
                response = r.json()
                if 'results' in response:
                    success = True
            elif r.status_code == 404:
                end = True
                break
            else:
                time.sleep(2)

        for res in response['results']:
            docs.append(res['document'])

        set_progress([{"font-size":"100%", "height": "75"}, 100, "Gathering Documents... {}".format(len(docs))])

        if response['next'] is not None and response['next'] != url:
            url = response['next']
            start_params = None
        else:
            end = True
        time.sleep(1)

    # get text and zip
    set_progress([{"font-size":"100%", "height": "75"}, 0, "Importing documents..."])
    client = DocumentCloud(data['user'], p_decode(data['passw']))
    project_name = client.projects.get(id=value).title
    save_path = Path(proj['project']) / "data" / project_name.replace(' ', '_')
    save_path.mkdir(parents=True, exist_ok=True)

    total = len(docs)
    for i, doc_id in enumerate(docs):
        try:
            document = client.documents.get(doc_id)
            text = document.full_text
            with open((save_path / "{}.txt".format(document.slug)).as_posix(), 'w', encoding='utf-8') as txt:
                txt.write(text)
        except:
            pass
        prog = 100 * (i+1) // total
        set_progress([{"font-size":"100%", "height": "75"}, prog, "Importing document {}/{}".format(i+1, total)])

    set_progress([{"font-size":"100%", "height": "75px", "display":"none"}, 0, None])
    logging.getLogger("messages").critical("Import complete! {} files saved to {}".format(len([x for x in save_path.iterdir()]), save_path.as_posix()))

    return [no_update]