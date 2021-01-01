import requests, json, socket, select, re, os, importlib, threading, time, ctypes, sys, webbrowser, random, subprocess, pathlib, zipfile, shutil, io
import socketio as socket_io
from datetime import datetime
from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO

class ExtensionCrossover:
    def __init__(self):
        self.__SendMessage = []
        self.__StreamElementsAPI = []
        self.__ScriptTalk = []
        self.__CrossTalk = []
        self.__DeleteRegulars = []
        self.__AddRegulars = []
    
    def SendMessage(self, data=None):
        '''
        Send a twitch message.
        argument: dict with the keys "bot" and "message"
        bot = "local"/"StreamElements" (depends on your bot target, local is recommended)
        message = Your message that you wish to send in twitch chat (str)

        returns a dict with the key "type", value = "error"/"success"
        returns a dict with the key "message" on error, value = error message
        '''
        if type(data) != dict:
            return {'type':'error', 'message':'The input have to be a dictionary'}
        keys = data.keys()
        if not 'message' in keys:
            return {'type':'error', 'message':'The dict have to include the key message'}
        if not 'bot' in keys:
            return {'type':'error', 'message':'The dict have to include the key bot with the value "local" or "streamelements"'}
        if data['bot'].lower() != 'streamelements' and data['bot'].lower() != 'local':
            return {'type':'error', 'message':'The dict have to include the key bot with the value local or streamelements'}
        
        if type(data['message']) != str:
            data['message'] = str(data['message'])

        self.__SendMessage.append(data)
        return {'type':'success'}

    def StreamElementsAPI(self, data=None):
        '''
        Send an API request to StreamElements servers.
        argument: dict with the keys "endpoint" (str) and "options" (dict)

        returns a dict with the key "type", value = "error"/"success"
        returns a dict with the key "message" on error, value = error message
        '''
        if type(data) != dict:
            return {'error':'The StreamElementsAPI endpoint requires a dict as input'}
        keys = data.keys()
        if not 'endpoint' in keys:
            return {'type':'error', 'message':'The dict have to include the key "endpoint"'}
        if not 'options' in keys:
            return {'type':'error', 'message':'The dict have to include the key "options"'}
        if type(data['endpoint']) != str:
            return {'type':'error', 'message':'The dict key "endpoint" have to be a string'}
        if type(data['options']) != dict:
            return {'type':'error', 'message':'The dict key "options" have to be a dict'}
        self.__StreamElementsAPI.append(data)
        return {'type':'success'}

    def ScriptTalk(self, data=None):
        '''
        Send data between python scripts.
        argument: dict with the keys "module" (str) and "data" (any)
        module = Your target, example: "example.test_LSE"
        data = Your data to forward over

        returns a dict with the key "type", value = "error"/"success"
        returns a dict with the key "message" on error, value = error message
        '''
        if type(data) != dict:
            return {'type':'error', 'message':'The input have to be a dict'}
        keys = data.keys()
        if not 'module' in keys:
            return {'type':'error', 'message':'No module found, please include the key module'}
        if not 'data' in keys:
            return {'type':'error', 'message':'No data found, please include the key data'}
        self.__ScriptTalk.append(data)
        return {'type':'success'}

    def CrossTalk(self, data=None):
        '''
        Send data to HTML/JavaScript.
        argument: dict with the keys "event" (str) and "data" (any)
        event = Your target, have to start with "p-", example: "p-MyTestEvent"
        data = Your data to forward over

        returns a dict with the key "type", value = "error"/"success"
        returns a dict with the key "message" on error, value = error message
        '''
        if type(data) != dict:
            return {'type':'error', 'message':'The input have to be a dict'}
        keys = data.keys()
        if not 'event' in keys:
            return {'type':'error', 'message':'json require the key "event"'}
        if not 'data' in keys:
            return {'type':'error', 'message':'json require the key "data"'}
        if type(data['event']) != str:
            return {'type':'error', 'message':'The value for the key "event" has to be a string'}
        if not data['event'].startswith('p-'):
            return {'type':'error', 'message':'The value for the key "event" has to start with "p-", for example: p-example'}
        self.__CrossTalk.append(data)
        return {'type':'success', 'message':'The event has been sent over socket!'}

    def DeleteRegular(self, data=None):
        '''
        Delete a regular.
        argument: username (string)

        returns a dict with the key "type", value = "error"/"success"
        returns a dict with the key "message" on error, value = error message
        '''
        if type(data) != str:
            return {'type':'error', 'message':'The input have to be a string'}
        
        self.__DeleteRegulars.append(data.lower())
        return {'type':'success', 'message':data.lower() + ' removed!'}
    
    def AddRegular(self, data=None):
        '''
        Add a regular.
        argument: username (string)

        returns a dict with the key "type", value = "error"/"success"
        returns a dict with the key "message" on error, value = error message
        '''
        if type(data) != str:
            return {'type':'error', 'message':'The input have to be a string'}
        
        self.__AddRegulars.append(data.lower())
        return {'type':'success', 'message':data.lower() + ' added!'}
        

    
    def GetValue(self, ValueType: str='all'):
        '''
        Only accessible from the main thread.
        Optional parameter: "streamelementsapi"/"sendmessage"/"crosstalk"/"scripttalk"/"all"
        Returns a dict with the keys "type" ("error") and "message" (error message) on error
        Returns a dict with the keys "type" ("success"), "data" (event handle), "event" (event type)
        '''

        if type(self.__StreamElementsAPI) != list:
            self.__StreamElementsAPI = []
        if type(self.__SendMessage) != list:
            self.__SendMessage = []
        if type(self.__CrossTalk) != list:
            self.__CrossTalk = []
        if type(self.__ScriptTalk) != list:
            self.__ScriptTalk = []
        if type(self.__AddRegulars) != list:
            self.__AddRegulars = []
        if type(self.__DeleteRegulars) != list:
            self.__DeleteRegulars = []

        if threading.current_thread().getName() != 'DataIn':
            return {'type':'error', 'message':'You are not allowed to execute this function'}
        
        LowerValueType = ValueType.lower()

        if LowerValueType != 'all' and LowerValueType != 'streamelementsapi' and LowerValueType != 'sendmessage' and LowerValueType != 'crosstalk' and LowerValueType != 'scripttalk':
            return {'type': 'error', 'message':'invalid input'}
        
        if len(self.__StreamElementsAPI) > 0 and (LowerValueType == 'all' or LowerValueType == 'streamelementsapi'):
            ReturnValue = self.__StreamElementsAPI[0].copy()
            self.__StreamElementsAPI.pop(0)
            return {'type':'success', 'data':ReturnValue, 'event':'StreamElementsAPI'}

        if len(self.__SendMessage) > 0 and (LowerValueType == 'all' or LowerValueType == 'sendmessage'):
            ReturnValue = self.__SendMessage[0].copy()
            self.__SendMessage.pop(0)
            return {'type':'success', 'data':ReturnValue, 'event':'SendMessage'}

        if len(self.__CrossTalk) > 0 and (LowerValueType == 'all' or LowerValueType == 'crosstalk'):
            ReturnValue = self.__CrossTalk[0].copy()
            self.__CrossTalk.pop(0)
            return {'type':'success', 'data':ReturnValue, 'event':'CrossTalk'}

        if len(self.__ScriptTalk) > 0 and (LowerValueType == 'all' or LowerValueType == 'scripttalk'):
            ReturnValue = self.__ScriptTalk[0].copy()
            self.__ScriptTalk.pop(0)
            return {'type':'success', 'data':ReturnValue, 'event':'ScriptTalk'}

        if len(self.__AddRegulars) > 0 and (LowerValueType == 'all' or LowerValueType == 'addregulars'):
            ReturnValue = self.__AddRegulars[0]
            self.__AddRegulars.pop(0)
            return {'type':'success', 'data':ReturnValue, 'event':'AddRegulars'}

        if len(self.__DeleteRegulars) > 0 and (LowerValueType == 'all' or LowerValueType == 'deleteregulars'):
            ReturnValue = self.__DeleteRegulars[0]
            self.__DeleteRegulars.pop(0)
            return {'type':'success', 'data':ReturnValue, 'event':'DeleteRegulars'}
        
        return {'type':'success', 'data':None, 'event':None}

