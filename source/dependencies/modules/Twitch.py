import asyncio, time, datetime, typing, copy, json
from . import Misc, Errors

if typing.TYPE_CHECKING:
    from . import Extensions

class Twitch:
    async def parseTMI(tmi : str) -> tuple[str, str, None] | tuple[None, None, str]:
        if tmi.startswith('oauth:'): tmi = tmi[6:]

        if len(tmi) == 0: return None, None, 'tmi have to be a string with a length larger than 0'

        resp, errorCode = await Misc.fetchUrl('https://id.twitch.tv/oauth2/validate', headers={'Authorization': f'Bearer {tmi}'})

        if errorCode != 1: return None, None, 'unable to send HTTP request to validate TMI'

        try: parsedResp = json.loads(resp)
        except Exception: return None, None, 'unable to parse HTTP response from TMI validation'

        if not isinstance(parsedResp, dict): return None, None, 'invalid format returned by HTTP response from TMI validation, should be json dictionary'

        botname = parsedResp.get('login', None)
        if botname is None: return None, None, 'HTTP response from TMI validation does not include a login'

        return f'oauth:{tmi}', botname, None

    def __init__(self, id_ : str, alias : str, extensions : 'Extensions.Extensions', tmi : str, botname : str, channels : list, regularGroups : list[str], channelConfig : dict[str, dict[str, typing.Any]]):
        self.__id = id_
        self.alias = alias

        self.__runnerId = 0
        self.__extensions = extensions

        self.__reader = None
        self.__writer = None

        self.__tmi = tmi
        self.__botname = botname
        self.__channels : list[str] = channels

        self.__regularGroups = regularGroups
        self.__channelConfig = channelConfig

        self.__runTask : asyncio.Task = None

        self.__clientContext = TwitchContext(self)

        self.start()

    @property
    def id(self): return self.__id

    @property
    def botname(self): return self.__botname

    @property
    def tmi(self): return self.__tmi

    @property
    def allChannels(self): return self.__channels.copy()

    @property
    def regularGroups(self): return self.__regularGroups.copy()

    @property
    def channelConfig(self): return copy.deepcopy(self.__channelConfig)

    @property
    def clientContext(self): return self.__clientContext

    @property
    def running(self):
        if self.__runTask is None: return False
        return not self.__runTask.done()

    async def setTMI(self, tmi : str):
        if tmi == self.__tmi: return True, None
        tmi, botname, erorMsg = await Twitch.parseTMI(tmi)
        if not erorMsg is None: return False, erorMsg

        self.__tmi = tmi
        self.__botname = botname

        if not self.__runTask.done(): self.start()
        return True, None

    def defaultChannel(self):
        if len(self.__channels) > 0: return self.__channels[0]

    async def sendMessage(self, message : str, channel : str):
        '''
        ** Exceptions **
        - Errors.Twitch.NotRunningError: Twitch not running
        - TypeError: Invalid data type of message 
        - Errors.Twitch.ChannelNotFoundError: Provided channel does not exist
        '''
        if self.__writer == None: raise Errors.Twitch.NotRunningError('twitch chat not running')
        if not isinstance(message, str): raise TypeError('message has to be a string')
        sendInChannel = None
        if not isinstance(channel, str): sendInChannel = self.defaultChannel()
        for i in self.__channels:
            if i == channel:
                sendInChannel = i
                break

        if sendInChannel == None: Errors.Twitch.ChannelNotFoundError('invalid channel to send in')
        self.__writer.write(f'PRIVMSG #{sendInChannel.lower()} :{message}\r\n'.encode('utf-8'))

    def setRegularGroups(self, regularGroups : list[str]):
        self.__regularGroups.clear()
        for rg in regularGroups: self.addRegularGroup(rg)

    def addRegularGroup(self, regularGroup : str):
        if not isinstance(regularGroup, str) or len(regularGroup) == 0 or regularGroup in self.__regularGroups: return
        self.__regularGroups.append(regularGroup)

    def isRegular(self, channel : str, username : str):
        regularGroups = [i for i in self.__regularGroups]
        if channel != None: regularGroups.append(f'channel.{channel}')
        self.__extensions.regulars.isRegular(username, regularGroups, 'twitch')

    def onrawMsg(self, rawMsg : str):
        self.__extensions.twitchMessage(TwitchMessage(self, rawMsg))

    def start(self):
        self.stopTwitch()

        loop = asyncio.get_event_loop()
        loop.create_task(self.listen(self.__runnerId))

    def setChannels(self, channels : list[str]):
        parsedChannels = set([i.lower() for i in channels if isinstance(i, str) and len(i) > 0])
        currentChannels = set(self.__channels)

        newChannels = parsedChannels - currentChannels
        removedChannels = currentChannels - parsedChannels

        for c in newChannels: self.addChannel(c)
        for c in removedChannels: self.removeChannel(c)

    def addChannel(self, rawChannel : str):
        if not isinstance(rawChannel, str) or len(rawChannel) == 0: return
        channel = rawChannel.lower()
        if channel in self.__channels: return
        self.__channels.append(channel)

        if self.__writer == None: return

        self.__writer.write(b'JOIN #' + channel.lower().encode('utf-8') + b'\r\n')

    def removeChannel(self, rawChannel : str):
        if not isinstance(rawChannel, str) or len(rawChannel) == 0: return
        channel = rawChannel.lower()
        if not channel in self.__channels: return
        self.__channels.remove(channel)

        if self.__writer == None: return

        self.__writer.write(b'PART #' + channel.lower().encode('utf-8') + b'\r\n')

    def stopTwitch(self):
        self.__runnerId += 1

    def __close(self):
        if self.__writer == None:
            self.__reader = None
            return

        if not self.__writer.is_closing():
            self.__writer.close()

        self.__reader = None
        self.__writer = None

    async def read(self):
        if self.__reader == None: return None
        try: data = await self.__reader.readuntil(b'\n')
        except ConnectionError: return None
        return data.decode('utf-8').rstrip()

    async def listen(self, runnerId : int):
        myTask = asyncio.current_task()
        running = True
        while isinstance(self.__runTask, asyncio.Task) and not self.__runTask.done():
            await asyncio.sleep(1)

        self.__runTask = myTask

        while running and self.__runnerId == runnerId:
            if len(self.__channels) == 0 or self.__tmi == '' or self.__botname == '': return

            self.__reader, self.__writer = await asyncio.open_connection('irc.twitch.tv', 6667)

            self.__writer.write(b'PASS ' + self.__tmi.lower().encode('utf-8') + b'\r\n')
            self.__writer.write(b'NICK ' + self.__botname.lower().encode('utf-8') + b'\r\n')

            for channel in self.__channels:
                if isinstance(channel, str) and channel != '': self.__writer.write(b'JOIN #' + channel.lower().encode('utf-8') + b'\r\n')
            self.__writer.write(b'CAP REQ :twitch.tv/tags\r\n')

            while running and self.__runnerId == runnerId:
                data = await self.read()

                if data == None:
                    self.__close()
                    print(f'[Twitch {self.alias}] Connection to Twitch failed, retrying in 3 seconds...')
                    await asyncio.sleep(3)
                    break
                if data == ':tmi.twitch.tv NOTICE * :Login authentication failed' or data == ':tmi.twitch.tv NOTICE * :Improperly formatted auth':
                    print(f'[Twitch {self.alias}] Invalid TMI')
                    running = False
                    self.__close()
                    break
                elif 'End of /NAMES list' in data:
                    print(f'[Twitch {self.alias}] Connected to channels')
                    break

            if running and self.__writer == None: continue

            lastResponse = time.time()
            sentPing = False
            while running and self.__runnerId == runnerId:
                try: data = await asyncio.wait_for(self.read(), 5)
                except asyncio.TimeoutError: data = None

                if data == None:
                    if sentPing == False and time.time() - lastResponse > 30:
                        self.__writer.write(b'PING :tmi.twitch.tv\r\n')
                        sentPing = True
                    if sentPing == True and time.time() - lastResponse > 40:
                        self.__close()
                        print(f'[Twitch {self.alias}] Lost connection, retrying in 5 seconds')
                        await asyncio.sleep(5)
                        break
                else:
                    sentPing = False
                    lastResponse = time.time()
                    if data == 'PING :tmi.twitch.tv':
                        self.__writer.write(b'PONG :tmi.twitch.tv\r\n')
                    elif data[0] == '@' and 'PRIVMSG #' in data:
                        self.onrawMsg(data)
        self.__close()

