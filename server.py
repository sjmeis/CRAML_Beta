# Dash app initialization
# User management initialization
import os
from pathlib import Path

import dash
import dash_bootstrap_components as dbc

VERSION = "Beta v0.4"

#external_stylesheets=["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css",
#                        dbc.themes.BOOTSTRAP, "assets/style.css"]
external_stylesheets=[dbc.themes.BOOTSTRAP, "assets/new.css"]

app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
    suppress_callback_exceptions=True,
    update_title=None
)
app.title = "CRAML Wizard {}".format(VERSION)

server = app.server


