import requests, json, socket, re, os, importlib, threading, time, ctypes, sys, webbrowser, random, subprocess
import socketio as socket_io
from datetime import datetime
from flask import Flask, render_template, request
from flask_socketio import SocketIO

SoftwareVersion = 1

NewestVersion = json.loads(requests.get('https://raw.githubusercontent.com/Yazaar/StreamElements-Local-Cloudbot/master/LatestVersion.json').text)

logs = []
events = []
enabled = []
extensions = []

ExtensionHandles = []
EventHandles = []
TestEventHandles = []
ToggleHandles = []
CrossScriptTalkHandles = []

def WaitForYN():
    while True:
        temp = input().lower()
        if temp == 'y':
            return True
        elif temp == 'n':
            return False

def LoadExtensions():
    global extensions
    extensions = []
    for i in os.listdir("extensions"):
        temp = "extensions\\" + i
        if os.path.isdir(temp):
            for j in os.listdir(temp):
                if j[-7:] == "_LSE.py":
                    if i + "." + j[:-3] in enabled:
                        extensions.append({"state":True, "module":importlib.import_module("extensions." + i + "." + j[:-3])})
                    else:
                        extensions.append({"state":False, "module":importlib.import_module("extensions." + i + "." + j[:-3])})

def HandleExtensionError(item, e, action):
    logs.append({'module':item['module'].__name__.replace('extensions.', ''), 'message':str(e) + ' (' + action + ')'})
    item['state'] = False
    socketio.emit('log', logs[-1])

def extensionThread():
    while ChatThreadRuns == False:
        time.sleep(1)
    time.sleep(1)
    while True:
        if len(CrossScriptTalkHandles) > 0:
            ExecType = 'talk'
        elif len(ToggleHandles) > 0:
            ExecType = 'toggle'
        elif len(EventHandles) > 0:
            socketio.emit('StreamElementsEvent', EventHandles[0])
            ExecType = 'event'
        elif len(TestEventHandles) > 0:
            socketio.emit('StreamElementsTestEvent', TestEventHandles[0])
            ExecType = 'testevent'
        elif len(ExtensionHandles) > 0:
            ExecType = 'execute'
        else:
            ExecType = 'tick'
        for i in extensions:
            if ExecType == 'tick':
                if i['state'] and 'Tick' in dir(i['module']):
                    try:
                        i['module'].Tick()
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            elif ExecType == 'testevent':
                if i['state'] and 'TestEvent' in dir(i['module']):
                    try:
                        i['module'].TestEvent(TestEventHandles[0])
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            elif ExecType == 'execute':
                if i['state'] and 'Execute' in dir(i['module']):
                    try:
                        i['module'].Execute(ExtensionHandles[0])
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            elif ExecType == 'talk':
                if i['module'].__name__[11:] == CrossScriptTalkHandles[0]['module'] and i['state'] and 'CrossTalk' in dir(i['module']):
                    try:
                        i['module'].CrossTalk(CrossScriptTalkHandles[0]['data'])
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            elif ExecType == 'toggle':
                if i['module'].__name__ == ToggleHandles[0]['module'].__name__:
                    try:
                        i['module'].Toggle(ToggleHandles[0]['state'])
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            else:
                if i['state'] and 'Event' in dir(i['module']):
                    try:
                        i['module'].Event(EventHandles[0])
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
        
        if ExecType == 'event':
            EventHandles.pop(0)
        elif ExecType == 'execute':
            ExtensionHandles.pop(0)
        elif ExecType == 'testevent':
            TestEventHandles.pop(0)
        elif ExecType == 'talk':
            CrossScriptTalkHandles.pop(0)
        elif ExecType == 'toggle':
            ToggleHandles.pop(0)
        time.sleep(1/settings['executions_per_second'])

def handleAPIRequest(endpoint, options):
    if type(options) != dict:
        return 'Invalid options, have to be a dict'
    keys = options.keys()
    if not 'type' in keys:
        return 'Invalid options, options["type"] have to be included'
    if options['type'].lower() != 'delete' and options['type'].lower() != 'post' and options['type'].lower() != 'get' and options['type'].lower() != 'put':
        return 'options["type"] have to be delete, post, get or put'
    if not 'include_jwt' in keys:
        options['include_jwt'] = False
    
    if options['include_jwt'] == True:
        headers = {"Authorization": "Bearer " + settings['jwt_token']}
    else:
        headers = {}
    
    if 'headers' in keys:
        if type(options['headers']) != dict:
            return 'options["headers"] have to be a dict'
        
        for i in options['headers']:
            if i.lower() == 'authorization':
                return 'you are not allowed to specify the authorization header, set options["include_jwt"] to True'
            headers[i] = options['headers'][i]

    return requests.request(options['type'], 'https://api.streamelements.com/'+endpoint.replace(':channel', settings['user_id']), headers=headers).text

