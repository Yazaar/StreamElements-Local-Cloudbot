from pathlib import Path
import os, asyncio, aiohttp, json, sys, hashlib, time

def autoUpdate():
    for i in sys.argv:
        iL = i.lower()
        if iL == '--noupdate': return -1
        elif iL == '--autoupdate': return 1
    return 0

def forceUpdate():
    for i in sys.argv:
        if i.lower() == '--forceupdate': return True
    return False

def doMakeLatestVersionsFile():
    for i in sys.argv:
        if i.lower() == '--makelatestversions': return True
    return False

UPDATE_STATE = autoUpdate()

async def fetchUrl(url, readBytes=False):
    try:
        async with aiohttp.ClientSession() as sesson:
            async with sesson.get(url) as response:
                if readBytes: data = await response.read()
                else: data = await response.text()
    except aiohttp.ClientConnectorError:
        return None, -1
    except aiohttp.InvalidURL:
        return None, -2
    except Exception:
        return None, -3
    await asyncio.sleep(0.1)
    # asyncio.sleep(0.1) prevents RuntimeError from being raised if loop is closing too soon
    # aiohttp seem have a problem with asyncio.new_event_loop(), probably used by asyncio.run(), since using asyncio.get_event_loop() to get a new loop is depricated
    # Not a problem if asyncio.get_event_loop() + loop.run_until_complete(main()) is used explicitly, except that a DepricatedWarning print is visible (python 3.10)
    return data, 1

def generateDLUrl(posixPath : str): return f'https://raw.githubusercontent.com/Yazaar/StreamElements-Local-Cloudbot/master/source/{posixPath}'

def hashFile(fp : Path):
    posixPath = fp.as_posix()
    with open(fp, 'rb') as fb: return {'hash': hashlib.md5(fb.read()).hexdigest(), 'url': generateDLUrl(posixPath)}

def makeLatestVersionsFile():
    files = {}

    matchDirs = [
        'dependencies/modules',
        'dependencies/modules/vendor/StructGuard',
        'dependencies/web/HTML',
        'dependencies/web/static/scripts',
        'dependencies/web/static/styles'
    ]

    matchFiles = ['LocalStreamElements.py', 'requirements.txt']

    for d in matchDirs:
        for f in Path(d).glob('*'):
            if f.is_file():
                files[f.as_posix()] = hashFile(f)
    
    for f in matchFiles:
        fp = Path(f)
        if fp.is_file():
            files[fp.as_posix()] = hashFile(fp)
    
    with open(f'LatestVersion-{time.time_ns()}.json', 'w') as f:
        json.dump({'log': '', 'files': files}, f)

async def patchFile(filepath : Path, url : str):
    data, _ = await fetchUrl(url, readBytes=True)
    if data is None: return False
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'wb') as f: f.write(data)
    return True

async def main():
    os.chdir(Path(__file__).parent.absolute())

    if doMakeLatestVersionsFile():
        makeLatestVersionsFile()
        return

    await update()

    return

    try: from dependencies.modules import Core
    except ImportError:
        input('Unable to launch due to missing dependencies, automatically exiting once you hit enter\n')
        return
    
    await Core.run()

def getCurrentVersions() -> dict[str, int]:
    versionFile = Path('dependencies/data/version.json')
    try:
        if not versionFile.is_file(): raise FileNotFoundError()
        with open(versionFile, 'r') as f: data = json.load(f)
        if not isinstance(data, dict): raise ValueError()
        return data
    except: return {}

def saveCurrentVersions(data):
    versionFile = Path('dependencies/data/version.json')
    versionFile.parent.mkdir(parents=True, exist_ok=True)
    with open(versionFile, 'w') as f: json.dump(data, f)

async def downloadNewestVersions() -> dict | None:
    text, errorCode = await fetchUrl('https://raw.githubusercontent.com/Yazaar/StreamElements-Local-Cloudbot/master/LatestVersion.json')
    if errorCode < 0:
        print('[Error] Unable to check for updates. No internet connection? (trying to launch anyways)')
        return None
    
    return json.loads(text)

def WaitForYN(msg : str):
    if UPDATE_STATE == -1:
        print('>> n')
        return False
    elif UPDATE_STATE == 1:
        print('>> y')
        return True
    
    while True:
        temp = input(msg).lower()
        if temp == 'y': return True
        elif temp == 'n': return False

async def update():
    newestVersion = await downloadNewestVersions()
    if newestVersion is None:
        print('Unable to load update log, unable to check for updates')
        return

    currentVersions = getCurrentVersions()
    if forceUpdate(): currentVersions.clear()

    patches = []

    newestFiles = newestVersion.get('files', None)
    if newestFiles is None: return

    for i in newestFiles:
        filePatch = newestFiles[i]
        if not i in currentVersions or currentVersions[i] != filePatch['hash']:
            patches.append({'file': i, 'patch': filePatch})
    
    patchCount = len(patches)
    if patchCount == 0: return

    print(f'{patchCount} files require an update, would you like to continue (y/n)?')
    if not WaitForYN('>> '): return

    patchChanges = False

    for patch in patches:
        if await patchFile(Path(patch['file']), patch['patch']['url']):
            currentVersions[patch['file']] = patch['patch']['hash']
            patchChanges = True
    
    if not patchChanges:
        print('Failed to patch files, trying to launch anyways\n')
        return
    
    saveCurrentVersions(currentVersions)

    print('Update complete!')

if __name__ == '__main__':
    asyncio.run(main())