def WaitForYN():
    while True:
        temp = input().lower()
        if temp == 'y':
            return True
        elif temp == 'n':
            return False

def downloadExeLauncher():
    try:
        content = requests.get('https://github.com/Yazaar/StreamElements-Local-Cloudbot/raw/master/source/SoftwareUpdater.exe')
    except Exception:
        print('Unable to download SoftwareUpdater.exe (Check again later or download manually from my github)\nhttps://github.com/Yazaar/StreamElements-Local-Cloudbot/blob/master/source/SoftwareUpdater.exe')
        input()
        raise SystemExit
    with open('SoftwareUpdater.exe', 'wb') as f:
        f.write(content.content)

def fetchUrl(url):
    try:
        response = requests.get(url)
    except Exception:
        return False
    
    if response.status_code != 200:
        return False

    return response.text

def validateIP(environ):
    try:
        if environ['HTTP_X_FORWARDED_FOR'] == currentIP:
            return False
    except Exception:
        if ':' in environ['HTTP_HOST']:
            environ['HTTP_HOST'] = environ['HTTP_HOST'].rsplit(':', 1)[0]
        if environ['HTTP_HOST'] == '127.0.0.1':
            return False
        elif environ['HTTP_HOST'] == 'localhost':
            return False
        elif re.search(r'^192\.168\.\d{1,3}\.\d{1,3}$', environ['HTTP_HOST']) != None:
            return False
        elif re.search(r'^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$', environ['HTTP_HOST']) != None:
            return False
        elif re.search(r'^172\.\d{1,2}\.\d{1,3}\.\d{1,3}$', environ['HTTP_HOST']) != None:
            temp = int(re.search(r'^172\.(\d{1,2})\.\d{1,3}\.\d{1,3}$', environ['HTTP_HOST']).group(1))
            if temp > 15 and temp < 32:
                return False
    return True

def LoadExtensions():
    global extensions, ExtensionSettings
    extensions = []
    ExtensionSettings = {}
    for i in os.listdir('extensions'):
        temp = pathlib.Path() / 'extensions' / i
        if os.path.isdir(temp):
            for j in os.listdir(temp):
                if j[-7:] == '_LSE.py':
                    if i + '.' + j[:-3] in enabled:
                        try:
                            extensions.append({'state':True, 'module':importlib.import_module('extensions.' + i + '.' + j[:-3])})
                        except Exception as e:
                            logs.append({'module':i, 'message':str(e) + ' (import)'})
                            try:
                                socketio.emit('log', logs[-1])
                            except Exception as e:
                                pass
                    else:
                        try:
                            extensions.append({'state':False, 'module':importlib.import_module('extensions.' + i + '.' + j[:-3])})
                        except Exception as e:
                            logs.append({'module':i, 'message':str(e) + ' (import)'})
                            try:
                                socketio.emit('log', logs[-1])
                            except Exception as e:
                                pass
                if j == 'SettingsUI.json':
                    with open(temp / 'SettingsUI.json', 'r') as f:
                        ui = json.load(f)
                        ExtensionSettings[ui['name']] = ui
                    if 'settings.json' in os.listdir(temp):
                        with open(temp / 'settings.json', 'r') as f:
                            ExtensionSettings[ui['name']]['current'] = json.load(f)
    InitializeHandles.append({'port':settings['server_port'], 'twitch_channel':settings['twitch_channel']})

def HandleExtensionError(item, e, action):
    logs.append({'module':item['module'].__name__.replace('extensions.', ''), 'message':str(e) + ' (' + action + ')'})
    item['state'] = False
    socketio.emit('log', logs[-1])

