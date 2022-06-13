# Author: Stephen Meisenbacher
# view for rules page

import os
from pathlib import Path
import pandas as pd
import logging

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash import dash_table

from server import app
from .utility import get_keywords, get_rules, open_file

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

def create_tab(name):
    temp = dcc.Tab(id="tab-{}".format(name), label=name.stem, value=name.stem, 
            style=tab_style, selected_style=tab_selected_style, children=None)
    return temp

def get_layout(project):

    add_modal = html.Div(dbc.Modal(
                [
                    dbc.ModalHeader("Add new rule file"),
                    dbc.ModalBody(
                        [
                            dbc.Label("File name:"),
                            dbc.Input(id="new_file_name", type="text", placeholder="Enter file name.", debounce=True),
                            dbc.Label("Which tags to include?"),
                            dcc.Checklist(id="add-check", options=None, value=None)
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("OK", color="primary", id="rules_modal_ok"),
                            dbc.Button("Cancel", id="rules_modal_cancel"),
                        ]
                    ),
                ],
                id="addfile_modal",
                size="lg",
                centered=True,
                is_open=False,
                keyboard=True
            )
            )

    remove_modal = html.Div(dbc.Modal(
                [
                    dbc.ModalHeader("Remove a rule file"),
                    dbc.ModalBody(
                        [
                            dbc.Label("Name:"),
                            dcc.RadioItems(id="file-remove-radio", options=None, value=None)
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("OK", color="primary", id="rules_modal_remove_ok"),
                            dbc.Button("Cancel", id="rules_modal_remove_cancel"),
                        ]
                    ),
                ],
                id="removefile_modal",
                size="lg",
                centered=True,
                is_open=False,
                keyboard=True
            )
            )


    modals = [add_modal, remove_modal]

    add_rule = dbc.Button("+", id="addfile-button")
    remove_rule = dbc.Button("-", id="removefile-button")
    buttons = html.Div(dbc.ButtonGroup([add_rule, remove_rule], size="lg", className="me-1"), style={"width":"80%"})

    tabs = dcc.Tabs(id="rule-tabs", value=None, style=tabs_styles,
                children=[create_tab(x) for x in get_rules(project)])

    table = dash_table.DataTable(
                id="rules-table",
                columns=None,
                data=None,
                editable=True,
                row_deletable=True,
                style_cell = {
                    'font_size': '16px',
                    'text_align': 'center',
                    'minWidth':'50px'
                },
                fixed_rows={'headers': True},
                style_table={'max_height': 700},
                style_as_list_view=True,
                style_header={
                    'backgroundColor': 'rgb(30, 30, 30)',
                    'color': 'white'
                },
                style_data={
                    'backgroundColor': 'rgb(50, 50, 50)',
                    'color': 'white'
                },
                sort_action='native'
    )

    add_rule = dbc.Button("Add rule", id="rules-table-add")
    save_rules_table = dbc.Button("Save rules", id="rules-table-save")
    open_rules = dbc.Button("Open rules", id="open-rules")
    key_buttons = html.Div(dbc.ButtonGroup([add_rule, save_rules_table, open_rules], size="lg", className="me-1"), style={"width":"80%"})

    loading = dcc.Loading(id="open-rules-load")

    save_remind = dcc.Interval(id="save-remind-rules", interval=10000)
    autosave = dcc.Interval(id="rule-autosave", interval=30000)

    hidden_div = html.Div(id="rules-hidden-div", children=None, style={"display":"none"})
    hidden_div2 = html.Div(id="rules-hidden-div2", children=None, style={"display":"none"})
    hidden_div3 = html.Div(id="rules-hidden-div3", children=None, style={"display":"none"})
    rules_current_tab = html.Div(id="rules-hidden-cur-tab", children=None, style={"display":"none"})
    hidden = [hidden_div, hidden_div2, hidden_div3, rules_current_tab]

    layout = modals+[html.H1("Rules"), html.H4("Create rules for your tags."), 
                buttons, html.Hr(), tabs, table, key_buttons, loading, save_remind, autosave]+hidden

    return layout

