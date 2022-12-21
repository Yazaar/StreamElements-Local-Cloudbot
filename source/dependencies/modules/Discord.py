import asyncio, typing, discord, json
from . import Misc

if typing.TYPE_CHECKING:
    from dependencies.modules.Extensions import Extensions

class Discord():
    async def parseToken(token : str) -> tuple[bool, str]:
        resp, errorCode = await Misc.fetchUrl('https://discord.com/api/users/@me', headers={'authorization': f'Bot {token}'})

        if errorCode != 1: return False, 'unable to send HTTP request to validate Token'

        try: parsedResp = json.loads(resp)
        except Exception: return False, 'unable to parse HTTP response from Token validation'

        if not isinstance(parsedResp, dict): return False, 'invalid format returned by HTTP response from Token validation, should be json dictionary'

        botname = parsedResp.get('username', None)
        if botname is None: return False, 'HTTP response from Token validation does not include a username'
        return True, botname
    
    def __init__(self, id_ : str, alias : str, extensions : 'Extensions', token : str, regularGroups : list[str], guildConfig : dict[str, dict[str, typing.Any]], *, membersIntent=False, presencesIntent=False, messageContentIntent=False):
        self.__id = id_
        self.alias = alias
        
        self.__extensions = extensions
        self.__token = token
        self.__regularGroups = regularGroups
        self.__guildConfig = guildConfig

        intents = discord.Intents.default()
        intents.members = membersIntent
        intents.presences = presencesIntent
        intents.message_content = messageContentIntent

        self.__discordCom = DiscordCom(self, self.__extensions, membersIntent=membersIntent, presencesIntent=presencesIntent, messageContentIntent=messageContentIntent)

        self.__clientContext = DiscordClientContext(self)

        self.startDiscord()

    @property
    def id(self): return self.__id

    @property
    def token(self): return self.__token

    @property
    def regularGroups(self): return self.__regularGroups.copy()

    @property
    def guildConfig(self): return self.__guildConfig

    @property
    def clientContext(self): return self.__clientContext

    @property
    def intents(self): return self.__discordCom.intents

    async def setIntents(self, *, membersIntent=False, presencesIntent=False, messageContentIntent=False):
        if self.__discordCom.intents.members != membersIntent or self.__discordCom.intents.presences != presencesIntent or self.__discordCom.intents.message_content != messageContentIntent:
            await self.__discordCom.close()
            self.__discordCom = DiscordCom(self, self.__extensions, membersIntent=membersIntent, presencesIntent=presencesIntent, messageContentIntent=messageContentIntent)
            self.startDiscord()

    async def setToken(self, token : str):
        if token == self.__token: return True, None
        validToken, erroMsgOrBotname = await Discord.parseToken(token)
        if not validToken: return False, erroMsgOrBotname
        self.__token = token
        self.startDiscord()
        return True, None

    def setRegularGroups(self, regularGroups : list[str]): self.__regularGroups = [i for i in regularGroups if isinstance(i, str) and len(i) > 0]

    def stopDiscord(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.__discordCom.close())
    
    def startDiscord(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.startupDiscord())
    
    async def startupDiscord(self):
        #try: await self.close()
        #except Exception: pass
        try: await self.__discordCom.start(self.__token)
        except discord.errors.LoginFailure: print(f'[Discord {self.alias}] Failed to connect')
        except discord.errors.PrivilegedIntentsRequired: print(f'[Discord {self.alias}] Unable to start, one of the three optional intents not enabled in Discord application dashboard')
    
    async def getTextChannel(self, textChannel):
        try: channel = await self.__discordCom.fetch_channel(textChannel)
        except discord.errors.NotFound: return None, 'Invalid Channel ID'
        except discord.errors.Forbidden: return None, 'You do not have permission to fetch this channel'
        if not isinstance(channel, discord.TextChannel): return None, 'Channel not a text channel'
        return channel, None

