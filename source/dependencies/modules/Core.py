from dependencies.modules import Extensions, Settings, Misc, Web
from aiohttp import web
from pathlib import Path
import socketio, jinja2, aiohttp_jinja2, asyncio, json

site = None
STATIC_FOLDER = Path('dependencies/web/static').resolve()
EXTENSIONS_FOLDER = Path('extensions').resolve()

settings = Settings.Settings()
currentIP = None

PORT = Misc.portOverride(settings.port)[1]

sio = socketio.AsyncServer(async_mode='aiohttp', async_handlers=True, cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

extensions = Extensions.Extensions(sio, settings)

aiohttp_jinja2.setup(app, enable_async=True, loader=jinja2.FileSystemLoader(Path('dependencies/web/HTML')))

routes = web.RouteTableDef()

async def handleStreamElementsAPI(data : dict) -> tuple[bool, str]:
    if not isinstance(data, dict): return False, 'data have to be of type dict'
    
    args = {}
    if 'alias' in data and isinstance(data['alias'], str): args['alias'] = data['alias']
    if 'id' in data and isinstance(data['id'], str): args['id_'] = data['id']

    streamelements = extensions.findStreamElements(**args)
    if streamelements == None: streamelements = extensions.defaultStreamElements()
    if streamelements == None: return False, 'The body requires the key alias or id'
    
    return await streamelements.APIRequest(data)

async def handleTwitchMessage(data : dict) -> tuple[bool, str]:
    if not isinstance(data, dict): return False, 'data have to be of type dict'
    if not 'message' in data or not isinstance(data['message'], str): return False, 'JSON require the string key "message"'
    if not 'bot' in data or not isinstance(data['bot'], str): return False, 'JSON require the string key "bot"'

    success = False
    resp = None

    kwargs = {}
    if 'alias' in data and isinstance(data['alias'], str): kwargs['alias'] = data['alias']
    if 'id' in data and isinstance(data['id'], str): kwargs['id_'] = data['id']
    
    if data['bot'] in ['twitch', 'local']:
        twitch = extensions.findTwitch(**kwargs)
        if twitch == None: twitch = extensions.defaultTwitch()
        if twitch == None: return False, 'The body requires the key alias or id'
        success, resp = await twitch.sendMessage(data['message'], data.get('channel', None))
    elif data['bot'] == 'streamelements':
        streamelements = extensions.findStreamElements(**kwargs)
        if streamelements == None: streamelements = extensions.defaultStreamElements()
        if streamelements == None: return False, 'The body requires the key alias or id'
        success, resp = await streamelements.sendMessage(data['message'])
    return success, resp

async def handleDiscordMessage(data : dict) -> tuple[bool, str]:
    if not isinstance(data, dict): return False, 'data have to be of type dict'
    if not 'message' in data or not isinstance(data['message'], str): return False, 'JSON require the string key "message"'
    if not 'textChannel' in data: return False, 'JSON require the key "textChannel"'
    
    kwargs = {}
    if 'alias' in data and isinstance(data['alias'], str): kwargs['alias'] = data['alias']
    if 'id' in data and isinstance(data['id'], str): kwargs['id_'] = data['id']
    
    discordBot = extensions.findDiscord(**kwargs)
    if discordBot == None: extensions.defaultDiscord()
    if discordBot == None: return False, 'Unable to find dicord bot'

    channel = await discordBot.getTextChannel(data['textChannel'])
    if channel == None: return False, 'Unable to find the specified channel'
    await channel.send(data['message'])

    return True, None

async def handleCrossTalk(data : dict) -> tuple[bool, str]:
    events = []
    scripts = []

    if not isinstance(data, dict): return False, 'Data have to be of type dict'
    if not 'data' in data: return False, 'JSON require the key "data"'
    
    if 'event' in data:
        if (not isinstance(data['event'], str)) or data['event'][:2] != 'p-': return False, 'Value of the key "event" has to start with "p-", example: "p-example"'
        events.append(data['event'])
    
    if 'events' in data and isinstance(data['events'], list):
        for i in data['events']:
            if (not isinstance(i, str)) or i[:2] != 'p-': return False, 'Value of the key "events" has to be a list with strings start with "p-", example: "p-example"'
            events.append(i)
    
    if 'scripts' in data and isinstance(data['scripts'], list):
        for script in data['scripts']:
            if (not isinstance(script, str)) or len(script) == 0: return False, 'Value of key "scripts" has to be a list with strings containing at least one character (length 1+)'
            scripts.append(script)

    ct = Web.CrossTalk(data['data'])

    extensions.crossTalk(ct, scripts, events)
    return True, None

async def handleScriptTalk(data : dict) -> tuple[bool, str]:
    if not isinstance(data, dict): return False, 'Data have to be of type dict'
    if 'scripts' in data and not 'module' in data: data['module'] = data['scripts']

    if not 'module' in data: return False, 'JSON require the key "module" or "scripts"'
    if not 'data' in data: return False, 'JSON require the key "data"'

    return handleCrossTalk({
        'scripts': [data['module']],
        'data': data['data']
    })
    
@routes.get('/')
async def web_index(request : web.Request):
    context = {
        'extensions': [], 'ExtensionsSettings': [], 'events': [], 'messages': [], 'ExtensionLogs': [], 'regulars': [],
        'settings': {
            'tmi': '',
            'tmi_twitch_username': '',
            'twitch_channel': '',
            'jwt_token': '',
            'SEListener': 2
        }
    }
    return await aiohttp_jinja2.render_template_async('index.html', request, context)

@routes.get('/socket.io/socket.io.js')
async def web_socketIO_js(request : web.Request):
    socketIOJS = Path('dependencies/web/static/scripts/socket.io.js')
    if socketIOJS.is_file(): return web.FileResponse(socketIOJS)
    else: return web.Response(text='console.error("ERROR: socket.io.js not found")')

@routes.get('/static/{path:.+}')
async def web_static(request : web.Request):
    try: target : Path = (STATIC_FOLDER / request.match_info['path'])
    except Exception: return web.Response(text='invalid file path')
    
    if not Misc.isSubfolder(STATIC_FOLDER, target):
        return web.Response(text='file path outside static folder')
    
    if not target.is_file(): return web.Response(text='file does not exist')
    return web.FileResponse(target)

@routes.get('/dependencies/data/url.js')
async def web_urljs(request : web.Request):
    urljs = Path('dependencies/data/url.js')
    if urljs.is_file(): return web.FileResponse(urljs)
    else: return web.Response(text='console.error("ERROR: url.js not found");var server_url=""')

@routes.get('/extensions/{path:.+}')
async def web_extensions(request : web.Request):
    try: target : Path = (EXTENSIONS_FOLDER / request.match_info['path'])
    except Exception: return web.Response(text='invalid file path')

    if not Misc.isSubfolder(EXTENSIONS_FOLDER, target): return web.Response(text='file path not inside of extensions folder')

    if not target.is_file(): return web.Response(text='file does not exist')

    filenameLower = target.name.lower()

    if filenameLower[-5:] == '.html':
        with open(target, 'r') as f:
            content = f.read()
        templ : jinja2.Template = jinja2.Template(content)
        templ_rendered = templ.render(server_url=f'http://{Misc.getServerIP()}:{str(PORT)}')
        return web.Response(text=templ_rendered, content_type='text/html')
    
    return web.FileResponse(target)

@routes.post('/StreamElementsAPI')
async def web_SEAPI(request : web.Request):
    try:
        data : dict = await request.json()
        if not isinstance(data, dict): raise Exception()
    except Exception: return web.Response(text='{"type":"error", "message":"Please forward json... post_request(url, json=JSON_DATA)"}')
    
    success, resp = handleStreamElementsAPI(data)

    if success: return web.Response(text=json.dumps({'type':'success', 'success': True, 'response': resp}))
    else: return web.Response(text=json.dumps({'type':'error', 'success': False, 'message': resp}))

@routes.post('/TwitchMessage')
@routes.post('/SendMessage')
async def web_sendMessage(request : web.Request):
    try:
        data : dict = await request.json()
        if not isinstance(data, dict): raise Exception()
    except Exception: return web.Response(text='{"type":"error", "message":"Please forward json... post_request(url, json=JSON_DATA)"}')

    success, resp = await handleTwitchMessage(data)

    if success: return web.Response(text='{"type":"success", "success":true}')
    else: return web.Response(text=json.dumps({'type':'error', 'success': False, 'message': resp}))

@routes.post('/DiscordMessage')
async def web_discordMessage(request : web.Request):
    try:
        data : dict = await request.json()
        if not isinstance(data, dict): raise Exception()
    except Exception: return web.Response(text='{"type":"error", "message":"Please forward json... post_request(url, json=JSON_DATA)"}')

    success, resp = await handleDiscordMessage(data)

    if success: return web.Response(text='{"type":"success", "success":true}')
    else: return web.Response(text=json.dumps({'type':'error', 'success': False, 'message': resp}))

@routes.post('/ScriptTalk')
async def web_scriptTalk(request : web.Request):
    try:
        data : dict = await request.json()
        if not isinstance(data, dict): raise Exception()
    except Exception: return web.Response(text='{"type":"error", "message":"Please forward json... post_request(url, json=JSON_DATA)"}')

    success, resp = await handleScriptTalk(data)

    if success: return web.Response(text='{"type":"success", "success":true}')
    else: return web.Response(text=json.dumps({'type':'error', 'success': False, 'message': resp}))

@routes.post('/CrossTalk')
async def web_crossTalk(request : web.Request):
    try:
        data : dict = await request.json()
        if not isinstance(data, dict): raise Exception()
    except Exception: return web.Response(text='{"type":"error", "message":"Please forward json... post_request(url, json=JSON_DATA)"}')

    success, resp = await handleCrossTalk(data)

    if success: return web.Response(text='{"type":"success", "success":true}')
    else: return web.Response(text=json.dumps({'type':'error', 'success': False, 'message': resp}))

@routes.post('/DeleteRegular')
async def web_deleteRegular(request : web.Request):
    try:
        data : dict = await request.json()
        if not isinstance(data, dict): raise Exception()
    except Exception: return web.Response(text='{"type":"error", "message":"Please forward json... post_request(url, json=JSON_DATA)"}')

    return web.Response(text='hi')

@routes.post('/AddRegular')
async def web_addRegular(request : web.Request):
    try:
        data : dict = await request.json()
        if not isinstance(data, dict): raise Exception()
    except Exception: return web.Response(text='{"type":"error", "message":"Please forward json... post_request(url, json=JSON_DATA)"}')

    return web.Response(text='hi')

@routes.route('*', '/webhook/{moduleName:[^/]+}/{secret:.*}')
async def web_webhook(request : web.Request):
    try:
        data = await request.text()
        if len(data) == 0 and not request.body_exists(): raise Exception()
    except Exception: data = None
    method = request.method
    secret = request.match_info['secret']
    moduleName = request.match_info['moduleName']

    wh = Web.Webhook(method, data, secret)

    extensions.webhook(moduleName, wh)

    return web.Response()

#@sio.on('connect')
#def sio_connect(sid, *args): pass

#@sio.on('disconnect')
#def sio_disconnect(sid, *args): pass

@sio.on('message')
async def sio_message(sid, data=''):
    return

@sio.on('ToggleExtension')
async def sio_toggleExtension(sid, data=''):
    return

@sio.on('SaveSettings')
async def sio_saveSettings(sid, data=''):
    return

@sio.on('ClearEvents')
async def sio_clearEvents(sid, data=''):
    return

@sio.on('ClearMessages')
async def sio_clearMessages(sid, data=''):
    return

@sio.on('ClearLogs')
async def sio_clearLogs(sid, data=''):
    return

@sio.on('AddRegular')
async def sio_addRegular(sid, data=''):
    return

@sio.on('DeleteRegular')
async def sio_deleteRegular(sid, data=''):
    return

@sio.on('UpdateSettings')
async def sio_updateSettings(sid, data=''):
    return

#@sio.on('RestartTwitch')
#async def sio_restartTwitch(sid, data=''):
#    return

#@sio.on('RestartSE')
#async def sio_restartSE(sid, data=''):
#    return

@sio.on('ResetExtensions')
async def sio_restartExtensions(sid, data=''):
    extensions.reloadExtensions()
    await sio.emit('ResetExtensions', room=sid)

@sio.on('StreamElementsAPI')
async def sio_SEAPI(sid, data):
    try:
        data : dict = json.loads(data='')
        if not isinstance(data, dict): raise Exception()
    except Exception:
        await sio.emit('StreamElementsAPI', {'type': 'error', 'message': 'Please forward json... sio.emit("StreamElementsAPI", JSON_DATA)'}, room=sid)
        return

    success, resp = handleStreamElementsAPI(data)

    if success: await sio.emit('StreamElementsAPI', {'type':'success', 'success': True, 'response': resp})
    else: await sio.emit('StreamElementsAPI', {'type':'error', 'success': False, 'message': resp})

@sio.on('ScriptTalk')
async def sio_scriptTalk(sid, data=''):
    return

@sio.on('CrossTalk')
async def sio_crossTalk(sid, data=''):
    return

@sio.on('SendMessage')
async def sio_sendMessage(sid, data=''):
    if not isinstance(data, dict):
        try:
            data : dict = json.loads(data)
            if not isinstance(data, dict): raise Exception()
        except Exception:
            await sio.emit('SendMessage', {'type': 'error', 'message': 'Please forward json... sio.emit("SendMessage", JSON_DATA)'}, room=sid)
            return
    
    return
    success, resp = await handleSendMessage(data)

    if success: await sio.emit('SendMessage', {'type': 'success', 'success': True}, room=sid)
    else: await sio.emit('SendMessage', {'type': 'error', 'message': resp}, room=sid)

app.add_routes(routes=routes)

runner = web.AppRunner(app)

async def run():
    global site, currentIP
    if site != None: return

    currentIP, errorCode = await Misc.fetchUrl('https://ident.me')
    if errorCode < 0: currentIP, errorCode = await Misc.fetchUrl('https://api.ipify.org')
    if errorCode < 0: print('[ERROR]: Unable to check for your public IP, no network connection? (trying to run anyway)')

    extensions.loadServices()

    with open('website.html', 'w') as f: f.write('<script>window.location = "http://localhost:' + str(PORT) + '"</script>')
    urlJsPath = Path('dependencies/data/url.js')
    urlJsPath.parent.mkdir(parents=True, exist_ok=True)
    with open(urlJsPath, 'w') as f: f.write('var server_url = \"http://' + Misc.getServerIP() + ':' + str(PORT) + '\";')

    print('starting website: http://localhost:' + str(PORT) + ' (Saving website shortcut to website.html)')

    await runner.setup()
    site = web.TCPSite(runner=runner, host='0.0.0.0', port=PORT)
    await site.start()

    while True:
        # run loop
        await asyncio.sleep(10)
