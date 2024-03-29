from .vendor.StructGuard import StructGuard
from pathlib import Path
import json, os

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
            regulars, _, _ = self.__getGroup(platform, i)
            if regulars != None: allRegulars.append(regulars)
        
        for regularGroup in allRegulars:
            for regularUser in regularGroup:
                if regularUser['id'] == userId: return True
        return False

    def addRegular(self, alias : str, userId : str, groupName : str, platform : str) -> tuple[bool, str | None, bool]:
        if not isinstance(userId, str) or not isinstance(groupName, str) or not isinstance(alias, str):
            return False, 'alias, userId, groupName and platform has to be strings', False
        
        regularGroup, regularFile, createdGroup = self.__getGroup(platform, groupName, create=True)
        if regularGroup == None: return False, f'invalid regular group', False

        for regularMember in regularGroup:
            if regularMember['id'] == userId: return False, 'regular does already exist', False
        
        regularGroup.append({'alias': alias, 'id': userId})

        self.__saveRegulars(regularGroup, regularFile)
        return True, None, createdGroup

    def removeRegular(self, userId : str, groupName : str, platform : str) -> tuple[bool, str | None, bool]:
        if not isinstance(userId, str): return False, 'userId has to be a string', False
        if not isinstance(groupName, str): return False, 'groupName has to be a string', False

        regularGroup, regularFile, _ = self.__getGroup(platform, groupName)
        if regularGroup == None: return False, 'invalid regular group', False

        deleted = False
        for index, regular in enumerate(regularGroup):
            if regular['id'] == userId:
                regularGroup.pop(index)
                deleted = True
                break
        
        deletedGroup = False
        if deleted:
            if len(regularGroup) == 0:
                deletedGroup = True
                self.__deleteGroup(platform, groupName)
            else: self.__saveRegulars(regularGroup, regularFile)
        return True, None, deletedGroup

    def getRegulars(self, platform : str, groupname : str):
        if platform == 'twitch': return self.__twitchRegularGroups.get(groupname)
        elif platform == 'discord': return self.__discordRegularGroups.get(groupname)

    def getGroups(self, platform : str):
        if platform == 'twitch': return sorted(self.__twitchRegularGroups.keys())
        elif platform == 'discord': return sorted(self.__discordRegularGroups.keys())
        else: return None

    def __getGroupCategory(self, platform : str):
        if not isinstance(platform, str): return None, None
        if platform == 'twitch': return self.__twitchRegularGroups, self.__twitchRegularsPath
        elif platform == 'discord': return self.__discordRegularGroups, self.__discordRegularsPath
        else: return None, None
    
    def __getGroup(self, platform : str, groupName : str, *, create=False) -> tuple[list[dict], Path, bool] | tuple[None, None, False]:
        regularGroups, regularsPath = self.__getGroupCategory(platform)
        if regularGroups is None: return None, None, False

        createdGroup = False

        regularGroup = regularGroups.get(groupName, None)
        if not create and regularGroup is None: return None, None, False

        if regularGroup == None:
            createdGroup = True
            regularGroups[groupName] = []
            regularGroup = regularGroups[groupName]

        return regularGroup, regularsPath / f'{groupName}.json', createdGroup

    def __deleteGroup(self, platform : str, groupName : str):
        regularGroups, _ = self.__getGroupCategory(platform)
        if regularGroups is None: return
        
        _, regularsPath, _ = self.__getGroup(platform, groupName)
        if regularsPath is None: return

        if not groupName in regularGroups: return
        del regularGroups[groupName]

        if regularsPath.is_file(): os.remove(regularsPath)

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
