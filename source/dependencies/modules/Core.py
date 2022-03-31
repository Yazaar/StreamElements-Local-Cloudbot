from dependencies.modules import Extensions, Settings, Misc, StreamElements, Twitch, Discord

from aiohttp import web
from pathlib import Path
import socketio, jinja2, aiohttp_jinja2, asyncio, json

site = None
STATIC_FOLDER = Path('dependencies/web/static').resolve()
EXTENSIONS_FOLDER = Path('extensions').resolve()

settings = Settings.Settings()
currentIP = None

PORT = Misc.portOverride(settings.port)[1]

sio = socketio.AsyncServer(async_mode='aiohttp', async_handlers=True)
app = web.Application()
sio.attach(app)

extensions = Extensions.Extensions(sio, settings)

aiohttp_jinja2.setup(app, enable_async=True, loader=jinja2.FileSystemLoader(Path('dependencies/web/HTML')))

routes = web.RouteTableDef()

async def handleStreamElementsAPI(data : dict):
    if not isinstance(data, dict): return False, 'data have to be of type dict'
    streamelements : StreamElements.StreamElements = None

    if 'alias' in data:
        streamelements = extensions.streamElementsByAlias(data['alias'])
    if streamelements == None and 'id' in data:
        streamelements = extensions.streamElementsById(data['id'])
    if streamelements == None:
        streamelements = extensions.defaultStreamElements()
    if streamelements == None:
        return False, 'The body requires the key alias or id'
    
    return await streamelements.APIRequest(data)

async def handleSendMessage(data : dict) -> tuple[bool, str]:
    if not isinstance(data, dict): return False, 'data have to be of type dict'
    if not 'message' in data or not isinstance(data['message'], str): return False, 'JSON require the string key \"message\"'
    if not 'bot' in data or not isinstance(data['bot'], str): return False, 'JSON require the string key \"bot\"'

    success = False
    resp = None

    if data['bot'] in ['twitch', 'local']:
        twitch : Twitch.Twitch = None
        if 'alias' in data:
            twitch = extensions.twitchByAlias(data['alias'])
        if twitch == None and 'id' in data:
            twitch = extensions.twitchById(data['id'])
        if twitch == None:
            twitch = extensions.defaultTwitch()
        if twitch == None:
            return False, 'The body requires the key alias or id'
        
        success, resp = await twitch.sendMessage(data['message'], data.get('channel', None))

    elif data['bot'] == 'streamelements':
        streamelements : StreamElements.StreamElements = None
        if 'alias' in data:
            streamelements = extensions.streamElementsByAlias(data['alias'])
        if streamelements == None and 'id' in data:
            streamelements = extensions.streamElementsById(data['id'])
        if streamelements == None:
            streamelements = extensions.defaultStreamElements()
        if streamelements == None:
            return False, 'The body requires the key alias or id'
        
        success, resp = await streamelements.sendMessage(data['message'])

    return success, resp

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

@routes.get('/static/{path:.*}')
async def web_static(request : web.Request):
    try: target : Path = (STATIC_FOLDER / request.path[8:])
    except Exception: return web.Response(text='invalid file path')
    
    if not Misc.isSubfolder(STATIC_FOLDER, target):
        return web.Response(text='file path outside static folder')
    
    if not target.is_file(): return web.Response(text='file does not exist')
    return web.FileResponse(target)

@routes.get('/dependencies/data/url.js')
async def web_urljs(request : web.Request):
    urljs = Path('dependencies/data/url.js')
    if urljs.is_file(): return web.FileResponse(urljs)
    else: return web.Response(text="console.error(\"ERROR: url.js not found\");var server_url=\"\"")

@routes.get('/extensions/{path:.*}')
async def web_extensions(request : web.Request):
    try: target : Path = (EXTENSIONS_FOLDER / request.path[12:])
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

@routes.post('/SendMessage')
async def web_sendMessage(request : web.Request):
    try:
        data : dict = await request.json()
        if not isinstance(data, dict): raise Exception()
    except Exception: return web.Response(text='{"type":"error", "message":"Please forward json... post_request(url, json=JSON_DATA)"}')

    success, resp = await handleSendMessage(data)

    if success: return web.Response(text='{"type":"success", "success":true}')
    else: return web.Response(text=json.dumps({'type':'error', 'success': False, 'message': resp}))

@routes.post('/ScriptTalk')
async def web_scriptTalk(request : web.Request):
    return web.Response(text='hi')

@routes.post('/CrossTalk')
async def web_crossTalk(request : web.Request):
    return web.Response(text='hi')

@routes.post('/DeleteRegular')
async def web_deleteRegular(request : web.Request):
    return web.Response(text='hi')

@routes.post('/AddRegular')
async def web_addRegular(request : web.Request):
    return web.Response(text='hi')

@routes.route('*', '/webhook/<destination>/<secret>')
async def web_webhook(request : web.Request):
    return web.Response(text='hi')

@sio.on('connect')
async def sio_connect(sid, data=''):
    print(sid, 'connected')

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
