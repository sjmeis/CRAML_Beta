# Author: Stephen Meisenbacher
# view for DocumentCloud login

import requests
from datetime import datetime
import logging
from documentcloud import DocumentCloud
import time

import dash
from dash import dcc, no_update
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_daq as daq

from .utility import p_encode
from server import app

def auth(USER, PASS, data):
    MR_BASE = "https://accounts.muckrock.com/api"

    if 'REFRESH' not in data or data['REFRESH'] is None:
        auth_params = {"username":USER, "password":PASS}
        url = "{}/token/".format(MR_BASE)
        s_mess = "Login Complete!"   
    else:
        auth_params = {"refresh":data['REFRESH']}
        url = "{}/refresh/".format(MR_BASE)
        s_mess = "Reauthentication complete!"
        
    r = requests.post(url, data=auth_params)
    if r.ok:
        response = r.json()
        data['ACCESS'] = response['access']
        data['REFRESH'] = response['refresh']
        if "username" in auth_params and "password" in auth_params:
            data['user'] = USER
            data['passw'] = p_encode(PASS)
        data['last_update'] = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
        logging.getLogger("messages").critical(s_mess)
        return data, 0          
    else:
        if "detail" in r.json() and r.json()['detail'] == "No active account found with the given credentials":
            logging.getLogger("messages").error("Invalid login credentials.")
        else:
            logging.getLogger("messages").error("Login connection failed.")
        return data, 1

def get_layout(dc):
    if len(dc.keys()) > 0:
        logging.getLogger("messages").info("Already logged in!")
        USER = dc['user']
        passw_disabled = True
        status = "logged in as {}".format(USER)
        login_disabled = True
        logout_disabled = False
        reauth_disabled = False
    else:
        USER = None
        passw_disabled = False
        status = "not logged in"
        login_disabled = False
        logout_disabled = True
        reauth_disabled = True

    info = html.Div([html.H6("Login Status: ", style={"display":"inline-block", "padding":"1rem"}), 
                    html.B(status, id="login-status", style={"display":"inline-block"})],
                    style={"display":"inline-block"})

    user = html.Div(dbc.Input(id="username-input", type="text", value=USER, placeholder="DocumentCloud Username", autoComplete=False),
                    style={"padding":"1rem"})

    password = html.Div(dbc.Input(id="username-pass", type="password", placeholder="DocumentCloud Password", autoComplete=False, disabled=passw_disabled),
                    style={"padding":"1rem"})

    login = dbc.Button("Login", id="dc-login-button", disabled=login_disabled)
    logout = dbc.Button("Logout", id="dc-logout-button", disabled=logout_disabled)
    buttons = html.Div(dbc.ButtonGroup([login, logout], size="md", className="me-1"), style={"width":"80%"})

    loading = dcc.Loading(id="login-load")
    reauth = dcc.Interval(id="reauth-timer", interval=5000, disabled=reauth_disabled)

    layout = [html.H1("DocumentCloud Login"), html.H4("Connect with your DC account."), 
                info, user, password, buttons, loading, reauth]

    return layout

@app.callback([Output("dc", "data"), Output("username-input", "disabled"),
                Output("username-pass", "disabled"), Output("dc-login-button", "disabled"),
                Output("dc-logout-button", "disabled"), Output("login-status", "children"),
                Output("username-input", "value"), Output("username-pass", "value"),
                Output("reauth-timer", "disabled")],
                [Input("dc-login-button", "n_clicks"), Input("dc-logout-button", "n_clicks"),
                Input("reauth-timer", "n_intervals")],
                [State("username-input", "value"), State("username-pass", "value"),
                State("dc", "data")])
def try_login(n, n2, n3, user, passw, data):

    ctx = dash.callback_context
    which = ctx.triggered[0]['prop_id'].split('.')[0]

    if which == "dc-login-button":
        if n is None:
            raise PreventUpdate

        if user is None or user == "" or passw is None or passw == "":
            logging.getLogger("messages").error("Missing username and/or password!")
            raise PreventUpdate

        logging.getLogger("messages").info("Attempting login...")
        data, ret = auth(user, passw, data)
        if ret == 0:
            return data, True, True, True, False, "logged in as {}".format(user), no_update, no_update, False
        else:
            return no_update, False, False, False, True, "login failed", no_update, no_update, True
    elif which == "dc-logout-button":
        if n2 is None:
            raise PreventUpdate

        logging.getLogger("messages").critical("Logout complete.")
        return {}, False, False, False, True, "not logged in", None, None, True
    else:
        if n3 is None or len(data.keys()) == 0:
            raise PreventUpdate

        if "ACCESS" in data and data['ACCESS'] is not None:
            if (datetime.now() - datetime.strptime(data['last_update'], "%Y-%m-%d %H:%M:%S")).total_seconds() >= 300:
                logging.getLogger("messages").info("Reauthenticating DocumentCloud login for {}".format(data['user']))
                data, ret = auth(None, None, data)
                if ret == 0:
                    if ret == 0:
                        return data, True, True, True, False, "logged in as {}".format(user), no_update, no_update, False
                    else:
                        return {}, False, False, False, True, "reauth failed - automatically logged out", None, None, True
            else:
                raise PreventUpdate
        else:
            raise PreventUpdate