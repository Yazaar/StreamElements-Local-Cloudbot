from dependencies.modules import Templates

#######################
# all twitch triggers #
#######################
async def twitchMessage(message : Templates.TwitchMessage):
    print('[Async example] twitchMessage: ', message)

###############################
# all StreamElements triggers #
###############################
async def streamElementsEvent(data : Templates.StreamElementsGenericEvent): # DonationEvent etc in reality, all going through this trigger
    print('[Async example] streamElementsEvent: ', data)

async def streamElementsTestEvent(data : Templates.StreamElementsGenericEvent): # DonationEvent etc in reality, all going through this trigger
    print('[Async example] streamElementsTestEvent: ', data)

####################
# general triggers #
####################
async def initialize():
    print('[Async example] initialize')

async def toggle(data):
    print('[Async example] toggle: ', data)

async def crossTalk(data):
    print('[Async example] crossTalk: ', data)

async def newSettings(data):
    print('[Async example] newSettings: ', data)

async def tick():
    print('[Async example] tick')

async def webhook(webhook : Templates.Webhook):
    print('[Async example] webhook')

async def crossTalk(data : Templates.CrossTalk):
    print('[Async example] crossTalk: ', data)

########################
# all discord triggers #
########################
async def discordMessage(data : Templates.DiscordMessage):
    print('[Async example] discordMessage: ', data)

async def discordMessageDeleted(data : Templates.DiscordMessageDeleted):
    print('[Async example] discordMessageDeleted: ', data)

async def discordMessageEdited(data : Templates.DiscordMessageEdited):
    print('[Async example] discordMessageEdited: ', data)

async def discordMessageNewReaction(data : Templates.DiscordMessageNewReaction):
    print('[Async example] discordMessageNewReaction: ', data)

async def discordMessageRemovedReaction(data : Templates.DiscordMessageRemovedReaction):
    print('[Async example] discordMessageRemovedReaction: ', data)

async def discordMessageReactionsCleared(data : Templates.DiscordMessageReactionsCleared):
    print('[Async example] discordMessageReactionsCleared: ', data)

async def discordMessageReactionEmojiCleared(data : Templates.DiscordMessageReactionEmojiCleared):
    print('[Async example] discordMessageReactionEmojiCleared: ', data)

async def discordMemberJoined(data : Templates.DiscordMemberJoined):
    print('[Async example] discordMemberJoined: ', data)

async def discordMemberRemoved(data : Templates.DiscordMemberRemoved):
    print('[Async example] discordMemberRemoved: ', data)

async def discordMemberUpdated(data : Templates.DiscordMemberUpdated):
    print('[Async example] discordMemberUpdated: ', data)

async def discordMemberBanned(data : Templates.DiscordMemberBanned):
    print('[Async example] discordMemberBanned: ', data)

async def discordMemberUnbanned(data : Templates.DiscordMemberUnbanned):
    print('[Async example] discordMemberUnbanned: ', data)

async def discordGuildJoined(data : Templates.DiscordGuildJoined):
    print('[Async example] discordGuildJoined: ', data)

async def discordGuildRemoved(data : Templates.DiscordGuildRemoved):
    print('[Async example] discordGuildRemoved: ', data)

async def discordVoiceStateUpdate(data : Templates.DiscordVoiceStateUpdate):
    print('[Async example] discordVoiceStateUpdate: ', data)
