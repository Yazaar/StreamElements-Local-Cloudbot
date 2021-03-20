import json, ipaddress, socket
from pathlib import Path
from sys import argv

class Users:
    def __init__(self):
        self.regulars = self.loadRegulars()
    
    def addRegular(self, raw_name):
        name = raw_name.lower()
        if name in self.regulars:
            return False
        
        self.regulars.append(name)
        self.saveRegulars()
        return True
    
    def removeRegular(self, raw_name):
        name = raw_name.lower()
        if not name in self.regulars:
            return False
        
        self.regulars.remove(name)
        self.saveRegulars()
        return True
    
    def loadRegulars(self):
        regularsFile = Path('dependencies/data/regulars.json')
        if not regularsFile.is_file(): return []

        with open(regularsFile, 'r') as f:
            try: regulars = json.load(f)
            except Exception: regulars = []
        
        if isinstance(regulars, list): return regulars
        else: return []
    
    def saveRegulars(self):
        regularsFile = Path('dependencies/data/regulars.json')
        regularsFile.parent.mkdir(parents=True, exist_ok=True)
        with open(regularsFile, 'w') as f:
            json.dump(self.regulars, f)

    
    def isRegular(self, user):
        for i in self.regulars:
            if i == user:
                return True
        return False

def validateSetting(key, value):
    structure = {
        'server_port': int,
        'executions_per_second': (int, float),
        'jwt_token': str,
        'tmi': str,
        'twitch_channel': str,
        'tmi_twitch_username': str,
        'use_node': bool,
        'SEListener': int
        }
    
    if not key in structure or not isinstance(value, structure[key]):
        return False
    
    return True

def validateSettings(settings):
    structure = {
        'server_port': int,
        'executions_per_second': (int, float),
        'jwt_token': str,
        'tmi': str,
        'twitch_channel': str,
        'tmi_twitch_username': str,
        'SEListener': int
        }
    
    defaults = {
        'server_port': 80,
        'executions_per_second': 60,
        'jwt_token': '',
        'tmi': '',
        'twitch_channel': '',
        'tmi_twitch_username': '',
        'SEListener': 2
        }

    changedKeys = False

    settingsKeys = list(settings.keys())
    for key in settingsKeys:
        if not key in structure:
            del settings[key]
            changedKeys = True

    for key in structure:
        if not key in settings or not isinstance(settings[key], structure[key]):
            settings[key] = defaults[key]
            changedKeys = True
    
    return changedKeys

def saveSettings(settings):

    validateSettings(settings)

    filePath = Path('dependencies/data/settings.json')
    filePath.parent.mkdir(parents=True, exist_ok=True)
    with open(filePath, 'w') as f:
        json.dump(settings, f)

def loadSettings():
    filePath = Path('dependencies/data/settings.json')

    if not filePath.is_file():
        settings = {}
    else:
        with open(filePath, 'r') as f:
            try:
                settings = json.load(f)
            except Exception:
                settings = {}
    
    keyChanges = validateSettings(settings)

    if keyChanges:
        saveSettings(settings)
    return settings

def portOverload():
    argvLength = len(argv)
    for i in range(argvLength):
        if argv[i] == '--port' and i != argvLength - 1:
            try:
                port = int(argv[i + 1])
                if port > -1 and port < 65354:
                    return True, port
            except Exception:
                pass
    return False, -1

def localIP(environ, currentIP=None):
    if 'HTTP_X_FORWARDED_FOR' in environ and currentIP != None:
        return environ['HTTP_X_FORWARDED_FOR'] == currentIP
    
    if 'REMOTE_ADDR' in environ:
        try:
            ipObj = ipaddress.ip_address(environ['REMOTE_ADDR'])
        except ValueError:
            return False
        return ipObj.is_private

def getServerIP():
    return socket.gethostbyname(socket.gethostname())

def getMimetype(filename):
    mimetypes = {
        '.aac': 'audio/aac',
        '.avi': 'video/x-msvideo',
        '.bin': 'application/octet-stream',
        '.bmp': 'image/bmp',
        '.css': 'text/css',
        '.csv': 'text/csv',
        '.gif': 'image/gif',
        '.htm': 'text/html',
        '.html': 'text/html',
        '.ico': 'image/vnd.microsoft.icon',
        '.jpeg': 'image/jpeg',
        '.jpg': 'image/jpeg',
        '.js': 'text/javascript',
        '.json': 'application/json',
        '.jsonld': 'application/ld+json',
        '.mjs': 'text/javascript',
        '.mp3': 'audio/mpeg',
        '.mpeg': 'video/mpeg',
        '.ogv': 'video/ogg',
        '.opus': 'audio/opus',
        '.png': 'image/png',
        '.pdf': 'application/pdf',
        '.php': 'application/x-httpd-php',
        '.svg': 'image/svg+xml',
        '.tif': 'image/tiff',
        '.tiff': 'image/tiff',
        '.ts': 'video/mp2t',
        '.txt': 'text/plain',
        '.wav': 'audio/wav',
        '.weba': 'audio/webm',
        '.webm': 'video/webm',
        '.webp': 'image/webp',
        '.xhtml': 'application/xhtml+xml',
        '.xml': 'application/xml'
    }

    extension = '.' + filename.rsplit('.')[-1]
    
    if not extension in mimetypes:
        return None
    
    return mimetypes[extension]