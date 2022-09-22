import time

class Tick():
    def __init__(self, prevTimeNs : int):
        self.__timeNs = time.time_ns()
        self.__timeNsDiff = self.__timeNs - prevTimeNs
    
    @property
    def timeNs(self): return self.__timeNs

    @property
    def timeS(self): return self.__timeNs / 1000000000

    @property
    def timeNsDiff(self): return self.__timeNsDiff

class Toggle():
    pass

class Initialize():
    pass