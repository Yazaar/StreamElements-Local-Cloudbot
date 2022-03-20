import asyncio, typing, discord

class Discord(discord.Client):
    def __init__(self, extensions, key : str):
        self.__extensions = extensions
        self.__key = key

        intents = discord.Intents.default()
        intents.members = True

        super().__init__(intents=intents)
        
        self.clientContext = DiscordClientContext(self)

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.start(self.__key))

    async def on_ready(self):
        print('Booted as: ' + self.user.name)
    
    async def on_message(self, message : discord.Message):
        self.__extensions.discordMessage(DiscordMessage(self.clientContext, message))
    
    async def on_raw_message_delete(self, payload : discord.RawMessageDeleteEvent):
        self.__extensions.discordMessageDeleted(DiscordMessageDeleted(self.clientContext, payload))

    async def on_raw_message_edit(self, payload : discord.RawMessageUpdateEvent):
        self.__extensions.discordMessageEdited(DiscordMessageEdited(self.clientContext, payload))

    async def on_raw_reaction_add(self, payload : discord.RawReactionActionEvent):
        self.__extensions.discordMessageNewReaction(DiscordMessageNewReaction(self.clientContext, payload))

    async def on_raw_reaction_remove(self, payload : discord.RawReactionActionEvent):
        self.__extensions.discordMessageRemovedReaction(DiscordMessageRemovedReaction(self.clientContext, payload))

    async def on_raw_reaction_clear(self, payload : discord.RawReactionClearEvent):
        self.__extensions.discordMessageReactionsCleared(DiscordMessageReactionsCleared(self.clientContext, payload))

    async def on_raw_reaction_clear_emoji(self, payload : discord.RawReactionClearEmojiEvent):
        self.__extensions.discordMessageReactionEmojiCleared(DiscordMessageReactionEmojiCleared(self.clientContext, payload))

    async def on_member_join(self, member : discord.Member):
        self.__extensions.discordMemberJoined(DiscordMemberJoined(self.clientContext, member))

    async def on_member_remove(self, member : discord.Member):
        self.__extensions.discordMemberRemoved(DiscordMemberRemoved(self.clientContext, member))

    async def on_member_update(self, before : discord.Member, after : discord.Member):
        self.__extensions.discordMemberUpdated(DiscordMemberUpdated(self.clientContext, before, after))

    async def on_member_ban(self, guild : discord.Guild, user : typing.Union[discord.Member, discord.User]):
        self.__extensions.discordMemberBanned(DiscordMemberBanned(self.clientContext, guild, user))

    async def on_member_unban(self, guild : discord.Guild, user : typing.Union[discord.Member, discord.User]):
        self.__extensions.discordMemberUnbanned(DiscordMemberUnbanned(self.clientContext, guild, user))

    async def on_guild_join(self, guild : discord.Guild):
        self.__extensions.discordGuildJoined(DiscordGuildJoined(self.clientContext, guild))

    async def on_guild_remove(self, guild : discord.Guild):
        self.__extensions.discordGuildRemoved(DiscordGuildRemoved(self.clientContext, guild))

    async def on_voice_state_update(self, member : discord.Member, before : discord.VoiceState, after : discord.VoiceState):
        self.__extensions.discordVoiceStateUpdate(DiscordVoiceStateUpdate(self.clientContext, member, before, after))

class DiscordClientContext():
    def __init__(self, parent : Discord):
        self.__parent = parent
        pass

    def id(self): return self.__parent.id

    @property
    def activity(self): return self.__parent.activity

    @property
    def allowedMentions(self): return self.__parent.allowed_mentions

    @property
    def cachedMessages(self): return self.__parent.cached_messages

    @property
    def emojis(self): return self.__parent.emojis

    @property
    def guilds(self): return self.__parent.guilds

    @property
    def intents(self): return self.__parent.intents

    @property
    def latency(self): return self.__parent.latency

    @property
    def privateChannels(self): return self.__parent.private_channels

    @property
    def user(self): return self.__parent.user

    @property
    def users(self): return self.__parent.users

    @property
    def voiceClients(self): return self.__parent.voice_clients
    
    def getChannel(self, channelId : int): return self.__parent.get_channel(channelId)
    async def fetchChannel(self, channelId : int): return await self.__parent.fetch_channel(channelId)
    
    def getGuild(self, guildId : int): return self.__parent.get_guild(guildId)
    async def fetchGuild(self, guildId : int): return await self.__parent.fetch_guild(guildId)
    
    def getUser(self, userId : int): return self.__parent.get_user(userId)
    async def fetchUser(self, userId : int): return await self.__parent.fetch_user(userId)
    
    def getEmoji(self, emojiId : int): return self.__parent.get_emoji(emojiId)

    async def changePresence(self, activity=None, status=None, afk=None): return await self.__parent.change_presence(activity=activity, status=status, afk=afk)

    async def waitFor(self, event, check=None, timeout=None): return await self.__parent.wait_for(event, check=check, timeout=timeout)

    def getAllChannels(self): return self.__parent.get_all_channels()

    def getAllMembers(self): return self.__parent.get_all_members()

    async def applicationInfo(self): return await self.__parent.application_info()

    async def fetchInvite(self, url : typing.Union[discord.Invite, str], withCounts=True): return await self.__parent.fetch_invite(url, with_counts=withCounts)