def extensionThread():
    while ChatThreadRuns == False:
        time.sleep(1)
    time.sleep(1)
    while True:
        if len(InitializeHandles) > 0:
            ExecType = 'initialize'
        elif len(UpdatedScriptsHandles) > 0:
            ExecType = 'newsettings'
        elif len(CrossScriptTalkHandles) > 0:
            ExecType = 'talk'
        elif len(WebhookHandles) > 0:
            ExecType = 'webhook'
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
            elif ExecType == 'initialize':
                if 'Initialize' in dir(i['module']):
                    try:
                        i['module'].Initialize(InitializeHandles[0].copy(), ExCrossover)
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            elif ExecType == 'talk':
                if i['module'].__name__[11:] == CrossScriptTalkHandles[0]['module'] and i['state'] and 'CrossTalk' in dir(i['module']):
                    try:
                        i['module'].CrossTalk(CrossScriptTalkHandles[0]['data'])
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            elif ExecType == 'webhook':
                if i['module'].__name__[11:] == WebhookHandles[0]['module'] and i['state'] and 'webhook' in dir(i['module']):
                    try:
                        i['module'].webhook(WebhookHandles[0])
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            elif ExecType == 'toggle':
                if i['module'].__name__ == ToggleHandles[0]['module'].__name__:
                    try:
                        i['module'].Toggle(ToggleHandles[0]['state'])
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            elif ExecType == 'newsettings':
                if i['module'].__name__ == UpdatedScriptsHandles[0]['module'] and 'NewSettings' in dir(i['module']):
                    try:
                        i['module'].NewSettings(UpdatedScriptsHandles[0]['settings'])
                    except Exception as e:
                        HandleExtensionError(i, e, ExecType)
            else:
                if i['state'] and 'Event' in dir(i['module']):
                    try:
                        i['module'].Event(EventHandles[0].copy())
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
        elif ExecType == 'initialize':
            InitializeHandles.pop(0)
        elif ExecType == 'newsettings':
            UpdatedScriptsHandles.pop(0)
        elif ExecType == 'webhook':
            WebhookHandles.pop(0)
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
        headers = {'Authorization': 'Bearer ' + settings['jwt_token']}
    else:
        headers = {}

    if 'headers' in keys:
        if type(options['headers']) != dict:
            return 'options["headers"] have to be a dict'
    
        for i in options['headers']:
            if i.lower() == 'authorization':
                return 'you are not allowed to specify the authorization header, set options["include_jwt"] to True'
            headers[i] = options['headers'][i]

    if 'json' in keys:
        if type(options['json']) != dict:
            return 'options["json"] have to be a dict'
        return requests.request(options['type'], 'https://api.streamelements.com/'+endpoint.replace(':channel', settings['user_id']), headers=headers, json=options['json']).text

    return requests.request(options['type'], 'https://api.streamelements.com/'+endpoint.replace(':channel', settings['user_id']), headers=headers).text

def processMessage(message):
    res = {'raw':message, 'badges':{}}
    
    res['message'] = re.search(r'PRIVMSG #[^ ]* :(.*)', message).group(1)
    
    temp = re.search(r';badges=([^;]*)', message).group(1).split(',')
    if temp == ['']:
        res['badges'] = {}
    else:
        for i in temp:
            item = i.split('/')
            res["badges"][item[0]] = item[1]

    if re.search(r';mod=(\d)', message).group(1) == '1' or 'broadcaster' in res['badges'].keys():
        res['moderator'] = True
    else:
        res['moderator'] = False
    
    if re.search(r';subscriber=(\d)', message).group(1) == '1' or 'subscriber' in res['badges'].keys():
        res['subscriber'] = True
    else:
        res['subscriber'] = False
    
    if re.search(r';turbo=(\d)', message).group(1) == '1' or 'turbo' in res['badges'].keys():
        res['turbo'] = True
    else:
        res['turbo'] = False
    
    
    res['name'] = re.search(r';display-name=([^;]*)', message).group(1)

    if res['name'].lower() in regulars:
        res['regular'] = True
    else:
        res['regular'] = False

    res['room'] = re.search(r';room-id=([^;]*)', message).group(1)

    res['id'] = re.search(r';id=([^;]*)', message).group(1)
    
    res['utc-timestamp'] = datetime.utcfromtimestamp(int(re.search(r';tmi-sent-ts=([^;]*)', message).group(1))/1000).strftime('%Y-%m-%d %H:%M:%S')
    res['emotes'] = {}

    temp = re.search(r';emotes=([^;]*)', message).group(1).split('/')
    if temp[0] != '':
        for i in temp:
            res['emotes'][i.split(':')[0]] = i.split(':')[1].split(',')
    return res

