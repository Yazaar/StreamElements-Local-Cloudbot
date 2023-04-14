import time, typing
from . import ExtensionCrossover

if typing.TYPE_CHECKING:
    from . import Extensions

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
    def __init__(self, enabled : bool):
        self.__enabled = enabled
    
    @property
    def enabled(self): return self.__enabled

    def legacy(self): return (self.__enabled,)

class Initialize():
    def __init__(self, extension : 'Extensions.Extension'):
        self.__crossover = ExtensionCrossover.AsyncExtensionCrossover(extension)
        self.__extension = extension
    
    @property
    def crossover(self): return self.__crossover

    def legacy(self):
        dataArg = {
            'port': self.__crossover.port,
            'twitch_channel': self.__extension.twitch.defaultChannel() if self.__extension.twitch is not None else None
        }

        return (dataArg, self.__crossover.legacy())