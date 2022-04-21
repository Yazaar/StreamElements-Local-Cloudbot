from . import Web

import typing, discord, asyncio

if typing.TYPE_CHECKING:
    from .Extensions import Extensions

class AsyncExtensionCrossover():
    def __init__(self, extensions : Extensions):
        self.__extensions = extensions
    
    @property
    def serverPort(self): return 80
    @property
    def port(self): return self.serverPort
    
    async def twitchMessage(self, message : str, channel : str, *, alias : str = None, id_ : str = None) -> tuple[bool, str | None]:
        twitch = self.__extensions.findTwitch(alias=alias, id_=id_)
        if twitch == None: return False, 'Unable to find the specified Twitch (alias or id)'
        return await twitch.sendMessage(message, channel)
    
    async def streamElementsMessage(self, message : str, *, alias : str = None, id_ : str = None) -> tuple[bool, str | None]:
        se = self.__extensions.findStreamElements(alias=alias, id_=id_)
        if se == None: return False, 'Unable to find the specified StreamElements (alias or id)'
        return await se.sendMessage(message)
    
    async def discordMessage(self, channel : str, message : str = None, embed : discord.Embed = None, *, alias : str = None, id_ : str = None) -> tuple[bool, str | None]:
        bot = self.__extensions.findDiscord(alias=alias, id_=id_)
        if bot == None: return False, 'Unable to find the specified Discord (alias or id)'
        textChannel, resp = await bot.getTextChannel(channel)
        if channel == None: return False, resp
        
        try: await textChannel.send(content=message, embed=embed)
        except discord.Forbidden: return False, 'Not allowed to send messages in the specified channel'
        return True, None
    
    async def streamElementsAPI(self, endpoint : str, *, body : str = None, headers : dict[str, str] = None, method : str = 'get', includeJWT : bool = False, alias : str = None, id_ : str = None) -> tuple[bool, str | None]:
        se = self.__extensions.findStreamElements(alias=alias, id_=id_)
        if se == None: return False, 'Unable to find the specified StreamElements (alias or id)'
        return se.APIRequest(endpoint, body=body, headers=headers, method=method, includeJWT=includeJWT)
    
    async def crossTalk(self, data, *, scripts : list[str] = None, events : list[str] = None):
        ct = Web.CrossTalk(data)
        return self.__extensions.crossTalk(ct, scripts, events)
    
    async def deleteRegular(self, userId: str, regularGroupName: str, platform: str):
        return self.__extensions.regulars.removeRegular(userId, regularGroupName, platform)
    
    async def addRegular(self, alias: str, userId: str, regularGroupName: str, platform: str):
        return self.__extensions.regulars.addRegular(alias, userId, regularGroupName, platform)

class LegacyExtensionCrossover():
    def __init__(self, extensions : Extensions):
        self.__extensions = extensions
        self.__asyncExtensionCrossover = AsyncExtensionCrossover(extensions)
        self.__loop = asyncio.get_event_loop()
    
    @property
    def twitchBotName(self):
        twitch = self.__extensions.defaultTwitch()
        return twitch.botname

    @property
    def twitchChannel(self):
        twitch = self.__extensions.defaultTwitch()
        if twitch == None: return
        channels = twitch.allChannels()
        if len(channels) > 0: return channels[0]
    
    @property
    def serverPort(self): return self.__asyncExtensionCrossover.serverPort
    
    @property
    def port(self): return self.__asyncExtensionCrossover.port
    
    def SendMessage(self, data : dict = None):
        if not isinstance(data, dict): return {'type': 'error', 'success': False, 'message': 'The input has to be a dictionary'}

        message = data.get('message', None)
        bot = data.get('bot', '').lower()

        if not isinstance(message, str): return {'type': 'error', 'success': False, 'message': 'The message has to be a string'}
        
        if bot in ['local', 'twitch']:
            twitch = self.__extensions.defaultTwitch()
            if twitch == None: return {'type': 'error', 'success': False, 'message': 'No twitch bot is connected'}
            self.__loop.create_task(self.__asyncExtensionCrossover.twitchMessage(message, twitch.defaultChannel(), id_=twitch.id))
        
        elif bot == 'streamelements':
            se = self.__extensions.defaultStreamElements()
            if se == None: return {'type': 'error', 'success': False, 'message': 'No StreamElements is connected'}
            self.__loop.create_task(self.__asyncExtensionCrossover.streamElementsMessage(message, id_=se.id))

        else: return {'type': 'error', 'success': False, 'message': 'The dict has to include the key bot with the value "local", "twitch" or "streamelements"'}
        return {'type':'success', 'success': True}
    
    def StreamElementsAPI(self, data : dict = None):
        if not isinstance(data, dict): return {'type': 'error', 'success': False, 'message': 'The input has to be a dictionary'}

        data = data.copy()

        if 'options' in data and isinstance(data['options'], dict):
            options = data['options']
            if 'type' in options: data['method'] = options['type']
            if 'include_jwt' in options: data['includeJWT'] = options['include_jwt']
            if 'headers' in options: data['headers'] = options['headers']
        
        method = data.get('method', '').lower()
        if method in ['get', 'post', 'put', 'delete']: return {'type': 'error', 'success': False, 'message': 'The method has to be get, post, put or delete'}

        endpoint = data.get('endpoint', None)
        if not isinstance(endpoint, str): return {'type': 'error', 'success': False, 'message': 'The endpoint has to be a string'}

        self.__loop.create_task(self.__asyncExtensionCrossover.streamElementsAPI(
            method=method,
            endpoint=endpoint,
            headers=data.get('headers', None),
            body=data.get('body', None),
            includeJWT=data.get('includeJWT', False)
        ))

        return {'type':'success', 'success': True}

    
    def ScriptTalk(self, data : dict = None):
        if not isinstance(data, dict): return {'type': 'error', 'success': False, 'message': 'The input has to be a dictionary'}

        if not 'module' in data: return {'type':'error', 'success': False, 'message':'No module found, please include the key module'}
        if not 'data' in data: return {'type':'error', 'success': False, 'message':'No data found, please include the key data'}

        if not isinstance(data['module'], str): return {'type':'error', 'success': False, 'message':'The module has to be a string'}

        self.__loop.create_task(self.__asyncExtensionCrossover.crossTalk(data=data['data'], scripts=[data['module']]))
    
    def CrossTalk(self, data : dict = None):
        if not isinstance(data, dict): return {'type': 'error', 'success': False, 'message': 'The input has to be a dictionary'}
        
        if not 'event' in data: return {'type':'error', 'success': False, 'message':'No event found, please include the key event'}
        if not 'data' in data: return {'type':'error', 'success': False, 'message':'No data found, please include the key data'}

        if not isinstance(data['event'], str): return {'type':'error', 'success': False, 'message':'The event has to be a string'}
        if not data['event'][:2] == 'p-': return {'type':'error', 'success': False, 'message':'The value for the key "event" has to start with "p-", for example: p-example'}

        self.__loop.create_task(self.__asyncExtensionCrossover.crossTalk(data=data['data'], events=[data['event']]))
    
    def DeleteRegular(self, data : str = None):
        if not isinstance(data, str): return {'type': 'error', 'success': False, 'message': 'The input has to be a string'}
        self.__loop.create_task(self.__asyncExtensionCrossover.deleteRegular(data, 'default', 'twitch'))
    
    def AddRegular(self, data : dict = None):
        if not isinstance(data, str): return {'type': 'error', 'success': False, 'message': 'The input has to be a string'}
        self.__loop.create_task(self.__asyncExtensionCrossover.addRegular(data, data, 'default', 'twitch'))
