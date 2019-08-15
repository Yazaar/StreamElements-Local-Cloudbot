import requests, zipfile, io, sys, time, os, shutil, threading

version = '0.0.1'


def downloadUpdate():
    eventHandler.SendMessage({'bot':'local', 'message':'Updating YouTube Analyzer... ...'})
    data = requests.get('https://github.com/Yazaar/StreamElements-Local-Cloudbot/blob/master/verified_extensions/Yazaar-YouTube_Analyzer/update.zip?raw=true')

    rootDir = __file__.rsplit('\\', 1)[0]
    
    if data.status_code != 200:
        eventHandler.SendMessage({'bot':'local', 'message':'/me Error: Failed to update YouTube Analyzer... (URL error)'})
        return

    with zipfile.ZipFile(io.BytesIO(data.content)) as f:
        f.extractall(rootDir + '\\UpdateData')

    for root, dirs, files in os.walk(rootDir + '\\UpdateData'):
        # d for directories
        d = root.split('UpdateData\\')
        if len(d) == 1:
            d = ''
        else:
            d = d[1]
        for i in files:
            if not os.path.isdir(rootDir + '\\' + d):
                os.makedirs(rootDir + '\\' + d)
            shutil.move(root + '\\' + i, rootDir + '\\' + d + i)
    
    shutil.rmtree(rootDir + '\\UpdateData', ignore_errors=True)
    eventHandler.SendMessage({'bot':'local', 'message':'Update of YouTube Analyzer complete!'})


def Initialize(data, EData):
    global port, eventHandler
    port = data['port']
    eventHandler = EData

def Execute(data):
    words = data['message'].split(' ')
    if words[0].lower() != '!youtubeanalyzer' or len(words) < 2:
        return

    if data['moderator'] == False:
        return
    
    if words[1] == 'version':
        eventHandler.SendMessage({'bot':'local', 'message':f'Current version: {version}'})
        return

    if words[1] == 'update':
        threading.Thread(target=downloadUpdate).start()
        return