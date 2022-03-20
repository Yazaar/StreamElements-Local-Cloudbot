class ExtensionCrossoverAdmin():
    def __init__(self):
        self.twitch = None
        self.streamElements = None
        self.discord = None
        self.web = None

        self.sendMessage = []
        self.streamElementsAPI = []
        self.scriptTalk = []
        self.crossTalk = []
        self.deleteRegulars = []
        self.addRegulars = []

class ExtensionCrossover():
    def __init__(self, context : ExtensionCrossoverAdmin):
        self.__context = context

    @property
    def twitchBotName(self):
        if self.__context.twitch == None: return None
        return self.__context.twitch.botname
    
    @property
    def twitchChannel(self):
        if self.__context.twitch == None: return None
        return self.__context.twitch.channel
    
    @property
    def twitchChannels(self):
        if self.__context.twitch == None: return None
        return self.__context.twitch.channels
    
    @property
    def serverPort(self):
        if self.__context.web == None: return None
        return self.__context.web.port
    
    @property
    def port(self):
        if self.__context.web == None: return None
        return self.__context.web.port
    
    def SendMessage(self, data=None):
        pass

    def StreamElementsAPI(self, data=None):
        pass

    def ScriptTalk(self, data=None):
        pass

    def CrossTalk(self, data=None):
        pass

    def DeleteRegular(self, data=None):
        pass

    def AddRegular(self, data=None):
        pass
