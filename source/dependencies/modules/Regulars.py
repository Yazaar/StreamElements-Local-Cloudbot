from pathlib import Path
import json, typing

GROUP_DATA_TYPE = dict[str, list[dict]]

class Regulars:
    def __init__(self):
        regularsDir = Path('dependencies/data/regulars')
        self.__twitchRegularsPath = regularsDir / 'twitch'
        self.__discordRegularsPath = regularsDir / 'discord'

        self.__discordRegularGroups : GROUP_DATA_TYPE = {}
        self.__twitchRegularGroups : GROUP_DATA_TYPE = {}

        self.__loadRegulars()

    def isRegular(self, userId, regularGroups : list, platform : str):
        if isinstance(regularGroups, str): regularGroups = [regularGroups]
        elif not isinstance(regularGroups, list): return False
        
        allRegulars = []
        for i in regularGroups:
            regulars, _ = self.__getGroup(platform, i)
            if regulars != None: allRegulars.append(regulars)
        
        for regularGroup in allRegulars:
            for regularUser in regularGroup:
                if regularUser['id'] == userId: return True
        return False

    def addRegular(self, alias : str, userId : str, regularGroupName : str, platform : str):
        if not isinstance(userId, str) or not isinstance(regularGroupName, str) or not isinstance(alias, str): return False
        
        regularGroup, regularFile = self.__getGroup(platform, regularGroupName)
        if regularGroup == None: return False

        for regularMember in regularGroup:
            if regularMember[1] == userId: return False
        
        regularGroup.append({'alias': alias, 'id': userId})

        self.__saveRegulars(regularGroup, regularFile)
        return True

    def removeRegular(self, userId : str, regularGroupName : str, platform : str):
        if not isinstance(userId, str) or not isinstance(regularGroupName, str): return False

        regularGroup, regularFile = self.__getGroup(platform)
        if regularGroup == None: return False

        deleted = False
        for index, regular in enumerate(reversed(regularGroup)):
            if regular[1] == userId:
                regularGroup.pop(index)
                deleted = True
                break
        
        if deleted: self.__saveRegulars(regularGroup, regularFile)
        return deleted

    def __getGroup(self, platform : str, groupName : str):
        if not isinstance(platform, str): return None, None
        if platform == 'twitch': regularGroups, regularsPath = self.__twitchRegularGroups, self.__twitchRegularsPath
        elif platform == 'discord': regularGroups, regularsPath = self.__discordRegularGroups, self.__discordRegularsPath
        else: return None, None

        regularGroup = regularGroups.get(groupName, None)
        if regularGroup == None: return None, None

        return regularGroup, regularsPath / f'{groupName}.json'

    def __loadRegulars(self):
        self.__discordRegularGroups.clear()
        self.__twitchRegularGroups.clear()
        for f in self.__discordRegularsPath.glob('*.json'):
            self.__loadGroupFile(self.__discordRegularGroups, f)
        for f in self.__twitchRegularsPath.glob('*.json'):
            self.__loadGroupFile(self.__twitchRegularGroups, f)

    def __loadGroupFile(self, dest : GROUP_DATA_TYPE, filePath : Path):
        if not filePath.is_file(): return
        fname = filePath.name[:-5]
        if len(fname) == 0: return
        changes, group = self.__verifyRegulars(self.__loadRegularsFile(filePath))
        if group == None:
            filePath.unlink()
            return
        if changes: self.__saveRegulars(group, filePath)
        dest[fname] = group

    def __loadRegularsFile(self, filepath : Path) -> GROUP_DATA_TYPE | None:
        if not filepath.is_file(): return None

        with open(filepath, 'r') as f:
            try: return json.load(f)
            except Exception: return None

    def __verifyRegulars(self, validateGroup : list[dict]):
        keys = ['alias', 'id']
        changes = False
        if not isinstance(validateGroup, list): return changes, None
        for index, regularMember in enumerate(reversed(validateGroup)):
            isValid, didChanges = self.__verifyDict(regularMember, keys)
            if not isValid:
                validateGroup.pop(index)
                changes = True
            elif didChanges: changes = True
        return changes, validateGroup
    
    def __verifyDict(self, checkDict : dict, keys : list) -> tuple[bool, bool]:
        changes = False
        for i in keys:
            if checkDict.get(i, None) == None: return False, changes
        
        for i in checkDict:
            if not i in keys:
                changes = True
                del checkDict[i]
        
        return True, changes

    def __saveRegulars(self, obj : list[dict], filepath : Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f: json.dump(obj, f)
