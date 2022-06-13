# Author: Stephen Meisenbacher
# view for project selector page

import os
from pathlib import Path
import logging

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from server import app

def get_layout():
    proj_path = Path("projects")
    if proj_path.is_dir() == False:
        os.makedirs("projects")

    new_modal = html.Div(dbc.Modal(
                [
                    dbc.ModalHeader("Add new project"),
                    dbc.ModalBody(
                        [
                            dbc.Label("Name:"),
                            dbc.Input(id="new_proj_name", type="text", placeholder="Enter project name.", debounce=True),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("OK", color="primary", id="modal_ok_proj"),
                            dbc.Button("Cancel", id="modal_cancel_proj"),
                        ]
                    ),
                ],
                id="new_modal",
                size="lg",
                centered=True,
                is_open=False,
                keyboard=True
            )
            )

    #confirm = dcc.ConfirmDialog(id="project-confirm")

    options = [{"label":"New Project", "value":"new"}]
    for d in os.listdir("projects"):
        options.append({"label":d, "value":d})

    drop = dcc.Dropdown(
            id="project-drop",
            options=options,
            value="new",
            style={"width":"50rem", "display":"inline-block", "padding":"1rem"}
    )

    button = dbc.Button("Select", id="project-select", style={"display":"inline-block"})

    body = html.Div(dbc.Row([drop, button], align="center"),
                    style={"display":"inline-block"})

    layout = [new_modal, html.H1("Project"), 
                html.H4("Please select a project to begin (or create a new one)."),
                html.Hr(), body]

    return layout

@app.callback([Output("project", "data"), Output("new_modal", "is_open"),
                Output("url", "pathname")],
                [Input("project-select", "n_clicks"), Input("modal_ok_proj", "n_clicks"),
                Input("modal_cancel_proj", "n_clicks")],
                [State("project-drop", "value"), State("project", "data"),
                State("new_proj_name", "value"), State("new_modal", "is_open")])
def select_project(n, o, c, value, data, proj, is_open):
    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if which == "modal_ok_proj":
        if o == 0 or o is None:
            raise PreventUpdate

        if proj is None:
            logging.getLogger("messages").error("Please enter a project name.")
            return data, True, no_update
        else:
            path = Path("projects") / proj
            os.makedirs(path.as_posix())
            os.makedirs((path / "csv").as_posix())
            os.makedirs((path / "logs").as_posix())
            os.makedirs((path / "train").as_posix())
            data['project'] = path.as_posix()
            logging.getLogger("messages").info("Project created and selected: {}".format(proj))
            return data, False, "/home"
    elif which == "modal_cancel_proj":
        if c == 0 or c is None:
            raise PreventUpdate

        return no_update, False
    elif which == "project-select":
        if n == 0 or n is None:
            raise PreventUpdate

        if value == "new" and is_open == False:
            return no_update, True, no_update
        else:
            data['project'] = (Path("projects") / value).as_posix()
            logging.getLogger("messages").info("Switched to project: {}".format(value))
            return data, False, "/home"

    raise PreventUpdate