def chatThread():
    global s
    while True:
        try:
            socketio
            break
        except Exception:
            time.sleep(1)
    HOST = 'irc.twitch.tv'
    PORT = 6667
    ReadBuffer = ''

    s = socket.socket()
    s.connect((HOST, PORT))
    s.send(b'PASS ' + settings['tmi'].lower().encode('utf-8') + b'\r\n')
    s.send(b'NICK ' + settings['tmi_twitch_username'].lower().encode('utf-8') + b'\r\n')
    s.send(b'JOIN #' + settings['twitch_channel'].lower().encode('utf-8') + b'\r\n')
    s.send(b'CAP REQ :twitch.tv/tags\r\n')

    Loading = True
    sentPing = False

    while Loading:
        ReadBuffer += s.recv(1024).decode('utf-8')
        temp = ReadBuffer.split('\n')
        ReadBuffer = temp.pop()

        for line in temp:
            if 'End of /NAMES list' in line:
                print('Connected to twitch chat: ' + settings['twitch_channel'].lower())
                Loading = False
    global ChatThreadRuns
    ChatThreadRuns = True
    ReadBuffer = ''
    lastResponse = time.time()
    
    while True:
        if select.select([s], [], [], 5)[0]:
            lastResponse = time.time()
            sentPing = False
            ReadBuffer += s.recv(1024).decode('utf-8')
            temp = ReadBuffer.split('\n')
            ReadBuffer = temp.pop()
            for line in temp:
                if line == 'PING :tmi.twitch.tv\r':
                    s.send(b'PONG :tmi.twitch.tv\r\n')
                elif 'PRIVMSG #' in line:
                    GeneratedMessage = processMessage(line[:-1])
                    socketio.emit('TwitchMessage', GeneratedMessage)
                    ExtensionHandles.append(GeneratedMessage)
        elif sentPing == False and time.time() - lastResponse > 360:
            sentPing = True
        elif sentPing == True and time.time() - lastResponse > 390:
            s.close()
            sentPing = False
            s = socket.socket()
            s.connect((HOST, PORT))
            s.send(b'PASS ' + settings['tmi'].lower().encode('utf-8') + b'\r\n')
            s.send(b'NICK ' + settings['tmi_twitch_username'].lower().encode('utf-8') + b'\r\n')
            s.send(b'JOIN #' + settings['twitch_channel'].lower().encode('utf-8') + b'\r\n')
            s.send(b'CAP REQ :twitch.tv/tags\r\n')
            reconnecting = True
            ReadBuffer = ''
            while reconnecting:
                ReadBuffer += s.recv(1024).decode('utf-8')
                temp = ReadBuffer.split('\n')
                ReadBuffer = temp.pop()
                for line in temp:
                    if 'End of /NAMES list' in line:
                        reconnecting = False
                        break
            lastResponse = time.time()

def rebootExtensionsThread():
    global ExtensionVariable
    for i in threading._active.items():
        if i[1].name == 'ExtensionThread':
            ctypes.pythonapi.PyThreadState_SetAsyncExc(i[0], ctypes.py_object(SystemExit))
    for i in extensions:
        if i['module'].__name__ in sys.modules:
            del sys.modules[i['module'].__name__]
    LoadExtensions()
    ExtensionVariable = threading.Thread(target=extensionThread, daemon=True, name='ExtensionThread')
    ExtensionVariable.start()

def sendMessagesHandler():
    while ChatThreadRuns == False:
        time.sleep(1)
    time.sleep(1)
    while True:
        if len(MessagesToSend) > 0:
            if MessagesToSend[0]['bot'].lower() == 'local':
                s.send(('PRIVMSG #' + settings['twitch_channel'] + ' :' + MessagesToSend[0]['message'] + '\r\n').encode('UTF-8'))
                MessagesToSend.pop(0)
                time.sleep(0.4)
            else:
                requests.post('https://api.streamelements.com/kappa/v2/bot/' + settings['user_id'] + '/say', headers={'Content-Type':'application/json', 'Authorization': 'Bearer ' + settings['jwt_token']}, json={'message':MessagesToSend[0]['message']})
                MessagesToSend.pop(0)
                time.sleep(1.5)
        else:
            time.sleep(0.5)

def ExtensionDataThread():
    while True:
        temp = ExCrossover.GetValue('StreamElemenetsAPI')
        if temp['type'] != 'error' and temp['data'] != None:
            StreamElementsAPI(temp['data'])
        temp = ExCrossover.GetValue('SendMessage')
        if temp['type'] != 'error' and temp['data'] != None:
            SendMessage(temp['data'])
        temp = ExCrossover.GetValue('CrossTalk')
        if temp['type'] != 'error' and temp['data'] != None:
            CrossTalk(temp['data'])
        temp = ExCrossover.GetValue('ScriptTalk')
        if temp['type'] != 'error' and temp['data'] != None:
            ScriptTalk(temp['data'])
        temp = ExCrossover.GetValue('AddRegular')
        if temp['type'] != 'error' and temp['data'] != None:
            AddRegular(temp)
        temp = ExCrossover.GetValue('DeleteRegular')
        if temp['type'] != 'error' and temp['data'] != None:
            DeleteRegular(temp)
        time.sleep(2/(settings['executions_per_second']))

def StreamElementsAPI(message):
    if type(message) != dict:
        return json.dumps({'error':'The StreamElementsAPI socket endpoint requires a dict as input'})
    keys = message.keys()
    if not 'endpoint' in keys:
        return json.dumps({'type':'error', 'message':'The dict have to include the key "endpoint"'})
    if not 'options' in keys:
        return json.dumps({'type':'error', 'message':'The dict have to include the key "options"'})
    if type(message['endpoint']) != str:
        return json.dumps({'type':'error', 'message':'The dict key "endpoint" have to be a string'})
    if type(message['options']) != dict:
        return json.dumps({'type':'error', 'message':'The dict key "options" have to be a dict'})
    return handleAPIRequest(message['endpoint'], message['options'])

def SendMessage(message):
    if type(message) != dict:
        return json.dumps({'type':'error', 'message':'The input have to be a dictionary'})
    keys = message.keys()
    if not 'message' in keys:
        return json.dumps({'type':'error', 'message':'The dict have to include the key message'})
    if not 'bot' in keys:
        return json.dumps({'type':'error', 'message':'The dict have to include the key bot with the value "local" or "streamelements"'})
    if message['bot'].lower() != 'streamelements' and message['bot'].lower() != 'local':
        return json.dumps({'type':'error', 'message':'The dict have to include the key bot with the value local or streamelements'})
    
    if type(message['message']) != str:
        message['message'] = str(message['message'])

    MessagesToSend.append(message)
    return json.dumps({'type':'success'})

def ScriptTalk(message):
    if type(message) != dict:
        return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json=JSON_DATA)'})
    keys = message.keys()
    if not 'module' in keys:
        return json.dumps({'type':'error', 'message':'No module found, please include the key module'})
    if not 'data' in keys:
        return json.dumps({'type':'error', 'message':'No data found, please include the key data'})
    CrossScriptTalkHandles.append(message)
    return json.dumps({'type':'success'})

def AddRegular(user):
    if user in regulars:
        return
    
    regulars.append(user)
    with open(pathlib.Path('dependencies/data/regulars.json'), 'w') as f:
        json.dump(regulars, f)