class TwitchMessage():
    def __init__(self, context : Twitch, rawMessage : str):
        self.__context = context
        self.raw = rawMessage

        data = self.__parseRawMsg(rawMessage)

        self.message : str = data.get('message', None)
        self.emotes : dict = data.get('emotes', {})

        self.badges : dict = data.get('badges', {})

        self.UTCTimestamp : datetime.datetime = data.get('UTCTimestamp', None)

        self.mod : bool = data.get('mod', None)
        self.subscriber : bool = data.get('subscriber', None)
        self.turbo : bool = data.get('turbo', None)

        self.channel : str = data.get('channel', None)
        self.roomId : str = data['keys'].get('room-id', None)

        self.userId : str = data['keys'].get('user-id', None)
        self.username : str = data.get('username', None)
        self.displayName : str = data['keys'].get('display-name', None)
        self.color : str = data['keys'].get('color', None)
        self.userType : str = data['keys'].get('user-type', None)
        self.firstMsg : bool = data.get('firstMsg', None)
        self.regular : bool = self.__context.isRegular(self.channel, self.username)

        self.id : str = data['keys'].get('id', None)
        self.clientNonce : str = data['keys'].get('client-nonce', None)
        self.flags : str = data['keys'].get('flags', None)
        self.badgeInfo : str = data['keys'].get('badge-info', None)

        self.replyDisplayName : str = data['keys'].get('reply-parent-display-name', None)
        self.replyMsg : str = data['keys'].get('reply-parent-msg-body', None)
        self.replyId : str = data['keys'].get('reply-parent-msg-id', None)
        self.replyUserId : str = data['keys'].get('reply-parent-user-id', None)
        self.replyUsername : str = data['keys'].get('reply-parent-user-login', None)

    @property
    def isReply(self): return self.replyId != None

    @property
    def name(self): return self.username

    @property
    def twitchContext(self): return self.__context.clientContext

    def __parseRawMsg(self, rawMsg : str):
        dictRes = {}
        if (rawMsg[0] != '@'): return dictRes
        split = rawMsg[1:].split('.tmi.twitch.tv PRIVMSG #', 1)
        if (len(split) != 2): return dictRes

        dictRes['channel'], dictRes['message'] = split[1].split(' :', 1)

        split, dictRes['username'] = split[0].rsplit('@', 1)
        split = split.rsplit(' :', 1)[0]

        dictRes['keys'] = {}      
        rawKeyValuePairs = split.split(';')
        for pair in rawKeyValuePairs:
            pairSplit = pair.split('=')
            if len(pairSplit) != 2: continue
            dictRes['keys'][pairSplit[0]] = pairSplit[1]

        dictRes['badges'] = self.__parseBadges(dictRes['keys'].get('badges', None))
        dictRes['emotes'] = self.__parseEmotes(dictRes['keys'].get('emotes', None))

        dictRes['mod'] = dictRes['keys'].get('mod', None) == '1'
        dictRes['subscriber'] = dictRes['keys'].get('subscriber', None) == '1'
        dictRes['turbo'] = dictRes['keys'].get('turbo', None) == '1'
        dictRes['firstMsg'] = dictRes['keys'].get('first-msg', None) == '1'

        dictRes['UTCTimestamp'] = self.__parseUTCTimeStamp(dictRes['keys'].get('tmi-sent-ts', None))
        return dictRes

    def __parseBadges(self, badgeStr : str):
        badges = {}
        if badgeStr == None: return badges
        for badge in badgeStr.split(','):
            if not '/' in badge: continue
            name, tier = badge.split('/')
            badges[name] = int(tier)
        return badges

    def __parseEmotes(self, emoteStr: str):
        emotes = {}
        for emote in emoteStr.split('/'):
            split = emote.split(':', 1)
            if len(split) != 2: continue
            emoteId = split[0]
            emotes[emoteId] = []
            for index in split[1].split(','):
                indexSplit = index.split('-', 1)
                if len(indexSplit) != 2: continue
                try:
                    fromIndex = int(indexSplit[0])
                    toIndex = int(indexSplit[1])
                except Exception: continue
                emotes[emoteId].append([fromIndex, toIndex])
        return emotes

    def __parseUTCTimeStamp(self, timestamp : str):
        try: timestampInt = int(timestamp)
        except Exception: timestampInt = 0
        return datetime.datetime.utcfromtimestamp(timestampInt/1000)

    def legacy(self):
        response = self.__dict__
        response['room'] = response['roomId']
        response['timestamp'] = response['UTCTimestamp'].strftime('%Y-%m-%d %H:%M:%S')

        response['_emotes'] = {}

        for emote in response['emotes']:
            response['_emotes'][emote] = response['emotes'][emote].copy()
            for i in range(len(response['emotes'][emote])):
                response['emotes'][emote][i] = str(response['emotes'][emote][i]['start']) + '-' + str(response['emotes'][emote][i]['end'])

        return response

class TwitchContext():
    def __init__(self, twitch : Twitch):
        self.__parent = twitch

    @property
    def defaultChannel(self): return self.__parent.defaultChannel()

    @property
    def twitchId(self): return self.__parent.id

    async def sendMessage(self, msg : str, channel : str):
        '''
        ** Exceptions **
        - Errors.Twitch.NotRunningError: Twitch not running
        - TypeError: Invalid data type of message
        - Errors.Twitch.ChannelNotFoundError: Provided channel does not exist
        '''
        await self.__parent.sendMessage(msg, channel)

    def isRegular(self, channel : str, username : str):
        return self.__parent.isRegular(channel, username)
