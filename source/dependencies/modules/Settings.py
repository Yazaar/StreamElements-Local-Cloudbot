import json, copy, asyncio
from pathlib import Path
from . import Misc
from .vendor.StructGuard import StructGuard

class Settings():
    def __init__(self):
        datafolder = Path('dependencies/data')
        
        self.__generalSettingsFile = datafolder / 'settings/general.json'
        self.__twitchSettingsFile = datafolder / 'settings/twitch.json'
        self.__discordSettingsFile = datafolder / 'settings/discord.json'
        self.__streamelementsSettingsFile = datafolder / 'settings/streamelements.json'

        self.__extensionPermissionsFile = datafolder / 'permissions/extensions.json'
        self.__urlPermissionsFile = datafolder / 'permissions/urls.json'

        self.__defaultPort = 80
        self.port : int = None

        loop = asyncio.get_event_loop()

        self.currentPort : int = None
        self.currentIP : str = None
        
        loop.create_task(self.__getIP())

        self.__twitch : list[dict] = []
        self.__twitchStructure = [
            {
                'tmi': str,
                'botname': str,
                'channels': [str],
                'alias': str,
                'regularGroups': [str],
                'channel': {
                    str: {
                        'regularGroups': [str]
                    }
                }
            }
        ]

        self.__streamelements : list[dict] = []
        self.__streamelementsStructure = [
            {
                'jwt': str,
                'alias': str,
                'useSocketIO': bool
            }
        ]
        
        self.__discord : list[dict] = []
        self.__discordStructure = [
            {
                'token': str,
                'alias': str,
                'regularGroups': [str],
                'guild': {
                    str: {
                        'regularGroups': [str]
                    }
                }
            }
        ]

        self.__loadSettings()
    
    async def __getIP(self):
        currentIP, errorCode = await Misc.fetchUrl('https://ident.me')
        if errorCode < 0: currentIP, errorCode = await Misc.fetchUrl('https://api.ipify.org')
        if errorCode < 0: print('[ERROR]: Unable to check for your public IP, no network connection? (trying to run anyway)')
        self.currentIP = currentIP
    
    def __filterYield(self, obj : list, *, filterMethod = None):
        if filterMethod == None: filterMethod = lambda _: True
        for i in obj:
            iCopy = copy.deepcopy(i)
            try:
                if not filterMethod(iCopy): continue
            except Exception: continue
            yield iCopy    
    
    def getTwitch(self, *, filterMethod = None):
        for twitch in self.__filterYield(self.__twitch, filterMethod=filterMethod):
            yield twitch
    
    def getDiscord(self, *, filterMethod = None):
        for discord in self.__filterYield(self.__discord, filterMethod=filterMethod):
            yield discord
    
    def getStreamElements(self, *, filterMethod = None):
        for streamelements in self.__filterYield(self.__streamelements, filterMethod=filterMethod):
            yield streamelements

    def __loadSettings(self):
        generalSettings = self.__readFile(self.__generalSettingsFile)
        if not isinstance(generalSettings, dict) or (port := generalSettings.get('port', None)) == None or not isinstance(port, int):
            self.port = self.__defaultPort
            self.__saveSettings({'port': self.port}, self.__generalSettingsFile)
        else: self.port = port

        portOverride = Misc.portOverride(self.port)
        if portOverride[0]: self.currentPort = portOverride[1]
        else: self.currentPort = self.port

        twitchChanges, self.__twitch = StructGuard.verifyListStructure(self.__readFile(self.__twitchSettingsFile), self.__twitchStructure)
        if twitchChanges != StructGuard.NO_CHANGES: self.__saveSettings(self.__twitch, self.__twitchSettingsFile)
        
        discordChanges, self.__discord = StructGuard.verifyListStructure(self.__readFile(self.__discordSettingsFile), self.__discordStructure)
        if discordChanges != StructGuard.NO_CHANGES: self.__saveSettings(self.__discord, self.__discordSettingsFile)
        
        streamelementsChanges, self.__streamelements = StructGuard.verifyListStructure(self.__readFile(self.__streamelementsSettingsFile), self.__streamelementsStructure)
        if streamelementsChanges != StructGuard.NO_CHANGES: self.__saveSettings(self.__streamelements, self.__streamelementsSettingsFile)

    def __readFile(self, filepath : Path):
        if not filepath.is_file(): return None
        with open(filepath, 'r') as f:
            try: return json.load(f)
            except Exception: return None

    def __saveSettings(self, obj, filepath : Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f: json.dump(obj, f)