def DeleteRegular(user):
    if not user in regulars:
        return
    
    regulars.remove(user)
    with open(pathlib.Path('dependencies/data/regulars.json'), 'w') as f:
        json.dump(regulars, f)

def CrossTalk(message):
    if type(message) != dict:
        return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json=JSON_DATA)'})
    keys = message.keys()
    if not 'event' in keys:
        return json.dumps({'type':'error', 'message':'json require the key "event"'})
    if not 'data' in keys:
        return json.dumps({'type':'error', 'message':'json require the key "data"'})
    if type(message['event']) != str:
        return json.dumps({'type':'error', 'message':'The value for the key "event" has to be a string'})
    if not message['event'].startswith('p-'):
        return json.dumps({'type':'error', 'message':'The value for the key "event" has to start with "p-", for example: p-example'})
    socketio.emit(message['event'], message['data'])
    return json.dumps({'type':'success', 'message':'The event has been sent over socket!'})

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
        temp.append({'state':extensions[i]['state'], 'module':extensions[i]['module'].__name__.replace('extensions.', '')})
        i += 1
    return temp

def updateLSE(url):
    data = requests.get(url)

    with zipfile.ZipFile(io.BytesIO(data.content)) as f:
        f.extractall()

def startFlask():
    global socketio
    IP = socket.gethostbyname(socket.gethostname())
    f = open(pathlib.Path('dependencies/data/url.js'), 'w')
    f.write('var server_url = "http://' + IP + ':' + str(settings['server_port']) + '";')
    f.close()
    app = Flask(__name__, template_folder='dependencies/web/HTML', static_folder='dependencies/web/static')
    socketio = SocketIO(app, async_mode='gevent')

    @app.route('/')
    def web_index():
        if validateIP(request.environ) == True:
            return '<h1>Access denied</h1><p>You are not allowed to enter this area</p>'
        return render_template('index.html', data=processExtensions(), ExtensionLogs=logs, events=events, SetupValues=settings, ExtensionSettings=ExtensionSettings, regulars=regulars)
    
    @app.route('/<path:path>')
    def web_CustomPath(path):
        if validateIP(request.environ) == True:
            return '<h1>Access denied</h1><p>You are not allowed to enter this area</p>'

        if not os.path.isfile(path):
            return 'invalid path, have to target a file...'
        try:
            with open(path) as f:
                fileData = f.read()
            return fileData
        except Exception:
            return send_file(path, mimetype='image/gif')

    @app.route('/StreamElementsAPI', methods=['post'])
    def web_StreamElementsAPI():
        if validateIP(request.environ) == True:
            return '<h1>Access denied</h1><p>You are not allowed to enter this area</p>'

        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json=JSON_DATA)'})
        return StreamElementsAPI(message)
    
    @app.route('/SendMessage', methods=['post'])
    def web_SendMessage():
        if validateIP(request.environ) == True:
            return '<h1>Access denied</h1><p>You are not allowed to enter this area</p>'
        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json=JSON_DATA)'})
        return SendMessage(message)

    @app.route('/ScriptTalk', methods=['post'])
    def web_ScriptTalk():
        if validateIP(request.environ) == True:
            return '<h1>Access denied</h1><p>You are not allowed to enter this area</p>'
        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json=JSON_DATA)'})

        if type(message) != dict:
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json=JSON_DATA)'})
        keys = message.keys()
        if not 'module' in keys:
            return json.dumps({'type':'error', 'message':'No module found, please include the key module'})
        if not 'data' in keys:
            return json.dumps({'type':'error', 'message':'No data found, please include the key data'})
        CrossScriptTalkHandles.append(message)
        return json.dumps({'type':'success'})

    @app.route('/CrossTalk', methods=['post'])
    def web_CrossTalk():
        if validateIP(request.environ) == True:
            return '<h1>Access denied</h1><p>You are not allowed to enter this area</p>'

        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json=JSON_DATA)'})

        if type(message) != dict:
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json=JSON_DATA)'})
        keys = message.keys()
        if not 'event' in keys:
            return json.dumps({'type':'error', 'message':'json require the key "event"'})
        if not 'data' in keys:
            return json.dumps({'type':'error', 'message':'json require the key "data"'})
        if type(message['event']) != str:
            return json.dumps({'type':'error', 'message':'The value for the key "event" has to be a string'})
        if not message['event'].startswith('p-'):
            return json.dumps({'type':'error', 'message':'The value for the key "event" has to start with "p-", for example: p-example'})
        socketio.emit(message['event'], message['data'])
        return json.dumps({'type':'success', 'message':'The event was sent over socket!'})

    @app.route('/DeleteRegular', methods=['post'])
    def web_DeleteRegular():
        if validateIP(request.environ) == True:
            return '<h1>Access denied</h1><p>You are not allowed to enter this area</p>'

        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json={"user":"username_to_add"})'})
        if not 'user' in message.keys():
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json={"user":"username_to_add"})'})
        if not message['user'].lower() in regulars:
            return json.dumps({'type':'error', 'message':'User not a regular'})
        regulars.remove(message['user'].lower())
        with open(pathlib.Path('dependencies/data/regulars.json')) as f:
            json.dump(regulars, f)
        return json.dumps({'type':'success', 'message':'User has been deleted as a regular'})

    @app.route('/AddRegular', methods=['post'])
    def web_AddRegular():
        if validateIP(request.environ) == True:
            return '<h1>Access denied</h1><p>You are not allowed to enter this area</p>'

        try:
            message = json.loads(request.data.decode('UTF-8'))
        except Exception:
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json={"user":"username_to_add"})'})
        if not 'user' in message.keys():
            return json.dumps({'type':'error', 'message':'Please forward json... requests.post(url, json={"user":"username_to_add"})'})
        if type(message['user']) != str:
            message['user'] = str(message['user'])
        if message['user'].lower() in regulars:
            return json.dumps({'type':'error', 'message':'User already a regular'})
        regulars.append(message['user'].lower())
        with open(pathlib.Path('dependencies/data/regulars.json')) as f:
            json.dump(regulars, f)
        return json.dumps({'type':'success', 'message':'User has been added as a regular'})
    
    @app.route('/webhook/<destination>/<secret>', methods=['get', 'post'])
    def web_webhook(destination, secret):
        requestData = {'module': destination, 'secret': secret, 'request': {}}
        try:
            requestData['request']['postData'] = request.data.decode('UTF-8')
        except Exception:
            requestData['request']['postData'] = ''
        
        requestData['request']['args'] = dict(request.args)
        requestData['request']['headers'] = dict(request.headers)
        WebhookHandles.append(requestData)
        return ''

    if settings['use_node'] == True:
        if settings['jwt_token'] != '*' and settings['user_id'] != '*':
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
        else:
            print('StreamElements: Disabled')

    @socketio.on('ClearLogs')
    def websocket_ClearLogs(data=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        logs.clear()

    @socketio.on('ClearEvents')
    def websocket_ClearEvents(data=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return
        events.clear()
    
    @socketio.on('UpdateSettings')
    def websocket_UpdateSettings(data=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        for i in data.keys():
            if i in SettingsKeys:
                settings[i] = data[i]
        with open(pathlib.Path('dependencies/data/settings.json'), 'w') as f:
            json.dump(settings, f)
        socketio.emit('UpdatedSettings', room=request.sid)
    
    @socketio.on('ScriptSettings')
    def websocket_ScriptSettings(data=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        if type(data) != dict:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'You have to forward data in form of a dict'}, room=request.sid)
            return
        keys = data.keys()
        if not 'path' in keys:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'The dict have to include the key path'}, room=request.sid)
            return
        if not 'settings' in keys:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'The dict have to include the key settings'}, room=request.sid)
            return
        if not 'name' in keys:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'The dict have to include the key name'}, room=request.sid)
            return
        if type(data['settings']) != dict:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'The key settings requires a dict as a value'}, room=request.sid)
            return
        if not os.path.isdir(data['path']):
            socketio.emit('ScriptSettings', {'type':'error', 'message':'The key path does not point on a valid directory'}, room=request.sid)
            return
        keys = data['settings'].keys()
        jsfile = pathlib.Path(data['path']) / 'settings.js'
        if os.path.isfile(jsfile):
            with open(jsfile, 'r') as f:
                JSScriptData = f.read()
            JSScriptData = json.loads(JSScriptData[15:][:-1])
            for i in keys:
                JSScriptData[i] = data['settings'][i]
            with open(jsfile, 'w') as f:
                f.write('var settings = ' + json.dumps(JSScriptData) + ';')
        else:
            JSScriptData = data['settings']
            with open(jsfile, 'w') as f:
                f.write('var settings = ' + json.dumps(data['settings']) + ';')

        jsonfile = pathlib.Path(data['path']) / 'settings.json'
        if os.path.isfile(jsonfile):
            with open(jsonfile, 'r') as f:
                PyScriptData = json.load(f)
            for i in keys:
                PyScriptData[i] = data['settings'][i]
            with open(jsonfile, 'w') as f:
                json.dump(PyScriptData, f)
        else:
            PyScriptData = data['settings']
            with open(jsonfile, 'w') as f:
                json.dump(data['settings'], f)
        
        ExtensionSettings[data['name']]['current'] = json.loads(json.dumps(PyScriptData))
        
        if 'event' in data.keys():
            if type(data['event']) == str:
                if data['event'].startswith('p-'):
                    socketio.emit(data['event'], JSScriptData)
        
        if 'scripts' in data.keys():
            if type(data['scripts']) == list:
                for i in data['scripts']:
                    if type(i) == str:
                        UpdatedScriptsHandles.append({'module':'extensions.'+i, 'settings':PyScriptData})
        
        socketio.emit('ScriptSettings', {'type':'success'}, room=request.sid)

    @socketio.on('message')
    def websocket_message(message=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        print(message)

    @socketio.on('AddRegular')
    def websocket_AddRegular(message=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        if type(message) != str:
            user = str(message).lower()
        else:
            user = message.lower()
        if user in regulars:
            socketio.emit('AddRegular', {'type':'error', 'message':'User already a regular'}, room=request.sid)
            return
        regulars.append(user)
        with open(pathlib.Path('dependencies/data/regulars.json'), 'w') as f:
            json.dump(regulars, f)
        socketio.emit('AddRegular', {'type':'success', 'message':'User has been added as a regular'}, room=request.sid)
        return
        

    @socketio.on('DeleteRegular')
    def websocket_DeleteRegular(message=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        if type(message) != str:
            user = str(message).lower()
        else:
            user = message.lower()
        if not user in regulars:
            socketio.emit('AddRegular', {'type':'error', 'message':'User not a regular'}, room=request.sid)
            return
        regulars.remove(user)
        with open(pathlib.Path('dependencies/data/regulars.json'), 'w') as f:
            json.dump(regulars, f)
        socketio.emit('AddRegular', {'type':'success', 'message':'User has been deleted as a regular'}, room=request.sid)
        return

    @socketio.on('StreamElementsAPI')
    def websocket_StreamElementsAPI(message=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        if type(message) != dict:
            socketio.emit('StreamElementsAPI', {'type':'error', 'message':'The StreamElementsAPI socket endpoint requires a dict as input'}, room=request.sid)
            return
        keys = message.keys()
        if not 'endpoint' in keys:
            socketio.emit('StreamElementsAPI', {'type':'error', 'message':'The dict have to include the key "endpoint"'}, room=request.sid)
            return
        if not 'options' in keys:
            socketio.emit('StreamElementsAPI', {'type':'error', 'message':'The dict have to include the key "options"'}, room=request.sid)
            return
        if type(message['endpoint']) != str:
            socketio.emit('StreamElementsAPI', {'type':'error', 'message':'The dict key "endpoint" have to be a string'}, room=request.sid)
            return
        if type(message['options']) != dict:
            socketio.emit('StreamElementsAPI', {'type':'error', 'message':'The dict key "options" have to be a dict'}, room=request.sid)
            return
        socketio.emit('StreamElementsAPI', handleAPIRequest(message['endpoint'], message['options']), room=request.sid)
        return

    @socketio.on('ReloadExtensions')
    def websocket_RebootExtensions(data=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        rebootExtensionsThread()
        socketio.emit('ReloadChange', {'type':'success', 'data':processExtensions()}, room=request.sid)

    @socketio.on('ScriptTalk')
    def websocket_ScriptTalk(message=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        if type(message) != dict:
            socketio.emit('ScriptTalk', {'type':'error', 'message':'The data argument have to be a dict'}, room=request.sid)
            return
        keys = message.keys()
        if not 'event' in keys:
            socketio.emit('ScriptTalk', {'type':'error', 'message':'No event found, please include the key event'}, room=request.sid)
            return
        if not 'data' in keys:
            socketio.emit('ScriptTalk', {'type':'error', 'message':'No data found, please include the key data'}, room=request.sid)
            return
        if not message['event'].startswith('p-'):
            socketio.emit('ScriptTalk', {'type':'error', 'message':'The event have to start with p-'}, room=request.sid)
            return
        socketio.emit(message['event'], message['data'], broadcast=True)

    @socketio.on('CrossTalk')
    def websocket_CrossTalk(message=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        if type(message) != dict:
            socketio.emit('CrossTalk', {'type':'error', 'message':'The data argument have to be a dict'}, room=request.sid)
            return
        keys = message.keys()
        if not 'module' in keys:
            socketio.emit('CrossTalk', {'type':'error', 'message':'No module found, please include the key module'}, room=request.sid)
            return
        if not 'data' in keys:
            socketio.emit('CrossTalk', {'type':'error', 'message':'No data found, please include the key data'}, room=request.sid)
            return
        CrossScriptTalkHandles.append(message)
        socketio.emit('CrossTalk', {'type':'success'}, room=request.sid)
    
    @socketio.on('SendMessage')
    def websocket_SendMessage(message=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        if type(message) != dict:
            socketio.emit('SendMessage', {'type':'error', 'message':'The data that you send have to be in form of a dict.'}, room=request.sid)
            return
        keys = message.keys()
        if not 'bot' in keys:
            socketio.emit('SendMessage', {'type':'error', 'message':'The dict have to include the key bot with the value local or streamelements'}, room=request.sid)
            return
        if message['bot'].lower() != 'streamelements' and message['bot'].lower() != 'local':
            socketio.emit('SendMessage', {'type':'error', 'message':'The dict have to include the key bot with the value local or streamelements'}, room=request.sid)
            return
        if not 'message' in keys:
            socketio.emit('SendMessage', {'type':'error', 'message':'The dict have to include the key message with the value of your message to send'}, room=request.sid)
            return
        if type(message['message']) != str:
            MessagesToSend.append({'bot':message['bot'], 'message':str(message['message'])})
        else:
            MessagesToSend.append(message)
        socketio.emit('SendMessage', {'type':'success'}, room=request.sid)

    @socketio.on('toggle')
    def websocket_toggle(message=''):
        if validateIP(request.environ) == True:
            socketio.emit('ScriptSettings', {'type':'error', 'message':'Access denied!'}, room=request.sid)
            return

        for i in extensions:
            if i['module'].__name__.replace('extensions.', '') == message['item']:
                if message['to'] == True:
                    i['state'] = True
                    if 'Toggle' in dir(i['module']):
                        ToggleHandles.append({'module':i['module'], 'state':True})
                    if not message['item'] in enabled:
                        enabled.append(message['item'])
                        with open(pathlib.Path('dependencies/data/enabled.json'), 'w') as f:
                            json.dump(enabled, f)
                    socketio.emit('toggle', {'type':'success'}, room=request.sid)
                    return
                else:
                    i['state'] = False
                    if 'Toggle' in dir(i['module']):
                        ToggleHandles.append({'module':i['module'], 'state':False})
                    if message['item'] in enabled:
                        enabled.remove(message['item'])
                        with open(pathlib.Path('dependencies/data/enabled.json'), 'w') as f:
                            json.dump(enabled, f)
                    socketio.emit('toggle', {'type':'success'}, room=request.sid)
                    return
        socketio.emit('toggle', {'type':'error'}, room=request.sid)

    print('starting website: http://localhost:' + str(settings['server_port']) + '\nSaving website shortcut to website.html!')
    with open('website.html', 'w') as f:
        f.write('<script>window.location = "http://localhost:' + str(settings['server_port']) + '"</script>')

    socketio.run(app, port=settings['server_port'], host='0.0.0.0')

def deleteOldFiles():
    deleted = False
    deletedDirs = [pathlib.Path('dependencies/web/styles'), pathlib.Path('dependencies/web/scripts')]
    for deletedDir in deletedDirs:
        if deletedDir.is_dir():
            if deleted == False:
                print('Deleting old depencency directories...')
            deleted = True
            shutil.rmtree(deletedDir)

def main(launcher = 'py'):
    global logs, events, enabled, extensions, ExtensionSettings, ExtensionHandles, EventHandles, TestEventHandles, ToggleHandles, CrossScriptTalkHandles, InitializeHandles, UpdatedScriptsHandles, MessagesToSend, settings, ChatThreadRuns, SettingsKeys, ExCrossover, regulars, currentIP, WebhookHandles
    
    print('Loading...')
    
    os.chdir(pathlib.Path(__file__).parent)

    if not os.getcwd() in sys.path:
        sys.path.append(pathlib.Path(__file__).parent)
    
    deleteOldFiles()

    SoftwareVersion = 24

    NewestVersion = fetchUrl('https://raw.githubusercontent.com/Yazaar/StreamElements-Local-Cloudbot/master/LatestVersion.json')

    if NewestVersion == False:
        print('[ERROR]: Unable to check for updates, no network connection?')
        NewestVersion = {'version': SoftwareVersion, 'download': '', 'log': ''}
    else:
        NewestVersion = json.loads(NewestVersion)
    
    currentIP = fetchUrl('https://ident.me')
    if currentIP == False:
        currentIP = fetchUrl('https://api.ipify.org')
        if currentIP == False:
            print('[ERROR]: Unable to check for your public IP, no network connection?')

    logs = []
    events = []
    enabled = []
    extensions = []
    ExtensionSettings = {}

    ExtensionHandles = []
    EventHandles = []
    TestEventHandles = []
    ToggleHandles = []
    CrossScriptTalkHandles = []
    WebhookHandles = []
    InitializeHandles = []
    UpdatedScriptsHandles = []
    MessagesToSend = []

    if NewestVersion['version'] > SoftwareVersion:
        print('\n\n\n\n\nNew version found!')
        print('\n\nChanges:')
        print(NewestVersion['log'])
        print('\n\nWould you like to update? (y/n)')
        if WaitForYN():
            updateLSE(NewestVersion['download'])
            raise SystemExit

    if not os.path.isdir(pathlib.Path('dependencies/data')):
        os.makedirs(pathlib.Path('dependencies/data'))
    
    #load settings.json
    if os.path.isfile(pathlib.Path('dependencies/data/settings.json')):
        with open(pathlib.Path('dependencies/data/settings.json'), 'r') as f:
            try:
                settings = json.load(f)
                SettingsKeys = settings.keys()
                if len(SettingsKeys) == 8 and 'executions_per_second' in SettingsKeys and 'jwt_token' in SettingsKeys and 'user_id' in SettingsKeys and 'tmi' in SettingsKeys and 'twitch_channel' in SettingsKeys and 'tmi_twitch_username' in SettingsKeys and 'server_port' in SettingsKeys and 'use_node' in SettingsKeys:
                    pass
                else:
                    print('\n\n\n\n\nYour settings are invalid. Would you like to reset? (y/n)')
                    if WaitForYN():
                        with open(pathlib.Path('dependencies/data/settings.json'), 'w') as g:
                            g.write('{\n    "server_port":80,\n    "executions_per_second":60,\n    "jwt_token":"",\n    "user_id":"",\n    "tmi":"",\n    "twitch_channel":"",\n    "tmi_twitch_username":"",\n    "use_node":false\n}')
                    raise SystemExit
            except Exception:
                print('\n\n\n\n\nYour settings are invalid. Would you like to reset? (y/n)')
                if WaitForYN():
                    with open(pathlib.Path('dependencies/data/settings.json'), 'w') as g:
                        g.write('{\n    "server_port":80,\n    "executions_per_second":60,\n    "jwt_token":"",\n    "user_id":"",\n    "tmi":"",\n    "twitch_channel":"",\n    "tmi_twitch_username":"",\n    "use_node":false\n}')
                raise SystemExit
    
    #load regulars.json
    if not os.path.isfile(pathlib.Path('dependencies/data/regulars.json')):
        with open(pathlib.Path('dependencies/data/regulars.json'), 'w') as f:
            f.write('[]')
        regulars = []
    else:
        with open(pathlib.Path('dependencies/data/regulars.json'), 'r') as f:
            try:
                regulars = json.load(f)
            except Exception:
                f.close()
                temp = 0
                while os.path.isfile(pathlib.Path('dependencies/data') / ('regulars' + str(temp) + '.json')):
                    temp += 1
                os.rename(pathlib.Path('dependencies/data/regulars.json'), pathlib.Path('dependencies/data') / ('regulars' + str(temp) + '.json'))
                print('Whoops, dependencies/data/regulars.json seems to be invalid. Generating new file (old file has been renamed to ' + 'regulars' + str(temp) + '.json' + ')')
                temp = 0
                time.sleep(5)
                with open(pathlib.Path('dependencies/data/regulars.json'), 'w') as f:
                    f.write('[]')
                regulars = []


    if type(settings['server_port']) != int:
        print('\n\n\n\n\nserver_port have to be an int (ex: 123)\nHave to reset the port to proceed. Go? (y/n)')
        if WaitForYN():
            settings['server_port'] = 80
            with open(pathlib.Path('dependencies/data/settings.json'), 'w') as f:
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
        with open(pathlib.Path('dependencies/data/settings.json'), 'w') as f:
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
    jsonfile = pathlib.Path('dependencies/data/enabled.json')
    if os.path.isfile(jsonfile):
        with open(jsonfile, 'r') as f:
            try:
                enabled = json.load(f)
                if type(enabled) != list:
                    with open(jsonfile, 'w') as g:
                        g.write(str([]))
                        g.close()
            except Exception:
                with open(jsonfile, 'w') as g:
                    g.write(str([]))
                    g.close()
    else:
        temp = open(jsonfile, 'w')
        temp.write(str([]))
        temp.close()

    ExCrossover = ExtensionCrossover()
    
    LoadExtensions()

    ChatThreadRuns = False
    ExtensionVariable = threading.Thread(target=extensionThread, daemon=True, name='ExtensionThread')
    ExtensionVariable.start()
        
    if settings['tmi'] != '*' and settings['tmi_twitch_username'] != '*' and settings['twitch_channel'] != '*':
        sendMessageThread = threading.Thread(target=sendMessagesHandler, daemon=True, name='ChatOut')
        sendMessageThread.start()

        ChatVariable = threading.Thread(target=chatThread, daemon=True, name='ChatIn')
        ChatVariable.start()
    else:
        print('Twitch chat: Disabled')
        ChatThreadRuns = True

    ExtensionDataVariable = threading.Thread(target=ExtensionDataThread, daemon=True, name='DataIn')
    ExtensionDataVariable.start()

    if settings['use_node'] == False:
        if settings['user_id'] != '*' and settings['jwt_token'] != '*':    
            StreamElementsActivity = threading.Thread(target=StreamElementsThread, daemon=True)
            StreamElementsActivity.start()
        else:
            print('StreamElements: Disabled')

    startFlask()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass