from . import StreamElements, Web
import asyncio, typing

if typing.TYPE_CHECKING:
    from . import Extensions

class AsyncExtensionCrossover():
    def __init__(self, extension : 'Extensions.Extension'):
        self.__extension = extension

    @property
    def port(self): return self.__extension.extensions.settings.currentPort

    @property
    def twitch(self):
        if self.__extension.twitch is None: return None
        return self.__extension.twitch.clientContext

    @property
    def streamElements(self):
        if self.__extension.streamelements is None: return
        return self.__extension.streamelements.clientContext

    async def toPy(self, extName : str | list[str], payload):
        '''
        ** Exceptions **
        - TypeError: Invalid data type of scripts or events (should be lists of strings)
        '''
        ct = Web.CrossTalk(payload)
        if isinstance(extName, str): extName = [extName]
        self.__extension.extensions.crossTalk(ct, extName, [])

    async def toWeb(self, eventName : str | list[str], payload):
        '''
        ** Exceptions **
        - TypeError: Invalid data type of scripts or events (should be lists of strings)
        '''
        ct = Web.CrossTalk(payload)
        if isinstance(eventName, str): eventName = [eventName]
        self.__extension.extensions.crossTalk(ct, [], eventName)

    async def deleteRegular(self, userId: str, regularGroupName: str, platform: str):
        return self.__extension.extensions.regulars.removeRegular(userId, regularGroupName, platform)

    async def addRegular(self, alias: str, userId: str, regularGroupName: str, platform: str):
        return self.__extension.extensions.regulars.addRegular(alias, userId, regularGroupName, platform)

    def legacy(self): return LegacyExtensionCrossover(self, self.__extension)

class LegacyExtensionCrossover():
    def __init__(self, asyncExtensionCrossover : AsyncExtensionCrossover, extension : 'Extensions.Extension'):
        self.__asyncExtensionCrossover = asyncExtensionCrossover
        self.__extension = extension

    def SendMessage(self, data=None):
        '''
        Send a twitch message.
        argument: dict with the keys "bot" and "message"
        bot = "local"/"StreamElements" (depends on your bot target, local is recommended)
        message = Your message that you wish to send in twitch chat (str)
        returns a dict with the key "type", value = "error"/"success" (DEPRICATED)
        returns a dict with the key "success", value = True/False
        returns a dict with the key "message" on error, value = error message
        '''
        if not isinstance(data, dict):
            return {'type':'error', 'success': False, 'message':'The input has to be a dictionary'}

        if not 'message' in data:
            return {'type':'error', 'success': False, 'message':'The dict has to include the key message'}
        if not 'bot' in data:
            return {'type':'error', 'success': False, 'message':'The dict has to include the key bot with the value "local" or "streamelements"'}

        if not isinstance(data['bot'], str):
            return {'type':'error', 'success': False, 'message':'The dict has to include the key bot with the value "local" or "streamelements"'}

        msg : str | None = None
        if isinstance(data['message'], str): msg = data['message']
        else:
            try: msg = str(data['message'])
            except Exception: return {'type':'error', 'success': False, 'message':'The dict has to include the key message containing a message'}

        if len(msg) == 0: return {'type':'error', 'success': False, 'message':'The dict has to include the key message containing a message'}

        loop = asyncio.get_event_loop()

        bot = data['bot'].lower()
        if bot == 'streamelements': loop.create_task(self.__safeStreamElementsMessage(msg))
        elif bot == 'local': loop.create_task(self.__safeTwitchMessage(msg))
        else: return {'type':'error', 'success': False, 'message':'The dict has to include the key bot with the value "local" or "streamelements"'}

        return {'type':'success', 'success': True}

    def StreamElementsAPI(self, data=None):
        '''
        Send an API request to StreamElements servers.
        argument: dict with the keys "endpoint" (str) and "options" (dict)
        returns a dict with the key "type", value = "error"/"success" (DEPRICATED)
        returns a dict with the key "success", value = True/False
        returns a dict with the key "message" on error, value = error message
        '''

        success, msg = StreamElements.StreamElements.validateApiStruct(data)

        if not success: return {'type': 'error', 'success': False, 'message': msg}

        endpoint = data['endpoint']
        options = data['options']

        loop = asyncio.get_event_loop()
        loop.create_task(self.__safeStreamElementsAPI(endpoint, options))
        return {'type':'success', 'success': True}

    def ScriptTalk(self, data=None):
        '''
        Send data between python scripts.
        argument: dict with the keys "module" (str) and "data" (any)
        module = Your target, example: "example.test_LSE"
        data = Your data to forward over
        returns a dict with the key "type", value = "error"/"success" (DEPRICATED)
        returns a dict with the key "success", value = True/False
        returns a dict with the key "message" on error, value = error message
        '''
        if not isinstance(data,  dict):
            return {'type':'error', 'message':'The input has to be a dict'}

        if not 'module' in data:
            return {'type':'error', 'success': False, 'message':'No module found, please include the key module'}
        if not 'data' in data:
            return {'type':'error', 'success': False, 'message':'No data found, please include the key data'}

        if not isinstance(data['module'], str) or len(data['module']) == 0:
            return {'type':'error', 'success': False, 'message':'Invalid module, please forward a valid module'}

        module = data['module']
        sendData = data['data']

        loop = asyncio.get_event_loop()
        loop.create_task(self.__safeToPy(module, sendData))
        return {'type':'success', 'success': True}

    def CrossTalk(self, data=None):
        '''
        Send data to HTML/JavaScript.
        argument: dict with the keys "event" (str) and "data" (any)
        event = Your target, has to start with "p-", example: "p-MyTestEvent"
        data = Your data to forward over
        returns a dict with the key "type", value = "error"/"success" (DEPRICATED)
        returns a dict with the key "success", value = True/False
        returns a dict with the key "message" on error, value = error message
        '''
        if not isinstance(data, dict):
            return {'type':'error', 'success': False, 'message':'The input has to be a dict'}
        
        if not 'event' in data:
            return {'type':'error', 'success': False, 'message':'json require the key "event"'}
        if not 'data' in data:
            return {'type':'error', 'success': False, 'message':'json require the key "data"'}

        if not isinstance(data['event'], str):
            return {'type':'error', 'success': False, 'message':'The value for the key "event" has to be a string'}
        if not data['event'].startswith('p-'):
            return {'type':'error', 'success': False, 'message':'The value for the key "event" has to start with "p-", for example: p-example'}

        event = data['event']
        sendData = data['data']

        loop = asyncio.get_event_loop()
        loop.create_task(self.__safeToWeb(event, sendData))
        return {'type':'success', 'success': True}

    def DeleteRegular(self, data : str = None):
        if not isinstance(data, str): return {'type': 'error', 'success': False, 'message': 'The input has to be a string'}
        loop = asyncio.get_event_loop()
        loop.create_task(self.__asyncExtensionCrossover.deleteRegular(data, 'default', 'twitch'))
        return {'type':'success', 'success': True}

    def AddRegular(self, data : dict = None):
        if not isinstance(data, str): return {'type': 'error', 'success': False, 'message': 'The input has to be a string'}
        loop = asyncio.get_event_loop()
        loop.create_task(self.__asyncExtensionCrossover.addRegular(data, data, 'default', 'twitch'))
        return {'type':'success', 'success': True}

    async def __safeTwitchMessage(self, msg : str):
        t = self.__asyncExtensionCrossover.twitch
        if t is None: return

        try: t.sendMessage(msg, t.defaultChannel)
        except Exception: pass

    async def __safeStreamElementsMessage(self, msg : str):
        se = self.__asyncExtensionCrossover.streamElements
        if se is None: return
        try: await se.sendMessage(msg)
        except Exception: pass

    async def __safeStreamElementsAPI(self, method: str, endpoint: str, *, body: str = None, headers: dict[str, str] = None, includeJWT: bool = False):
        se = self.__asyncExtensionCrossover.streamElements
        if se is None: return
        try: await se.APIRequest(method, endpoint, body=body, headers=headers, includeJWT=includeJWT)
        except Exception: pass
    
    async def __safeToPy(self, extName : str | list[str], payload):
        try: await self.__asyncExtensionCrossover.toPy(extName, payload)
        except Exception: pass
    
    async def __safeToWeb(self, eventName : str | list[str], payload):
        try: await self.__asyncExtensionCrossover.toWeb(eventName, payload)
        except Exception: pass