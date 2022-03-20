from . import Discord, Twitch, StreamElements, Settings, Regulars
import importlib, inspect, types, asyncio, threading, typing, socketio
from pathlib import Path

class Extension():
    def __init__(self, modulePath : Path):
        self.methods : typing.Dict[str, ExtensionMethod] = {}
        self.modulePath : str = modulePath
        self.importName : str = self.modulePath.as_posix().replace('/', '.')[:-3]
        self.moduleName : str = self.importName[11:]

        self.module = None
        self.error : bool = False
        self.errorData : Exception = None

        self.__loadModule()
    
    def __loadModule(self):
        try:
            self.module = importlib.import_module(self.importName)
            self.error = False
            self.errorData = None
        except Exception as e:
            self.errorData = e
            self.module = None
            self.error = True
        
        self.methods.clear()
        
        if (self.error): return

        moduleItems = dir(self.module)
        for moduleItem in moduleItems:
            attr = getattr(self.module, moduleItem)
            if ExtensionMethod.isFuncOrMethod(attr):
                extMethod = ExtensionMethod(attr, self)
                if extMethod.name != None:
                    self.methods[extMethod.name] = extMethod

    def getEndpoint(self, endpointStr : str):
        endpoint = Extension.ENDPOINTS.get(endpointStr, None)
        if endpoint == None: return None, None
        legacySupport : str = endpoint['legacySupport']
        callback = None
        isAsync : bool = None
        
        moduleItems = dir(self.module)
        for i in moduleItems:
            if i in endpoint['alias']:
                callback = self.module[i]
                if legacySupport and self.isLegacy(callback):
                    isAsync = False
                    break
                elif self.isAsync(callback):
                    isAsync = True
                    break
        
        if isAsync == None: return None, None

        return callback, isAsync

class ExtensionMethod():
    ENDPOINTS = {
        'initialize': {
            'alias': ['initialize', 'Initialize'],
            'legacySupport': True
        },
        'tick': {
            'alias': ['tick', 'Tick'],
            'legacySupport': True
        },
        'twitchMessage': {
            'alias': ['Execute'],
            'legacySupport': True
        },
        'streamElementsEvent': {
            'alias': ['StreamElementsEvent'],
            'legacySupport': True
        },
        'streamElementsTestEvent': {
            'alias': ['StreamElementsTestEvent'],
            'legacySupport': True
        },
        'toggle': {
            'alias': ['Toggle'],
            'legacySupport': True
        },
        'crossTalk': {
            'alias': ['CrossTalk'],
            'legacySupport': True
        },
        'unload': {
            'alias': ['Unload'],
            'legacySupport': True
        },
        'newSettings': {
            'alias': ['NewSettings'],
            'legacySupport': True
        },
        'discordMessage': {
            'alias': [],
            'legacySupport': False
        },
        'discordMessageDeleted': {
            'alias': [],
            'legacySupport': False
        },
        'discordMessageEdited': {
            'alias': [],
            'legacySupport': False
        },
        'discordMessageNewReaction': {
            'alias': [],
            'legacySupport': False
        },
        'discordMessageRemovedReaction': {
            'alias': [],
            'legacySupport': False
        },
        'discordMessageReactionsCleared': {
            'alias': [],
            'legacySupport': False
        },
        'discordMessageReactionEmojiCleared': {
            'alias': [],
            'legacySupport': False
        },
        'discordMemberJoined': {
            'alias': [],
            'legacySupport': False
        },
        'discordMemberRemoved': {
            'alias': [],
            'legacySupport': False
        },
        'discordMemberUpdated': {
            'alias': [],
            'legacySupport': False
        },
        'discordMemberBanned': {
            'alias': [],
            'legacySupport': False
        },
        'discordMemberUnbanned': {
            'alias': [],
            'legacySupport': False
        },
        'discordGuildJoined': {
            'alias': [],
            'legacySupport': False
        },
        'discordGuildRemoved': {
            'alias': [],
            'legacySupport': False
        },
        'discordVoiceStateUpdate': {
            'alias': [],
            'legacySupport': False
        }
    }

    def __init__(self, func, extension : Extension):
        self.extension = extension
        self.callback = func
        self.asyncMethod : bool = None
        self.name : str = ExtensionMethod.getFuncName(self.callback.__name__)
        if self.name == None: return

        if ExtensionMethod.isLegacy(func):
            self.asyncMethod = False
        elif ExtensionMethod.isAsync(func):
            self.asyncMethod = True

    def getFuncName(funcName : str):
        match : str = ExtensionMethod.ENDPOINTS.get(funcName, None)
        if match != None: return funcName
        for realFuncName in ExtensionMethod.ENDPOINTS:
            for funcAlias in realFuncName['alias']:
                if funcAlias == funcName: return realFuncName
        return None
    
    def isFuncOrMethod(func):
        return inspect.isfunction(func) or inspect.ismethod(func)

    def isLegacy(func):
        return ExtensionMethod.isFuncOrMethod(func) and not inspect.iscoroutinefunction(func)

    def isAsync(func):
        return inspect.iscoroutinefunction(func)

