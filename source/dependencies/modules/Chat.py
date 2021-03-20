import socket, time, select, threading, re, datetime

class Chat:
    def __init__(self, users, SE, socketio, appContext):
        self.__users = users
        self.__SE = SE
        self.__extensions = None
        self.__socketio = socketio
        self.__appContext = appContext
        
        self.__twitchTmi = ''
        self.__twitchTmiUsername = ''
        self.__twitchChannel = ''
        self.__twitchSocket = None
        self.__twitchConnected = False
        self.__twitchConnectedData = ('', '', '')
        self.__twitchRestartCooldown = None
        self.__twitchThreadID = 0
        self.__twitchMessages = []
        self.twitchMessagesHistory = []

        self.connectedTwitchChannel = None
        self.connectedTwitchBotname = None

        self.__messagesToSend = []

        self.__twitchThread = None

        threading.Thread(target=self.__sendMessagesHandler, daemon=True).start()
    
    def bindExtensions(self, extensions):
        self.__extensions = extensions

    def addMessage(self, content):
        if not isinstance(content, dict):
            return False, 'Please forward JSON: requests.post(url, json=JSON_DATA) / socket.emit(event, json)'
        
        if not 'message' in content:
            return False, 'JSON require the key \"message\"'
        if not 'bot' in content:
            return False, 'JSON require the key \"bot\"'
        
        if not isinstance(content['bot'], str):
            return False, 'The key \"bot\" require a string value of \"local\" or \"streamelements\"'
        
        bot = content['bot'].lower()
        if not bot in ['local', 'streamelements']:
            return False, 'The key \"bot\" require a string value of \"local\" or \"streamelements\"'
        
        if not isinstance(content['message'], str):
            return False, 'The key \"message\" require a string value'
        
        self.__messagesToSend.append({'bot': bot, 'message': content['message']})
        return True, None

    def pickMessageSource(self, bot):
        stateTwitch = self.__twitchConnected
        stateSE = self.__SE.canSendMessages()

        if bot == 'local' and stateTwitch:
            return 'local'
        
        if bot == 'streamelements' and stateSE:
            return 'streamelements'
        
        if stateSE:
            return 'streamelements'
        
        if stateTwitch:
            return 'local'
        
        return None
        
    def __sendMessagesHandler(self):
        while True:
            if len(self.__messagesToSend) == 0:
                time.sleep(0.5)
            else:
                msg = self.__messagesToSend.pop(0)
                bot = self.pickMessageSource(msg['bot'])
                if bot == 'local':
                    self.__twitchSocket.send(('PRIVMSG #' + self.connectedTwitchChannel.lower() + ' :' + msg['message'] + '\r\n').encode('UTF-8'))
                    time.sleep(0.4)
                elif bot == 'streamelements':
                    self.__SE.sendMessage(msg['message'])
                    time.sleep(1.5)
                else:
                    print('[Chat] Error, no message source is active. Unable to send message')
                    time.sleep(2)

    def getNextTwitchMessage(self):
        if len(self.__twitchMessages) == 0:
            return None
        return self.__twitchMessages.pop(0)

    def setTwitchData(self, tmi=None, tmi_username=None, twitch_channel=None):
        if isinstance(tmi, str): self.__twitchTmi = tmi
        if isinstance(tmi_username, str): self.__twitchTmiUsername = tmi_username
        if isinstance(twitch_channel, str): self.__twitchChannel = twitch_channel

    def awaitStart(self, timeout):
        timeoutAt = time.time() + timeout
        while True:
            if self.__twitchThread == None or self.__twitchThread.is_alive() == False:
                return False
            if self.__twitchConnected:
                return True
            if time.time() > timeoutAt:
                return False
            time.sleep(1)

    def startTwitch(self):
        currentTime = time.time()
          
        if self.__twitchTmi == self.__twitchConnectedData[0] and self.__twitchTmiUsername == self.__twitchConnectedData[1] and self.__twitchChannel == self.__twitchConnectedData[2]:
            return 0, self.__twitchRestartCooldown

        if self.__twitchRestartCooldown != None and self.__twitchRestartCooldown > currentTime:
            return -1, self.__twitchRestartCooldown
        
        self.__twitchRestartCooldown = currentTime + 30
        
        self.__twitchConnectedData = (self.__twitchTmi, self.__twitchTmiUsername, self.__twitchChannel)
        
        self.__twitchThreadID += 1
        
        self.__twitchThread = threading.Thread(target=self.twitchThread, args=(self.__twitchTmi, self.__twitchTmiUsername, self.__twitchChannel, self.__twitchThreadID), daemon=True, name='TwitchChatThread')
        self.__twitchThread.start()
        
        return 1, self.__twitchRestartCooldown

    def stopTwitchThread(self):
        if self.__twitchConnected:
            self.__twitchConnected = False
            self.__twitchThreadID += 1
    
    def processTwitchMessage(self, message):
        res = {'raw':message, 'badges':{}}
    
        res['message'] = re.search(r'PRIVMSG #[^ ]* :(.*)', message).group(1)
        
        temp = re.search(r';badges=([^;]*)', message).group(1).split(',')
        if temp == ['']:
            res['badges'] = {}
        else:
            for i in temp:
                item = i.split('/')
                res["badges"][item[0]] = item[1]

        if re.search(r';mod=(\d)', message).group(1) == '1' or 'broadcaster' in res['badges'].keys():
            res['moderator'] = True
        else:
            res['moderator'] = False
        
        if re.search(r';subscriber=(\d)', message).group(1) == '1' or 'subscriber' in res['badges'].keys():
            res['subscriber'] = True
        else:
            res['subscriber'] = False
        
        if re.search(r';turbo=(\d)', message).group(1) == '1' or 'turbo' in res['badges'].keys():
            res['turbo'] = True
        else:
            res['turbo'] = False
        
        
        res['name'] = re.search(r';display-name=([^;]*)', message).group(1)

        if self.__users.isRegular(res['name'].lower()):
            res['regular'] = True
        else:
            res['regular'] = False

        res['room'] = re.search(r';room-id=([^;]*)', message).group(1)

        res['id'] = re.search(r';id=([^;]*)', message).group(1)
        
        res['utc-timestamp'] = datetime.datetime.utcfromtimestamp(int(re.search(r';tmi-sent-ts=([^;]*)', message).group(1))/1000).strftime('%Y-%m-%d %H:%M:%S')
        res['emotes'] = {}

        temp = re.search(r';emotes=([^;]*)', message).group(1).split('/')
        if temp[0] != '':
            for i in temp:
                res['emotes'][i.split(':')[0]] = i.split(':')[1].split(',')
        return res

    def __closeTwitchSocket(self):
        if self.__twitchSocket != None:
            self.__twitchSocket.close()
            self.__twitchSocket = None

        self.__twitchConnected = False

    def twitchThread(self, tmi, tmiUsername, channel, threadID):
        if tmi in ['', '*'] or tmiUsername in ['', '*'] or channel in ['', '*']:
            return
        HOST = 'irc.twitch.tv'
        PORT = 6667
        
        while self.__twitchSocket != None:
            time.sleep(1)
        
        while True:
            if self.__twitchThreadID != threadID: return
            
            readBuffer = ''
            
            try:
                self.__twitchSocket = socket.socket()
                self.__twitchSocket.connect((HOST, PORT))
            except Exception:
                print('[Twitch Chat] Unable to connect to Twitch (Retrying in 5s)')
                time.sleep(5)
                continue
            
            self.__twitchSocket.send(b'PASS ' + tmi.lower().encode('utf-8') + b'\r\n')
            self.__twitchSocket.send(b'NICK ' + tmiUsername.lower().encode('utf-8') + b'\r\n')
            self.__twitchSocket.send(b'JOIN #' + channel.lower().encode('utf-8') + b'\r\n')
            self.__twitchSocket.send(b'CAP REQ :twitch.tv/tags\r\n')
            
            loading = True
            sentPing = False

            while loading:
                if self.__twitchThreadID != threadID:
                    self.__closeTwitchSocket()
                    return
                try:
                    readBuffer += self.__twitchSocket.recv(1024).decode('utf-8')
                except Exception:
                    self.__closeTwitchSocket()
                    break
                temp = readBuffer.split('\n')
                readBuffer = temp.pop()

                for line in temp:
                    if line == ':tmi.twitch.tv NOTICE * :Login authentication failed\r' or line == ':tmi.twitch.tv NOTICE * :Improperly formatted auth\r':
                        print('[Twitch Chat] Invalid TMI')
                        self.__closeTwitchSocket()
                        return
                    if 'End of /NAMES list' in line:
                        print('Connected to twitch chat: ' + channel.lower())
                        loading = False
                        break
            
            if self.__twitchSocket == None: break

            self.connectedTwitchBotname = tmiUsername
            self.connectedTwitchChannel = channel

            if self.__extensions != None:
                self.__extensions.setCrossoverData(twitchChannel=channel, twitchBotName=tmiUsername)
            
            self.__twitchConnected = True
            readBuffer = ''
            lastResponse = time.time()
            while True:
                if self.__twitchThreadID != threadID:
                    self.__closeTwitchSocket()
                    return
                if select.select([self.__twitchSocket], [], [], 5)[0]:
                    lastResponse = time.time()
                    sentPing = False
                    try:
                        readBuffer += self.__twitchSocket.recv(1024).decode('utf-8')
                    except Exception:
                        print('[Twitch Chat] Error while reading chat')
                        self.__closeTwitchSocket()
                        break

                    temp = readBuffer.split('\n')
                    readBuffer = temp.pop()
                    for line in temp:
                        if line == 'PING :tmi.twitch.tv\r':
                            self.__twitchSocket.send(b'PONG :tmi.twitch.tv\r\n')
                        elif 'PRIVMSG #' in line:
                            generatedMessage = self.processTwitchMessage(line[:-1])
                            self.__twitchMessages.append(generatedMessage)
                            self.twitchMessagesHistory.append(generatedMessage['name'] + ': ' + generatedMessage['message'])
                            if len(self.twitchMessagesHistory) > 100:
                                self.twitchMessagesHistory.pop(0)
                            with self.__appContext:
                                self.__socketio.emit('TwitchMessage', generatedMessage, broadcast=True)
                elif sentPing == False and time.time() - lastResponse > 350:
                    sentPing = True
                elif sentPing == True and time.time() - lastResponse > 400:
                    self.__twitchSocket.close()
                    break