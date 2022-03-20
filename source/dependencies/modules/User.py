from pathlib import Path
import json

class Users:
    def __init__(self, data):
        self.data = data
        self.data.regulars = self.loadRegulars()
    
    def addRegular(self, raw_name):
        name = raw_name.lower()
        if name in self.data.regulars:
            return False
        
        self.data.regulars.append(name)
        self.saveRegulars()
        return True
    
    def removeRegular(self, raw_name):
        name = raw_name.lower()
        if not name in self.data.regulars:
            return False
        
        self.data.regulars.remove(name)
        self.saveRegulars()
        return True
    
    def loadRegulars(self):
        regularsFile = Path('dependencies/data/regulars.json')
        if not regularsFile.is_file(): return []

        with open(regularsFile, 'r') as f:
            try: regulars = json.load(f)
            except Exception: regulars = []
        
        if isinstance(regulars, list): return regulars
        else: return []
    
    def saveRegulars(self):
        regularsFile = Path('dependencies/data/regulars.json')
        regularsFile.parent.mkdir(parents=True, exist_ok=True)
        with open(regularsFile, 'w') as f:
            json.dump(self.data.regulars, f)
    
    def isRegular(self, user):
        for i in self.data.regulars:
            if i == user:
                return True
        return False
