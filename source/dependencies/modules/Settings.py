import json
from pathlib import Path

class Settings():
    def __init__(self):
        settingsFolder = Path('dependencies/data/settings')
        
        self.__generalSettingsFile = settingsFolder / 'general.json'
        self.__twitchSettingsFile = settingsFolder / 'twitch.json'
        self.__discordSettingsFile = settingsFolder / 'discord.json'
        self.__streamelementsSettingsFile = settingsFolder / 'streamelements.json'

        self.__defaultPort = 80
        self.port = None

        self.__twitchStructure = {'tmi': str, 'botname': str, 'channels': list, 'alias': str, 'regularGroups': list}
        self.twitch : list[dict] = []

        self.__streamelementsStructure = {'jwt': str, 'alias': str, 'useSocketIO': bool}
        self.streamelements : list[dict] = []
        
        self.__discordStructure = {'token': str, 'alias': str, 'regularGroups': list}
        self.discord : list[dict] = []

        self.__loadSettings()

    def __loadSettings(self):
        generalSettings = self.__readFile(self.__generalSettingsFile)
        if not isinstance(generalSettings, dict) or (port := generalSettings.get('port', None)) == None or not isinstance(port, int):
            self.port = self.__defaultPort
            self.__saveSettings({'port': self.port}, self.__generalSettingsFile)
        else:
            self.port = port
        
        twitchChanges, self.twitch = self.__validateSettings(self.__readFile(self.__twitchSettingsFile), self.__twitchStructure, self.__enhancedTwitchVerification)
        if twitchChanges:
            self.__saveSettings(self.twitch, self.__twitchSettingsFile)
        
        discordChanges, self.discord = self.__validateSettings(self.__readFile(self.__discordSettingsFile), self.__discordStructure, self.__enhancedDiscordVerification)
        if discordChanges:
            self.__saveSettings(self.discord, self.__discordSettingsFile)
        
        streamelementsChanges, self.streamelements = self.__validateSettings(self.__readFile(self.__streamelementsSettingsFile), self.__streamelementsStructure)
        if streamelementsChanges:
            self.__saveSettings(self.streamelements, self.__streamelementsSettingsFile)

    def __readFile(self, filepath : Path):
        if not filepath.is_file(): return None
        with open(filepath, 'r') as f:
            try: return json.load(f)
            except Exception: return None

    def __saveSettings(self, obj, filepath : Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f: json.dump(obj, f)

    def __validateSettings(self, obj : list, structure : dict, enhancedItemValidatorCallable = None):
        if not isinstance(obj, list): return True, []
        changes = False
        for index, item in enumerate(reversed(obj)):
            if not isinstance(item, dict):
                obj.pop(index)
                changes = True
                continue

            for key in structure:
                if not key in item or not isinstance(item[key], structure[key]):
                    obj.pop(index)
                    changes = True
                    continue
            
            for key in list(item.keys()):
                if not key in structure:
                    del item[key]
                    changes = True
            
            try:
                if enhancedItemValidatorCallable != None and enhancedItemValidatorCallable(item):
                    changes = True
            except Exception: pass
        return changes, obj

    def __enhancedTwitchVerification(self, obj):
        changes = False
        for index, channel in enumerate(reversed(obj['channels'])):
            if not isinstance(channel, str):
                obj['channels'].pop(index)
                changes = True
        if self.__enhancedRegularsVerification(obj): changes = True
        return changes

    def __enhancedDiscordVerification(self, obj):
        changes = False
        for index, channel in enumerate(reversed(obj['channels'])):
            if not isinstance(channel, str):
                obj['channels'].pop(index)
                changes = True
        if self.__enhancedRegularsVerification(obj): changes = True
        return changes
    
    def __enhancedRegularsVerification(self, obj):
        changes = False
        for index, groupname in enumerate(reversed(obj['regularGroups'])):
            if not isinstance(groupname, str):
                obj['regularGroups'].pop(index)
                changes = True
        return changes