from pathlib import Path
import os, datetime, json

class cooldowns():
    def __init__(self):
        self.__userCooldowns = {}
        self.__globalCooldown = datetime.datetime.now()
    
    def onPersonalCooldown(self, user):
        if not user.lower() in self.__userCooldowns:
            return False
        if self.__userCooldowns[user.lower()] < datetime.datetime.now():
            return False
        return True
    
    def onGlobalCooldown(self):
        if self.__globalCooldown < datetime.datetime.now():
            return False
        return True
    
    def setGlobalCooldown(self, seconds):
        if not seconds > 0:
            return {'status':'Error', 'message':'The duration can not be negative or zero...'}
        self.__globalCooldown = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        return {'status':'Success', 'until': self.__globalCooldown}
    
    def setUserCooldown(self, user, seconds):
        if not seconds > 0:
            return {'status':'Error', 'message':'The duration can not be negative or zero...'}
        self.__userCooldowns[user.lower()] = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        return {'status':'Success', 'user':user, 'until': self.__globalCooldown}

cooldownManager = cooldowns()
currentDate = datetime.date.today().strftime('%Y-%m-%d')
count = 0
root = Path(os.path.dirname(__file__))

if os.path.isfile(root / 'settings.json'):
    with open(root / 'settings.json', 'r') as f:
        try:
            settings = json.load(f)
        except Exception:
            settings = {}
else:
    settings = {}

def checkHistoryFile():
    if not os.path.isdir(root / 'history'):
        os.mkdir(root / 'history')

    if not os.path.isfile(root / 'history' / (currentDate + '.json')):
        with open(root / 'history' / (currentDate + '.json'), 'w') as f:
            f.write('[]')
        return []
    else:
        with open(root / 'history' / (currentDate + '.json'), 'r') as f:
            try:
                history = json.load(f)
                if type(history) != list:
                    raise Exception
                return history
            except Exception:
                pass
        with open(root / 'history' / (currentDate + '.json'), 'w') as f:
            f.write('[]')
            return []

def Initialize(data, EventData):
    global port, EData, history, channel
    port = data['port']
    channel = data['twitch_channel']
    EData = EventData
    history = checkHistoryFile()

def Execute(data):
    global count
    words = data['message'].split(' ')
    if words[0].lower() != '!followercounter':
        return

    if cooldownManager.onGlobalCooldown():
        return

    if cooldownManager.onPersonalCooldown(data['name']):
        return

    if len(words) > 1 and words[1].lower() == 'count':
        cooldownManager.setGlobalCooldown(10)
        cooldownManager.setUserCooldown(data['name'].lower(), 60)
        EData.SendMessage({'bot':'local', 'message':channel + ' has gained ' + str(count) + ' new followers today'})
        return
    
    if not data['moderator']:
        return

    if len(words) > 1 and words[1].lower() == 'realcount':
        cooldownManager.setGlobalCooldown(10)
        cooldownManager.setUserCooldown(data['name'].lower(), 60)
        EData.SendMessage({'bot':'local', 'message':'Real follower count of this stream: ' + str(len(history))})
        return


    if data['moderator'] and len(words) > 2 and words[1].lower() == 'set':
        try:
            setValue = int(words[2].replace(',', '.'))
            if setValue >= 0:
                count = setValue
            else:
                raise Exception
        except Exception:
            EData.SendMessage({'bot':'local', 'message':'Parameter 3 is invalid (should be a number, larger or equal to 0)'})
            return
        EData.CrossTalk({'event':'p-FollowerCounter:CurrentCount', 'data':count})

    if data['moderator'] and len(words) > 2 and words[1].lower() == 'add':
        try:
            increment = int(words[2].replace(',', '.'))
            if increment > 0:
                count += increment
            else:
                raise Exception
        except Exception:
            EData.SendMessage({'bot':'local', 'message':'Parameter 3 is invalid (should be a number, larger than 0)'})
            return
        EData.CrossTalk({'event':'p-FollowerCounter:CurrentCount', 'data':count})
    
    if data['moderator'] and len(words) > 2 and words[1].lower() == 'remove':
        try:
            reduction = int(words[2].replace(',', '.'))
            if reduction > 0 and reduction <= count:
                count -= reduction
            else:
                raise Exception
        except Exception:
            EData.SendMessage({'bot':'local', 'message':'Parameter 3 is invalid (should be a number, between 0 and ' + str(count+1) + ')'})
            return
        EData.CrossTalk({'event':'p-FollowerCounter:CurrentCount', 'data':count})

    if data['moderator'] and len(words) > 2 and words[1].lower() == 'load':
        if not os.path.isfile(root / 'history' / (words[2] + '.json')):
            EData.SendMessage({'bot':'local', 'message':'The date ' + words[2] + ' could not be found... (should follow the format YYYY-MM-DD)'})
            return
        with open(root / 'history' / (words[2] + '.json'), 'r') as f:
            try:
                loadDate = json.load(f)
            except Exception:
                EData.SendMessage({'bot':'local', 'message':'The following date ' + words[2] + ' was found, but the file is corrupted...'})
                return
        count += len(loadDate)
        EData.CrossTalk({'event':'p-FollowerCounter:CurrentCount', 'data':count})

def Tick():
    global currentDate
    if datetime.date.today().strftime('%Y-%m-%d') != currentDate:
        currentDate = datetime.date.today().strftime('%Y-%m-%d')
        checkHistoryFile()

def Event(data):
    global count
    if data['type'] == 'follow' and data['data']['username'].lower() not in history:
        history.append(data['data']['username'].lower())
        if not os.path.isdir(root / 'history'):
            os.mkdir(root / 'history')
        with open(root / 'history' / (currentDate + '.json'), 'w') as f:
            json.dump(history, f)
        count += 1
        EData.CrossTalk({'event':'p-FollowerCounter:NewFollow', 'data':data})

def NewSettings(data):
    global settings
    settings = data

def CrossTalk(message):
    if message == 'Request Current Count':
            EData.CrossTalk({'event':'p-FollowerCounter:CurrentCount', 'data':count})