from .vendor.StructGuard import StructGuard
from . import Misc, Errors
import asyncio, json, time, typing, datetime, aiohttp

if typing.TYPE_CHECKING:
    from dependencies.modules.Extensions import Extensions

class StreamElements:
    async def parseJWT(jwt : str) -> tuple[str, None] | tuple[None, str]:
        if len(jwt) == 0: return None, 'JWT have to be a string with a length larger than 0'

        resp, errorCode = await Misc.fetchUrl('https://api.streamelements.com/kappa/v2/users/current', headers={'Authorization': f'Bearer {jwt}'})

        if errorCode != 1: return None, 'unable to send HTTP request to validate JWT'
        
        try: parsedResp = json.loads(resp)
        except Exception: return None, 'unable to parse HTTP response from JWT validation'
        
        if not isinstance(parsedResp, dict): return None, 'invalid format returned by HTTP response from JWT validation, should be json dictionary'

        accountName = parsedResp.get('username', None)
        if accountName == None: return None, 'HTTP response from TMI validation does not include a login'

        return accountName, None
    
    def __init__(self, id_ : str, alias : str, extensions : 'Extensions', jwt : str):
        self.__id = id_
        self.alias = alias

        self.clientContext = StreamElementsClientContext(self)
        
        self.__extensions = extensions

        self.__jwt = jwt
        self.__accountName : str = None
        self.__userId : str = None
        self.__clientId : str = None
        self.__eventHistory = []

        self.__currentTask = None

        self.__PingInterval = 20
        self.__PingTimeout = 10
        self.__taskId = 0
        self.__ws = None

        self.__loop = asyncio.get_event_loop()
        self.startStreamElements()

    @property
    def id(self): return self.__id
    
    @property
    def jwt(self): return self.__jwt

    @property
    def accountName(self): return self.__accountName

    @property
    def eventHistory(self): return self.__eventHistory

    @property
    def userId(self): return self.__userId

    @property
    def clientId(self): return self.__clientId

    @property
    def connected(self):
        if self.__currentTask is None: return False
        return not self.__currentTask.done()

    async def setJWT(self, jwt : str) -> tuple[bool, str | None]:
        accountName, errorMsg = await StreamElements.parseJWT(jwt)
        if accountName is None: return False, errorMsg

        self.__jwt = jwt
        self.__accountName = accountName

        if not self.connected: self.startStreamElements()
        return True, None

    def startStreamElements(self):
        self.__loop.create_task(self.connect())

    def stopStreamElements(self):
        self.disconnect()

    async def connect(self):
        self.disconnect()
        loop = asyncio.get_event_loop()
        print(f'[StreamElements {self.alias}] Connecting StreamElements')
        self.__currentTask = loop.create_task(self.__readWs(self.__taskId))

    def disconnect(self):
        self.__taskId += 1
    
    async def APIRequest(self, method : str, endpoint : str, *, body : str = None, headers : dict[str, str] = None, includeJWT : bool = False) -> dict:
        '''
        ** Exceptions **
        - Errors.TypeError: Invalid type of parameter
        - Errors.ValueError: Invalid value of parameter
        - Errors.StreamElements.APIConnectionErrorError: Unable to reach the end server
        - Errors.StreamElements.APIBadRequestError: The HTTP request is invalid
        - Errors.StreamElements.APIBadResponseError: Invalid API response, expected JSON data
        '''

        if headers == None: headers = {}
        elif isinstance(headers, dict): headers = headers.copy()

        if not isinstance(endpoint, str): raise TypeError('The argument endpoint has to be a string')
        
        validMethods = ['get', 'post', 'put', 'delete']
        if not method.lower() in validMethods: raise ValueError('The method has to be one of the following: ' + ' '.join(validMethods))

        if not StructGuard.verifyDictStructure(headers, {str: str})[0]: raise ValueError('The headers has to be a dict with string keys and string values')
        
        kwargs = {'method': method, 'headers': headers}
        
        if body != None:
            if not isinstance(kwargs['body'], str):
                try: kwargs['body'] = json.dumps(body)
                except Exception: False, 'invalid body, has to be json or string'
            else: kwargs['body'] = body

        if includeJWT:
            kwargs['headers']['Authorization'] = 'Bearer ' + self.__jwt

        resp, errorCode = await Misc.fetchUrl('https://api.streamelements.com/'+ endpoint.replace(':channel', self.__userId), **kwargs)
        if errorCode == -1: raise Errors.StreamElements.APIConnectionErrorError('Unable to connect to streamelements.com')
        elif errorCode == -2: raise Errors.StreamElements.APIBadRequestError('Invalid HTTP request')

        try: return json.loads(resp)
        except Exception: raise Errors.StreamElements.APIBadResponseError('Invalid API response, expected JSON data')

    async def sendMessage(self, message : str):
        '''
        ** Exceptions **
        - TypeError: Invalid data type of message, should be string
        - Errors.StreamElements.SendMessageError: Error occured during HTTP request
        '''
        if not isinstance(message, str): raise TypeError('message has to be a string')

        resp, errorcode = await Misc.fetchUrl('https://api.streamelements.com/kappa/v2/bot/' + self.__userId + '/say', method='post',
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + self.__jwt
            }, body=json.dumps({'message': message})
        )

        if errorcode != 1: raise Errors.StreamElements.SendMessageError(resp)

    def validateApiStruct(content) -> tuple[bool, str | None]:
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
        if not self.__currentTask.done():
            await self.__ws.send_str('42' + json.dumps([event, data]))
    
    async def __onOpen(self, data=''):
        if isinstance(data, dict):
            if 'pingInterval' in data:
                self.__PingInterval = int(data['pingInterval'] / 1000)
            if 'pingTimeout' in data:
                self.__PingTimeout = int(data['pingTimeout'] / 1000)
    
    async def __onConnect(self, data=''):
        print(f'[StreamElements {self.alias}] Connected! Authenticating...')
        await self.__emit('authenticate', { 'method': 'jwt', 'token': self.__jwt })

    async def __onAuthenticated(self, data=''):
        if isinstance(data, dict):
            if 'channelId' in data:
                self.__userId = data['channelId']
            if 'clientId' in data:
                self.__clientId = data['clientId']
        print(f'[StreamElements {self.alias}] Authenticated')

    async def __onEvent(self, data=''):
        if not isinstance(data, dict): return
        event = StreamElementsGenericEvent(self.clientContext, data, False)
        self.__extensions.streamElementsEvent(event)
        self.__eventHistory.append(event)
        if len(self.__eventHistory) > 100: self.__eventHistory.pop(0)

    async def __onTestEvent(self, data=''):
        if not isinstance(data, dict): return
        event = StreamElementsGenericEvent(self.clientContext, data, True)
        self.__extensions.streamElementsTestEvent(event)

    async def __onDisconnect(self, data=''):
        print(f'[StreamElements {self.alias}] Disconnected')

    async def __readWs(self, taskId):
        while not self.__currentTask.done() != None:
            await asyncio.sleep(1)
        
        if self.__taskId != taskId: return

        self.__currentTask = asyncio.current_task()
        
        lastSend = time.time()
        sentPing = False

        while True:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect('wss://realtime.streamelements.com/socket.io/?EIO=3&transport=websocket') as ws:
                    self.__ws = ws
                    while True:
                        if taskId != self.__taskId: return
                        if ws.closed: break

                        try: raw = await ws.receive(timeout=2)
                        except TimeoutError: raw = None
                        
                        if raw is not None: raw = raw.data
                        
                        currentTime = time.time()
                        timeDelta = currentTime - lastSend

                        if timeDelta >= self.__PingInterval:
                            #print('Sent: Ping')
                            lastSend = currentTime
                            await ws.send_str('2')
                            sentPing = True
                        elif sentPing and timeDelta > self.__PingTimeout:
                            await self.__onDisconnect()
                            break
                        
                        if raw is None: continue
                        if not isinstance(raw, str): break
                        
                        code = raw[:2]
                        
                        if code == '42':
                            raw = json.loads(raw[2:])
                            event = raw[0]
                            data = raw[1]
                        elif code == '3':
                            #print('Received: Pong')
                            sentPing = False
                            continue
                        elif code == '40':
                            event = 'connect'
                        elif code == '0{':
                            event = 'open'
                            data = json.loads(raw[1:])
                        else:
                            #print('junk:', raw)
                            continue

                        if event == 'event':
                            await self.__onEvent(data)
                        elif event == 'event:test':
                            await self.__onTestEvent(data)
                        elif event == 'open':
                            await self.__onOpen(data)
                        elif event == 'connect':
                            await self.__onConnect()
                        elif event == 'authenticated':
                            await self.__onAuthenticated(data)

class StreamElementsClientContext():
    def __init__(self, streamElements : StreamElements):
        self.__streamElements = streamElements
    
    @property
    def userId(self): return self.__streamElements.userId
    
    @property
    def clientId(self): return self.__streamElements.clientId
    
    @property
    def streamElementsId(self): return self.__streamElements.id

    async def sendMessage(self, msg : str):
        '''
        ** Exceptions **
        - TypeError: Invalid data type of message, should be string
        - Errors.StreamElements.SendMessageError: Error occured during HTTP request
        '''
        await self.__streamElements.sendMessage(msg)
    
    async def APIRequest(self, method : str, endpoint : str, *, body : str = None, headers : dict[str, str] = None, includeJWT : bool = False):
        '''
        ** Exceptions **
        - Errors.TypeError: Invalid type of parameter
        - Errors.ValueError: Invalid value of parameter
        - Errors.StreamElements.APIConnectionErrorError: Unable to reach the end server
        - Errors.StreamElements.APIBadRequestError: The HTTP request is invalid
        - Errors.StreamElements.APIBadResponseError: Invalid API response, expected JSON data
        '''
        await self.__streamElements.APIRequest(method, endpoint, body=body, headers=headers, includeJWT=includeJWT)

class StreamElementsGenericEvent():
    def __init__(self, client : StreamElementsClientContext, data : dict, testEvent: bool):
        self.__clientContext = client
        self.UTCTimestamp = datetime.datetime.utcnow()
        self.raw = data
        self.testEvent = testEvent

    @property
    def streamElementsContext(self): return self.__clientContext

    def legacy(self):
        return self.raw
