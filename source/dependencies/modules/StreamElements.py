from pathlib import Path
import socketio, asyncio, json, time, websockets

class StreamElements:
    def __init__(self, extensions, jwt : str, useSocketio : bool):
        self.extensions = extensions

        self.__jwt = jwt
        self.userId : str = None
        self.clientId : str = None
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
    
    def setMethod(self, useSocketIO): self.__useSocketioMethod = useSocketIO == True

    async def __emit(self, event, data):
        if self.__useSocketio:
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
                self.userId = data['channelId']
            if 'clientId' in data:
                self.clientId = data['clientId']
        print('[StreamElements] Authenticated')

    async def __onEvent(self, data=''):
        if not isinstance(data, dict): return
        event = StreamElementsGenericEvent(self, data, False)
        #self.parent.registerStreamElementsEvent.append(SEEvent)
        #self.eventHistory.append(SEEvent)
        #if len(self.eventHistory) > 100: self.eventHistory.pop(0)

    async def __onTestEvent(self, data=''):
        if not isinstance(data, dict): return
        event = StreamElementsGenericEvent(self, data, True)
        #self.parent.registerStreamElementsTestEvent(SEEvent)

    async def __onDisconnect(self, data=''):
        print('[StreamElements] Disconnected')

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
        self.client = client
        self.raw = data
        self.testEvent = testEvent
    
    def legacy(self):
        return self.raw
