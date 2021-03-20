import json, requests, shutil, os
from pathlib import Path
from flask import Flask, render_template, render_template_string, send_file, request
from flask_socketio import SocketIO

try:
    from dependencies.modules.StreamElements import StreamElements
    from dependencies.modules.Misc import loadSettings, portOverload, Users, validateSetting, saveSettings, localIP, getMimetype, getServerIP
    from dependencies.modules.Extensions import Extensions
    from dependencies.modules.Chat import Chat
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False

#######################
## Auto update start ##
#######################

def WaitForYN():
    while True:
        temp = input().lower()
        print()
        if temp == 'y':
            return True
        elif temp == 'n':
            return False

def fetchUrl(url):
    try:
        response = requests.get(url)
    except Exception:
        return 0
    
    if response.status_code != 200:
        return -1

    return response

def update():
    newestVersion = fetchUrl('https://raw.githubusercontent.com/Yazaar/StreamElements-Local-Cloudbot/master/LatestVersion.json')
    
    if IMPORT_SUCCESS:
        if newestVersion == 0:
            print('No internet connection, unable to load update information.\nUsing existing build')
            return
        elif newestVersion == -1:
            print('No connection to GitHub, unable to load update information.\nUsing existing build')
            return
    else:
        if newestVersion == 0:
            print('Dependencies missing and no internet connection.\nUnable to continue without an internet connection.\n\nHit enter to exit')
            input()
            raise SystemExit
        elif newestVersion == -1:
            print('Unable to continue, dependencies missing and unable to load update information.\n\nHit enter to exit')
            input()
            raise SystemExit
        else:
            print('Update required to continue because of missing dependencies, would you like to continue (input y) or exit (input n)')
            if WaitForYN() == False:
                print('Unable to continue since dependencies are missing.\n\nHit enter to exit')
                input()
                raise SystemExit
    
    try: newestVersion = json.loads(newestVersion.text)
    except Exception: newestVersion = {}
    
    if not 'files' in newestVersion or not isinstance(newestVersion['files'], dict):
        if IMPORT_SUCCESS:
            print('Invalid update information structure, using existing build.')
            return
        else:
            print('Invalid update information structure, unable to continue.\nBecause of missing dependencies unable to continue.\n\nHit enter to exit')
            input()
            raise SystemExit

    versionTrackerPath = Path('dependencies/data/versionTracker.json')
    if versionTrackerPath.is_file():
        with open(versionTrackerPath, 'r') as f:
            try: versionData = json.load(f)
            except Exception: versionData = {}
    else:
        versionData = {}
    
    # index 0: Path object; index 1: URL; index 2: raw path string; index 3: file version 
    filesToUpdate = []

    for rawFilepath in newestVersion['files']:
        filePath = Path(rawFilepath)
        if filePath.is_file():
            if not rawFilepath in versionData or newestVersion['files'][rawFilepath]['version'] > versionData[rawFilepath]:
                filesToUpdate.append([filePath, newestVersion['files'][rawFilepath]['url'], rawFilepath, newestVersion['files'][rawFilepath]['version']])
        else:
            filesToUpdate.append([filePath, newestVersion['files'][rawFilepath]['url'], rawFilepath, newestVersion['files'][rawFilepath]['version']])
    
    updateCount = len(filesToUpdate)
    if updateCount == 0:
        return

    print(str(updateCount) + ' files require an update, would you like to update? (y/n)')
    if not WaitForYN():
        if IMPORT_SUCCESS:
            print('Update declined, launching')
            return
        else:
            print('Update declined, closing (missing dependencies)')
            raise SystemExit
    
    for file in filesToUpdate:
        content = fetchUrl(file[1])
        if content in [-1, 0]:
            print('#########')
            print('ERROR, unable to update file')
            print('file path:', file[2])
            print('file url:', file[1])
            print('#########')
            continue
        file[0].parent.mkdir(parents=True, exist_ok=True)
        with open(file[0], 'wb') as f:
            f.write(content.content)
        versionData[file[2]] = file[3]

    versionTrackerPath.parent.mkdir(parents=True, exist_ok=True)
    with open(versionTrackerPath, 'w') as f:
        try: json.dump(versionData, f)
        except Exception: print('Unable to save to versionTracker.json for some odd reason')
    
    if 'delete' in newestVersion and isinstance(newestVersion['delete'], list):
        for entity in newestVersion['delete']:
            entityPath = Path(entity)
            if entityPath.is_file():
                try: os.remove(entityPath)
                except Exception: print('Unable to delete: ' + entity)
            elif entityPath.is_dir():
                try: shutil.rmtree(entityPath)
                except Exception: print('Unable to delete: ' + entity)
    
    print('\n\nUpdate complete, please restart.\nHit enter to exit')
    input()
    raise SystemExit

