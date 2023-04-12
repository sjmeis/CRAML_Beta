# Author: Stephen Meisenbacher
# view for training set vs hand-code validation

import cmd
import os
import sys
from pathlib import Path
import logging
import pandas as pd
import shutil
from datetime import datetime
import base64
import io
from scipy.fft import idst

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt

import dash
from dash import dcc, no_update, dash_table
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_daq as daq

from server import app
from .utility import get_rule_files, get_options, open_file, get_ext_log, get_settings

sys.path.append("classes")
from Train import Train
from Extrapolate import Extrapolate

def get_layout(project, arg):
    log = get_ext_log(project)
    if arg not in [x['pid'] for x in log]:
        arg = None
    else:
        logging.getLogger("messages").info("Preloaded with pid {}".format(arg))

    drop_dir = html.Div(dcc.Dropdown(id="val-dir-drop", options=get_options(project, True), 
                                    placeholder="Select an extracted directory...",
                                    value=arg),
                        style={"padding":"1rem"})

    drop_rules = html.Div(dcc.Dropdown(id="val-rule-drop", options=get_rule_files(project), 
                placeholder="Select a rules file to train and validate..."),
                style={"padding":"1rem"})

    min_rule = html.Div(children=[html.Div(html.P(children="Mininum instances per rule (if available):\t"), style={"display":"inline-block", "padding":"1rem"}),
        html.Div(dbc.Input(id="val-min", type="number", min=1, max=100, value=5, size="sm", debounce=True), style={"display":"inline-block", "width":75})],
        style={"display":"inline-block", "padding":"1rem", "padding-right":"2rem"})

    number = html.Div(children=[html.Div(html.P(children="Number of training instances (approximate):\t"), style={"display":"inline-block", "padding":"1rem"}),
        html.Div(dbc.Input(id="val-x", type="number", min=1, max=1000, value=100, size="sm", debounce=True), style={"display":"inline-block", "width":100})],
        style={"display":"inline-block", "padding":"1rem", "padding-right":"2rem"})

    generate = dbc.Button("Generate", id="val-run")
    reload = dbc.Button("Reload", id="val-reload")
    run_button = html.Div(dbc.ButtonGroup([generate, reload]), style={"display":"inline-block", "padding-left":"5rem"})

    table = dash_table.DataTable(
                id="val-table",
                #columns=[{"id":"chunk", "name":"chunk", "selectable":True}, 
                #        {"id":"count", "name":"count", "selectable":False}],
                columns=None,
                data=None,
                editable=False,
                row_deletable=False,
                style_cell = {
                    'font_size':'16px',
                    'text_align':'center',
                    'maxWidth':'500px',
                    'minWidth':'50px'
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
                style_data_conditional=[
                    {
                        'if': {
                            'column_id': 'truth',
                        },
                        'backgroundColor': 'dodgerblue',
                        'color': 'white'
                    }
                ],
                persistence="session"
    )

    score = dbc.Button("Score", id="val-score")
    export = dbc.Button("Export", id="val-export")
    val_import = dcc.Upload(id="val-import", children=dbc.Button("Import"))
    bottom_buttons = dbc.ButtonGroup([score, export, val_import])

    loading = dcc.Loading(id="val-load")
    loading2 = dcc.Loading(id="score-load")
    loading3 = dcc.Loading(id="export-load")
    hidden = html.Div(id="val-hidden", style={"display":"none"})
    hidden2 = html.Div(id="val-hidden2", style={"display":"none"})
    export_download = dcc.Download(id="export-download")

    layout = [html.H1("Validation"), html.H4("Verify training data against your own hand-coded data."),
                html.Hr(), drop_dir, drop_rules, min_rule, number, run_button, loading, loading2, loading3, html.Hr(), 
                table, bottom_buttons, hidden, hidden2, export_download]

    return layout

@app.callback([Output("val-load", "children"), Output("val-table", "columns"), 
                Output("val-table", "data"), Output("val-hidden", "children")],
                [Input("val-run", "n_clicks"), Input("val-import", "contents"),
                Input("val-reload", "n_clicks")],
                [State("val-dir-drop", "value"), State("val-rule-drop", "value"), 
                State("val-x", "value"), State("val-x", "min"),
                State("val-min", "value"), State("project", "data")])
def fill_table(n, contents, n2, dir, value, X, xmin, ins_min, data):
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if dir is None:
        logging.getLogger("messages").error("No extracted directory selected!")
        raise PreventUpdate

    if value is None:
        logging.getLogger("messages").error("No rules selected!")
        raise PreventUpdate

    parent = Path(data['project']) / "csv" / dir        
    rules = Path(data['project']) / "rules" / "{}.csv".format(value)
    name = "{}_val_{}_{}".format(rules.stem, X, dir)

    settings = get_settings(data['project'])
    id = None
    for s in settings:
        if settings[s]['extract'] != "None":
            id = settings[s]['id']
            break

    if which == "val-run":
        if n is None:
            raise PreventUpdate

        t = Train("val", name, parent.as_posix(), rules.as_posix(), 1, False, data['project'])
        train_file = t.extrapolate()

        logging.getLogger("messages").info("[VALIDATION] Training data extrapolation complete. Preparing dataset.")
        validate = pd.read_csv(train_file)
        validate.to_csv(train_file, index=True)

        # operations to prepare dataset
        validate['wc'] = validate['rule'].apply(lambda x: len(x.split()))
        validate = validate.sample(frac=1)
        validate = validate.sort_values(by=['rule'])
        validate['rank'] = validate.groupby('rule').cumcount() + 1 #ordinal ranking
        val_counts = validate.groupby('rule')['rule'].count().to_dict() # get total counts of all rules

        # smooth
        #min_count = min(val_counts, key=lambda x:val_counts[x])
        #smooth = max(val_counts[min_count], len(val_counts.keys())-1)
        #val_counts = {k:(v+smooth if k == min_count else v-1) for k,v in val_counts.items()}
        #val_counts = {k:round(v/len(validate.index)*X) for k,v in val_counts.items()} # get "share" of final to display
        total = sum([v for _,v in val_counts.items()])
        val_counts = {k:int(v/total*(X+xmin) + 5) for k,v in val_counts.items()}

        new_total = 0
        for _, v in val_counts.items():
            if v > ins_min:
                new_total += v
        val_counts = {k:(max(int((v-ins_min)/new_total*(X+xmin)), ins_min) if v > ins_min else v) for k,v in val_counts.items()}

        validate['keep'] = validate.apply(lambda x: x['rank'] <= val_counts[x['rule']], axis=1) # keep only share 
        validate = validate[validate['keep'] == True]
        validate = validate.drop(columns=['wc','rank','keep'])
        validate.index = validate.index.set_names(['id'])
        validate = validate.reset_index()
        validate['truth'] = None
        validate = validate.sample(frac=1)
        validate.to_csv((Path(data['project']) / "train" / "val" / "{}.csv".format(name)).as_posix(), index=True)
    elif which == "val-import":
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        validate = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        validate.to_csv((Path(data['project']) / "train" / "val" / "{}.csv".format(name)).as_posix(), index=True)
        train_file = Path(data['project']) / "train" / "val" / name
    elif which == "val-reload":
        if n2 is None:
            raise PreventUpdate

        search = Path(data['project']) / "train" / "val" / "{}.csv".format(name)
        if search.is_file() == True:
            validate = pd.read_csv(search.as_posix(), index_col=0)
            train_file = Path(data['project']) / "train" / "val" / name
        else:
            found = [x.name.split('_')[-2] for x in (Path(data['project']) / "train" / "val").iterdir() if dir in x.name and "csv" in x.name]
            logging.getLogger("messages").error("No existing validation files exist for this setup! (Existing for X = {})".format(",".join(found)))
            raise PreventUpdate

    columns = [{"id":x, "name":x, "selectable":False} for x in validate.columns[:-1]] + \
                [{"id":"truth", "name":"truth", "selectable":True, "editable":True}]

    logging.getLogger("messages").critical("[VALIDATION] Displaying validation dataset.")

    return " ", columns, validate.to_dict('records'), train_file.as_posix()
    
@app.callback(Output("score-load", "children"),
                Input("val-score", "n_clicks"),
                [State("val-hidden", "children"), State("val-table", "data"),
                State("project", "data")])
def do_score(n, file, data, proj):
    if n is None:
        raise PreventUpdate

    if any(x['truth'] is None for x in data):
        logging.getLogger("messages").error("Please fill out all \'truth\' values.")
        #shutil.rmtree(Path(file).parent.as_posix())
        raise PreventUpdate
    if any(str(x['truth']) != '0' and str(x['truth']) != '1' for x in data):
        logging.getLogger("messages").error("Invalid \'truth\' value detected. Must be 0 or 1.")
        #shutil.rmtree(Path(file).parent.as_posix())
        raise PreventUpdate

    logging.getLogger("messages").info("[VALIDATION] Scoring...")
    train = pd.read_csv(file, index_col=0)
    name = train.columns[-1]
    handcode = pd.DataFrame(data)
    pred = train.iloc[handcode['id'].tolist()].iloc[:,-1].tolist()
    true = handcode['truth'].astype(int).tolist()

    # scores
    acc = str(round(accuracy_score(true, pred) * 100, 2)) + "%"
    prec = precision_score(true, pred, zero_division=0)
    rec = recall_score(true, pred, zero_division=0)
    f1 = f1_score(true, pred, zero_division=0)
    stats = "\n\nAccuracy={}\nPrecision={:.2f}\nRecall={:.2f}\nF1 Score={:.2f}".format(acc,prec,rec,f1)

    # confusion matrix
    cm = confusion_matrix(true, pred, labels=[0, 1])
    hm_labels = ["TN", "FP", "FN", "TP"]
    hm_counts = ["{0:0.0f}".format(x) for x in cm.flatten()]
    hm_per = ["{0:.2%}".format(x) for x in cm.flatten()/np.sum(cm)]
    hm_annot = ["{}\n{}\n{}".format(x,y,z) for x,y,z in zip(hm_labels, hm_counts, hm_per)]
    hm_annot = np.asarray(hm_annot).reshape(2,2)

    # plot
    s = sns.heatmap(cm, annot=hm_annot, fmt='')
    s.set(xlabel="Predicted{}".format(stats), ylabel="True", title="{} Validation".format(name))
    fig = s.get_figure()
    plt_save = Path(file).parent / "hm_{}_{}.jpg".format(name, datetime.now().strftime("%m-%d-%Y,_%H:%M:%S"))
    fig.savefig(plt_save.as_posix(), bbox_inches='tight')

    logging.getLogger("messages").info("[VALIDATION] Confusion Matrix saved to {}".format(plt_save.as_posix()))

    open_file(plt_save)

@app.callback([Output("export-load", "children"), Output("export-download", "data")],
                Input("val-export", "n_clicks"),
                [State("val-table", "data"),
                State("val-dir-drop", "value"),
                State("val-rule-drop", "value"), 
                State("val-x", "value")])
def export_val(n, data, dir, rule, x):
    if n is None:
        raise PreventUpdate

    if data is None:
        logging.getLogger("messages").error("No data to export!")
        raise PreventUpdate

    logging.getLogger("messages").info("Preparing dataset for download.")
    to_export = pd.DataFrame(data)
    to_export = to_export[['id','chunk']+[x for x in to_export.columns if x not in ['id', 'chunk']]]

    name = "{}_val_{}_{}.csv".format(rule, x, dir)
    return " ", dcc.send_data_frame(to_export.to_csv, name, index=False)

@app.callback(Output("val-x", "min"),
                [Input("val-min", "value"), Input("val-rule-drop", "value")],
                State("project", "data"))
def update_min(min, rule_file, data):
    if rule_file is None:
        raise PreventUpdate

    rules = len(pd.read_csv((Path(data['project']) / "rules" / "{}.csv".format(rule_file)).as_posix()).index)
    logging.getLogger("messages").info("{} rule(s) in {} - minimum required total instances updated to {}".format(rules, rule_file, min*rules))
    return min * rules

@app.callback(Output("val-hidden2", "children"),
                Input("val-import", "n_clicks"))
def import_val(n):
    if n is None or n == 0:
        raise PreventUpdate

    

