import json
from pathlib import Path

class Settings():
    def __init__(self):
        self.settingsStructure = {
                'server_port': (int, 80),
                'executions_per_second': ((int, float), 60),
                'jwt_token': (str, ''),
                'tmi': (str, ''),
                'twitch_channel': (str, ''),
                'tmi_twitch_username': (str, ''),
                'SEListener': (int, 2)
        }

        self.settings = self.loadSettings()

    def loadSettings(self):
        filePath = Path('dependencies/data/settings.json')

        if not filePath.is_file():
            settings = {}
        else:
            with open(filePath, 'r') as f:
                try: settings = json.load(f)
                except Exception: settings = {}
        
        if self.validateSettings(settings): self.saveSettings(settings)

        return settings
    
    def saveSettings(self):
        self.validateSettings(self.settings)

        filePath = Path('dependencies/data/settings.json')
        filePath.parent.mkdir(parents=True, exist_ok=True)
        with open(filePath, 'w') as f:
            json.dump(self.settings, f)
    
    def validateSetting(self, key, value):      
        if not key in self.settingsStructure: return False, None
        
        if not isinstance(value, self.settingsStructure[key][0]): return False, self.settingsStructure[key][1]
        
        return True, None

    def validateSettings(self, settings):
        changedKeys = False

        for key in self.settingsStructure:
            valid, default = self.validateSetting(key, settings.get(key))
            if not valid:
                changedKeys = True
                if default == None:
                    del settings[key]
                else:
                    settings[key] = default
        
        return changedKeys