#####################
## Auto update end ##
#####################

def boot():
    os.chdir(Path(__file__).parent)
    update()

    settings = loadSettings()

    overloadBool, overloadPort = portOverload()
    if overloadBool:
        settings['server_port'] = overloadPort
        saveSettings(settings)
    
    currentIP = fetchUrl('https://ident.me')
    if currentIP in [-1, 0]:
        currentIP = fetchUrl('https://api.ipify.org')
        if currentIP in [-1, 0]:
            print('[ERROR]: Unable to check for your public IP, no network connection?')
    
    if not currentIP in [-1, 0]:
        currentIP = currentIP.text

    app = Flask(__name__, template_folder='dependencies/web/HTML', static_folder='dependencies/web/static')
    sio = SocketIO(app, async_mode='gevent')

    appContext = app.test_request_context('/')

    SE = StreamElements(sio, appContext)
    users = Users()
    chat = Chat(users, SE, sio, appContext)

    chat.setTwitchData(tmi=settings['tmi'], tmi_username=settings['tmi_twitch_username'], twitch_channel=settings['twitch_channel'])
    if chat.startTwitch()[0] == 1:
        chat.awaitStart(10)

    SE.setData(jwt=settings['jwt_token'], method=settings['SEListener'])
    if SE.start()[0] == 1:
        SE.awaitStart(10)
    
    extensions = Extensions(chat, SE, users, sio, appContext, settings['server_port'])
    extensions.setData(executionsPerSecond=settings['executions_per_second'])

    chat.bindExtensions(extensions)

    SERVER_IP = getServerIP()

    NO_ACCESS_STRING = '<h1>Access denied</h1><p>You are not allowed to enter this area</p>'

    @app.route('/', methods=['GET'])
    def webRoot():
        if not localIP(request.environ, currentIP): return NO_ACCESS_STRING
        return render_template('index.html', extensions=extensions.dump(), ExtensionsSettings=extensions.settings, events=SE.eventHistory, messages=chat.twitchMessagesHistory, ExtensionLogs=extensions.log, regulars=users.regulars, settings=settings)
    
    @app.route('/dependencies/data/url.js')
    def webUrlJs():
        if not localIP(request.environ, currentIP): return NO_ACCESS_STRING
        path = Path('dependencies/data/url.js')
        if not path.is_file:
            return ''
        return send_file(path, 'text/javascript')
    
    @app.route('/extensions/<path:raw_path>')
    def webCustomPath(raw_path):
        if not localIP(request.environ, currentIP): return NO_ACCESS_STRING
        mimetype = request.args.get('mimetype')

        path = Path('extensions') / raw_path

        if path.is_file() == False:
            return 'No file at selected path'
        
        filenameLower = path.name.lower()

        if mimetype == None:
            if filenameLower[-5:].lower() == '.html':
                with open(path, 'r') as f:
                    try: return render_template_string(f.read())
                    except Exception: pass
            mimetype = getMimetype(filenameLower)

        if mimetype != None:
            return send_file(path, mimetype=mimetype)
        else:
            with open (path, 'r') as f:
                try: return f.read()
                except Exception: pass
        return 'Unknown file :( Try using http://url/path/file?mimetype=file_mimetype (preferably, use %2F instead of /, as an example, image/png (png) becomes image%2Fpng)'
    
    @app.route('/StreamElementsAPI', methods=['post'])
    def webStreamElementsAPI():
        if not localIP(request.environ, currentIP): return NO_ACCESS_STRING
        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json=JSON_DATA)'})
        success, msg = SE.APIRequest(message)
        if success:
            return json.dumps({'type':'success', 'success': True, 'response': msg})
        else:
            return json.dumps({'type':'error', 'success': False, 'message': msg})

    @app.route('/SendMessage', methods=['post'])
    def webSendMessage():
        if not localIP(request.environ, currentIP): return NO_ACCESS_STRING
        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'success': False, 'message':'Please forward json... requests.post(url, json={\"message\":\"this is my message\", \"bot\": \"local\"})'})
        success, msg = chat.addMessage(message)
        if success:
            return json.dumps({'type':'success', 'success': True})
        else:
            return json.dumps({'type':'error', 'success': False, 'message': msg})
    
    @app.route('/ScriptTalk', methods=['post'])
    def webScriptTalk():
        if not localIP(request.environ, currentIP): return NO_ACCESS_STRING
        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'success': False, 'message':'Please forward json... requests.post(url, json={\"module\":\"test.test_LSE\", \"data\": [\"example\", \"of\", \"data\"]})'})
        success, msg = extensions.scriptTalk(message)
        if success:
            return json.dumps({'type':'success', 'success': True})
        else:
            return json.dumps({'type':'error', 'success': False, 'message': msg})
    
    @app.route('/CrossTalk', methods=['post'])
    def webCrossTalk():
        if not localIP(request.environ, currentIP): return NO_ACCESS_STRING
        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'success': False, 'message':'Please forward json... requests.post(url, json={\"event\":\"p-example\", \"data\": [\"example\", \"of\", \"data\"]})'})
        success, msg = extensions.crossTalk(message)
        if success:
            return json.dumps({'type':'success', 'success': True})
        else:
            return json.dumps({'type':'error', 'success': False, 'message': msg})
        
    
    @app.route('/DeleteRegular', methods=['post'])
    def webDeleteRegular():
        if not localIP(request.environ, currentIP): return NO_ACCESS_STRING
        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'success': False, 'message':'Please forward json... requests.post(url, json={"user":"username_to_add"})'})
        if users.removeRegular(message):
            return json.dumps({'type':'error', 'success': False, 'message':'User not a regular'})
        else:
            return json.dumps({'type':'error', 'success': True})

    @app.route('/AddRegular', methods=['post'])
    def webAddRegular():
        if not localIP(request.environ, currentIP): return NO_ACCESS_STRING
        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'success': False, 'message':'Please forward json... requests.post(url, json={"user":"username_to_add"})'})
        if users.addRegular(message):
            return json.dumps({'type':'error', 'success': False, 'message':'Please forward json... requests.post(url, json={"user":"username_to_add"})'})
        else:
            return json.dumps({'type':'success', 'success': True})
    
    @app.route('/webhook/<destination>/<secret>', methods=['get', 'post'])
    def webWebhook(destination, secret):
        requestData = {'module': destination, 'secret': secret, 'request': {}}
        try:
            requestData['request']['postData'] = request.data.decode('UTF-8')
        except Exception:
            requestData['request']['postData'] = ''
        
        requestData['request']['args'] = request.args.to_dict()
        requestData['request']['headers'] = dict(request.headers)
        extensions.webHookHandles.append(requestData)
        return ''
    
    @sio.on('connect')
    def sioOnConnect(data=''):
        if not localIP(request.environ, currentIP): return False
    
    @sio.on('message')
    def sioOnConnect(data=''):
        if not localIP(request.environ, currentIP): return False
        print(data)

    @sio.on('ToggleExtension')
    def sioToggleExtension(data=''):
        if not localIP(request.environ, currentIP): return False
        if not isinstance(data, dict):
            sio.emit('ToggleExtension', json.dumps({'success': False}), room=request.sid)
            return
        if not 'module' in data or not isinstance(data['module'], str) or not 'active' in data or not isinstance(data['active'], bool):
            data['success'] = False
            sio.emit('ToggleExtension', json.dumps(data), room=request.sid)
            return
        extensions.toggle(data['module'], data['active'])
        data['success'] = True
        sio.emit('ToggleExtension', json.dumps(data), room=request.sid)
    
    @sio.on('SaveSettings')
    def sioSaveSettings(data=''):
        if not localIP(request.environ, currentIP): return False
        if not isinstance(data, dict):
            sio.emit('SaveSettings', json.dumps({'success': False}), room=request.sid)
            return
        if not 'name' in data or not isinstance(data['name'], str) or not 'index' in data or not isinstance(data['index'], int) or not 'settings' in data or not isinstance(data['settings'], dict):
            data['success'] = False
            sio.emit('SaveSettings', json.dumps(data), room=request.sid)
            return
        extensions.updateSettings(data['index'], data['name'], data['settings'])
        data['success'] = True
        sio.emit('SaveSettings', json.dumps(data), room=request.sid)
    
    @sio.on('ClearEvents')
    def sioClearEvents(data=''):
        if not localIP(request.environ, currentIP): return False
        SE.eventHistory.clear()
    
    @sio.on('ClearMessages')
    def sioClearEvents(data=''):
        if not localIP(request.environ, currentIP): return False
        chat.twitchMessagesHistory.clear()
    
    @sio.on('ClearLogs')
    def sioClearLogs(data=''):
        if not localIP(request.environ, currentIP): return False
        extensions.log.clear()
    
    @sio.on('AddRegular')
    def sioAddRegular(data=''):
        if not localIP(request.environ, currentIP): return False
        if not isinstance(data, str) or len(data) == 0:
            return
        users.addRegular(data)
        sio.emit('AddRegular', data, room=request.sid)
    
    @sio.on('DeleteRegular')
    def sioAddRegular(data=''):
        if not localIP(request.environ, currentIP): return False
        if not isinstance(data, str) or len(data) == 0:
            return
        users.removeRegular(data)
        sio.emit('DeleteRegular', data, room=request.sid)
    
    @sio.on('UpdateSettings')
    def sioUpdateSettings(data=''):
        if not localIP(request.environ, currentIP): return False
        if not isinstance(data, dict): return

        setTwitchData = False
        setSEData = False

        for key in data:
            if validateSetting(key, data[key]):
                settings[key] = data[key]
                if key in ['tmi', 'twitch_channel', 'tmi_twitch_username']: setTwitchData = True
                if key in ['jwt_token', 'user_id', 'SEListener']: setSEData = True
        
        if setTwitchData: chat.setTwitchData(tmi=settings['tmi'], tmi_username=settings['tmi_twitch_username'], twitch_channel=settings['twitch_channel'])
        
        if setSEData: SE.setData(jwt=settings['jwt_token'], method=settings['SEListener'])
        
        saveSettings(settings)
        sio.emit('UpdateSettings', data, room=request.sid)

    @sio.on('RestartTwitch')
    def sioRestartTwitch(data=''):
        if not localIP(request.environ, currentIP): return False
        state, cooldown = chat.startTwitch()
        sio.emit('RestartTwitch', {'state': state, 'cooldown': cooldown}, room=request.sid)

    @sio.on('RestartSE')
    def sioRestartSE(data=''):
        if not localIP(request.environ, currentIP): return False
        state, cooldown = SE.start()
        sio.emit('RestartSE', {'state': state, 'cooldown': cooldown}, room=request.sid)
    
    @sio.on('ResetExtensions')
    def sioResetExtensions(data=''):
        if not localIP(request.environ, currentIP): return False
        extensions.resetExtensions()
        sio.emit('ResetExtensions', room=request.sid)
    
    @sio.on('StreamElementsAPI')
    def sioStreamElementsAPI(data=''):
        if not localIP(request.environ, currentIP): return False
        
        success, msg = SE.APIRequest(data)

        if success:
            sio.emit('StreamElementsAPI', {'type':'success', 'success': True, 'response': msg}, room=request.sid)
        else:
            sio.emit('StreamElementsAPI', {'type':'error', 'success': False, 'message': msg}, room=request.sid)
    
    @sio.on('ScriptTalk')
    def sioScriptTalk(data=''):
        if not localIP(request.environ, currentIP): return False
        
        success, msg = extensions.scriptTalk(data)
        if success:
            sio.emit('ScriptTalk', {'type':'success', 'success': True}, room=request.sid)
        else:
            sio.emit('ScriptTalk', {'type':'error', 'success': False, 'message': msg}, room=request.sid)
    
    @sio.on('CrossTalk')
    def sioCrossTalk(data=''):
        if not localIP(request.environ, currentIP): return False

        success, msg = extensions.crossTalk(data)
        if success:
            sio.emit('CrossTalk', {'type':'success', 'success': True}, room=request.sid)
        else:
            sio.emit('CrossTalk', {'type':'error', 'success': False, 'message': msg}, room=request.sid)
    
    @sio.on('SendMessage')
    def sioSendMessage(data=''):
        if not localIP(request.environ, currentIP): return False
        success, msg = chat.addMessage(data)
        if success:
            sio.emit('SendMessage', {'type':'success', 'success': True}, room=request.sid)
        else:
            sio.emit('SendMessage', {'type':'error', 'success': False, 'message': msg}, room=request.sid)

    print('starting website: http://localhost:' + str(settings['server_port']) + ' (Saving website shortcut to website.html)')
    
    with open('website.html', 'w') as f: f.write('<script>window.location = "http://localhost:' + str(settings['server_port']) + '"</script>')
    
    urlJsPath = Path('dependencies/data/url.js')
    urlJsPath.parent.mkdir(parents=True, exist_ok=True)
    with open(urlJsPath, 'w') as f: f.write('var server_url = \"http://' + SERVER_IP + ':' + str(settings['server_port']) + '\";')
    
    sio.run(app, host='0.0.0.0', port=settings['server_port'])

if __name__ == '__main__':
    try: boot()
    except KeyboardInterrupt: pass