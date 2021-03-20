import socketio, threading, time, websocket, ssl, json, requests, asyncio

class StreamElements:
    def __init__(self, sio, appContext):
        self.__sio = sio
        self.__appContext = appContext

        self.__method = 2
        self.__connectedMethod = None

        self.__events = []
        self.__testEvents = []
        self.eventHistory = []
        self.__jwt = ''
        self.__connectedJwt = ''
        self.__validJwt = ''
        self.__userId = ''
        self.__cooldown = None
        self.__threadId = 0

        self.__SESIO = socketio.Client()

        self.__SESIO.on('connect', self.__onConnect)
        self.__SESIO.on('authenticated', self.__onAuthenticated)
        self.__SESIO.on('event', self.__onEvent)
        self.__SESIO.on('event:test', self.__onTestEvent)
        self.__SESIO.on('disconnect', self.__onDisconnect)

        self.__ws = None
        self.__wsRunning = False
        self.__wsBuffer = []
        self.__wsPingInterval = 20
        self.__wsPingTimeout = 10
        self.__wsTimer = time.time()
        self.__sentPing = False

        threading.Thread(target=self.__BGTask).start()

    def canSendMessages(self):
        return self.__validJwt != '' and self.__userId != ''

    def sendMessage(self, message):
        if not self.canSendMessages(): return False
        if not isinstance(message, str): return False
        x = requests.post('https://api.streamelements.com/kappa/v2/bot/' + self.__userId + '/say', headers={'Content-Type':'application/json', 'Authorization': 'Bearer ' + self.__validJwt}, json={'message': message})
        return True

    def validateApiStruct(content):
        if not isinstance(content, dict):
            return False, 'Please forward JSON: requests.post(url, json=JSON_DATA) / socket.emit(event, json)'
        if not 'endpoint' in content:
            return False, 'JSON require the key \"endpoint\"'
        if not 'options' in content:
            return False, 'JSON require the key \"options\"'
        if not isinstance(content['endpoint'], str):
            return False, 'The key \"endpoint\" require a string value'
        if not isinstance(content['options'], dict):
            return False, 'The key \"options\" require a dict value'

        if not 'type' in content['options']:
            return False, 'data.options require the key \"type\"'
        if not isinstance(content['options']['type'], str):
            return False, 'data.options.type require a string value'

        content['options']['type'] = content['options']['type'].lower()
        if not content['options']['type'] in ['delete', 'post', 'get', 'put']:
            return False, 'data.options.type require a string value of \"delete\", \"post\", \"get\" or \"put\"'

        if not 'include_jwt' in content['options']:
            content['options']['include_jwt'] = False

        if 'headers' in content['options']:
            if not isinstance(content['options']['headers'], dict):
                return False, 'data.options.headers have to be a dict'

            for header in content['options']['headers']:
                if header.lower() == 'authorization':
                    return False, 'You are not allowed to specify the authorization header, set options["include_jwt"] to True'

        if 'json' in content['options']:
            if not isinstance(content['options']['json'], dict):
                return False, 'data.options.json have to be a dict'

        return True, None

    def APIRequest(self, content):
        success, msg = StreamElements.validateApiStruct(content)
        if not success:
            return False, msg

        if content['options']['include_jwt'] == True:
            headers = {'Authorization': 'Bearer ' + self.__validJwt}
        else:
            headers = {}

        if 'headers' in content['options']:
            for header in content['options']['headers']:
                headers[header] = content['options']['headers'][header]

        if 'json' in content['options']:
            return True, requests.request(content['options']['type'], 'https://api.streamelements.com/'+ content['endpoint'].replace(':channel', self.__userId), headers=headers, json=content['options']['json']).text
        else:
            return True, requests.request(content['options']['type'], 'https://api.streamelements.com/'+ content['endpoint'].replace(':channel', self.__userId), headers=headers).text

    def getEvent(self):
        if len(self.__events) == 0:
            return None
        return self.__events.pop(0)

    def getTestEvent(self):
        if len(self.__testEvents) == 0:
            return None
        return self.__testEvents.pop(0)

    def setData(self, jwt=None, method=None):
        if isinstance(jwt, str): self.__jwt = jwt

        if method in [1, 2]: self.__method = method

    def sendSocketMessage(self, event, message):
        if self.__connectedMethod == 1:
            self.__SESIO.emit(event, message)
        else:
            if isinstance(self.__ws, websocket.WebSocket) and self.__ws.connected:
                self.__ws.send('42' + json.dumps([event, message]))

    def awaitStart(self, timeout):
        timeoutAt = time.time() + timeout
        while True:
            
            if self.__validJwt != '':
                return True
            if time.time() > timeoutAt:
                return False

    def start(self):
        currentTime = time.time()

        if self.__jwt == self.__connectedJwt and self.__connectedMethod == self.__method: return 0, self.__cooldown

        if self.__cooldown != None and self.__cooldown > currentTime: return -1, self.__cooldown

        self.__connectedJwt = self.__jwt

        try: self.__SESIO.disconnect()
        except Exception: pass

        self.__threadId += 1

        if not self.__connectedJwt in ['', '*']:
            print('[StreamElements] Connecting...')
            self.__cooldown = currentTime + 30

            if self.__method == 1:
                self.__connectedMethod = 1
                self.__SESIO.connect('https://realtime.streamelements.com', transports=['websocket'])
            else: #if self.__method == 2:
                self.__connectedMethod = 2
                threading.Thread(target=self.__altDriver, args=(self.__threadId,), daemon=True).start()
            return 1, self.__cooldown
        return 0, self.__cooldown
    
    def __closeAltDriver(self):
        if isinstance(self.__ws, websocket.WebSocket):
            try: self.__ws.close()
            except Exception: pass

            self.__wsBuffer.clear()
            self.__ws = None

    def __altDriverReader(self, ws):
        while True:
            try: data = ws.recv()
            except Exception: data = None

            if data in ['', None]: return

            self.__wsBuffer.append(data)

    def __altDriver(self, threadId):
        while self.__wsRunning:
            time.sleep(1)
            if threadId != self.__threadId: return
        while True:
            if threadId != self.__threadId:
                self.__closeAltDriver()
                self.__wsRunning = False
                return

            self.__wsRunning = True
            self.__ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
            self.__ws.connect("wss://realtime.streamelements.com/socket.io/?transport=websocket&EIO=4")

            self.__wsTimer = time.time()
            self.__sentPing = False

            threading.Thread(target=self.__altDriverReader, args=(self.__ws,), daemon=True).start()

            while True:
                if threadId != self.__threadId:
                    self.__onDisconnect()
                    self.__closeAltDriver()
                    self.__wsRunning = False
                    return

                if not self.__ws.connected:
                    self.__onDisconnect()
                    self.__closeAltDriver()
                    break

                if time.time() - self.__wsTimer >= self.__wsPingInterval:
                    #print('Sent: ping')
                    self.__wsTimer = time.time()
                    self.__ws.send('2')
                    self.__sentPing = True

                if self.__sentPing and time.time() - self.__wsTimer > self.__wsPingTimeout:
                    self.__onDisconnect()
                    self.__closeAltDriver()
                    break

                time.sleep(0.2)

                for _ in range(len(self.__wsBuffer)):
                    raw = self.__wsBuffer.pop(0)
                    if raw == '3':
                        #print('Received: pong')
                        self.__sentPing = False
                        self.__wsTimer = time.time()
                        continue
                    elif raw.startswith('0'):
                        event = 'connect'
                        data = json.loads(raw[1:])
                    elif raw.startswith('42'):
                        raw = json.loads(raw[2:])
                        event = raw[0]
                        data = raw[1]
                    else:
                        #print('junk:', raw)
                        continue

                    if event == 'connect':
                        self.__onConnect(data)
                    elif event == 'authenticated':
                        self.__onAuthenticated(data)
                    elif event == 'event':
                        self.__onEvent(data)
                    elif event == 'event:test':
                        self.__onTestEvent(data)

    def __onConnect(self, data=''):
        print('[StreamElements] Connected! Authenticating...')
        self.sendSocketMessage('authenticate', { 'method': 'jwt', 'token': self.__connectedJwt })

    def __onAuthenticated(self, data=''):
        if isinstance(data, dict) and 'channelId' in data:
            self.__userId = data['channelId']
        self.__validJwt = self.__connectedJwt
        print('[StreamElements] Authenticated')

    def __onEvent(self, data=''):
        self.__events.append(data)
        self.eventHistory.append(data)
        with self.__appContext:
            self.__sio.emit('StreamElementsEvent', data)
        if len(self.eventHistory) > 100: self.eventHistory.pop(0)

    def __onTestEvent(self, data=''):
        self.__testEvents.append(data)
        with self.__appContext:
            self.__sio.emit('StreamElementsTestEvent', data)

    def __onDisconnect(self, data=''):
        print('[StreamElements] Disconnected')
    
    def __BGTask(self):
        mt = threading.main_thread()
        while True:
            time.sleep(1)
            if not mt.isAlive():
                try: self.__SESIO.disconnect()
                except Exception: pass
                
                self.__threadId += 1
                try:
                    self.__closeAltDriver()
                except Exception: pass
                
                return