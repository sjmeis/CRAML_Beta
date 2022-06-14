# Author: Stephen Meisenbacher
# view for tags page

import logging
from pathlib import Path 

import dash
from dash import dcc
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash import dash_table, no_update

from server import app
from .utility import get_keywords, save_keywords, open_file

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

def create_tab(name, project):
    if project is None:
        return []

    keys = get_keywords(project)
    if name in keys:
        temp = dcc.Tab(id="tab-{}".format(name), label=name, value=name, style=tab_style, 
                    selected_style=tab_selected_style, children=None)
        return temp
    else:
        return None

def get_layout(project):
    add_modal = html.Div(dbc.Modal(
                [
                    dbc.ModalHeader("Add new tag"),
                    dbc.ModalBody(
                        [
                            dbc.Label("Name:"),
                            dbc.Input(id="new_label_name", type="text", placeholder="Enter tag name.", debounce=True),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("OK", color="primary", id="modal_ok"),
                            dbc.Button("Cancel", id="modal_cancel"),
                        ]
                    ),
                ],
                id="addtag_modal",
                size="lg",
                centered=True,
                is_open=False,
                keyboard=True
            )
            )

    remove_modal = html.Div(dbc.Modal(
                [
                    dbc.ModalHeader("Remove a tag"),
                    dbc.ModalBody(
                        [
                            dbc.Label("Name:"),
                            dcc.RadioItems(id="remove-radio", options=None, value=None)
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("OK", color="primary", id="modal_remove_ok"),
                            dbc.Button("Cancel", id="modal_remove_cancel"),
                        ]
                    ),
                ],
                id="removetag_modal",
                size="lg",
                centered=True,
                is_open=False,
                keyboard=True
            )
            )


    modals = [add_modal, remove_modal]

    #dialog = dcc.ConfirmDialog(id="tag-success", message=None, displayed=False)

    tabs = dcc.Tabs(id="tag-tabs", value=None, style=tabs_styles,
                children=[create_tab(x, project) for x in get_keywords(project).keys()])

    add_tab = dbc.Button("+", id="addtag-button")
    remove_tab = dbc.Button("-", id="removetag-button")
    buttons = html.Div(dbc.ButtonGroup([add_tab, remove_tab], size="lg", className="me-1"), style={"width":"80%"})

    table = dash_table.DataTable(
                id="key-table",
                columns=None,
                data=None,
                editable=True,
                row_deletable=True,
                style_cell = {
                    'font_size': '16px',
                    'text_align': 'center'
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
                }
    )

    add_key = dbc.Button("Add keyword", id="table-add")
    save_table = dbc.Button("Save keywords", id="table-save")
    open_file = dbc.Button("Open Keyword File", id="open-keys")
    key_buttons = html.Div(dbc.ButtonGroup([add_key, save_table, open_file], size="lg", className="me-1"), style={"width":"80%"})

    loading = dcc.Loading(id="open-load")

    save_remind = dcc.Interval(id="save-remind", interval=10000)
    autosave = dcc.Interval(id="tag-autosave", interval=30000)

    hidden_div = html.Div(id="hidden-div", children=None, style={"display":"none"})
    hidden_div2 = html.Div(id="hidden-div2", children=None, style={"display":"none"})
    hidden_div3 = html.Div(id="hidden-div3", children=None, style={"display":"none"})
    current_tab = html.Div(id="hidden-cur-tab", children=None, style={"display":"none"})
    
    layout = modals+[html.H1("Tags"), html.H4("Tags are binary classes that are defined to characterize your text."),
                buttons, html.Hr(), tabs, table, key_buttons, loading, save_remind, autosave, hidden_div, hidden_div2, hidden_div3, current_tab]

    return layout

@app.callback(
    [Output("addtag_modal", "is_open"), Output("new_label_name", "value"), 
    Output("new_label_name", "placeholder"), Output("hidden-div", "children")],
    [
        Input("addtag-button", "n_clicks"),
        Input("modal_ok", "n_clicks"),
        Input("modal_cancel", "n_clicks"),
    ],
    [State("addtag_modal", "is_open"), State("new_label_name", "value"), State("tag-tabs", "value"),
    State("project", "data")]
)
def show_add_modal(n1, n2, n3, is_open, name, cur, data):
    KEYWORDS = get_keywords(data['project'])

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if is_open == False and which == "addtag-button":
        return True, None, "Enter tag name.", cur

    if is_open == True:
        if which == "modal_ok":
            if name is None:
                return True, None, "Please enter a tag name!", cur
            else:
                KEYWORDS[name] = ["Enter first keyword here."]
                KEYWORDS = KEYWORDS

                save_keywords(data['project'], KEYWORDS)

                return False, None, "Enter tag name.", name
        elif which == "modal_cancel":
            return False, None, "Enter tag name.", cur
        else:
            raise PreventUpdate

    return False, None, "Enter tag name.", cur

@app.callback(
    [Output("remove-radio", "options"), Output("remove-radio", "value"), 
    Output("hidden-div2", "children"), Output("removetag_modal", "is_open")],
    [
        Input("removetag-button", "n_clicks"),
        Input("modal_remove_ok", "n_clicks"),
        Input("modal_remove_cancel", "n_clicks"),
    ],
    [State("removetag_modal", "is_open"), State("remove-radio", "value"),
    State("project", "data")]
)
def show_remove_modal(n1, n2, n3, is_open, value, data):
    KEYWORDS = get_keywords(data['project'])

    if len(KEYWORDS.keys()) == 0:
        raise PreventUpdate
    
    options = [{"label":" "+x, "value":x} for x in KEYWORDS.keys()]
    first = list(KEYWORDS.keys())[0]

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if is_open == False and which == "removetag-button":
        return options, first, None, True
    if is_open == True:
        if which == "modal_remove_ok":
            if value is None:
                return options, first, None, True
            else:
                del KEYWORDS[value]

                save_keywords(data['project'], KEYWORDS)

                return [o for o in options if o['value'] != value], None, value, False
        elif which == "modal_remove_cancel":
            return options, None, None, False
        else:
            raise PreventUpdate

    return options, None, None, False

@app.callback([Output("tag-tabs", "children"), Output("tag-tabs", "value")],
                [Input("hidden-div", "children"), Input("hidden-div2", "children"),
                Input("hidden-div3", "children")],
                State("project", "data"))
def refresh_tags(x, y, z, data):
    KEYWORDS = get_keywords(data['project'])

    if x is None and y is None and z is None:
        raise PreventUpdate

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if which == "hidden-div3":
        if z is None:
            raise PreventUpdate
        else:
            
            message = "{} {} tag(s) saved successfully!".format(z.split(':::')[1], z.split(':::')[0])
            logging.getLogger("messages").critical(message)
            return [create_tab(k, data['project']) for k in KEYWORDS.keys()], z.split(':::')[0]
    elif which == "hidden-div2":
        if y is None:
            raise PreventUpdate
        else:
            if len(KEYWORDS.keys()) != 0:
                cur = list(KEYWORDS.keys())[-1]
            else:
                cur = None

            message = "{} successfully deleted.".format(y)
            logging.getLogger("messages").critical(message)
            return [create_tab(k, data['project']) for k in KEYWORDS.keys() if k != y], cur
    elif which == "hidden-div":
        if x is None:
            raise PreventUpdate
        else:
            #num_tags = len(KEYWORDS.keys())
            message = "{} tag created successfully!".format(x)
            logging.getLogger("messages").critical(message)
            return [create_tab(k, data['project']) for k in KEYWORDS.keys()], x
    else:
        raise PreventUpdate

@app.callback([Output("hidden-cur-tab", "children"),
                Output("table-add", "disabled"), Output("table-save", "disabled"),
                Output("open-keys", "disabled")],
                Input("tag-tabs", "value"))
def update_cur_tab_hidden(val):
    if val is None:
        return val, True, True, True
    else:
        return val, False, False, False

@app.callback([Output("key-table", "columns"), Output("key-table", "data"),
                Output("table-add", "children"), Output("table-save", "children")],
                [Input("hidden-cur-tab", "children"), Input("table-add", "n_clicks")],
                [State("key-table", "data"), State("key-table", "columns"),
                State("project", "data")])
def update_cur_tab(tag, n, rows, cols, proj):
    KEYWORDS = get_keywords(proj['project'])

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if which == "table-add":
        if n is None and tag is None:
            raise PreventUpdate

        rows.append({c['id']: "Enter new keyword here!" for c in cols})
        logging.getLogger("messages").info("New {} row added".format(tag))
        return cols, rows, "Add {} keyword".format(tag), "Save {} keywords".format(tag)  
    else:
        if tag is None:
            return None, None, "Add keyword", "Save keywords"
        else:
            new_cols = ([{"id":tag, "name":tag}])
            data = [{tag:key} for key in KEYWORDS[tag]]
            logging.getLogger("messages").info("Tag tab set to: \'{}\'".format(tag))
            return new_cols, data, "Add {} keyword".format(tag), "Save {} keywords".format(tag) 

@app.callback(
    Output("hidden-div3", "children"),
    Input("table-save", "n_clicks"),
    [State("key-table", "data"), State("hidden-cur-tab", "children"),
    State("project", "data")])
def save_keys(n_clicks, rows, tag, data):
    if n_clicks is None:
        raise PreventUpdate

    KEYWORDS = get_keywords(data['project'])

    if n_clicks > 0:
        KEYWORDS[tag] = [d[tag] for d in rows]
        save_keywords(data['project'], KEYWORDS)

    return tag+":::"+str(len(KEYWORDS[tag]))
    
@app.callback(Output("save-remind", "interval"),
                [Input("save-remind", "n_intervals"), Input("tag-autosave", "n_intervals")],
                [State("tag-tabs", "value"), State("key-table", "data"),
                State("project", "data")])
def remind(n, n2, cur, data, proj):
    if data is None or cur is None:
        raise PreventUpdate

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if which == "save-remind":
        table_keys = [d[cur] for d in data]
        saved = get_keywords(proj['project'])[cur]

        if set(table_keys) != set(saved):
            logging.getLogger("messages").warning("Friendly Reminder - you have unsaved changes!")
            return 5000
        else:
            return 10000
    else:
        if n2 is None or n2 == 0:
            raise PreventUpdate

        logging.getLogger("messages").info("Autosaving changes...")
        KEYWORDS = get_keywords(proj['project'])
        KEYWORDS[cur] = [d[cur] for d in data]
        save_keywords(proj['project'], KEYWORDS)
        return 10000

@app.callback(Output("open-load", "children"),
                Input("open-keys", "n_clicks"),
                State("project", "data"))
def open_keywords(n, data):
    if n is None:
        raise PreventUpdate

    filepath = Path(data['project']) / "keywords.json"
    if filepath.is_file() == False:
        logging.getLogger("messages").error("No keyword file exists yet!")
        return " "
    else:
        open_file(filepath.resolve())
        return " "
    