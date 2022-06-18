from .vendor.StructGuard import StructGuard
from pathlib import Path
import json

GROUP_DATA_TYPE = dict[str, list[dict]]

class Regulars:
    def __init__(self):
        regularsDir = Path('dependencies/data/regulars')
        self.__twitchRegularsPath = regularsDir / 'twitch'
        self.__discordRegularsPath = regularsDir / 'discord'

        self.__groupStructure = {
            str: [
                {
                    'id': str,
                    'alias': str
                }
            ]
        }

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

    def addRegular(self, alias : str, userId : str, groupName : str, platform : str) -> tuple[bool, str | None]:
        if not isinstance(userId, str) or not isinstance(groupName, str) or not isinstance(alias, str):
            return False, 'alias, userId, groupName and platform has to be strings'
        
        regularGroup, regularFile = self.__getGroup(platform, groupName)
        if regularGroup == None: return False, 'unable to find groupName in platform ' + platform

        for regularMember in regularGroup:
            if regularMember[1] == userId: return False
        
        regularGroup.append({'alias': alias, 'id': userId})

        self.__saveRegulars(regularGroup, regularFile)
        return True, None

    def removeRegular(self, userId : str, groupName : str, platform : str) -> tuple[bool, str | None]:
        if not isinstance(userId, str): return False, 'userId has to be a string'
        if not not isinstance(groupName, str): return False, 'groupName has to be a string'

        regularGroup, regularFile = self.__getGroup(platform)
        if regularGroup == None: return False, 'invalid regular group'

        deleted = False
        for index, regular in enumerate(regularGroup):
            if regular[1] == userId:
                regularGroup.pop(index)
                deleted = True
                break

        if deleted: self.__saveRegulars(regularGroup, regularFile)
        return True, None

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
        changes, group = self.__verifyGroup(self.__loadRegularsFile(filePath))
        if changes: self.__saveRegulars(group, filePath)
        dest[fname] = group

    def __verifyGroup(self, group):
        changes, group = StructGuard.verifyListStructure(group, self.__groupStructure[str])
        for index in reversed(range(len(group))):
            if '' in [group[index]['id'], group[index]['alias']]:
                changes = True
                group.pop(index)
        return changes, group

    def __loadRegularsFile(self, filepath : Path) -> GROUP_DATA_TYPE | None:
        if not filepath.is_file(): return None

        with open(filepath, 'r') as f:
            try: return json.load(f)
            except Exception: return None
    
    def __saveRegulars(self, obj : list[dict], filepath : Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f: json.dump(obj, f)