@app.callback(
    [Output("add-check", "options"), Output("add-check", "value"), 
    Output("addfile_modal", "is_open"), Output("new_file_name", "value"), 
    Output("new_file_name", "placeholder"), Output("rules-hidden-div", "children")],
    [
        Input("addfile-button", "n_clicks"),
        Input("rules_modal_ok", "n_clicks"),
        Input("rules_modal_cancel", "n_clicks"),
    ],
    [State("addfile_modal", "is_open"), State("new_file_name", "value"), \
        State("rule-tabs", "value"), State("add-check", "value"),
        State("project", "data")]
)
def show_add_modal(n1, n2, n3, is_open, name, cur, rule_val, data):

    if n1 is None and n2 is None and n3 is None:
        raise PreventUpdate

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    options = [{"label":" "+x, "value":x} for x in get_keywords(data['project']).keys()]
    first = [list([x for x in get_keywords(data['project']).keys()])[0]]

    if is_open == False and which == "addfile-button":
        return options, first, True, None, "Enter file name.", cur

    if is_open == True:
        if which == "rules_modal_ok":
            if name is None:
                return options, first, True, None, "Please enter a file name!", cur
            else:
                base = name
                name = name.split('.')[0]+".csv"

                path = Path(data['project']) / "rules" / name
                with open(path.as_posix(), 'w') as out:
                    chosen = ",".join(rule_val)
                    out.write("rule,prio,{}\n".format(chosen))
                    
                    KEYWORDS = get_keywords(data['project'])
                    new_keys = []
                    for r in rule_val:
                        for k in KEYWORDS[r]:
                            new_keys.append(k)
                    new_keys = list(set(new_keys))
                    for k in new_keys:
                        out.write("{},0,".format(k)+",".join(['0' for x in range(len(rule_val))]))
                        out.write('\n')

                return options, first, False, None, "Enter file name.", base
        elif which == "rules_modal_cancel":
            return options, no_update, False, no_update, no_update, no_update
        else:
            raise PreventUpdate
    else:
        raise PreventUpdate

@app.callback(
    [Output("file-remove-radio", "options"), Output("file-remove-radio", "value"), 
    Output("rules-hidden-div2", "children"), Output("removefile_modal", "is_open")],
    [
        Input("removefile-button", "n_clicks"),
        Input("rules_modal_remove_ok", "n_clicks"),
        Input("rules_modal_remove_cancel", "n_clicks"),
    ],
    [State("removefile_modal", "is_open"), State("file-remove-radio", "value"),
    State("project", "data")]
)
def show_remove_modal(n1, n2, n3, is_open, value, data):

    if n1 is None and n2 is None and n3 is None:
        raise PreventUpdate

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    options = [{"label":" "+x.stem, "value":x.as_posix()} for x in get_rules(data['project'])]
    first = list([x.stem for x in get_rules(data['project'])])[0]

    if is_open == False and which == "removefile-button":
        return options, first, None, True
    if is_open == True:
        if which == "rules_modal_remove_ok":
            if value is None:
                return options, first, None, True
            else:
                os.remove(value)
                return [o for o in options if o['value'] != value], None, value, False
        elif which == "rules_modal_remove_cancel":
            return options, None, None, False
        else:
            raise PreventUpdate
    else:
        raise PreventUpdate

@app.callback([Output("rule-tabs", "children"), Output("rule-tabs", "value")],
                [Input("rules-hidden-div", "children"), Input("rules-hidden-div2", "children"),
                Input("rules-hidden-div3", "children")],
                State("project", "data"))
def refresh_tags(x, y, z, data):
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if which == "rules-hidden-div3":
        if z is None:
            raise PreventUpdate
        else:
            num_rules = z.split(':::')[1]
            stem = z.split(':::')[0].split('.')[0]
            save_path = Path(data['project']) / "rules" / z.split(':::')[0]
            message = "{} [{} rule(s)] saved to {}".format(stem, num_rules, save_path.as_posix())
            logging.getLogger("messages").critical(message)
            return [create_tab(x) for x in get_rules(data['project'])], z.split(':::')[0]
    elif which == "rules-hidden-div2":
        if y is None:
            raise PreventUpdate
        else:
            if len(get_rules(data['project'])) != 0:
                cur = list(get_rules(data['project']))[-1].as_posix()
            else:
                cur = None

            message = "{} rules successfully deleted.".format(Path(y).stem)
            logging.getLogger("messages").critical(message)

            return [create_tab(x) for x in get_rules(data['project'])], cur
    elif which == "rules-hidden-div":
        if x is None:
            raise PreventUpdate
        else:
            save_path = Path(data['project']) / "rules" / "{}".format(x)
            message = "{} rules file created! Located at {}".format(x, save_path.as_posix())
            logging.getLogger("messages").critical(message)
            return [create_tab(x) for x in get_rules(data['project'])], Path(x).name
    else:
        raise PreventUpdate

@app.callback([Output("rules-hidden-cur-tab", "children"),
                Output("rules-table-add", "disabled"), Output("rules-table-save", "disabled"),
                Output("open-rules", "disabled")],
                Input("rule-tabs", "value"))
def update_cur_tab(val):
    if val is None:
        return val, True, True, True
    else:
        return val, False, False, False

@app.callback([Output("rules-table", "columns"), Output("rules-table", "data"), 
                Output("rules-table", "tooltip_header"),
                Output("rules-table-add", "children"), Output("rules-table-save", "children"),
                Output("open-rules", "children")],
                [Input("rules-hidden-cur-tab", "children"), Input("rules-table-add", "n_clicks")],
                [State("rules-table", "data"), State("rules-table", "columns"),
                State("project", "data")])