def processMessage(message):
    res = {"raw":message, "badges":{}}
    
    res["message"] = re.search(r"PRIVMSG #[^ ]* :(.*)", message).group(1)
    
    temp = re.search(r";badges=([^;]*)", message).group(1).split(",")
    if temp == ['']:
        res["badges"] = {}
    else:
        for i in temp:
            item = i.split("/")
            res["badges"][item[0]] = item[1]

    if re.search(r";mod=(\d)", message).group(1) == "1" or "broadcaster" in res["badges"].keys():
        res["moderator"] = True
    else:
        res["moderator"] = False
    
    if re.search(r";subscriber=(\d)", message).group(1) == "1" or "subscriber" in res["badges"].keys():
        res["subscriber"] = True
    else:
        res["subscriber"] = False
    
    if re.search(r";turbo=(\d)", message).group(1) == "1" or "turbo" in res["badges"].keys():
        res["turbo"] = True
    else:
        res["turbo"] = False
    
    res["name"] = re.search(r";display-name=([^;]*)", message).group(1)

    res["room"] = re.search(r";room-id=([^;]*)", message).group(1)

    res["id"] = re.search(r";id=([^;]*)", message).group(1)
    
    res["utc-timestamp"] = datetime.utcfromtimestamp(int(re.search(r";tmi-sent-ts=([^;]*)", message).group(1))/1000).strftime('%Y-%m-%d %H:%M:%S')
    res["emotes"] = {}

    temp = re.search(r";emotes=([^;]*)", message).group(1).split("/")
    if temp[0] != "":
        for i in temp:
            res["emotes"][i.split(":")[0]] = i.split(":")[1].split(",")
    return res

def chatThread():
    global s
    while True:
        try:
            socketio
            break
        except Exception:
            time.sleep(1)
    HOST = "irc.twitch.tv"
    PORT = 6667
    ReadBuffer = ""

    s = socket.socket()
    s.connect((HOST, PORT))
    s.send(b"PASS " + settings['tmi'].lower().encode("utf-8") + b"\r\n")
    s.send(b"NICK " + settings['tmi_twitch_username'].lower().encode("utf-8") + b"\r\n")
    s.send(b"JOIN #" + settings['twitch_channel'].lower().encode("utf-8") + b"\r\n")
    s.send(b"CAP REQ :twitch.tv/tags\r\n")

    Loading = True

    while Loading:
        ReadBuffer += s.recv(1024).decode("utf-8")
        temp = ReadBuffer.split("\n")
        ReadBuffer = temp.pop()

        for line in temp:
            if "End of /NAMES list" in line:
                print('Connected to twitch chat: ' + settings['twitch_channel'].lower())
                Loading = False
    global ChatThreadRuns
    ChatThreadRuns = True
    ReadBuffer = ""
    while True:
        ReadBuffer += s.recv(1024).decode("utf-8")
        temp = ReadBuffer.split("\n")
        ReadBuffer = temp.pop()

        for line in temp:
            if line == "PING :tmi.twitch.tv\r":
                s.send(b"PONG :tmi.twitch.tv\r\n")
                print("Sent: PONG :tmi.twitch.tv")
            elif "PRIVMSG #" in line:
                GeneratedMessage = processMessage(line[:-1])
                socketio.emit('TwitchMessage', GeneratedMessage)
                ExtensionHandles.append(GeneratedMessage)

def rebootExtensionsThread():
    global extensionThread
    for i in threading._active.items():
        if i[1].name == 'ExtensionThread':
            ctypes.pythonapi.PyThreadState_SetAsyncExc(i[0], ctypes.py_object(SystemExit))
    for i in extensions:
        if i['module'].__name__ in sys.modules:
            del sys.modules[i['module'].__name__]
    LoadExtensions()
    ExtensionVariable = threading.Thread(target=extensionThread, daemon=True, name='ExtensionThread')
    ExtensionVariable.start()

