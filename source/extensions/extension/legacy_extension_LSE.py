#######################
# all twitch triggers #
#######################
def twitchMessage(message : dict):
    print('[Legacy example] twitchMessage: ', message)

###############################
# all StreamElements triggers #
###############################
def streamElementsEvent(data : dict):
    print('[Legacy example] streamElementsEvent: ', data)

def streamElementsTestEvent(data : dict):
    print('[Legacy example] streamElementsTestEvent: ', data)

####################
# general triggers #
####################
def initialize(data : dict):
    print('[Legacy example] toggle: ', data)

def toggle(data : dict):
    print('[Legacy example] toggle: ', data)

def newSettings(data : dict):
    print('[Legacy example] newSettings: ', data)

def tick():
    print('[Legacy example] tick')

def webhook(secret : str, data):
    print('[Legacy example] webhook')

def crossTalk(data):
    print('[Legacy example] crossTalk: ', data)
