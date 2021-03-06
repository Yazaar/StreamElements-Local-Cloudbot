# Executed on load (even if disabled)
# Data structure >> https://github.com/Yazaar/StreamElements-Local-Cloudbot/wiki/Script-structure-(Python)#initialize
def Initialize(data, EventHandler):
    global port, EHandler
    EHandler = EventHandler
    port = data['port']
    print(data)

# Executed on each chat message
# Data structure >> https://github.com/Yazaar/StreamElements-Local-Cloudbot/wiki/Script-structure-(Python)#execute
def Execute(data):
    print(data)


# Triggerd regularly, whenever none of the others are.
# How often it is triggerd depends on the amount of other events as well as their cap on executions per second.
a = 0
def Tick():
    global a
    #print(a)
    a += 1


# events:
#  follows
#  item redemptions
#  subscribtions
#  hosts
#  raids
#  cheers
#  tips
#
# Triggerd each time one of the event occurs (only real events, no simulated ones)
# Data structure >> https://developers.streamelements.com/endpoints/activities
def Event(data):
    print(data)


# events:
#  follows
#  item redemptions
#  subscribtions
#  hosts
#  raids
#  cheers
#  tips
#
# Triggerd each time one of the event occurs (only simulated events, no real ones)
# Special Data structure, test it out and see... (I can't see a reason to use it, but implemented because it exists)
def TestEvent(data):
    print(data)

# Triggerd each time that new settings are saved, the script have to be specified inside of the SettingsUI.json manually!
def NewSettings(data):
    print(data)

# state = True or False
# Whenever this script is enabled (True) or disabled (False).
def Toggle(state):
    print(state)

# message = whatever you sent
def CrossTalk(message):
    print(message)
