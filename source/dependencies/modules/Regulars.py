from pathlib import Path
import json, typing

GROUP_DATA_TYPE = typing.Dict[str, typing.List[typing.Tuple[str, str]]]

class Regulars:
    def __init__(self):
        regularsDir = Path('dependencies/data/regulars')
        self.__twitchRegularsFile = regularsDir / 'twitch.json'
        self.__discordRegularsFile = regularsDir / 'discord.json'

        self.__discordRegularGroups : GROUP_DATA_TYPE = {}
        self.__twitchRegularGroups : GROUP_DATA_TYPE = {}

        self.__loadRegulars()

    def isRegular(self, userId : str, regularGroups : list, platform : str):
        if isinstance(regularGroups, str): regularGroups = [regularGroups]
        elif not isinstance(regularGroups, list): return False
        if not isinstance(userId, str): return False

        allRegulars = self.__getPlatformList(platform)
        if allRegulars == None: return False

        for regularGroup in regularGroups:
            for regularUser in allRegulars.get(regularGroup, []):
                if regularUser[1] == userId: return True
        return False

    def addRegular(self, alias : str, userId : str, regularGroupName : str, platform : str):
        if not isinstance(userId, str) or not isinstance(regularGroupName, str) or not isinstance(alias, str): return False
        
        regularGroups = self.__getPlatformList(platform)
        if regularGroups == None: return False

        regularGroup = regularGroups.get(regularGroupName, None)
        if regularGroup == None: return False

        for regularMember in regularGroup:
            if regularMember[1] == userId: return False
        
        regularGroup.append((alias, userId))

        self.__saveRegulars()
        return True

    def removeRegular(self, userId : str, regularGroupName : str, platform : str):
        if not isinstance(userId, str) or not isinstance(regularGroupName, str): return False

        regularGroups = self.__getPlatformList(platform)
        if regularGroups == None: return False

        regularGroup : list = regularGroups.get(regularGroupName, None)
        if regularGroup == None: return False

        deleted = False
        for index, regular in enumerate(reversed(regularGroup)):
            if regular[1] == userId:
                regularGroup.pop(index)
                deleted = True
                break
        
        if deleted: self.__saveRegulars()
        return deleted

    def __getPlatformList(self, platform : str):
        if not isinstance(platform, str): return None
        if platform == 'twitch': return self.__twitchRegularGroups
        elif platform == 'discord': return self.__discordRegularGroups
        else: return None

    def __loadRegulars(self):
        discordChanges, self.__discordRegularGroups = self.__verifyRegulars(self.__loadRegularsFile(self.__discordRegularsFile))
        if discordChanges:
            self.__saveRegulars(self.__discordRegularGroups, self.__discordRegularsFile)
        
        twitchChanges, self.__twitchRegularGroups = self.__verifyRegulars(self.__loadRegularsFile(self.__twitchRegularsFile))
        if twitchChanges:
            self.__saveRegulars(self.__twitchRegularGroups, self.__twitchRegularsFile)


    def __loadRegularsFile(self, filepath : Path) -> GROUP_DATA_TYPE | None:
        if not filepath.is_file(): return None

        with open(filepath, 'r') as f:
            try: return json.load(f)
            except Exception: return None

    def __verifyRegulars(self, validateGroup : GROUP_DATA_TYPE) -> typing.Tuple[bool, GROUP_DATA_TYPE]:
        changes = False
        if not isinstance(validateGroup, dict):
            return True, {}
        for regularGroup in validateGroup:
            if not isinstance(validateGroup[regularGroup], list):
                validateGroup[regularGroup] = []
                changes = True
                continue
            for index, regularMember in enumerate(reversed(validateGroup[regularGroup])):
                if not isinstance(regularMember, str):
                    validateGroup[regularGroup].pop(index)
                    changes = True
        return changes, validateGroup

    def __saveRegulars(self, obj : GROUP_DATA_TYPE, filepath : Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f: json.dump(obj, f)
