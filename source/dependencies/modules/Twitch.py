import asyncio, time, datetime

class Twitch:
    def __init__(self, extensions, tmi : str, botname : str, channels : list):
        self.extensions = extensions

        self.reader = None
        self.writer = None

        self.tmi = tmi
        self.botname = botname
        self.channels = channels

        self.regulars = {'global': [], 'channel': {}}

        self.getContext = self.__getContext()
        self.context = self.getContext()

        loop = asyncio.get_event_loop()

        loop.create_task(self.listen())
    
    def __getContext(self):
        parent = self

        class TwitchContext():
            def isRegular(self, channel : str, username : str):
                return parent.isRegular(channel, username)

        return TwitchContext
    
    @property
    def channel(self):
        if len(self.channels > 0): return self.channels[0]

        return None
    
    def onrawMsg(self, rawMsg : str):
        self.extensions.twitchMessage(TwitchMessage(self, rawMsg))
    
    def isRegular(self, channel : str, username : str):
        un, c = username.lower(), channel.lower()
        globalList = self.regulars['global']
        channelList = self.regulars['channel'].get(c, [])
        return un in globalList or un in channelList

    def close(self):
        if self.writer == None:
            self.reader = None
            return
        
        if not self.writer.is_closing():
            self.writer.close()
        
        self.reader = None
        self.writer = None
    
    async def read(self):
        if self.reader == None: return None
        try: data = await self.reader.readuntil(b'\n')
        except ConnectionError: return None
        return data.decode('utf-8').rstrip()
    
    async def listen(self):
        while True:
            self.reader, self.writer = await asyncio.open_connection('irc.twitch.tv', 6667)

            self.writer.write(b'PASS ' + self.tmi.lower().encode('utf-8') + b'\r\n')
            self.writer.write(b'NICK ' + self.botname.lower().encode('utf-8') + b'\r\n')

            for channel in self.channels:
                if not isinstance(channel, str) or channel == '': continue
                self.writer.write(b'JOIN #' + channel.lower().encode('utf-8') + b'\r\n')
            self.writer.write(b'CAP REQ :twitch.tv/tags\r\n')

            while True:
                data = await self.read()
                
                if data == None:
                    self.close()
                    print('[Twitch Chat] Connection to Twitch failed, retrying in 3 seconds...')
                    await asyncio.sleep(3)
                    break
                if data == ':tmi.twitch.tv NOTICE * :Login authentication failed' or data == ':tmi.twitch.tv NOTICE * :Improperly formatted auth':
                    print('[Twitch Chat] Invalid TMI')
                    self.close()
                    return
                elif 'End of /NAMES list' in data:
                    print('[Twitch Chat] Connected to: ' + ', '.join(self.channels).lower())
                    break
            
            if self.writer == None: continue
            
            lastResponse = time.time()
            sentPing = False
            while True:
                try: data = await asyncio.wait_for(self.read(), 5)
                except asyncio.TimeoutError: data = None

                if data == None:
                    if sentPing == False and time.time() - lastResponse > 30:
                        self.writer.write(b'PING :tmi.twitch.tv\r\n')
                        sentPing = True
                    if sentPing == True and time.time() - lastResponse > 40:
                        self.close()
                        print('[Twitch Chat] Lost connection, retrying in 5 seconds')
                        await asyncio.sleep(5)
                        break
                else:
                    sentPing = False
                    lastResponse = time.time()
                    if data == 'PING :tmi.twitch.tv':
                        self.writer.write(b'PONG :tmi.twitch.tv\r\n')
                    elif data[0] == '@' and 'PRIVMSG #' in data:
                        self.onrawMsg(data)

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