class Extensions():
    def __init__(self, websio : socketio.AsyncServer, settings : Settings.Settings):
        self.__websio = websio
        self.__settings = settings
        self.__regulars = Regulars.Regulars()

        self.__twitchInstances : typing.List[Twitch.Twitch] = []
        self.__discordInstances : typing.List[Discord.Discord] = []
        self.__streamElementsInstances : typing.List[StreamElements.StreamElements] = []

        self.EXTENSION_PATH = Path('extensions')

        self.logs = []

        self.__extensions : typing.List[Extension] = []

        self.__callbacks : typing.Dict[str, typing.List[ExtensionMethod]] = {}
        self.__legacyCallbacks : typing.Dict[str, typing.List[ExtensionMethod]] = {}

        self.__legacyThreads : typing.List[threading.Thread] = []

        self.__loop = asyncio.get_event_loop()

        self.__loop.create_task(self.__ticker())
    
    def load(self):
        self.__twitchInstances = self.__loadTwitchInstances()
        self.__discordInstances = self.__loadDiscordInstances()
        self.__streamElementsInstances = self.__loadStreamElementsInstances()

    def reloadExtensions(self):
        self.__unloadExtensions()
        self.__loadExtensions()

    def addTwitchInstance(self, alias : str, tmi : str, botname : str, channels : typing.List[str]):
        twitchInstance = Twitch.Twitch(alias, self, tmi, botname, channels)
        self.__twitchInstances.append(twitchInstance)
        return twitchInstance

    def removeTwitchInstance(self, twitchId : int):
        removeThis : Twitch.Twitch = self.__find(self.__twitchInstances, twitchId)
        if removeThis != None:
            self.__twitchInstances.remove(removeThis)
            removeThis.stop()

    def addDiscordInstance(self, alias : str, key : str):
        discordInstance = Discord.Discord(alias, self, key)
        self.__discordInstances.append(discordInstance)
        return discordInstance

    def removeDiscordInstance(self, discordId : int):
        removeThis : Discord.Discord = self.__find(self.__discordInstances, discordId)
        if removeThis != None:
            self.__discordInstances.remove(removeThis)
            removeThis.stop()

    def addStreamElementsInstance(self, alias : str, jwt : str, useSocketio : bool):
        streamElementsInstance = StreamElements.StreamElements(alias, self, jwt, useSocketio)
        self.__streamElementsInstances.append(streamElementsInstance)
        return streamElementsInstance

    def removeStreamElementsInstance(self, streamElementsId : int):
        removeThis : StreamElements.StreamElements = self.__find(self.__streamElementsInstances, streamElementsId)
        if removeThis != None:
            self.__streamElementsInstances.remove(removeThis)
            removeThis.stop()

    def addExtension(self, extension : Extension):
        for i in self.__extensions:
            if i.moduleName == extension.moduleName: return
        self.__extensions.append(extension)

        for method in extension.methods:
            if extension.methods[method].asyncMethod:
                callbackList = self.__callbacks.get(method, None)
                if callbackList == None: callbackList = self.__callbacks[method] = []
            else:
                callbackList = self.__legacyCallbacks.get(method, None)
                if callbackList == None: callbackList = self.__legacyCallbacks[method] = []
            callbackList.append(extension.methods[method])

    def removeExtension(self, extension : Extension):
        for methodName in extension.methods:
            if extension.methods[methodName].asyncMethod:
                callbacks = self.__callbacks.get(methodName, [])
            else:
                callbacks = self.__legacyCallbacks.get(methodName, [])
            for index, callback in enumerate(callbacks):
                if callback.extension.moduleName == extension.moduleName:
                    callbacks.pop(index)
                    break

        for index, ext in enumerate(self.__extensions):
            if ext.moduleName == extension.moduleName:
                self.__extensions.pop(index)
                break

    def twitchMessage(self, message : Twitch.TwitchMessage):
        print('[CORE] Twitch message')
        self.__addLegacy(self.__legacyCallbacks.get('twitchMessage', []), (message.legacy(),))

        for extMethod in self.__callbacks.get('twitchMessage', []):
            self.__loop.create_task(self.__addTask(extMethod, (message,)))

    def streamElementsEvent(self, event : StreamElements.StreamElementsGenericEvent):
        print('[CORE] StreamElements event')
        self.__addLegacy(self.__legacyCallbacks.get('streamElementsEvent', []), (event.legacy(),))

        for extMethod in self.__callbacks.get('streamElementsEvent', []):
            self.__loop.create_task(self.__addTask(extMethod, (event,)))

    def streamElementsTestEvent(self, event : StreamElements.StreamElementsGenericEvent):
        print('[CORE] StreamElements test event')
        for extMethod in self.__callbacks.get('streamElementsTestEvent', []):
            self.__loop.create_task(self.__addTask(extMethod, (event,)))

    # TODO: implement + fix codeflow of toggle
    def toggle(self, script : str, toggleStatus : bool):
        print('[CORE] toggle')
        for extMethod in self.__callbacks.get('toggle', []):
            if extMethod.extension.moduleName == script:
                self.__loop.create_task(self.__addTask(extMethod, (toggleStatus,)))
                break

    # TODO: implement + fix codeflow of crossTalk
    def crossTalk(self, data, scripts : typing.List[str], events : list):
        print('[CORE] cross talk')

    # TODO: implement + fix codeflow of newSettings
    def newSettings(self, settings : dict, scripts : list, event : str):
        print('[CORE] new settings')

    def discordMessage(self, data : Discord.DiscordMessage):
        print('[CORE] new Discord message')
        for extMethod in self.__callbacks.get('discordMessage', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMessageDeleted(self, data : Discord.DiscordMessageDeleted):
        print('[CORE] Discord message deleted')
        for extMethod in self.__callbacks.get('discordMessageDeleted', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMessageEdited(self, data : Discord.DiscordMessageEdited):
        print('[CORE] Discord message edited')
        for extMethod in self.__callbacks.get('discordMessageEdited', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMessageNewReaction(self, data : Discord.DiscordMessageNewReaction):
        print('[CORE] Discord reaction added')
        for extMethod in self.__callbacks.get('discordMessageNewReaction', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMessageRemovedReaction(self, data : Discord.DiscordMessageRemovedReaction):
        print('[CORE] Discord reaction removed')
        for extMethod in self.__callbacks.get('discordMessageRemovedReaction', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMessageReactionsCleared(self, data : Discord.DiscordMessageReactionsCleared):
        print('[CORE] Discord reactions cleared')
        for extMethod in self.__callbacks.get('discordMessageReactionsCleared', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMessageReactionEmojiCleared(self, data : Discord.DiscordMessageReactionEmojiCleared):
        print('[CORE] Discord reaction emoji cleared')
        for extMethod in self.__callbacks.get('discordMessageReactionEmojiCleared', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMemberJoined(self, data : Discord.DiscordMemberJoined):
        print('[CORE] Discord member joined')
        for extMethod in self.__callbacks.get('discordMemberJoined', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMemberRemoved(self, data : Discord.DiscordMemberRemoved):
        print('[CORE] Discord member removed')
        for extMethod in self.__callbacks.get('discordMemberRemoved', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMemberUpdated(self, data : Discord.DiscordMemberUpdated):
        print('[CORE] Discord member updated')
        for extMethod in self.__callbacks.get('discordMemberUpdated', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMemberBanned(self, data : Discord.DiscordMemberBanned):
        print('[CORE] Discord member banned')
        for extMethod in self.__callbacks.get('discordMemberBanned', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordMemberUnbanned(self, data : Discord.DiscordMemberUnbanned):
        print('[CORE] Discord member unbanned')
        for extMethod in self.__callbacks.get('discordMemberUnbanned', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordGuildJoined(self, data : Discord.DiscordGuildJoined):
        print('[CORE] joined Discord guild')
        for extMethod in self.__callbacks.get('discordGuildJoined', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordGuildRemoved(self, data : Discord.DiscordGuildRemoved):
        print('[CORE] removed from Discord guild')
        for extMethod in self.__callbacks.get('discordGuildRemoved', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def discordVoiceStateUpdate(self, data : Discord.DiscordVoiceStateUpdate):
        print('[CORE] Discord voice state changed')
        for extMethod in self.__callbacks.get('discordVoiceStateUpdate', []):
            self.__loop.create_task(self.__addTask(extMethod, (data,)))

    def __find(objects : list, objectId : int):
        for obj in objects:
            if obj.id == objectId:
                return obj
        return None

    def __unloadExtensions(self):
        self.__extensions.clear()
    
    def __loadExtensions(self, path = None):
        if path is None: path = self.EXTENSION_PATH
        for f in path.glob('*'):
            if f.is_dir():
                self.__loadExtensions(f)
            elif f.name.endswith('_LSE.py'):
                newExt = Extension(f)
                if newExt.error:
                    self.__handleExtensionError(newExt.moduleName, newExt.errorData, 'import')
                self.addExtension(newExt)

    def __loadTwitchInstances(self):
        instances = []
        for twitch in self.__settings.twitch:
            instances.append(Twitch.Twitch(self, twitch['alias'], twitch['tmi'], twitch['botname'], twitch['channels'].copy()))
        return instances

    def __loadDiscordInstances(self):
        instances = []
        for discord in self.__settings.discord:
            instances.append(Discord.Discord(self, discord['token']))
        return instances

    def __loadStreamElementsInstances(self):
        instances = []
        return instances

    def __handleExtensionError(self, rawModuleName : str, exception : Exception, executionType : str):
        if isinstance(rawModuleName, str): moduleName = rawModuleName[11:]
        elif isinstance(rawModuleName, types.ModuleType): moduleName = rawModuleName.__name__[11:]
        else: moduleName = 'unknown'
        newLog = {
            'module': moduleName,
            'message': str(exception) + ' (' + executionType + ')'
        }
        self.logs.append(newLog)

    async def __addTask(self, extMethod : ExtensionMethod, args : tuple):
        try: await extMethod.callback(*args)
        except Exception as e: self.__handleExtensionError(extMethod.extension.moduleName, e, extMethod.name)

    def __addLegacy(self, extMethods : typing.List[ExtensionMethod], args : tuple):
        callbacks : typing.List[ExtensionMethod] = []
        for extMethod in extMethods:
            if extMethod.asyncMethod == False:
                callbacks.append(extMethod)

        if len(callbacks) == 0: return

        t = threading.Thread(target=self.__legacyExecuter, args=(callbacks,args), daemon=True, name='LE_Thread')
        self.__legacyThreads.append(t)
        t.start()

    def __legacyExecuter(self, extMethods : typing.List[ExtensionMethod], args : tuple):
        t = threading.current_thread()
        for extMethod in extMethods:
            try: extMethod.callback(*args)
            except Exception as e: self.__handleExtensionError(extMethod.extension.moduleName, e, 'legacy execute')
        self.__legacyThreads.remove(t)

    async def __ticker(self):
        while True:
            await asyncio.sleep(1)

            self.__addLegacy(self.__legacyCallbacks.get('tick', []), tuple())
            
            for i in self.__callbacks.get('tick', []):
                await i.callback()
