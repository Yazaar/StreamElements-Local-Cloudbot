from .vendor.StructGuard import StructGuard
from . import Discord, Twitch, StreamElements, Settings, Regulars, Web, ExtensionCrossover, SettingsUI, MinorExtensionArgs
import importlib, inspect, asyncio, threading, socketio, json, time
from pathlib import Path

class Extension():
    def __init__(self, extensions, modulePath : Path):
        self.extensions : Extensions = extensions
        self.__asyncExtensionCrossover = None
        self.__legacyExtensionCrossover = None

        self.__modulePath = modulePath
        self.enabled = False

        self.methods : dict[str, ExtensionMethod] = {}
        self.__importName : str = self.__modulePath.as_posix().replace('/', '.')[:-3]
        self.moduleName : str = self.__importName[11:]

        self.__module = None

        # TODO: exception management
        self.error : bool = False
        self.errorData : Exception = None

        self.reload()
    
    @property
    def asyncExtensionCrossover(self):
        if self.asyncExtensionCrossover == None: self.__asyncExtensionCrossover = ExtensionCrossover.AsyncExtensionCrossover(self.extensions)
        return self.__asyncExtensionCrossover

    @property
    def legacyExtensionCrossover(self):
        if self.legacyExtensionCrossover == None: self.__legacyExtensionCrossover = ExtensionCrossover.LegacyExtensionCrossover(self.extensions)
        return self.__legacyExtensionCrossover

    def __loadModule(self):
        try:
            self.__module = importlib.import_module(self.__importName)
            self.error = False
            self.errorData = None
        except Exception as e:
            self.errorData = e
            self.__module = None
            self.error = True
    
    def __loadMethods(self):
        self.methods.clear()
        
        if (self.error): return

        moduleItems = dir(self.__module)
        for moduleItem in moduleItems:
            attr = getattr(self.__module, moduleItem)
            if ExtensionMethod.isFuncOrMethod(attr):
                extMethod = ExtensionMethod(attr, self)
                if extMethod.name != None:
                    self.methods[extMethod.name] = extMethod

    def reload(self):
        if self.__module == None: self.__loadModule()
        else: self.__module = importlib.reload(self.__module)
        self.__loadMethods()

    def getEndpoint(self, endpointStr : str):
        endpoint = self.methods.get(endpointStr, None)
        if endpoint == None: return None
        return endpoint

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
        'webhook': {
            'alias': ['Webhook'],
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
            for funcAlias in ExtensionMethod.ENDPOINTS[realFuncName]['alias']:
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
        self.regulars = Regulars.Regulars()

        self.__twitchInstances : list[Twitch.Twitch] = []
        self.__discordInstances : list[Discord.Discord] = []
        self.__streamElementsInstances : list[StreamElements.StreamElements] = []

        self.__callbacks : dict[str, list[ExtensionMethod]] = {}
        self.__legacyCallbacks : dict[str, list[ExtensionMethod]] = {}

        self.__legacyThreads : list[threading.Thread] = []

        self.__extensionsPath = Path('extensions')

        self.logs = []

        self.__enabledExtensionsPath = Path('dependencies/data/enabled.json')
        self.__enabledExtensions = self.__loadEnabled(self.__enabledExtensionsPath)

        self.extensions : list[Extension] = []
        self.settings : list[SettingsUI.SettingsUI] = []

        self.__loadExtensions(self.__extensionsPath)

        enabledChanged, self.__enabledExtensions = self.__verifyEnabled(self.__enabledExtensions, self.extensions)
        if enabledChanged: self.__saveEnabled(self.__enabledExtensions, self.__enabledExtensionsPath)

        self.__loop = asyncio.get_event_loop()

        self.__loop.create_task(self.__ticker())

    def findTwitch(self, *, alias : str = None, id_ : str = None):
        if (not isinstance(alias, str)) and (not isinstance(id_, str)): return
        for i in self.__twitchInstances:
            if i.alias == alias or i.id == id_: return i
    
    def findDiscord(self, *, alias : str = None, id_ : str = None):
        if (not isinstance(alias, str)) and (not isinstance(id_, str)): return
        for i in self.__discordInstances:
            if i.alias == alias or i.id == id_: return i
    
    def findStreamElements(self, *, alias : str = None, id_ : str = None):
        if (not isinstance(alias, str)) and (not isinstance(id_, str)): return
        for i in self.__streamElementsInstances:
            if i.alias == alias or i.id == id_: return i
    
    def defaultStreamElements(self):
        if len(self.__streamElementsInstances) == 0: return None
        return self.__streamElementsInstances[0]
    
    def defaultTwitch(self):
        if len(self.__twitchInstances) == 0: return None
        return self.__twitchInstances[0]
    
    def defaultDiscord(self):
        if len(self.__discordInstances) == 0: return None
        return self.__discordInstances[0]
    
    def loadServices(self):
        self.__twitchInstances = self.__loadTwitchInstances()
        self.__discordInstances = self.__loadDiscordInstances()
        self.__streamElementsInstances = self.__loadStreamElementsInstances()

    def reloadExtensions(self):
        self.__unloadExtensions()
        self.__loadExtensions(self.__extensionsPath)
    
    def toggleExtension(self, moduleName : str, enabled : bool):
        matchExt = self.__extensionByName(moduleName)
        if matchExt == None: return False
        isEnabled = moduleName in self.__enabledExtensions
        if enabled:
            if not isEnabled: self.__enabledExtensions.append(moduleName)
        else:
            if isEnabled: self.__enabledExtensions.remove(moduleName)
        matchExt.enabled = enabled
        self.__saveEnabled(self.__enabledExtensions, self.__enabledExtensionsPath)
        return True

    def __extensionByName(self, moduleName : str):
        for ext in self.extensions:
            if ext.moduleName == moduleName: return ext
        return None

    def addTwitchInstance(self, alias : str, tmi : str, botname : str, channels : list[str]):
        twitchInstance = Twitch.Twitch(alias, self, tmi, botname, channels, [])
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
        for i in self.extensions:
            if i.moduleName == extension.moduleName: return
        self.extensions.append(extension)

        self.__loadMethods(extension)

    def removeExtension(self, extension : Extension):
        for index, ext in enumerate(self.extensions):
            if ext.moduleName == extension.moduleName:
                self.extensions.pop(index)
                break
        
        self.__unloadMethods(extension)
    
    def reloadExtension(self, moduleName : str):
        matchingExtension : Extension = None
        for ext in self.extensions:
            if ext.moduleName == moduleName:
                matchingExtension = ext
                break
        if matchingExtension == None: return False
        
        matchingExtension.reload()
        self.__loadMethods(matchingExtension)
        return True
    
    def initialize(self, extension : Extension):
        ep = extension.getEndpoint('initialize')
        if ep == None: return
        if ep.asyncMethod: self.__loop.create_task(self.__addTask(ep, tuple()))
        else: self.__addLegacy([ep], tuple())

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

    def webhook(self, moduleName : str, wh : Web.Webhook):
        print('[CORE] webhook')
        for extMethod in self.__callbacks.get('webhook', []):
            if extMethod.extension.moduleName == moduleName:
                self.__loop.create_task(self.__addTask(extMethod, (wh, )))
                return
        
        for extMethod in self.__legacyCallbacks.get('webhook', []):
            if extMethod.extension.moduleName == moduleName:
                self.__addLegacy([extMethod], wh.legacy())
                return

    def toggle(self, script : str, toggleStatus : bool):
        print('[CORE] toggle')
        for extMethod in self.__callbacks.get('toggle', []):
            if extMethod.extension.moduleName == script:
                self.__loop.create_task(self.__addTask(extMethod, (toggleStatus,)))
                break

    def crossTalk(self, data : Web.CrossTalk, scripts : list[str], events : list[str]) -> tuple[bool, str | None]:
        print('[CORE] cross talk')

        structs = [str]
        if isinstance(scripts, list): scripts = scripts.copy()
        if isinstance(events, list): events = events.copy()

        if not StructGuard.verifyListStructure(scripts, structs)[0]: return False, 'Invalid scripts, should be a list with string items'
        if not StructGuard.verifyListStructure(events, structs)[0]: return False, 'Invalid events, should be a list with string items'

        for event in events: self.__loop.create_task(self.__websio.emit(event, data, broadcast=True))

        if len(scripts) == 0: return True, None

        for extMethod in self.__callbacks.get('crossTalk', []):
            if extMethod.extension.moduleName in scripts: self.__loop.create_task(self.__addTask(extMethod, (data, )))
        
        legacyCallbacks = []
        for extMethod in self.__legacyCallbacks.get('crossTalk', []):
            if extMethod.extension.moduleName in scripts: legacyCallbacks.append(extMethod)
        
        if len(legacyCallbacks) != 0: self.__addLegacy(legacyCallbacks, data.legacy())

        return True, None

    def newSettings(self, changedSettingsUI : SettingsUI.SettingsUI):
        print('[CORE] new settings')
        changedSettings = SettingsUI.Settings(changedSettingsUI)
        settingObj = changedSettings.settings
        for event in changedSettingsUI.events: self.__loop.create_task(self.__websio.emit(event, settingObj, broadcast=True))
        legacies = []
        for extName in changedSettingsUI.scripts:
            extObj = self.__extensionByName(extName)
            if not extObj: continue
            extMethod = extObj.getEndpoint('newSettings')
            if not extMethod: continue
            if extMethod.asyncMethod: self.__loop.create_task(self.__addTask(extMethod, (changedSettings,)))
            else: legacies.append(extMethod)
        if len(legacies) > 0: self.__addLegacy(legacies, (changedSettings.legacy(),))

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

    def __loadEnabled(self, enabledPath : Path) -> list[str]:
        if not enabledPath.exists(): return []

        with open(enabledPath, 'r') as f:
            try: enabled = json.load(f)
            except Exception: return []
        
        if not isinstance(enabled, list): return []

        for index in reversed(range(len(enabled))):
            if not isinstance(enabled[index], str): enabled.pop(index)

        return enabled
    
    def __loadMethods(self, extension : Extension):
        self.__unloadMethods(extension)
        for method in extension.methods:
            extMethod = extension.methods[method]
            if extMethod.asyncMethod:
                callbackList = self.__callbacks.get(method, None)
                if callbackList == None: callbackList = self.__callbacks[method] = []
            else:
                callbackList = self.__legacyCallbacks.get(method, None)
                if callbackList == None: callbackList = self.__legacyCallbacks[method] = []
            callbackList.append(extension.methods[method])

    def __unloadMethods(self, extension : Extension):
        for methodName in extension.methods:
            if extension.methods[methodName].asyncMethod:
                callbacks = self.__callbacks.get(methodName, [])
            else:
                callbacks = self.__legacyCallbacks.get(methodName, [])
            for index in reversed(range(len(callbacks))):
                if callbacks[index].extension.moduleName == extension.moduleName:
                    callbacks.pop(index)
                    break
    
    def __verifyEnabled(self, enabled : list[str], extensions : list[Extension]) -> tuple[bool, list[str]]:
        changes = False

        if not isinstance(enabled, list):
            return True, []

        for index in reversed(range(len(enabled))):
            item = enabled[index]
            if not isinstance(item, str):
                enabled.pop(index)
                changes = True
                continue

            extExists = False
            for ext in extensions:
                if item == ext.moduleName:
                    extExists = True
                    break
            if not extExists or enabled.count(item) > 1:
                enabled.pop(index)
                changes = True

        for ext in extensions:
            isEnabled = ext.moduleName in enabled
            if ext.enabled and not isEnabled:
                enabled.append(ext.moduleName)
                changes = True
            elif isEnabled and not ext.enabled:
                enabled.remove(ext.moduleName)
                changes = True

        return changes, enabled

    def __saveEnabled(self, enabled : list[str], enabledPath : Path):
        enabledPath.parent.mkdir(parents=True, exist_ok=True)
        with open(enabledPath, 'w') as f:
            json.dump(enabled, f)

    def __extensionEnabled(self, moduleName : str):
        return moduleName in self.__enabledExtensions

    def __find(objects : list, objectId : int):
        for obj in objects:
            if obj.id == objectId:
                return obj
        return None

    def __unloadExtensions(self):
        for i in self.__callbacks: self.__callbacks[i].clear()
        for i in self.__legacyCallbacks: self.__callbacks[i].clear()
        for i in self.extensions: i.reload()
        self.extensions.clear()
        self.settings.clear()

    def __addExtension(self, path : Path):
        newExt = Extension(self, path)
        newExt.enabled = self.__extensionEnabled(newExt.moduleName)
        if newExt.error: self.__handleExtensionError(newExt, newExt.errorData, 'import')
        self.addExtension(newExt)
    
    def __addSetting(self, path : Path):
        try: settingsUI = SettingsUI.SettingsUI(path.parent)
        except SettingsUI.SettingsUIError as e: return False, e.args[0]
        self.settings.append(settingsUI)
    
    def updateSettings(self, data):
        sgResp = StructGuard.verifyDictStructure(data, {
            'name': str,
            'index': int,
            'settings': {
                str: StructGuard.AdvancedType((str, int, float, bool, list), str)
            }
        }, rebuild=False)[0]
        if sgResp == StructGuard.INVALID: return False, 'Update settings data dict has invalid keys and values. Check documentation.'

        try: setting = self.settings[data[data['index']]]
        except Exception: setting = None

        if (not setting is None) and setting['name'] != data['name']: setting = None

        if setting is None:
            for i in self.settings:
                if i.name == data['name']:
                    setting = i
                    break
        
        if setting is None: return False, 'Update settings key index is invalid (have to be an int in range of existing settings or matching name for key name)'
        
        setting.update(data['settings'])

        self.newSettings(setting)

    def __loadExtensions(self, path : Path) -> None:
        for f in path.glob('*'):
            if f.is_dir(): self.__loadExtensions(f)
            elif f.name.endswith('_LSE.py'): self.__addExtension(f)
            elif f.name == 'SettingsUI.json': self.__addSetting(f)

    def __loadTwitchInstances(self):
        instances = []
        for twitch in self.__settings.getTwitch():
            instances.append(Twitch.Twitch(twitch['alias'], self, twitch['tmi'], twitch['botname'], twitch['channels'].copy(), twitch['regularGroups']))
        return instances

    def __loadDiscordInstances(self):
        instances = []
        for discord in self.__settings.getDiscord():
            instances.append(Discord.Discord(discord['alias'], self, discord['token']))
        return instances

    def __loadStreamElementsInstances(self):
        instances = []
        for streamelements in self.__settings.getStreamElements():
            instances.append(StreamElements.StreamElements(streamelements['alias'], self, streamelements['jwt'], streamelements['useSocketIO']))
        return instances

    def __handleExtensionError(self, ext : Extension, exception : Exception, executionType : str):
        #if isinstance(rawModuleName, str): moduleName = rawModuleName[11:]
        #elif isinstance(rawModuleName, types.ModuleType): moduleName = rawModuleName.__name__[11:]
        #else: moduleName = 'unknown'
        newLog = {
            'module': ext.moduleName[11:],
            'message': str(exception) + ' (' + executionType + ')'
        }
        self.toggleExtension(ext.moduleName, False)
        self.logs.append(newLog)

    async def __addTask(self, extMethod : ExtensionMethod, args : tuple):
        if not extMethod.extension.enabled: return
        try: await extMethod.callback(*args)
        except Exception as e: self.__handleExtensionError(extMethod.extension, e, extMethod.name)

    def __addLegacy(self, extMethods : list[ExtensionMethod], args : tuple):
        callbacks : list[ExtensionMethod] = []
        for extMethod in extMethods:
            if (not extMethod.asyncMethod) and extMethod.extension.enabled:
                callbacks.append(extMethod)

        if len(callbacks) == 0: return

        t = threading.Thread(target=self.__legacyExecuter, args=(callbacks,args), daemon=True, name='LE_Thread')
        self.__legacyThreads.append(t)
        t.start()

    def __legacyExecuter(self, extMethods : list[ExtensionMethod], args : tuple):
        t = threading.current_thread()
        for extMethod in extMethods:
            try: extMethod.callback(*args)
            except Exception as e: self.__handleExtensionError(extMethod.extension, e, 'legacy execute')
        self.__legacyThreads.remove(t)

    async def __ticker(self):
        arg = tuple()
        prev_time_ns = time.time_ns()
        while True:
            await asyncio.sleep(1)

            self.__addLegacy(self.__legacyCallbacks.get('tick', []), arg)
            
            tickArg = MinorExtensionArgs.Tick(prev_time_ns)
            for i in self.__callbacks.get('tick', []):
                await self.__addTask(i, (tickArg,))
