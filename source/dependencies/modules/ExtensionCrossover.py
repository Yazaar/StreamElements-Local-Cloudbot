import typing

if typing.TYPE_CHECKING:
    from dependencies.modules.Extensions import Extensions, Extension

class AsyncExtensionCrossover():
    def __init__(self, extension : Extension, extensions : Extensions):
        self.__extension = extension
        self.__extensions = extensions
    
    @property
    def twitchBotName(self): return ''
    
    @property
    def twitchChannel(self): return ''
    
    @property
    def twitchChannels(self): return []
    
    @property
    def serverPort(self): return 80
    @property
    def port(self): return self.serverPort
    
    async def TwitchMessage(self): pass
    
    async def DiscordMessage(self): pass
        
    async def StreamElementsAPI(self, data=None): pass
        
    async def CrossTalk(self, data=None): pass
    
    async def DeleteRegular(self, data=None): pass
    
    async def AddRegular(self, data=None): pass

class LegacyExtensionCrossover():
    def __init__(self, extension : Extension, extensions : Extensions):
        self.__asyncExtensionCrossover = AsyncExtensionCrossover(extension, extensions)
    
    @property
    def twitchBotName(self): return self.__asyncExtensionCrossover.twitchBotName
    
    @property
    def twitchChannel(self): return self.__asyncExtensionCrossover.twitchChannel
    
    @property
    def twitchChannels(self): return self.__asyncExtensionCrossover.twitchChannels
    
    @property
    def serverPort(self): return self.__asyncExtensionCrossover.serverPort
    
    @property
    def port(self): return self.__asyncExtensionCrossover.port
    
    def TwitchMessage(self): pass
    
    def DiscordMessage(self): pass
    
    def SendMessage(self, data=None): pass
    
    def StreamElementsAPI(self, data=None): pass
    
    def ScriptTalk(self, data=None): pass
    
    def CrossTalk(self, data=None): pass
    
    def DeleteRegular(self, data=None): pass
    
    def AddRegular(self, data=None): pass
