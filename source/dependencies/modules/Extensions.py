from .vendor.StructGuard import StructGuard
from . import Discord, Twitch, StreamElements, Settings, Regulars, Web, ExtensionCrossover, SettingsUI, MinorExtensionArgs, Misc
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
    def __init__(self, websio : socketio.AsyncServer):
        self.__websio = websio
        self.settings = Settings.Settings(self)
        self.regulars = Regulars.Regulars()

        self.twitchInstances : list[Twitch.Twitch] = []
        self.discordInstances : list[Discord.Discord] = []
        self.streamElementsInstances : list[StreamElements.StreamElements] = []

        self.__callbacks : dict[str, list[ExtensionMethod]] = {}
        self.__legacyCallbacks : dict[str, list[ExtensionMethod]] = {}

        self.__legacyThreads : list[threading.Thread] = []

        self.__extensionsPath = Path('extensions')

        self.logs = []

        self.__enabledExtensionsPath = Path('dependencies/data/enabled.json')
        self.__enabledExtensions = self.__loadEnabled(self.__enabledExtensionsPath)

        self.extensions : list[Extension] = []
        self.settingsUI : list[SettingsUI.SettingsUI] = []

        self.__loadExtensions(self.__extensionsPath)

        enabledChanged, self.__enabledExtensions = self.__verifyEnabled(self.__enabledExtensions, self.extensions)
        if enabledChanged: self.__saveEnabled(self.__enabledExtensions, self.__enabledExtensionsPath)

        self.__loop = asyncio.get_event_loop()

        self.__loop.create_task(self.__ticker())

    def loadServices(self):
        self.twitchInstances = self.settings.loadTwitch()
        self.discordInstances = self.settings.loadDiscord()
        self.streamElementsInstances = self.settings.loadStreamElements()

    def findTwitch(self, *, alias : str = None, id_ : str = None):
        if (not isinstance(alias, str)) and (not isinstance(id_, str)): return
        for i in self.twitchInstances:
            if i.alias == alias or i.id == id_: return i
    
    def findDiscord(self, *, alias : str = None, id_ : str = None):
        if (not isinstance(alias, str)) and (not isinstance(id_, str)): return
        for i in self.discordInstances:
            if i.alias == alias or i.id == id_: return i
    
    def findStreamElements(self, *, alias : str = None, id_ : str = None):
        if (not isinstance(alias, str)) and (not isinstance(id_, str)): return
        for i in self.streamElementsInstances:
            if i.alias == alias or i.id == id_: return i
    
    def defaultStreamElements(self):
        if len(self.streamElementsInstances) == 0: return None
        return self.streamElementsInstances[0]
    
    def defaultTwitch(self):
        if len(self.twitchInstances) == 0: return None
        return self.twitchInstances[0]
    
    def defaultDiscord(self):
        if len(self.discordInstances) == 0: return None
        return self.discordInstances[0]

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
    
    async def updateTwitch(self, tID, tAlias, tTMI, tChannels, tRegualarGroups) -> tuple[bool, str | Twitch.Twitch]:
        if tID == 'NEW':
            tCreated, t = await self.__addTwitchInstance(tAlias, tTMI)
            if not tCreated: return False, t
        else: t = self.findTwitch(id_=tID)
        if t is None: return False, 'Twitch ID not found'
        await t.setTMI(tTMI)
        t.alias = tAlias
        t.setChannels(tChannels)
        t.setRegularGroups(tRegualarGroups)
        if not t.running: t.start()
        self.settings.saveTwitch(self.twitchInstances)
        return True, t
    
    async def updateStreamElements(self, seID, seAlias, seJWT) -> tuple[bool, str | StreamElements.StreamElements]:
        if seID == 'NEW':
            seCreated, se = await self.__addStreamElementsInstance(seAlias, seJWT)
            if not seCreated: return False, se
        else: se = self.findStreamElements(id_=seID)
        if se is None: return False, 'StreamElements ID not found'
        await se.setJWT(seJWT)
        se.alias = seAlias
        if not se.connected: se.startStreamElements()
        self.settings.saveStreamElements(self.streamElementsInstances)
        return True, se
    
    async def updateDiscord(self, dID : str, dAlias : str, dToken : str, dRegularGroups : list[str], *, membersIntent=False, presencesIntent=False, messageContentIntent=False) -> tuple[bool, str | Discord.Discord]:
        if dID == 'NEW':
            dCreated, d = await self.__addDiscordInstance(dAlias, dToken, membersIntent=membersIntent, presencesIntent=presencesIntent, messageContentIntent=messageContentIntent)
            if not dCreated: return False, d
        else: d = self.findDiscord(id_=dID)
        if d is None: return False, 'Discord ID not found'
        await d.setToken(dToken)
        d.alias = dAlias
        d.setRegularGroups(dRegularGroups)
        await d.setIntents(membersIntent=membersIntent, presencesIntent=presencesIntent, messageContentIntent=messageContentIntent)
        self.settings.saveDiscord(self.discordInstances)
        return True, d

    def __newID(self, idPrefix : str, finder):
        idKey = 0
        idSuffix = hex(int(time.time()))[1:]
        while finder(id_=f'{idPrefix}{idKey}{idSuffix}') is not None: idKey += 1
        return f'{idPrefix}{idKey}{idSuffix}'
    
    def newDiscordID(self): return self.__newID('dc:', self.findDiscord)

    def newStreamElementsID(self): return self.__newID('se:', self.findStreamElements)

    def newTwitchID(self): return self.__newID('tw:', self.findTwitch)

    async def __addTwitchInstance(self, alias : str, tmi : str) -> tuple[bool, str | Twitch.Twitch]:
        if len(alias) == 0: return False, 'alias have to be a string with a length larger than 0'

        tmi, botname, errorMsg = await Twitch.Twitch.parseTMI(tmi)
        if tmi is None or botname is None: return False, errorMsg

        twitchInstance = Twitch.Twitch(self.newTwitchID(), alias, self, tmi, botname, [], [], {})
        self.twitchInstances.append(twitchInstance)
        return True, twitchInstance

    def removeTwitchInstance(self, twitchId : int):
        removeThis : Twitch.Twitch = self.__find(self.twitchInstances, twitchId)
        if removeThis != None:
            self.twitchInstances.remove(removeThis)
            removeThis.stopTwitch()
            self.settings.saveTwitch(self.twitchInstances)

    async def __addDiscordInstance(self, alias : str, token : str, *, membersIntent=False, presencesIntent=False, messageContentIntent=False):
        if len(alias) == 0: return False, 'alias have to be a string with a length larger than 0'
        validToken, errorMsgOrBotname = await Discord.Discord.parseToken(token)
        if not validToken: return False, errorMsgOrBotname

        discordInstance = Discord.Discord(self.newDiscordID(), alias, self, token, [], {}, membersIntent=membersIntent, presencesIntent=presencesIntent, messageContentIntent=messageContentIntent)
        self.discordInstances.append(discordInstance)
        self.settings.saveDiscord(self.discordInstances)
        return True, discordInstance

    def removeDiscordInstance(self, discordId : int):
        removeThis : Discord.Discord = self.__find(self.discordInstances, discordId)
        if removeThis != None:
            self.discordInstances.remove(removeThis)
            removeThis.stopDiscord()
            self.settings.saveDiscord(self.discordInstances)

    async def __addStreamElementsInstance(self, alias : str, jwt : str) -> tuple[bool, str] | tuple[bool, StreamElements.StreamElements]:
        accountName, errorMsg = await StreamElements.StreamElements.parseJWT(jwt)
        if accountName is None: return False, errorMsg
        streamElementsInstance = StreamElements.StreamElements(self.newStreamElementsID(), alias, self, jwt)
        self.streamElementsInstances.append(streamElementsInstance)
        return True, streamElementsInstance

    def removeStreamElementsInstance(self, streamElementsId : int):
        removeThis : StreamElements.StreamElements = self.__find(self.streamElementsInstances, streamElementsId)
        if removeThis != None:
            self.streamElementsInstances.remove(removeThis)
            removeThis.stopStreamElements()

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
        self.settingsUI.clear()

    def __addExtension(self, path : Path):
        newExt = Extension(self, path)
        newExt.enabled = self.__extensionEnabled(newExt.moduleName)
        if newExt.error: self.__handleExtensionError(newExt, newExt.errorData, 'import')
        self.addExtension(newExt)
    
    def __addSetting(self, path : Path):
        try: settingsUI = SettingsUI.SettingsUI(path.parent)
        except SettingsUI.SettingsUIError as e: return False, e.args[0]
        self.settingsUI.append(settingsUI)
    
    def updateSettings(self, data):
        sgResp = StructGuard.verifyDictStructure(data, {
            'name': str,
            'index': int,
            'settings': {
                str: StructGuard.AdvancedType((str, int, float, bool, list), str)
            }
        }, rebuild=False)[0]
        if sgResp == StructGuard.INVALID: return False, 'Update settings data dict has invalid keys and values. Check documentation.'

        try: setting = self.settingsUI[data[data['index']]]
        except Exception: setting = None

        if (not setting is None) and setting['name'] != data['name']: setting = None

        if setting is None:
            for i in self.settingsUI:
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
