from . import Misc
import socketio, asyncio, json, time, websockets, typing, datetime

if typing.TYPE_CHECKING:
    from dependencies.modules.Extensions import Extensions

class StreamElements:
    def __init__(self, alias : str, extensions : 'Extensions', jwt : str, useSocketio : bool):
        self.id = hex(id(self))
        self.alias = alias
        
        self.__extensions = extensions

        self.__jwt = jwt
        self.__userId : str = None
        self.__clientId : str = None
        self.eventHistory = []

        self.__sio = socketio.AsyncClient()
        self.__useSocketioMethod = useSocketio == True
        self.__useSocketio = None

        self.__PingInterval = 20
        self.__PingTimeout = 10
        self.__wsConn = None
        self.__taskId = 0
        self.__ws = None
        
        self.__sio.on('connect', self.__onConnect)
        self.__sio.on('authenticated', self.__onAuthenticated)
        self.__sio.on('event', self.__onEvent)
        self.__sio.on('event:test', self.__onTestEvent)
        self.__sio.on('disconnect', self.__onDisconnect)

        loop = asyncio.get_event_loop()
        loop.create_task(self.connect())
    
    @property
    def useSocketIO(self): return self.__useSocketioMethod
    
    @property
    def connectedMethod(self): return self.__useSocketio

    @property
    def connected(self):
        if self.__useSocketio: return self.__sio.connected
        else: return self.__wsConn != None

    async def setMethod(self, useSocketIO : bool):
        self.__useSocketioMethod = useSocketIO == True
        await self.connect()

    async def connect(self):
        await self.disconnect()
        self.__useSocketio = self.__useSocketioMethod
        loop = asyncio.get_event_loop()
        if self.__useSocketio:
            print('[StreamElements] Connecting SocketIO')
            await self.__sio.connect('https://realtime.streamelements.com', transports=['websocket'])
        else:
            print('[StreamElements] Connecting WebSocket')
            loop.create_task(self.__readWs(self.__taskId))

    async def disconnect(self):
        if self.__useSocketio:
            if self.__sio.connected:
                await self.__sio.disconnect()
        else:
            self.__taskId += 1
    
    async def APIRequest(self, content) -> tuple[bool, str]:
        success, msg = StreamElements.validateApiStruct(content)
        if not success:
            return False, msg
        
        kwargs = {'body': content['options'].get('json', None), 'headers': {}, 'method': content['options'].get('type', 'get')}
        if kwargs['body'] == None: del kwargs['body']
        elif not isinstance(kwargs['body'], str):
            try: kwargs['body'] = json.dumps(kwargs['body'])
            except Exception: False, 'invalid json payload'

        if content['options']['include_jwt'] == True:
            kwargs['headers']['Authorization'] = 'Bearer ' + self.__jwt

        if 'headers' in content['options']:
            for header in content['options']['headers']:
                kwargs['headers'][header] = content['options']['headers'][header]

        resp, errorCode = await Misc.fetchUrl('https://api.streamelements.com/'+ content['endpoint'].replace(':channel', self.__userId), **kwargs)

        return errorCode == 1, resp

    async def sendMessage(self, message : str):
        if not isinstance(message, str): return False, 'message has to be a string'

        resp, errorcode = await Misc.fetchUrl('https://api.streamelements.com/kappa/v2/bot/' + self.__userId + '/say', method='post',
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + self.__jwt
            }, body=json.dumps({'message': message})
        )
        print(resp, errorcode)

        return errorcode == 1, resp

    def validateApiStruct(content) -> tuple[bool, str]:
        if not isinstance(content, dict):
            return False, 'Please forward JSON: post_request(url, json=JSON_DATA) / socket.emit(event, JSON_DATA)'
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

    async def __emit(self, event, data):
        if self.__useSocketio:
            if self.__sio.connected:
                await self.__sio.emit(event, data)
        else:
            if self.__ws != None and self.__ws.open:
                await self.__ws.send('42' + json.dumps([event, data]))
    
    async def __onConnect(self, data=''):
        print('[StreamElements] Connected! Authenticating...')

        if isinstance(data, dict):
            if 'pingInterval' in data:
                self.__PingInterval = int(data['pingInterval'] / 1000)
            if 'pingTimeout' in data:
                self.__PingTimeout = int(data['pingTimeout'] / 1000)
        
        await self.__emit('authenticate', { 'method': 'jwt', 'token': self.__jwt })

    async def __onAuthenticated(self, data=''):
        if isinstance(data, dict):
            if 'channelId' in data:
                self.__userId = data['channelId']
            if 'clientId' in data:
                self.__clientId = data['clientId']
        print('[StreamElements] Authenticated')

    async def __onEvent(self, data=''):
        if not isinstance(data, dict): return
        event = StreamElementsGenericEvent(self, data, False)
        self.__extensions.streamElementsEvent(event)
        self.eventHistory.append(event)
        if len(self.eventHistory) > 100: self.eventHistory.pop(0)

    async def __onTestEvent(self, data=''):
        if not isinstance(data, dict): return
        event = StreamElementsGenericEvent(self, data, True)
        self.__extensions.streamElementsTestEvent(event)

    async def __onDisconnect(self, data=''):
        print('[StreamElements] Disconnected')

    async def __readWs(self, taskId):
        while self.__wsConn != None:
            await asyncio.sleep(1)
        
        if self.__taskId != taskId: return
        
        timer = time.time() - 5
        sentPing = False

        self.__wsConn = websockets.connect('wss://realtime.streamelements.com/socket.io/?transport=websocket&EIO=4')
        self.__ws = await self.__wsConn.__aenter__()
        
        while True:
            try: raw = await asyncio.wait_for(self.__ws.recv(), 2)
            except asyncio.TimeoutError: raw = None

            if taskId != self.__taskId:
                await self.__wsConn.__aexit__()
                self.__wsConn = None
                self.__ws = None
                return

            currentTime = time.time()
            timeDelta = currentTime - timer

            if timeDelta >= self.__PingInterval:
                #print('Sent: Ping')
                timer = currentTime
                await self.__ws.send('2')
                sentPing = True
            elif sentPing and timeDelta > self.__PingTimeout:
                await self.__onDisconnect()
                await self.connect()
                return

            if raw == None: continue

            if raw == '3':
                #print('Received: Pong')
                sentPing = False
                timer = currentTime
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
                await self.__onConnect(data)
            elif event == 'authenticated':
                await self.__onAuthenticated(data)
            elif event == 'event':
                await self.__onEvent(data)
            elif event == 'event:test':
                await self.__onTestEvent(data)

class StreamElementsClientContext():
    def __init__(self, streamElements : StreamElements):
        self.__streamElements = streamElements
    
    @property
    def userId(self): return self.__streamElements.userId
    
    @property
    def clientId(self): return self.__streamElements.clientId

class StreamElementsGenericEvent():
    def __init__(self, client : StreamElementsClientContext, data : dict, testEvent: bool):
        self.UTCTimestamp = datetime.datetime.utcnow()
        self.client = client
        self.raw = data
        self.testEvent = testEvent
    
    def legacy(self):
        return self.raw
