import json, asyncio, typing
from pathlib import Path
from . import Twitch, Discord, StreamElements, Misc
from .vendor.StructGuard import StructGuard

if typing.TYPE_CHECKING:
    from . import Extensions

class Settings():
    def __init__(self, extensions : 'Extensions.Extensions'):
        datafolder = Path('dependencies/data')

        self.__extensions = extensions
        
        self.__generalSettingsFile = datafolder / 'settings/general.json'
        self.__twitchSettingsFile = datafolder / 'settings/twitch.json'
        self.__discordSettingsFile = datafolder / 'settings/discord.json'
        self.__streamelementsSettingsFile = datafolder / 'settings/streamelements.json'

        self.__extensionPermissionsFile = datafolder / 'permissions/extensions.json'
        self.__urlPermissionsFile = datafolder / 'permissions/urls.json'

        self.__defaultTickrate = 60
        self.__tickrate = 60

        self.__defaultPort = 80
        self.__port : int = None

        loop = asyncio.get_event_loop()

        self.__currentPort : int = None
        self.__currentIP : str = None
        
        loop.create_task(self.__getIP())

        self.__twitchStructure = [
            {
                'id': str,
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

        self.__streamelementsStructure = [
            {
                'id': str,
                'jwt': str,
                'alias': str
            }
        ]
        
        self.__discordStructure = [
            {
                'id': str,
                'token': str,
                'alias': str,
                'regularGroups': [str],
                'membersIntent': bool,
                'presencesIntent': bool,
                'messageContentIntent': bool,
                'guild': {
                    str: {
                        'regularGroups': [str]
                    }
                }
            }
        ]

        self.__generalStucture = {
            'port': int,
            'tickrate': int
        }

        self.__loadSettings()
    
    @property
    def currentPort(self): return self.__currentPort
    
    @property
    def currentIP(self): return self.__currentIP

    @property
    def tickrate(self) -> int: return self.__tickrate

    @property
    def port(self) -> int: return self.__port

    async def __getIP(self):
        currentIP, errorCode = await Misc.fetchUrl('https://ident.me')
        if errorCode < 0: currentIP, errorCode = await Misc.fetchUrl('https://api.ipify.org')
        if errorCode < 0: print('[ERROR]: Unable to check for your public IP, no network connection? (trying to run anyway)')
        self.__currentIP = currentIP

    def loadTwitch(self):
        twitchChanges, twitchData = StructGuard.verifyListStructure(self.__readFile(self.__twitchSettingsFile), self.__twitchStructure)
        if twitchChanges != StructGuard.NO_CHANGES: self.__saveSettings(twitchData, self.__twitchSettingsFile)
        twitchs : list[Twitch.Twitch] = []
        for td in twitchData: twitchs.append(Twitch.Twitch(td['id'], td['alias'], self.__extensions, td['tmi'], td['botname'], td['channels'], td['regularGroups'], td['channel']))
        return twitchs
    
    def loadDiscord(self):
        discordChanges, discordData = StructGuard.verifyListStructure(self.__readFile(self.__discordSettingsFile), self.__discordStructure)
        if discordChanges != StructGuard.NO_CHANGES: self.__saveSettings(discordData, self.__discordSettingsFile)
        discords : list[Discord.Discord] = []
        for dd in discordData: discords.append(Discord.Discord(dd['id'], dd['alias'], self.__extensions, dd['token'], dd['regularGroups'], dd['guild'], membersIntent=dd['membersIntent'], presencesIntent=dd['presencesIntent'], messageContentIntent=dd['messageContentIntent']))
        return discords
    
    def loadStreamElements(self):
        streamelementsChanges, streamElementsData = StructGuard.verifyListStructure(self.__readFile(self.__streamelementsSettingsFile), self.__streamelementsStructure)
        if streamelementsChanges != StructGuard.NO_CHANGES: self.__saveSettings(streamElementsData, self.__streamelementsSettingsFile)
        streamElements : list[StreamElements.StreamElements] = []
        for sed in streamElementsData: streamElements.append(StreamElements.StreamElements(sed['id'], sed['alias'], self.__extensions, sed['jwt']))
        return streamElements
    
    def saveTwitch(self, twitchList : list[Twitch.Twitch]):
        td = []
        for t in twitchList:
            td.append({
                'id': t.id,
                'tmi': t.tmi,
                'botname': t.botname,
                'channels': t.allChannels,
                'alias': t.alias,
                'regularGroups': t.regularGroups,
                'channel': t.channelConfig
            })
        self.__saveSettings(td, self.__twitchSettingsFile)
    
    def saveDiscord(self, discordList : list[Discord.Discord]):
        dd = []
        for d in discordList:
            dd.append({
                'id': d.id,
                'token': d.token,
                'alias': d.alias,
                'membersIntent': d.intents.members,
                'presencesIntent': d.intents.presences,
                'messageContentIntent': d.intents.message_content,
                'regularGroups': d.regularGroups,
                'guild': d.guildConfig
            })
        self.__saveSettings(dd, self.__discordSettingsFile)
    
    def saveStreamElements(self, streamElementsList : list[StreamElements.StreamElements]):
        sed = []
        for se in streamElementsList:
            sed.append({
                'id': se.id,
                'jwt': se.jwt,
                'alias': se.alias,
            })
        self.__saveSettings(sed, self.__streamelementsSettingsFile)

    def setPort(self, port : int):
        if not Misc.validPort(port) or self.__port == port: return False
        self.__port = port
        self.__saveSettings({'port': self.__port, 'tickrate': self.__tickrate}, self.__generalSettingsFile)
        return True

    def setTickrate(self, tickrate : int):
        if self.__tickrate == tickrate: return False
        self.__tickrate = tickrate
        self.__saveSettings({'port': self.__port, 'tickrate': self.__tickrate}, self.__generalSettingsFile)
        return True

    def __loadSettings(self):
        generalSettings = self.__readFile(self.__generalSettingsFile)
        if StructGuard.verifyDictStructure(generalSettings, self.__generalStucture, rebuild=False)[0] != StructGuard.NO_CHANGES:
            self.__saveSettings({'port': self.__defaultPort, 'tickrate': self.__defaultTickrate}, self.__generalSettingsFile)
            self.__port = self.__defaultPort
            self.__tickrate = self.__defaultTickrate
        else:
            self.__port = generalSettings['port']
            self.__tickrate = generalSettings['tickrate']
        
        portOverride = Misc.portOverride(self.__port)
        if portOverride[0]: self.__currentPort = portOverride[1]
        else: self.__currentPort = self.__port      

    def __readFile(self, filepath : Path):
        if not filepath.is_file(): return None
        with open(filepath, 'r') as f:
            try: return json.load(f)
            except Exception: return None

    def __saveSettings(self, obj, filepath : Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f: json.dump(obj, f)
