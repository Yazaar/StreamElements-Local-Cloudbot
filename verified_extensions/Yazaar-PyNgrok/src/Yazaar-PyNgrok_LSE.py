import subprocess, os, signal, threading, re, ctypes, json, psutil

status = 'offline'

root = os.path.dirname(__file__)

if os.path.isfile(os.path.join(root, 'settings.json')):
    try:
        with open(os.path.join(root, 'settings.json'), 'r') as f:
            settings = json.load(f)
        if not settings['Region'] in ['us', 'eu', 'ap', 'au', 'sa', 'jp', 'in'] or not settings['Autorun'] in [True, False]:
            raise Exception
    except Exception:
        settings = {'Region':'eu', 'Autorun':False}
else:
    settings = {'Region':'eu', 'Autorun':False}

if os.path.isfile(os.path.join(root, 'status.json')):
    try:
        with open(os.path.join(root, 'status.json'), 'r') as f:
            historicalData = json.load(f)
        if historicalData['running'] == True and psutil.pid_exists(historicalData['pid']):
            print(historicalData)
            os.kill(historicalData['pid'], signal.SIGTERM)
    except Exception:
        pass



def createProcess():
    global ngrokProcess, status, host
    try:
        port
    except Exception:
       return
    ngrokProcess = subprocess.Popen(os.path.join(root, 'ngrok.exe') + ' http ' + str(port) + ' -region ' + settings['Region'] + ' -log stdout', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        line = ngrokProcess.stdout.readline().decode()
        errorRes = re.search(r'err="([^"]+)"', line)
        if errorRes != None:
            with open(os.path.join(root, 'error.txt'), 'a') as f:
                f.write('\n' + errorRes.group(1))
            EHandler.SendMessage({'bot':'local', 'message':'[PyNgrok] Error! Please check error.txt which can be found inside of this project folder (extensions/Yazaar-PyNgrok/error.txt)'})
            break
        res = re.search(r'msg="([^"]+)', line)
        if res != None:
            if res.group(1) == 'started tunnel':
                res2 = re.search(r'url=([^\s]+)', line)
                if res2 != None:
                    host = res2.group(1)
                    with open(os.path.join(root, 'status.json'), 'w') as f:
                        json.dump({'running':True, 'pid':ngrokProcess.pid}, f)
                    status = 'online'
                    EHandler.SendMessage({'bot':'local', 'message':'[PyNgrok] WebServer is now online!'})
                    break

def Initialize(data, EventHandler):
    global port, EHandler
    port = data['port']
    EHandler = EventHandler
    if settings['Autorun']:
        createProcess()

def Execute(data):
    global status
    words = data['message'].split(' ')
    if len(words) < 2:
        return
    if words[0].lower() != '!pyngrok':
        return

    if words[1].lower() == 'running':
        try:
            state = ngrokProcess.poll()
        except Exception:
            state = 'offline'
        if state == None:
            state = 'online'
        else:
            state = 'offline'

        EHandler.SendMessage({'bot':'local', 'message':f'[PyNgrok] Status: {state}'})

    if words[1].lower() == 'status':
        EHandler.SendMessage({'bot':'local', 'message':f'[PyNgrok] Status: {status}'})
    
    if not 'broadcaster' in data['badges']:
        return
    
    if words[1].lower() == 'run':
        if status == 'online' or status == 'loading':
            EHandler.SendMessage({'bot':'local', 'message':'[PyNgrok] Ngrok is already running...'})
            return
        EHandler.SendMessage({'bot':'local', 'message':'[PyNgrok] Starting ngrok...'})
        status = 'loading'
        createProcess()

    
    if words[1].lower() == 'stop' and status != 'offline':
        
        status = 'loading'

        try:
            if ngrokProcess.poll() == None:
                ngrokProcess.terminate()
                status = 'offline'
                EHandler.SendMessage({'bot':'local', 'message':'[PyNgrok] Stopped ngrok...'})
                with open(os.path.join(root, 'status.json'), 'w') as f:
                    json.dump({'running':False, 'pid':0}, f)

        except Exception:
            try:
                ngrokProcess
                EHandler.SendMessage({'bot':'local', 'message':'[PyNgrok] Failed to disable ngrok...'})
            except Exception:
                EHandler.SendMessage({'bot':'local', 'message':'[PyNgrok] Ngrok is not running...'})