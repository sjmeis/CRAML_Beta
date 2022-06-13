#!/usr/bin/env python3
# Author: Stephen Meisenbacher
# November 7, 2021
# CRaML_Tool.py
# run tool

import os
import webbrowser
import threading
import time
import signal

import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from flask import request
from server import app
from index import server, shutdown_server

server_thread = None
app_thread = None
root = None

def signal_handler(sig, frame):
    global server_thread
    global app_thread

    print("\nExiting...")
    shutdown_server()
    server_thread.join()
    app_thread.join()
    exit(0)

def main():
    controller = webbrowser.get()
    webbrowser.open("http://127.0.0.1:8011/")

if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal_handler)

    server_thread = threading.Thread(target=server, args=(), kwargs={})
    server_thread.start()
    
    app_thread = threading.Thread(target=main, args=(), kwargs={})
    app_thread.start()

    while app_thread.is_alive() == True and server_thread.is_alive() == True:
        time.sleep(1)

    shutdown_server()
    server_thread.join()
    app_thread.join()