def update_cur_tab(file, n, rows, cols, proj):
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    tooltip = {'prio':"Relative priority (ordinal ranking) of a given rule. \
        Greater priority will overwrite and overlapping rule with lower priority."}

    if file is not None:
        #name = file.split('.')[0]
        name = Path(file).stem
    else:
        name = None

    if which == "rules-table-add":
        if n is None and file is None:
            raise PreventUpdate

        pointers = ["Enter new rule here!", "Enter rule priority."]+["Enter tag value (0/1)." for i in range(len(cols)-2)]
        rows.append({c['id']: pointers[i] for i, c in enumerate(cols)})
        logging.getLogger("messages").info("New {} row added".format(name))
        return cols, rows, tooltip, "Add {} rule".format(name), "Save {} rules".format(name), "Open {} rules".format(name) 
    else:
        if file is None:
            return None, None, None, "Add rule", "Save rules", "Open rules"
        else:
            rules_path = (Path(proj['project']) / "rules" / "{}.csv".format(file.split(':::')[0])).as_posix()
            # check if file format correct, if not, fix
            with open(rules_path, 'r') as f:
                check = f.read()
            if check[-1] != '\n':
                with open(rules_path, 'w') as out:
                    out.write(check+'\n')

            data = pd.read_csv(rules_path)
            new_data = data.to_dict('records')
            new_cols = [{'id':'rule', 'name':'rule'},
                        {'id':'prio', 'name': 'priority', 'type':'numeric'}]+[{'id':x, 'name':x, 'type':'numeric'} for x in data.columns[2:]]
            logging.getLogger("messages").info("Rules tab set to: \'{}\'".format(name))
            return new_cols, new_data, tooltip, "Add {} rule".format(name), "Save {} rules".format(name), "Open {} rules".format(name)

@app.callback(
    Output("rules-hidden-div3", "children"),
    Input("rules-table-save", "n_clicks"),
    [State("rules-table", "data"), State("rules-hidden-cur-tab", "children"),
    State("project", "data")])
def save_rules(n_clicks, rows, file, proj):
    if n_clicks is None:
        raise PreventUpdate

    key_cols = get_keywords(proj['project']).keys()

    if n_clicks > 0:
        data = pd.DataFrame(rows)
        extra = [x for x in key_cols if x in data.columns]
        data = data[["rule", "prio"]+extra]
        save_path = Path(proj['project']) / "rules" / "{}.csv".format(file)
        data.to_csv(save_path.as_posix(), index=False)
        to_ret = "{}:::{}".format(file, len(data.index))
        return to_ret
    else:
        raise PreventUpdate

@app.callback([Output("save-remind-rules", "interval"), Output("rules-table-save", "n_clicks")],
                [Input("save-remind-rules", "n_intervals"), Input("rule-autosave", "n_intervals")],
                [State("rule-tabs", "value"), State("rules-table", "data"),
                State("rules-table", "columns"), State("project", "data"), 
                State("rules-table-save", "n_clicks")])
def remind_rules(n, n2, cur, data, cols, proj, clicks):
    if data is None or cur is None:
        raise PreventUpdate

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]
 
    if which == "save-remind-rules":
        table_rules = [d['rule'] for d in data]
        table_prio = [d['prio'] for d in data]
        rules_cols = [x['id'] for x in cols[2:]]
        table_vals = [[d[r] for d in data] for r in rules_cols]

        rules_path = Path(proj['project']) / "rules" / "{}.csv".format(cur)
        rules = pd.read_csv(rules_path.as_posix())
        saved_rules = rules['rule'].tolist()
        saved_prio = rules['prio'].tolist()
        saved_vals = [rules[x].tolist() for x in  rules_cols]

        if len(table_rules) != len(saved_rules) or any(x is False for x in [y == z for y,z in zip(table_rules, saved_rules)]):
            logging.getLogger("messages").warning("Friendly Reminder - you have unsaved changes! Rule change(s) detected.")
            return 5000, no_update
        elif len(table_prio) != len(saved_prio) or any(x is False for x in [y == z for y,z in zip(table_prio, saved_prio)]):
            logging.getLogger("messages").warning("Friendly Reminder - you have unsaved changes! Prio change(s) detected.")
            return 5000, no_update
        else:
            for i, tup in enumerate(zip(table_vals, saved_vals)):
                x = tup[0]
                y = tup[1]
                if any(z is False for z in [a == b for a,b in zip(x,y)]):
                    logging.getLogger("messages").warning("Friendly Reminder - you have unsaved changes! \'{}\' change(s) detected.".format(rules_cols[i]))
                    return 5000, no_update
            return 10000, no_update
    else:
        if n2 is None or n2 == 0:
            raise PreventUpdate

        logging.getLogger("messages").info("Autosaving changes...")
        if clicks is None:
            clicks = 1
        else:
            clicks += 1
        return 10000, clicks 

@app.callback(Output("open-rules-load", "children"),
                Input("open-rules", "n_clicks"),
                [State("rule-tabs", "value"), State("project", "data")])
def open_keywords(n, cur, data):
    if n is None:
        raise PreventUpdate

    filepath = Path(data['project']) / "rules" / "{}.csv".format(cur)
    open_file(filepath.resolve())
    return " "