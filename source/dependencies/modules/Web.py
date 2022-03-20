from aiohttp import web
from pathlib import Path
import socketio, jinja2, aiohttp_jinja2

sio = socketio.AsyncServer(async_mode='aiohttp', async_handlers=True)
app = web.Application()
sio.attach(app)

aiohttp_jinja2.setup(app, enable_async=True, loader=jinja2.FileSystemLoader(Path('dependencies/web/HTML')))

routes = web.RouteTableDef()

STATIC_PATH = Path('/static')
STATIC_FOLDER = Path('dependencies/web/static')

@routes.get('/')
async def web_index(request):
    # extensions=extensions.dump(), ExtensionsSettings=extensions.settings, events=SE.eventHistory, messages=chat.twitchMessagesHistory, ExtensionLogs=extensions.log, regulars=users.regulars, settings=settings
    return web.Response(text='hi')
    #return await aiohttp_jinja2.render_template_async('index.html', request, {'extensions': extensions.dump(), 'ExtensionsSettings': extensions.settings, 'events': SE.eventHistory, 'messages': chat.twitchMessagesHistory, 'ExtensionLogs': extensions.log, 'regulars': users.regulars, 'settings': settings})

@routes.get('/static/{path:.*}')
async def web_static(request):
    try: path = Path(request.path)
    except TypeError: return web.Response(text='invalid file path') 

    try: relative = path.relative_to(STATIC_PATH)
    except ValueError: return web.Response(text='invalid file path')

    file = STATIC_FOLDER / relative

    if not file.is_file(): return web.Response(text='file does not exist')

    return web.FileResponse(file)

@routes.get('/dependencies/data/url.js')
async def web_urljs(request):
    return web.Response(text='hi')

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
site = None

async def run():
    global site
    if site != None: return
    
    await runner.setup()
    site = web.TCPSite(runner=runner, host='0.0.0.0', port=8080)
    await site.start()
