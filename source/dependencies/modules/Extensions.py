import json, importlib, threading, time, ctypes, sys
from pathlib import Path
from .ExtensionCrossover import ExtensionCrossover

class Extensions():
    def __init__(self, chat, SE, users, SIO, appContext, serverPort):
        self.__chat = chat
        self.__SE = SE
        self.__users = users
        self.__SIO = SIO
        self.__appContext = appContext
        self.__serverPort = serverPort
        self.__crossover = ExtensionCrossover(serverPort, self.__chat.connectedTwitchChannel, self.__chat.connectedTwitchBotname)

        self.__executionDelay = 1 / 60
        self.log = []
        self.__extensions = []
        self.settings = []
        self.__enabled = self.__loadEnabled()
        self.__loadExtensions(Path('extensions'))

        self.initializeHandles = [{'port': self.__serverPort, 'twitch_channel': self.__chat.connectedTwitchChannel, 'twitch_bot_name': self.__chat.connectedTwitchBotname}]
        self.newSettingsHandles = []
        self.crossTalkHandles = []
        self.webHookHandles = []
        self.toggleHandles = []
        
        self.__thread = threading.Thread(target=self.__extensionsThread, daemon=True, name='ExtensionThread')
        self.__thread.start()

        Path('extensions').mkdir(parents=True, exist_ok=True)

        threading.Thread(target=self.__dataInThread, daemon=True, name='DataIn').start()

    def setCrossoverData(self, twitchChannel=None, twitchBotName=None):
        self.__crossover.setAttributes(twitchChannel, twitchBotName)

    def setData(self, executionsPerSecond=None):
        if isinstance(executionsPerSecond, (int, float)):
            self.__executionDelay = 1 / executionsPerSecond
    
    def crossTalk(self, content):
        if not isinstance(content, dict):
            return False, 'Please forward JSON: requests.post(url, json=JSON_DATA) / socket.emit(event, json)'
        if not 'event' in content or not isinstance(content['event'], str):
            return False, 'JSON require the key \"event\"'
        if not 'data' in content:
            return False, 'JSON require the key \"data\"'
        if content['event'][:2] != 'p-':
            return False, 'Value of the key \"event\" has to start with \"p-\", example: \"p-example\"'
        with self.__appContext:
            self.__SIO.emit(content['event'], content['data'], broadcast=True)
        return True, None
    
    def scriptTalk(self, content):
        if not isinstance(content, dict):
            return False, 'Please forward json... requests.post(url, json=JSON_DATA) / socket.emit(event, json)'
        if not 'module' in content:
            return False, 'JSON require the key \"module\"'
        if not 'data' in content:
            return False, 'JSON require the key \"data\"'
        if not isinstance(content['module'], str) or len(content['module']) == 0:
            return False, 'Invalid module'
        self.crossTalkHandles.append({'module': content['module'], 'data': content['data']})
        return True, None

    def resetExtensions(self):
        for i in threading._active.items():
            if i[1] == self.__thread:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(i[0], ctypes.py_object(SystemExit))
                self.__thread = None
                break

        for i in self.__extensions:
            if i['module'].__name__ in sys.modules:
                del sys.modules[i['module'].__name__]
        
        self.__extensions.clear()
        self.settings.clear()

        self.__loadExtensions(Path('extensions'))
        
        self.__thread = threading.Thread(target=self.__extensionsThread, daemon=True, name='ExtensionThread')
        self.__thread.start()

        self.initializeHandles.append({'port': self.__serverPort, 'twitch_channel': self.__chat.connectedTwitchChannel, 'twitch_bot_name': self.__chat.connectedTwitchBotname})

    def __loadExtensions(self, directory):
        if not isinstance(directory, Path): return

        glob = directory.glob('*')
        
        for i in glob:
            if i.is_dir():
                self.__loadExtensions(i)
            elif i.name[-7:] == '_LSE.py':
                self.addExtension(i)
            elif i.name == 'SettingsUI.json':
                self.addSetting(i)

    def addSetting(self, settingPath):
        if not isinstance(settingPath, Path) or not settingPath.is_file(): return

        with open(settingPath, 'r') as f:
            try: settings = json.load(f)
            except Exception: return

        if not self.__validateSettings(settings): return

        Path(settings['path'])

        configPath = Path(settings['path']) / 'settings.json'

        if configPath.is_file():
            with open(configPath, 'r') as f:
                try: config = json.load(f)
                except Exception: config = {}
        else:
            config = {}

        changes = False

        for setting in settings['settings']:
            notFound = True
            for settingName in config:
                if setting == settingName:
                    settings['settings'][setting]['current_value'] = config[settingName]
                    notFound = False
                    break
            if notFound:
                settings['settings'][setting]['current_value'] = settings['settings'][setting]['value']
                config[setting] = settings['settings'][setting]['value']
                changes = True
        
        
        self.settings.append(settings)
        if changes:
            self.__saveSettings(len(self.settings)-1)

    def addExtension(self, pyPath):
        if not isinstance(pyPath, Path) or not pyPath.is_file(): return
        importPath = pyPath.relative_to(Path()).as_posix()[:-3].replace('/', '.')

        self.__extensions.append({
            'active': importPath in self.__enabled,
            'module': importlib.import_module(importPath)
        })

    def __validateSettings(self, settings):
        if not isinstance(settings, dict): return False

        if not 'name' in settings or not 'path' in settings or not 'settings' in settings: return False

        if not isinstance(settings['name'], str) or not isinstance(settings['path'], str) or not isinstance(settings['settings'], dict): return False

        for setting in settings['settings']:
            if not 'value' in settings['settings'][setting]: return False
            if settings['settings'][setting]['type'].lower() == 'dropdown':
                if not 'choices' in settings['settings'][setting] or not isinstance(settings['settings'][setting]['choices'], list):
                    return False
                if not settings['settings'][setting]['value'] in settings['settings'][setting]['choices']:
                    return False

        return True
    
    def updateSettings(self, index, name, new_settings):
        if self.settings[index]['name'] == name:
            settings = self.settings[index]['settings']
        else:
            for settingIndex in range(len(self.settings)):
                if self.settings[settingIndex]['name'] == name:
                    settings = self.settings[settingIndex]['settings']
                    index = settingIndex
                    break
        
        for setting in settings:
            if not setting in new_settings: continue
            settings[setting]['current_value'] = new_settings[setting]
        
        self.__saveSettings(index)
    
    def __loadEnabled(self):
        enabledPath = Path('dependencies/data/enabled.json')
        enabledPath.parent.mkdir(parents=True, exist_ok=True)

        if enabledPath.is_file():
            with open(enabledPath, 'r') as f:
                try: enabled = json.load(f)
                except Exception: enabled = []
        else:
            enabled = []
        
        if isinstance(enabled, list): return enabled
        else: return []
    
    def __saveSettings(self, index):
        if not isinstance(index, int) or index < 0 or index >= len(self.settings): return

        content = {}

        for setting in self.settings[index]['settings']:
            if 'current_value' in self.settings[index]['settings'][setting]:
                content[setting] = self.settings[index]['settings'][setting]['current_value']
            elif 'value' in self.settings[index]['settings'][setting]:
                content[setting] = self.settings[index]['settings'][setting]['value']

        content = json.dumps(content)

        path = Path(self.settings[index]['path'])
        path.mkdir(parents=True, exist_ok=True)
        with open (path / 'settings.json', 'w') as f:
            f.write(content)
        with open (path / 'settings.js', 'w') as f:
            f.write('var settings = ' + content + ';')

    def __saveEnabled(self):
        enabledPath = Path('dependencies/data/enabled.json')
        enabledPath.parent.mkdir(parents=True, exist_ok=True)
        with open(enabledPath, 'w') as f:
            json.dump(self.__enabled, f)
    
    def toggle(self, raw_module, enable=None):
        module = 'extensions.' + raw_module
        if module in self.__enabled:
            if enable == True:
                return
            self.__enabled.remove(module)
            toValue = False
        else:
            if enable == False:
                return
            self.__enabled.append(module)
            toValue = True
        
        for extension in self.__extensions:
            if extension['module'].__name__ == module:
                extension['active'] = toValue
                break
        
        self.__saveEnabled()

    def dump(self):
        dumped = []
        for extension in self.__extensions:
            dumped.append({
                'active': extension['active'],
                'module': extension['module'].__name__[11:]
            })
        return dumped
    
    def __dataInThread(self):
        while True:
            time.sleep(self.__executionDelay * 10)
            
            while True:
                event = self.__crossover.GetValue()
                if not event['success'] or event['event'] == None:
                    break
                if event['event'] == 'StreamElementsAPI':
                    self.__SE.APIRequest(event['data'])
                if event['event'] == 'SendMessage':
                    self.__chat.addMessage(event['data'])
                if event['event'] == 'CrossTalk':
                    self.crossTalk(event['data'])
                if event['event'] == 'ScriptTalk':
                    self.scriptTalk(event['data'])
                if event['event'] == 'AddRegulars':
                    self.__users.addRegular(event['data'])
                if event['event'] == 'DeleteRegulars':
                    self.__users.removeRegular(event['data'])

    def __handleExtensionError(self, item, e, action):
        module = item['module'].__name__[11:]
        entry = {'module': module, 'message': str(e) + ' (' + action + ')'}
        self.log.append(entry)
        self.toggle(module, False)
        with self.__appContext:
            self.__SIO.emit('log', entry, broadcast=True)

    def __extensionsThread(self):
        while True:
            if len(self.initializeHandles) > 0:
                execType = 'initialize'
                execData = self.initializeHandles.pop(0)
            elif len(self.newSettingsHandles) > 0:
                execType = 'newsettings'
                execData = self.newSettingsHandles.pop(0)
            elif len(self.crossTalkHandles) > 0:
                execType = 'talk'
                execData = self.crossTalkHandles.pop(0)
            elif len(self.webHookHandles) > 0:
                execType = 'webhook'
                execData = self.webHookHandles.pop(0)
            elif len(self.toggleHandles) > 0:
                execType = 'toggle'
                execData = self.toggleHandles.pop(0)
            else:
                execData = self.__SE.getEvent()
                if execData != None:
                    execType = 'event'
                else:
                    execData = self.__SE.getTestEvent()
                    if execData != None:
                        execType = 'testevent'
                    else:
                        execData = self.__chat.getNextTwitchMessage()
                        if execData != None:
                            execType = 'execute'
                        else:
                            execType = 'tick'
            
            for i in self.__extensions:
                if execType == 'tick':
                    if i['active'] and 'Tick' in dir(i['module']):
                        try:
                            i['module'].Tick()
                        except Exception as e:
                            self.__handleExtensionError(i, e, execType)
                elif execType == 'testevent':
                    if i['active'] and 'TestEvent' in dir(i['module']):
                        try:
                            i['module'].TestEvent(execData)
                        except Exception as e:
                            self.__handleExtensionError(i, e, execType)
                elif execType == 'execute':
                    if i['active'] and 'Execute' in dir(i['module']):
                        try:
                            i['module'].Execute(execData)
                        except Exception as e:
                            self.__handleExtensionError(i, e, execType)
                elif execType == 'initialize':
                    if 'Initialize' in dir(i['module']):
                        try:
                            i['module'].Initialize(execData.copy(), self.__crossover)
                        except Exception as e:
                            self.__handleExtensionError(i, e, execType)
                elif execType == 'talk':
                    if i['module'].__name__[11:] == execData['module'] and i['active'] and 'CrossTalk' in dir(i['module']):
                        try:
                            i['module'].CrossTalk(execData['data'])
                        except Exception as e:
                            self.__handleExtensionError(i, e, execType)
                elif execType == 'webhook':
                    if i['module'].__name__[11:] == execData['module'] and i['active'] and 'webhook' in dir(i['module']):
                        try:
                            i['module'].webhook(execData)
                        except Exception as e:
                            self.__handleExtensionError(i, e, execType)
                elif execType == 'toggle':
                    if i['module'].__name__ == execData['module'].__name__:
                        try:
                            i['module'].Toggle(execData['active'])
                        except Exception as e:
                            self.__handleExtensionError(i, e, execType)
                elif execType == 'newsettings':
                    if i['module'].__name__ == execData['module'] and 'NewSettings' in dir(i['module']):
                        try:
                            i['module'].NewSettings(execData['settings'])
                        except Exception as e:
                            self.__handleExtensionError(i, e, execType)
                else: # StreamElementsEvent
                    if i['active'] and 'Event' in dir(i['module']):
                        try:
                            i['module'].Event(execData.copy())
                        except Exception as e:
                            self.__handleExtensionError(i, e, execType)
            time.sleep(self.__executionDelay)

