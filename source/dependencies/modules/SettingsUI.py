from .vendor.StructGuard import StructGuard
from pathlib import Path
import json

class SettingsUIError(Exception): pass

class SettingsUI():
    FORMAT = {
        'name': str,
        'settings': {
            str: {
                'type': str,
                str: StructGuard.AdvancedType((str, int, float, bool, list), str)
            }
        },
        'scripts': [str],
        'events': [str],
        'event': StructGuard.AdvancedType(str, None)
    }

    def __init__(self, directory : Path):
        self.directory = directory
        self.current = {}
        self.config = {}

        self.name : str = None
        self.scripts : list[str] = []
        self.events : list[str] = []

        self.load()
    
    @property
    def event(self):
        if len(self.events) == 0: return None
        else: return self.events[0]
    
    def save(self):
        jsonFile = self.directory / 'settings.json'
        jsFile = self.directory / 'settings.js'
        jsonContent = json.dumps(self.current)
        with open(jsonFile, 'w') as f: f.write(jsonContent)
        with open(jsFile, 'w') as f: f.write(f'var settings = {jsonContent};')

    def load(self):
        self.config.clear()
        self.current.clear()

        settingsUIFile = self.directory / 'SettingsUI.json'
        currentFile = self.directory / 'settings.json'

        if not settingsUIFile.is_file(): raise SettingsUIError('SettingsUI.json does not exist')

        with open(settingsUIFile, 'r') as f:
            try: settings = json.load(f)
            except Exception: raise SettingsUIError('Invalid file format of SettingsUI.json (have to be json)')
                
        isValid, resp = SettingsUI.validSettings(settings)
        if not isValid: raise SettingsUIError(resp)

        if len(settings['name']) == 0: raise SettingsUIError('Invalid value of key name of SettingsUI.json')

        self.name : str = settings['name']
        self.scripts : list[str] = settings['scripts']
        self.events : list[str] = settings['events']

        if len(settings['event']) > 0: self.events.append(settings['event'])

        absPathCutLength = len(Path('extensions').resolve().as_posix()) + 1
        for i in reversed(range(len(self.scripts))):
            if self.scripts[i].startswith('./'):
                if not self.scripts[i].endswith('.py'):
                    self.scripts.pop(i)
                    continue
                parsedScript = (self.directory / self.scripts[i][2:]).resolve().as_posix()
                parsedScript = parsedScript[absPathCutLength:][:-3].replace('/', '.')
                self.scripts[i] = parsedScript

        if currentFile.is_file():
            with open(currentFile, 'r') as f:
                try:
                    rawCurrent = json.load(f)
                    if isinstance(rawCurrent, dict): self.current = rawCurrent
                except Exception: pass
        
        changes = False
        self.config = settings['settings']
        for key in self.config:
            if not 'value' in self.config[key]: self.config[key]['value'] = SettingsUI.getDefault(self.config[key]['type'])

            if not key in self.current:
                changes = True
                self.current[key] = self.config[key]['value']
        
        if changes: self.save()

    def getDefault(settingType : str):
        if settingType in ['number', 'range']: return 0
        elif settingType == 'checkbox': return False
        else: return ''

    def update(self, newSettings : dict):
        changes = False
        for key in self.current:
            if key in newSettings:
                self.current[key] = newSettings[key]
                changes = True
        if changes: self.save()

    def validSettings(settingsData) -> tuple[bool, str | None]:
        structState, settingsData = StructGuard.verifyDictStructure(settingsData, SettingsUI.FORMAT)
        if structState == StructGuard.INVALID: return False, 'Format of SettingsUI.json is invalid, check the documentation'
        for settingKey in settingsData['settings']:
            setting = settingsData['settings'][settingKey]
            settingType = setting['type'].lower()
            if settingType == 'dropdown':
                if not 'value' in setting: return False, 'Missing the key value for SettingsUI.json dropdown'
                if not 'choices' in setting and StructGuard.verifyListStructure(setting['choices'], [(str, int, float, bool)])[0] != StructGuard.NO_CHANGES:
                    return False, 'Invalid list of dropdown choices'
                if not setting['value'] in setting['choices']:
                    return False, 'The value is not a part of the choices'
        return True, None

class Settings():
    def __init__(self, settingsUI : SettingsUI):
        self.__settingsUI = settingsUI
    
    @property
    def settings(self) -> dict: return self.__settingsUI.current.copy()

    def legacy(self): return self.settings