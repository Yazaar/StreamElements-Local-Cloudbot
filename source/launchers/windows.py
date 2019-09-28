import requests, os, sys, json, subprocess

version = 1

if not os.getcwd() in sys.path:
    sys.path.append(os.getcwd())

def checkForUpdates(url):
    try:
        downloadData = json.loads(requests.get(url).text)
        downloadData['version']
        downloadData['download']
        downloadData['log']
    except Exception:
        print('Unable to check for exe executable updates, no network connection?')
        downloadData = {'version': version, 'download': '', 'log': ''}
    return downloadData

def WaitForYN():
    while True:
        temp = input().lower()
        if temp == 'y':
            return True
        elif temp == 'n':
            return False

downloadData = checkForUpdates('https://raw.githubusercontent.com/Yazaar/StreamElements-Local-Cloudbot/master/exeVersion.json')

if downloadData['version'] > version:
    print('An update for the .exe has been found. Do you wish to update? (y/n)\nThis may be required to get it working')
    pick = WaitForYN()
    if pick == True:
        subprocess.Popen(sys.executable + ' SoftwareUpdater.py ' + downloadData['download'], creationflags=0x00000008, shell=True)
        raise SystemExit

import socketio as socket_io
from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO

from LocalStreamElements import main

try:
    main(launcher='exe')
except KeyboardInterrupt:
    pass