class DiscordCom(discord.Client):
    def __init__(self, discordHandle : Discord, extensions : 'Extensions', *, membersIntent=False, presencesIntent=False, messageContentIntent=False) -> None:
        self.__extensions = extensions
        self.__discordHandle = discordHandle

        intents = discord.Intents.default()
        intents.members = membersIntent
        intents.presences = presencesIntent
        intents.message_content = messageContentIntent
        super().__init__(intents=intents)
    
    async def on_ready(self):
        print(f'[Discord {self.__discordHandle.alias}] Connected')
    
    async def on_message(self, message : discord.Message):
        self.__extensions.discordMessage(DiscordMessage(self.__discordHandle.clientContext, message))
    
    async def on_raw_message_delete(self, payload : discord.RawMessageDeleteEvent):
        self.__extensions.discordMessageDeleted(DiscordMessageDeleted(self.__discordHandle.clientContext, payload))

    async def on_raw_message_edit(self, payload : discord.RawMessageUpdateEvent):
        self.__extensions.discordMessageEdited(DiscordMessageEdited(self.__discordHandle.clientContext, payload))

    async def on_raw_reaction_add(self, payload : discord.RawReactionActionEvent):
        self.__extensions.discordMessageNewReaction(DiscordMessageNewReaction(self.__discordHandle.clientContext, payload))

    async def on_raw_reaction_remove(self, payload : discord.RawReactionActionEvent):
        self.__extensions.discordMessageRemovedReaction(DiscordMessageRemovedReaction(self.__discordHandle.clientContext, payload))

    async def on_raw_reaction_clear(self, payload : discord.RawReactionClearEvent):
        self.__extensions.discordMessageReactionsCleared(DiscordMessageReactionsCleared(self.__discordHandle.clientContext, payload))

    async def on_raw_reaction_clear_emoji(self, payload : discord.RawReactionClearEmojiEvent):
        self.__extensions.discordMessageReactionEmojiCleared(DiscordMessageReactionEmojiCleared(self.__discordHandle.clientContext, payload))

    async def on_member_join(self, member : discord.Member):
        self.__extensions.discordMemberJoined(DiscordMemberJoined(self.__discordHandle.clientContext, member))

    async def on_member_remove(self, member : discord.Member):
        self.__extensions.discordMemberRemoved(DiscordMemberRemoved(self.__discordHandle.clientContext, member))

    async def on_member_update(self, before : discord.Member, after : discord.Member):
        self.__extensions.discordMemberUpdated(DiscordMemberUpdated(self.__discordHandle.clientContext, before, after))

    async def on_member_ban(self, guild : discord.Guild, user : typing.Union[discord.Member, discord.User]):
        self.__extensions.discordMemberBanned(DiscordMemberBanned(self.__discordHandle.clientContext, guild, user))

    async def on_member_unban(self, guild : discord.Guild, user : typing.Union[discord.Member, discord.User]):
        self.__extensions.discordMemberUnbanned(DiscordMemberUnbanned(self.__discordHandle.clientContext, guild, user))

    async def on_guild_join(self, guild : discord.Guild):
        self.__extensions.discordGuildJoined(DiscordGuildJoined(self.__discordHandle.clientContext, guild))

    async def on_guild_remove(self, guild : discord.Guild):
        self.__extensions.discordGuildRemoved(DiscordGuildRemoved(self.__discordHandle.clientContext, guild))

    async def on_voice_state_update(self, member : discord.Member, before : discord.VoiceState, after : discord.VoiceState):
        self.__extensions.discordVoiceStateUpdate(DiscordVoiceStateUpdate(self.__discordHandle.clientContext, member, before, after))

class DiscordClientContext():
    def __init__(self, parent : Discord):
        self.__parent = parent
        pass

    @property
    def discordId(self): return self.__parent.id

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

        self.__discordContext = client
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

    @property
    def discordContext(self): return self.__discordContext

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

    def __getAttributes(self, parts : list[str]):
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
        self.__discordContext = client
        self.payload = payload
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMessageEdited():
    def __init__(self, client : DiscordClientContext, payload : discord.RawMessageUpdateEvent):
        self.__discordContext = client
        self.payload = payload
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMessageNewReaction():
    def __init__(self, client : DiscordClientContext, payload : discord.RawReactionActionEvent):
        self.__discordContext = client
        self.payload = payload
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMessageRemovedReaction():
    def __init__(self, client : DiscordClientContext, payload : discord.RawReactionActionEvent):
        self.__discordContext = client
        self.payload = payload
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMessageReactionsCleared():
    def __init__(self, client : DiscordClientContext, payload : discord.RawReactionClearEvent):
        self.__discordContext = client
        self.payload = payload
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMessageReactionEmojiCleared():
    def __init__(self, client : DiscordClientContext, payload : discord.RawReactionClearEmojiEvent):
        self.__discordContext = client
        self.payload = payload
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMemberJoined():
    def __init__(self, client : DiscordClientContext, member : discord.Member):
        self.__discordContext = client
        self.member = member
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMemberRemoved():
    def __init__(self, client : DiscordClientContext, member : discord.Member):
        self.__discordContext = client
        self.member = member
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMemberUpdated():
    def __init__(self, client : DiscordClientContext, before : discord.Member, after : discord.Member):
        self.__discordContext = client
        self.before = before
        self.after = after
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMemberBanned():
    def __init__(self, client : DiscordClientContext, guild : discord.Guild, user : typing.Union[discord.Member, discord.User]):
        self.__discordContext = client
        self.guild = guild
        self.user = user
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordMemberUnbanned():
    def __init__(self, client : DiscordClientContext, guild : discord.Guild, user : typing.Union[discord.Member, discord.User]):
        self.__discordContext = client
        self.guild = guild
        self.user = user
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordGuildJoined():
    def __init__(self, client : DiscordClientContext, guild : discord.Guild):
        self.__discordContext = client
        self.guild = guild
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordGuildRemoved():
    def __init__(self, client : DiscordClientContext, guild : discord.Guild):
        self.__discordContext = client
        self.guild = guild
    
    @property
    def discordContext(self): return self.__discordContext

class DiscordVoiceStateUpdate():
    def __init__(self, client : DiscordClientContext, member : discord.Member, before : discord.VoiceState, after : discord.VoiceState):
        self.__discordContext = client
        self.member = member
        self.before = before
        self.after = after
    
    @property
    def discordContext(self): return self.__discordContext