def StreamElementsThread():
    print('[StreamElements Socket] Loading python solution')
    while ChatThreadRuns == False:
        time.sleep(1)
    time.sleep(1)
    print('Connecting to StreamElements, waiting for response...')
    sio = socket_io.Client()
    def onConnect():
        print('Connected to StreamElements! Authenticating...')
        sio.emit('authenticate', { 'method': 'jwt', 'token': settings['jwt_token'] })
    sio.on('connect', onConnect)

    def onEvent(data):
        EventHandles.append(data)
        if len(events) > 99:
            events.pop(0)
        events.append(data)
    sio.on('event', onEvent)

    def onTestEvent(data):
        if len(events) > 99:
            events.pop(0)
        if 'latest' in data['listener']:
            events.append(data)
        TestEventHandles.append(data)
    sio.on('event:test', onTestEvent)

    def onDisconnect():
        print('Disconnected from StreamElements')
    sio.on('disconnect', onDisconnect)

    def onAuthenticated(data):
        print('Authenticated to StreamElements!')
    sio.on('authenticated', onAuthenticated)

    sio.connect('https://realtime.streamelements.com', transports=['websocket'])

def processExtensions():
    temp = []
    i = 0
    while i < len(extensions):
        temp.append({"state":extensions[i]["state"], "module":extensions[i]["module"].__name__.replace('extensions.', '')})
        i += 1
    return temp

def startFlask():
    f = open('dependencies\\data\\url.js', 'w')
    f.write('let server_url = "localhost:' + str(settings['server_port']) + '"')
    f.close()
    global socketio
    app = Flask(__name__, template_folder="dependencies\\web\\HTML", static_folder="dependencies\\web")
    socketio = SocketIO(app, async_mode='gevent')

    @app.route("/")
    def web_index():
        return render_template("index.html", data=processExtensions(), ExtensionLogs=logs, events=events, SetupValues=settings)
    
    @app.route("/StreamElementsAPI", methods=['post'])
    def web_StreamElementsAPI():
        message = json.loads(request.data.decode('UTF-8'))
        if type(message) != dict:
            return {'error':'The StreamElementsAPI socket endpoint requires a dict as input'}
        keys = message.keys()
        if not 'endpoint' in keys:
            return json.dumps({'error':'The dict have to include the key "endpoint"'})
        if not 'options' in keys:
            return json.dumps({'error':'The dict have to include the key "options"'})
        if type(message['endpoint']) != str:
            return json.dumps({'error:''The dict key "endpoint" have to be a string'})
        if type(message['options']) != dict:
            return json.dumps({'error':'The dict key "options" have to be a dict'})
        return json.dumps(handleAPIRequest(message['endpoint'], message['options']))

    @app.route('/CrossTalk', methods=['post'])
    def web_CrossTalk():
        message = json.loads(request.data.decode('UTF-8'))
        if type(message) != dict:
            return json.dumps({'error':'Please forward json... requests.post(url, json=JSON_DATA)'})
        keys = message.keys()
        if not 'event' in keys:
            return json.dumps({'error':'json require the key "event"'})
        if not 'data' in keys:
            return json.dumps({'error':'json require the key "data"'})
        if type(message['event']) != str:
            return json.dumps({'error':'The value for the key "event" has to be a string'})
        if not message['event'].startswith('p-'):
            return json.dumps({'error':'The value for the key "event" has to start with "p-", for example: p-example'})
        socketio.emit(message['event'], message['data'])
        return json.dumps({'success':'The event was sent over socket the!'})

    if settings['use_node'] == True:
        print('[StreamElements Socket] Loading node solution')
        c = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        secret = ''.join(random.choices(c, k=25))
        @socketio.on(secret+'-onEvent')
        def StreamElementsNode_onEvent(data):
            EventHandles.append(data)
            if len(events) > 99:
                events.pop(0)
            events.append(data)
        
        @socketio.on(secret+'-onTestEvent')
        def StreamElementsNode_onTestEvent(data):
            if len(events) > 99:
                events.pop(0)
            if 'latest' in data['listener']:
                events.append(data)
            TestEventHandles.append(data)
        subprocess.Popen('dependencies\\node\\StreamElementsListener.exe ' + str(settings['server_port']) + ' ' + settings['jwt_token'] + ' ' + secret)

    @socketio.on('ClearLogs')
    def websocket_ClearLogs():
        logs.clear()

    @socketio.on('ClearEvents')
    def websocket_ClearEvents():
        events.clear()
    
    @socketio.on('UpdateSettings')
    def websocket_UpdateSettings(data):
        for i in data.keys():
            if i in SettingsKeys:
                settings[i] = data[i]
        with open('dependencies\\data\\settings.json', 'w') as f:
            json.dump(settings, f)
        socketio.emit('UpdatedSettings')

    @socketio.on("message")
    def websocket_message(message):
        print(message)

    @socketio.on("StreamElementsAPI")
    def websocket_StreamElementsAPI(message):
        if type(message) != dict:
            socketio.emit('StreamElementsAPI', 'The StreamElementsAPI socket endpoint requires a dict as input')
            return
        keys = message.keys()
        if not 'endpoint' in keys:
            socketio.emit('StreamElementsAPI', 'The dict have to include the key "endpoint"')
            return
        if not 'options' in keys:
            socketio.emit('StreamElementsAPI', 'The dict have to include the key "options"')
            return
        if type(message['endpoint']) != str:
            socketio.emit('StreamElementsAPI', 'The dict key "endpoint" have to be a string')
            return
        if type(message['options']) != dict:
            socketio.emit('StreamElementsAPI', 'The dict key "options" have to be a dict')
            return
        socketio.emit('StreamElementsAPI', handleAPIRequest(message['endpoint'], message['options']))
        return

    @socketio.on('ReloadExtensions')
    def websocket_RebootExtensions():
        rebootExtensionsThread()
        socketio.emit('ReloadChange', {'type':'success', 'data':processExtensions()})

    @socketio.on('CrossTalk')
    def websocket_ForwardTo(message):
        CrossScriptTalkHandles.append(message)

    @socketio.on('toggle')
    def websocket_toggle(message):
        for i in extensions:
            if i['module'].__name__.replace('extensions.', '') == message['item']:
                if message['to'] == True:
                    i['state'] = True
                    if 'Toggle' in dir(i['module']):
                        ToggleHandles.append({'module':i['module'], 'state':True})
                    if not message['item'] in enabled:
                        enabled.append(message['item'])
                        with open('dependencies\\data\\enabled.json', 'w') as f:
                            json.dump(enabled, f)
                    socketio.emit("toggle", {"type":"success"})
                    return
                else:
                    i['state'] = False
                    if 'Toggle' in dir(i['module']):
                        ToggleHandles.append({'module':i['module'], 'state':False})
                    if message['item'] in enabled:
                        enabled.remove(message['item'])
                        with open('dependencies\\data\\enabled.json', 'w') as f:
                            json.dump(enabled, f)
                    socketio.emit("toggle", {"type":"success"})
                    return
        socketio.emit("toggle", {"type":"error"})

    print('starting website: http://localhost:' + str(settings['server_port']) + '\nSaving website shortcut to website.html!')
    with open('website.html', 'w') as f:
        f.write('<script>window.location = "http://localhost:' + str(settings['server_port']) + '"</script>')

    socketio.run(app, port=settings['server_port'], host='0.0.0.0')

