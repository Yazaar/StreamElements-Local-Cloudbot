import requests, os, sys, json
from pathlib import Path

# LSE requirements
import requests, shutil, flask, flask_socketio, psutil, geventwebsocket
from engineio.async_drivers import gevent

def fetchUrl(url):
    try:
        response = requests.get(url)
    except Exception:
        return 0
    
    if response.status_code != 200:
        return -1

    return response

def checkForUpdates():
    response = fetchUrl('https://raw.githubusercontent.com/Yazaar/StreamElements-Local-Cloudbot/master/exeVersion.json')
    if response == 0:
        print('Unable to check for updates, no network?')
        return None
    elif response == -1:
        print('Unable to check for updates, GitHub down or file missing?')
        return None

    try:
        downloadData = json.loads(response.text)
    except Exception:
        print('Invalid update information structure (not JSON)')
        return None

    if not 'version' in downloadData:
        print('Update information key missing (version)')
        return None
    elif not 'url' in downloadData:
        print('Update information key missing (url)')
        return None
    elif not 'log' in downloadData:
        print('Update information key missing (log)')
        return None

    return downloadData

def WaitForYN():
    while True:
        temp = input().lower()
        if temp == 'y':
            return True
        elif temp == 'n':
            return False

def main():
    os.chdir(Path(__file__).parent)

    version = 2

    cwd = os.getcwd()

    if not cwd in sys.path:
        sys.path.append(cwd)
    
    downloadData = checkForUpdates()

    if downloadData == None:
        return
    
    if downloadData['version'] <= version:
        return

    print('Changelog:')
    print(downloadData['log'])
    print('\nAn update for the .exe has been found. Do you wish to update? (y/n)\nThis may be required to get everything working')
    
    if WaitForYN() == False:
        return
    
    response = fetchUrl(downloadData['url'])

    if response in [-1, 0]:
        print('Invalid download URL?\n Running existing build')
        return
    
    with open(Path(__file__), 'wb') as f:
        f.write(response.content)

main()

from LocalStreamElements import boot

try: boot()
except KeyboardInterrupt: pass