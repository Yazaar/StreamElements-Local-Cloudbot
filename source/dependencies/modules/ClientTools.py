import datetime

class CooldownManager():
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