if __name__ == '__main__':
    if NewestVersion['version'] > SoftwareVersion:
        print('\n\n\n\n\nNew version found!\nWould you like to update? (y/n)')
        if WaitForYN():
            subprocess.Popen('SoftwareUpdater.exe ' + NewestVersion['download'], creationflags=0x00000008, shell=True)
            raise SystemExit

    #load settings.json
    if os.path.isfile("dependencies\\data\\settings.json"):
        with open("dependencies\\data\\settings.json", "r") as f:
            try:
                settings = json.load(f)
                SettingsKeys = settings.keys()
                if len(SettingsKeys) == 8 and 'executions_per_second' in SettingsKeys and 'jwt_token' in SettingsKeys and 'user_id' in SettingsKeys and 'tmi' in SettingsKeys and 'twitch_channel' in SettingsKeys and 'tmi_twitch_username' in SettingsKeys and 'server_port' in SettingsKeys and 'use_node' in SettingsKeys:
                    pass
                else:
                    print('\n\n\n\n\nYour settings are invalid. Would you like to reset? (y/n)')
                    if WaitForYN():
                        with open("dependencies\\data\\settings.json", "w") as g:
                            g.write('{\n    "server_port":80,\n    "executions_per_second":60,\n    "jwt_token":"",\n    "user_id":"",\n    "tmi":"",\n    "twitch_channel":"",\n    "tmi_twitch_username":"",\n    "use_node":false\n}')
                    raise SystemExit
            except Exception:
                print('\n\n\n\n\nYour settings are invalid. Would you like to reset? (y/n)')
                if WaitForYN():
                    with open("dependencies\\data\\settings.json", "w") as g:
                        g.write('{\n    "server_port":80,\n    "executions_per_second":60,\n    "jwt_token":"",\n    "user_id":"",\n    "tmi":"",\n    "twitch_channel":"",\n    "tmi_twitch_username":"",\n    "use_node":false\n}')
                raise SystemExit

    if type(settings['server_port']) != int:
        print('\n\n\n\n\nserver_port have to be an int (ex: 123)\nHave to reset the port to proceed. Go? (y/n)')
        if WaitForYN():
            settings['server_port'] = 80
            with open('dependencies\\data\\settings.json', 'w') as f:
                json.dump(settings, f)
        else:
            raise SystemExit

    try:
        int(settings['executions_per_second'])
    except Exception:
        print('\n\n\n\n\nexecutions_per_second have to be a number (ex: 60, 30.5, 200)\nWould you like to open the setup tool? (y/n)')
        if WaitForYN():
            print('\n\n\n\n\nOkay, restart the software when you are done!')
            webbrowser.open('http://localhost:' + str(settings['server_port']))
            startFlask()
        else:
            raise SystemExit

    if type(settings['jwt_token']) != str:
        print('\n\n\n\n\njwt_token have to be a string (ex: "abcde", "123") Doublequotes required\nWould you like to open the setup tool? (y/n)')
        if WaitForYN():
            print('\n\n\n\n\nOkay, restart the software when you are done!')
            webbrowser.open('http://localhost:' + str(settings['server_port']))
            startFlask()
        else:
            raise SystemExit

    if type(settings['user_id']) != str:
        print('\n\n\n\n\nuser_id have to be a string (ex: "abcde", "123") Doublequotes required\nWould you like to open the setup tool? (y/n)')
        if WaitForYN():
            print('\n\n\n\n\nOkay, restart the software when you are done!')
            webbrowser.open('http://localhost:' + str(settings['server_port']))
            startFlask()
        else:
            raise SystemExit

    if type(settings['tmi']) != str:
        print('\n\n\n\n\ntmi have to be a string (ex: "oauth:abcdefgh") Doublequotes required\nWould you like to open the setup tool? (y/n)')
        if WaitForYN():
            print('\n\n\n\n\nOkay, restart the software when you are done!')
            webbrowser.open('http://localhost:' + str(settings['server_port']))
            startFlask()
        else:
            raise SystemExit

    if type(settings['twitch_channel']) != str:
        print('\n\n\n\n\ntwitch_channel have to be a string (ex: "abcde", "123") Doublequotes required\nWould you like to open the setup tool? (y/n)')
        if WaitForYN():
            print('\n\n\n\n\nOkay, restart the software when you are done!')
            webbrowser.open('http://localhost:' + str(settings['server_port']))
            startFlask()
        else:
            raise SystemExit

    if type(settings['tmi_twitch_username']) != str:
        print('\n\n\n\n\ntmi_twitch_username have to be a string (ex: "abcde", "123") Doublequotes required\nWould you like to open the setup tool? (y/n)')
        if WaitForYN():
            print('\n\n\n\n\nOkay, restart the software when you are done!')
            webbrowser.open('http://localhost:' + str(settings['server_port']))
            startFlask()
        else:
            raise SystemExit
    
    if type(settings['use_node']) != bool:
        settings['use_node'] = False
        with open('dependencies\\data\\settings.json', 'w') as f:
            json.dump(settings, f)

    if settings['jwt_token'] == '' or settings['user_id'] == '' or settings['tmi'] == '' or settings['twitch_channel'] == '' or settings['tmi_twitch_username'] == '':
        print('\n\n\n\n\nYour settings seems to be invalid. Would you like to set it up? (y/n)')
        if WaitForYN():
            print('\n\n\n\n\nOkay, restart the software when you are done!')
            webbrowser.open('http://localhost:' + str(settings['server_port']))
            startFlask()
        else:
            raise SystemExit

    # load enabled files
    if os.path.isfile("dependencies\\data\\enabled.json"):
        with open("dependencies\\data\\enabled.json", "r") as f:
            try:
                enabled = json.load(f)
                if type(enabled) != list:
                    with open("dependencies\\data\\enabled.json", "w") as g:
                        g.write(str([]))
                        g.close()
            except Exception:
                with open("dependencies\\data\\enabled.json", "w") as g:
                    g.write(str([]))
                    g.close()
    else:
        temp = open("dependencies\\data\\enabled.json", "w")
        temp.write(str([]))
        temp.close()

    LoadExtensions()

    ChatThreadRuns = False
    ExtensionVariable = threading.Thread(target=extensionThread, daemon=True, name='ExtensionThread')
    ExtensionVariable.start()

    ChatVariable = threading.Thread(target=chatThread, daemon=True)
    ChatVariable.start()

    if settings['use_node'] == False:
        StreamElementsActivity = threading.Thread(target=StreamElementsThread, daemon=True)
        StreamElementsActivity.start()

    startFlask()