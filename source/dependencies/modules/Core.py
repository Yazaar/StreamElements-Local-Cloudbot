from dependencies.modules import Extensions, Settings, Misc

from aiohttp import web
from pathlib import Path
import socketio, jinja2, aiohttp_jinja2, asyncio

site = None
STATIC_FOLDER = Path('dependencies/web/static').resolve()

settings = Settings.Settings()
currentIP = None

PORT = Misc.portOverride(settings.port)[1]

sio = socketio.AsyncServer(async_mode='aiohttp', async_handlers=True)
app = web.Application()
sio.attach(app)

extensions = Extensions.Extensions(sio, settings)

aiohttp_jinja2.setup(app, enable_async=True, loader=jinja2.FileSystemLoader(Path('dependencies/web/HTML')))

routes = web.RouteTableDef()

@routes.get('/')
async def web_index(request):
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
async def web_static(request):
    try: target : Path = (STATIC_FOLDER / request.path[8:])
    except TypeError: return web.Response(text='invalid file path')
    
    target = target.resolve()
    
    try: target.relative_to(STATIC_FOLDER) # throws exception if it is outside of the static folder
    except ValueError: return web.Response(text='file path outside static folder')
    
    if not target.is_file(): return web.Response(text='file does not exist')
    return web.FileResponse(target)

@routes.get('/dependencies/data/url.js')
async def web_urljs(request):
    urljs = Path('dependencies/data/url.js')
    if urljs.is_file(): return web.FileResponse(urljs)
    else: return web.Response(text="console.error(\"ERROR: url.js not found\");var server_url=\"\"")

@routes.get('/extensions/<path:raw_path>')
async def web_extensions(request):
    return web.Response(text='hi')

@routes.post('/StreamElementsAPI')
async def web_SEAPI(request):
    return web.Response(text='hi')

@routes.post('/SendMessage')
async def web_sendMessage(request):
    return web.Response(text='hi')

@routes.post('/ScriptTalk')
async def web_scriptTalk(request):
    return web.Response(text='hi')

@routes.post('/CrossTalk')
async def web_crossTalk(request):
    return web.Response(text='hi')

@routes.post('/DeleteRegular')
async def web_deleteRegular(request):
    return web.Response(text='hi')

@routes.post('/AddRegular')
async def web_addRegular(request):
    return web.Response(text='hi')

@routes.route('*', '/webhook/<destination>/<secret>')
async def web_webhook(request):
    return web.Response(text='hi')

@sio.on('connect')
def sio_connect(sid, data):
    print(sid, 'connected')

@sio.on('message')
def sio_message(sid, data):
    return

@sio.on('ToggleExtension')
def sio_toggleExtension(sid, data):
    return

@sio.on('SaveSettings')
def sio_saveSettings(sid, data):
    return

@sio.on('ClearEvents')
def sio_clearEvents(sid, data):
    return

@sio.on('ClearMessages')
def sio_clearMessages(sid, data):
    return

@sio.on('ClearLogs')
def sio_clearLogs(sid, data):
    return

@sio.on('AddRegular')
def sio_addRegular(sid, data):
    return

@sio.on('DeleteRegular')
def sio_deleteRegular(sid, data):
    return

@sio.on('UpdateSettings')
def sio_updateSettings(sid, data):
    return

@sio.on('RestartTwitch')
def sio_restartTwitch(sid, data):
    return

@sio.on('RestartSE')
def sio_restartSE(sid, data):
    return

@sio.on('ResetExtensions')
def sio_restartExtensions(sid, data):
    return

@sio.on('StreamElementsAPI')
def sio_SEAPI(sid, data):
    return

@sio.on('ScriptTalk')
def sio_scriptTalk(sid, data):
    return

@sio.on('CrossTalk')
def sio_crossTalk(sid, data):
    return

@sio.on('SendMessage')
def sio_sendMessage(sid, data):
    return

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
