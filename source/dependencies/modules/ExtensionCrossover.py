import threading
from .StreamElements import StreamElements

class ExtensionCrossover:
    def __init__(self, serverPort, twitchChannel, twitchBotName):
        self.__SendMessage = []
        self.__StreamElementsAPI = []
        self.__ScriptTalk = []
        self.__CrossTalk = []
        self.__DeleteRegulars = []
        self.__AddRegulars = []

        self.__serverPort = serverPort
        self.__twitchChannel = twitchChannel
        self.__twitchBotName = twitchBotName
    
    @property
    def twitchBotName(self):
        return self.__twitchBotName
    
    @property
    def twitchChannel(self):
        return self.__twitchChannel
    
    @property
    def serverPort(self):
        return self.__serverPort
    
    @property
    def port(self):
        return self.__serverPort
    
    def SendMessage(self, data=None):
        '''
        Send a twitch message.
        argument: dict with the keys "bot" and "message"
        bot = "local"/"StreamElements" (depends on your bot target, local is recommended)
        message = Your message that you wish to send in twitch chat (str)

        returns a dict with the key "type", value = "error"/"success" (DEPRICATED)
        returns a dict with the key "success", value = True/False
        returns a dict with the key "message" on error, value = error message
        '''
        if not isinstance(data, dict):
            return {'type':'error', 'success': False, 'message':'The input has to be a dictionary'}
        
        if not 'message' in data:
            return {'type':'error', 'success': False, 'message':'The dict has to include the key message'}
        if not 'bot' in data:
            return {'type':'error', 'success': False, 'message':'The dict has to include the key bot with the value "local" or "streamelements"'}
        
        if not isinstance(data['bot'], str):
            return {'type':'error', 'success': False, 'message':'The dict has to include the key bot with the value "local" or "streamelements"'}
        
        parsed = {'bot': data['bot'].lower()}

        if parsed['bot'] != 'streamelements' and parsed['bot'] != 'local':
            return {'type':'error', 'success': False, 'message':'The dict has to include the key bot with the value "local" or "streamelements"'}
        
        if isinstance(data['message'], str):
            parsed['message'] = data['message']
        else:
            try:
                parsed['message'] = str(data['message'])
            except Exception:
                return {'type':'error', 'success': False, 'message':'The dict has to include the key message containing a message'}
        
        if len(parsed['message']) == 0:
            return {'type':'error', 'success': False, 'message':'The dict has to include the key message containing a message'}

        self.__SendMessage.append(parsed)
        return {'type':'success', 'success': True}

    def StreamElementsAPI(self, data=None):
        '''
        Send an API request to StreamElements servers.
        argument: dict with the keys "endpoint" (str) and "options" (dict)

        returns a dict with the key "type", value = "error"/"success" (DEPRICATED)
        returns a dict with the key "success", value = True/False
        returns a dict with the key "message" on error, value = error message
        '''

        success, msg = StreamElements.validateApiStruct(data)

        if not success:
            return {'type': 'error', 'success': False, 'message': msg}

        parsed = {'endpoint': data['endpoint'], 'options': data['options']}

        self.__StreamElementsAPI.append(parsed)
        return {'type':'success', 'success': True}

    def ScriptTalk(self, data=None):
        '''
        Send data between python scripts.
        argument: dict with the keys "module" (str) and "data" (any)
        module = Your target, example: "example.test_LSE"
        data = Your data to forward over

        returns a dict with the key "type", value = "error"/"success" (DEPRICATED)
        returns a dict with the key "success", value = True/False
        returns a dict with the key "message" on error, value = error message
        '''
        if not isinstance(data,  dict):
            return {'type':'error', 'message':'The input has to be a dict'}
        
        if not 'module' in data:
            return {'type':'error', 'success': False, 'message':'No module found, please include the key module'}
        if not 'data' in data:
            return {'type':'error', 'success': False, 'message':'No data found, please include the key data'}
        
        if not isinstance(data['module'], str) or len(data['module']) == 0:
            return {'type':'error', 'success': False, 'message':'Invalid module, please forward a valid module'}

        parsed = {'module': data['module'], 'data': data['data']}

        self.__ScriptTalk.append(parsed)
        return {'type':'success', 'success': True}

    def CrossTalk(self, data=None):
        '''
        Send data to HTML/JavaScript.
        argument: dict with the keys "event" (str) and "data" (any)
        event = Your target, has to start with "p-", example: "p-MyTestEvent"
        data = Your data to forward over

        returns a dict with the key "type", value = "error"/"success" (DEPRICATED)
        returns a dict with the key "success", value = True/False
        returns a dict with the key "message" on error, value = error message
        '''
        if not isinstance(data, dict):
            return {'type':'error', 'success': False, 'message':'The input has to be a dict'}
        
        if not 'event' in data:
            return {'type':'error', 'success': False, 'message':'json require the key "event"'}
        if not 'data' in data:
            return {'type':'error', 'success': False, 'message':'json require the key "data"'}
        
        if not isinstance(data['event'], str):
            return {'type':'error', 'success': False, 'message':'The value for the key "event" has to be a string'}
        if not data['event'].startswith('p-'):
            return {'type':'error', 'success': False, 'message':'The value for the key "event" has to start with "p-", for example: p-example'}
        
        self.__CrossTalk.append(data)
        return {'type':'success', 'success': True}

    def DeleteRegular(self, data=None):
        '''
        Delete a regular.
        argument: username (string)

        returns a dict with the key "type", value = "error"/"success"
        returns a dict with the key "message" on error, value = error message
        '''
        if type(data) != str:
            return {'type':'error', 'success': False, 'message':'The input has to be a string'}
        
        self.__DeleteRegulars.append(data.lower())
        return {'type':'success', 'success': True}
    
    def AddRegular(self, data=None):
        '''
        Add a regular.
        argument: username (string)

        returns a dict with the key "type", value = "error"/"success"
        returns a dict with the key "message" on error, value = error message
        '''
        if not isinstance(data, str):
            return {'type':'error', 'success': False, 'message':'The input hsa to be a string'}
        
        if len(data) == 0:
            return {'type':'error', 'success': False, 'message':'Invalid input string'}
        
        self.__AddRegulars.append(data.lower())
        return {'type':'success', 'success': True}
    
    def setAttributes(self, twitchChannel=None, twitchBotName=None):
        if threading.current_thread().getName() != 'TwitchChatThread':
            return {'success': False, 'message':'You are not allowed to execute this method'}

        if isinstance(twitchChannel, str): self.__twitchChannel = twitchChannel
        if isinstance(twitchBotName, str): self.__twitchBotName = twitchBotName
        
        

    def GetValue(self, ValueType: str='all'):
        '''
        Blocked for extensions, do not bypass. Thanks
        Optional parameter: "streamelementsapi"/"sendmessage"/"crosstalk"/"scripttalk"/"all"
        Returns a dict with the keys "success" (value: False) and "message" on error
        Returns a dict with the keys "success" (value: True), "data" (event data), "event" (event type)
        '''
        
        if threading.current_thread().getName() != 'DataIn':
            return {'success': False, 'message':'You are not allowed to execute this method'}

        if not isinstance(self.__StreamElementsAPI, list):
            self.__StreamElementsAPI = []
        if not isinstance(self.__SendMessage, list):
            self.__SendMessage = []
        if not isinstance(self.__CrossTalk, list):
            self.__CrossTalk = []
        if not isinstance(self.__ScriptTalk, list):
            self.__ScriptTalk = []
        if not isinstance(self.__AddRegulars, list):
            self.__AddRegulars = []
        if not isinstance(self.__DeleteRegulars, list):
            self.__DeleteRegulars = []
        
        LowerValueType = ValueType.lower()

        if LowerValueType != 'all' and LowerValueType != 'streamelementsapi' and LowerValueType != 'sendmessage' and LowerValueType != 'crosstalk' and LowerValueType != 'scripttalk':
            return {'success': False, 'message': 'invalid ValueType'}
        
        if len(self.__StreamElementsAPI) > 0 and (LowerValueType == 'all' or LowerValueType == 'streamelementsapi'):
            ReturnValue = self.__StreamElementsAPI.pop(0).copy()
            return {'success': True, 'data': ReturnValue, 'event': 'StreamElementsAPI'}

        if len(self.__SendMessage) > 0 and (LowerValueType == 'all' or LowerValueType == 'sendmessage'):
            ReturnValue = self.__SendMessage.pop(0).copy()
            return {'success': True, 'data': ReturnValue, 'event': 'SendMessage'}

        if len(self.__CrossTalk) > 0 and (LowerValueType == 'all' or LowerValueType == 'crosstalk'):
            ReturnValue = self.__CrossTalk.pop(0).copy()
            return {'success': True, 'data': ReturnValue, 'event': 'CrossTalk'}

        if len(self.__ScriptTalk) > 0 and (LowerValueType == 'all' or LowerValueType == 'scripttalk'):
            ReturnValue = self.__ScriptTalk.pop(0).copy()
            return {'success': True, 'data': ReturnValue, 'event': 'ScriptTalk'}

        if len(self.__AddRegulars) > 0 and (LowerValueType == 'all' or LowerValueType == 'addregulars'):
            ReturnValue = self.__AddRegulars.pop(0)
            return {'success': True, 'data': ReturnValue, 'event': 'AddRegulars'}

        if len(self.__DeleteRegulars) > 0 and (LowerValueType == 'all' or LowerValueType == 'deleteregulars'):
            ReturnValue = self.__DeleteRegulars.pop(0)
            return {'success': True, 'data': ReturnValue, 'event': 'DeleteRegulars'}
        
        return {'success': True, 'data':None, 'event':None}