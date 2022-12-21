##############
# Exceptions #
##############
class StructFormatError(Exception): pass
class StructValueError(Exception): pass
class DefaultTypeArgsError(Exception): pass

##########
# STATES #
##########
NO_CHANGES = 0
CHANGES = 1
INVALID = -1

#########
# LOGIC #
#########
class AdvancedType:
    def __init__(self, instanceOf : type | tuple[type], defaultTypeOrInstance, defaultTypeArgs : tuple = None):
        self.__instanceOf = instanceOf
        self.__default = defaultTypeOrInstance

        if type(defaultTypeArgs) == tuple: self.__defaultTypeArgs = defaultTypeArgs
        elif defaultTypeArgs == None: self.__defaultTypeArgs = tuple()
        else: raise DefaultTypeArgsError('Invalid defaultTypeArgs')
    
    def createInstance(self):
        if type(self.__default) == type: return self.__default(*self.__defaultTypeArgs)
        else: return self.__default
    
    def isinstance(self, obj): return isinstance(obj, self.__instanceOf)

def verifyDictStructure(obj : dict, structure : dict, *, rebuild=True) -> tuple[int, dict]:
    changes = 0
    if not isinstance(obj, dict):
        changes = INVALID
        obj = {}
        if not rebuild: return changes, obj
    
    if not isinstance(structure, dict): raise StructFormatError(f'Structure has to be of type dict (not {type(structure)})')
    
    objKeys = obj.keys()

    for key in structure:
        if type(key) == type or key in objKeys: continue

        if not rebuild: return INVALID, {}

        valuetype = type(structure[key])
        if valuetype == type: obj[key] = structure[key]()
        elif valuetype == list: obj[key] = []
        elif valuetype == dict: obj[key] = verifyDictStructure({}, structure[key], rebuild=rebuild)[1]
        elif valuetype == AdvancedType: obj[key] = structure[key].createInstance()
        else: raise StructValueError(f'Invalid value of type {valuetype} in structure (key: {key})')

        if changes == 0: changes = 1

    objKeys = list(objKeys)

    for key in objKeys:
        structkey = None
        if key in structure: structkey = key
        elif type(key) in structure: structkey = type(key)

        if structkey == None:
            del obj[key]
            if changes == NO_CHANGES: changes = CHANGES
            continue

        valuetype = type(structure[structkey])
        if valuetype == type:
            if not isinstance(obj[key], structure[structkey]):
                if changes == NO_CHANGES: changes = CHANGES
                if type(structkey) == type: del obj[key]
                else: obj[key] = structure[structkey]()
        
        elif valuetype == AdvancedType:
            at : AdvancedType = structure[structkey]
            if not at.isinstance(obj[key]):
                if changes == NO_CHANGES: changes = CHANGES
                obj[key] = at.createInstance()

        elif valuetype == dict:
            subChanges, obj[key] = verifyDictStructure(obj[key], structure[structkey], rebuild=rebuild)
            if subChanges == INVALID: changes = INVALID
            elif subChanges == CHANGES and changes == NO_CHANGES: changes = CHANGES
        
        elif valuetype == list:
            subChanges, obj[key] = verifyListStructure(obj[key], structure[structkey], rebuild=rebuild)
            if subChanges == INVALID: changes = INVALID
            elif subChanges == CHANGES and changes == NO_CHANGES: changes = CHANGES
        
        else: raise StructValueError(f'Invalid value of type {valuetype} in structure (key: {structkey})')

    return changes, obj

def verifyListStructure(obj : list, structure : list, *, rebuild=True) -> tuple[int, list]:
    if not isinstance(obj, list): return INVALID, []
    changes = NO_CHANGES

    if not isinstance(structure, list) or len(structure) != 1: raise StructFormatError(f'Structure has to be of type list (not {type(structure)}) with length 1')

    checktype = structure[0]
    valuetype = type(checktype)

    iterable = reversed(range(len(obj)))

    if valuetype == list:
        for index in iterable:
            subChanges, subItem = verifyListStructure(obj[index], checktype, rebuild=rebuild)
            if subChanges == INVALID: obj.pop(index)
            elif subChanges == CHANGES: obj[index] = subItem
            if changes != NO_CHANGES: changes = CHANGES
    
    elif valuetype == dict:
        for index in iterable:
            subChanges, subItem = verifyDictStructure(obj[index], checktype, rebuild=rebuild)
            if subChanges == INVALID: obj.pop(index)
            elif subChanges == CHANGES: obj[index] = subItem
            if changes != NO_CHANGES: changes = CHANGES
    
    elif valuetype == type:
        for index in iterable:
            if not isinstance(obj[index], checktype):
                obj.pop(index)
                changes = CHANGES
    
    elif valuetype == AdvancedType:
        for index in iterable:
            if not checktype.isinstance(obj[index]):
                obj.pop(index)
                changes = CHANGES
    
    else: raise StructValueError(f'Invalid value of type {valuetype} in structure (key: [0])')
    return changes, obj