class DiscordMessage():
    def __init__(self, client : DiscordClientContext, msg : discord.Message, copy = None):
        if isinstance(copy, DiscordMessage):
            self.__copy(copy)
            return
        
        if not isinstance(msg, discord.Message):
            self.error = True
            return

        self.client = client
        self.context = msg
        
        self.error = False
        
        self.attributes = {}
        self.rawMessage = msg.content

        parts = self.rawMessage.split(' ')

        self.command = parts[0]
        parts = parts[1:]

        self.words = self.__getAttributes(parts)
        self.wordsLength = len(self.words)
        
        self.message = ' '.join(parts)
        self.length = len(self.message)
        self.lowerMessage = self.message.lower()

        self.lowerWords = self.lowerMessage.split(' ')

    def __copy(self, msg):
        self.client = msg.client
        self.context = msg.context
        self.error = msg.error
        self.attributes = msg.attributes.copy()
        self.rawMessage = msg.rawMessage
        self.command = msg.command
        self.words = msg.words.copy()
        self.wordsLength = msg.wordsLength
        self.message = msg.message
        self.length = msg.length
        self.lowerMessage = msg.lowerMessage
        self.lowerWords = msg.lowerWords.copy()

    def __getAttributes(self, parts : typing.List[str]):
        self.attributes.clear()
        index = -1
        lastIndex = len(parts) - 1

        skipNext = False
        for i in parts:
            index += 1
            if parts[i] == '': continue
            if skipNext:
                skipNext = False
                continue

            if parts[i][0] == '-':
                if index == lastIndex: self.attributes[parts[i][1:]] = True
                else: self.attributes[parts[i][1:]] = parts[i+1]
            else: break
        
        return parts[index+1:]

class DiscordMessageDeleted():
    def __init__(self, client : DiscordClientContext, payload : discord.RawMessageDeleteEvent):
        self.client = client
        self.payload = payload

class DiscordMessageEdited():
    def __init__(self, client : DiscordClientContext, payload : discord.RawMessageUpdateEvent):
        self.client = client
        self.payload = payload

class DiscordMessageNewReaction():
    def __init__(self, client : DiscordClientContext, payload : discord.RawReactionActionEvent):
        self.client = client
        self.payload = payload

class DiscordMessageRemovedReaction():
    def __init__(self, client : DiscordClientContext, payload : discord.RawReactionActionEvent):
        self.client = client
        self.payload = payload

class DiscordMessageReactionsCleared():
    def __init__(self, client : DiscordClientContext, payload : discord.RawReactionClearEvent):
        self.client = client
        self.payload = payload

class DiscordMessageReactionEmojiCleared():
    def __init__(self, client : DiscordClientContext, payload : discord.RawReactionClearEmojiEvent):
        self.client = client
        self.payload = payload

class DiscordMemberJoined():
    def __init__(self, client : DiscordClientContext, member : discord.Member):
        self.client = client
        self.member = member

class DiscordMemberRemoved():
    def __init__(self, client : DiscordClientContext, member : discord.Member):
        self.client = client
        self.member = member

class DiscordMemberUpdated():
    def __init__(self, client : DiscordClientContext, before : discord.Member, after : discord.Member):
        self.client = client
        self.before = before
        self.after = after

class DiscordMemberBanned():
    def __init__(self, client : DiscordClientContext, guild : discord.Guild, user : typing.Union[discord.Member, discord.User]):
        self.client = client
        self.guild = guild
        self.user = user

class DiscordMemberUnbanned():
    def __init__(self, client : DiscordClientContext, guild : discord.Guild, user : typing.Union[discord.Member, discord.User]):
        self.client = client
        self.guild = guild
        self.user = user

class DiscordGuildJoined():
    def __init__(self, client : DiscordClientContext, guild : discord.Guild):
        self.client = client
        self.guild = guild

class DiscordGuildRemoved():
    def __init__(self, client : DiscordClientContext, guild : discord.Guild):
        self.client = client
        self.guild = guild

class DiscordVoiceStateUpdate():
    def __init__(self, client : DiscordClientContext, member : discord.Member, before : discord.VoiceState, after : discord.VoiceState):
        self.client = client
        self.member = member
        self.before = before
        self.after = after
