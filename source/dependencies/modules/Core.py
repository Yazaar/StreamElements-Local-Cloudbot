from dependencies.modules import Extensions, Misc, Web
from aiohttp import web
from pathlib import Path
import socketio, jinja2, aiohttp_jinja2, asyncio, json

site = None
STATIC_FOLDER = Path('dependencies/web/static').resolve()
EXTENSIONS_FOLDER = Path('extensions').resolve()

sio = socketio.AsyncServer(async_mode='aiohttp', async_handlers=True, cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

extensions = Extensions.Extensions(sio)

aiohttp_jinja2.setup(app, enable_async=True, loader=jinja2.FileSystemLoader(Path('dependencies/web/HTML')))

routes = web.RouteTableDef()

async def handleStreamElementsAPI(data : dict) -> tuple[bool, str | None]:
    if not isinstance(data, dict): return False, 'The data has to be of type dict'

    streamelements = extensions.findStreamElements(alias=data.get('alias', None), id_=data.get('id', None))
    if streamelements == None: streamelements = extensions.defaultStreamElements()
    if streamelements == None: return False, 'The dict requires the key alias or id'

    if 'options' in data and isinstance(data['options'], dict):
        options = data['options']
        if 'type' in options: data['method'] = options['type']
        if 'include_jwt' in options: data['includeJWT'] = options['include_jwt']
        if 'headers' in options: data['headers'] = options['headers']

    return await streamelements.APIRequest(
        method=data.get('method', None),
        endpoint=data.get('endpoint', None),
        headers=data.get('headers', None),
        body=data.get('body', None),
        includeJWT=data.get('includeJWT', False)
    )

async def handleTwitchMessage(data : dict) -> tuple[bool, str | None]:
    if not isinstance(data, dict): return False, 'data have to be of type dict'
    if not 'message' in data or not isinstance(data['message'], str): return False, 'The dict require the string key "message"'
    if not 'bot' in data or not isinstance(data['bot'], str): return False, 'The dict require the string key "bot"'

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

async def handleDiscordMessage(data : dict) -> tuple[bool, str | None]:
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

async def handleCrossTalk(data : dict) -> tuple[bool, str | None]:
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

async def handleScriptTalk(data : dict) -> tuple[bool, str | None]:
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
        'extensions': extensions.extensions, 'ExtensionsSettings': extensions.settingsUI, 'events': [],
        'messages': [], 'ExtensionLogs': extensions.logs, 'regularPlatforms': ['Discord', 'Twitch'],
        'serverPort': extensions.settings.port,
        'tickrate': extensions.settings.tickrate,
        'discords': extensions.discordInstances,
        'twitch': extensions.twitchInstances,
        'twitchRegularGroups': extensions.regulars.getGroups('twitch'),
        'discordRegularGroups': extensions.regulars.getGroups('discord'),
        'streamelements': extensions.streamElementsInstances,
    }
    return await aiohttp_jinja2.render_template_async('index.html', request, context)

@routes.get('/socket.io/socket.io.js')
async def web_socketIO_js(request : web.Request):
    socketIOJS = Path('dependencies/web/static/scripts/SocketIO/socket.io.js')
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
        templ_rendered = templ.render(server_url=f'http://{Misc.getServerIP()}:{str(extensions.settings.currentPort)}')
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
    print(data)

@sio.on('ToggleExtension')
async def sio_toggleExtension(sid, data=''):
    if not isinstance(data, dict):
        await sio.emit('ToggleExtension', {'success': False}, room=sid)
        return
    if not 'module' in data or not isinstance(data['module'], str) or not 'active' in data or not isinstance(data['active'], bool):
        data['success'] = False
        await sio.emit('ToggleExtension', data, room=sid)
        return
    extensions.toggleExtension(data['module'], data['active'])
    data['success'] = True
    await sio.emit('ToggleExtension', data, room=sid)

@sio.on('SetExtensionConnectionTwitch')
async def sio_setExtensionConnectionTwitch(sid, data=''):
    if not isinstance(data, dict):
        await sio.emit('SetExtensionConnectionTwitch', {'success': False, 'message': 'Please pass a dictionary'}, room=sid)
        return

    success, errorMsg = extensions.setExtensionConnectionTwitch(data.get('extension'), data.get('twitchId'))

    resp = {'success': success, 'data': data}
    if not success: resp['message'] = errorMsg
    await sio.emit('SetExtensionConnectionTwitch', resp)

@sio.on('SetExtensionConnectionDiscord')
async def sio_setExtensionConnectionDiscord(sid, data=''):
    if not isinstance(data, dict):
        await sio.emit('SetExtensionConnectionDiscord', {'success': False, 'message': 'Please pass a dictionary'}, room=sid)
        return

    success, errorMsg = extensions.setExtensionConnectionDiscord(data.get('extension'), data.get('discordId'))

    resp = {'success': success, 'data': data}
    if not success: resp['message'] = errorMsg
    await sio.emit('SetExtensionConnectionDiscord', resp) 

@sio.on('SetExtensionConnectionStreamElements')
async def sio_setExtensionConnectionStreamElements(sid, data=''):
    if not isinstance(data, dict):
        await sio.emit('SetExtensionConnectionStreamElements', {'success': False, 'message': 'Please pass a dictionary'}, room=sid)
        return

    success, errorMsg = extensions.setExtensionConnectionStreamElements(data.get('extension'), data.get('streamelementsId'))

    resp = {'success': success, 'data': data}
    if not success: resp['message'] = errorMsg
    await sio.emit('SetExtensionConnectionStreamElements', resp) 

@sio.on('SaveTwitchInstance')
async def sio_saveTwitchInstance(sid, data=''):
    if not isinstance(data, dict):
        await sio.emit('SaveTwitchInstance', {'success': False, 'message': 'data have to be a dictionary'}, room=sid)
        return

    success, errorMsgOrDiscord = await extensions.updateTwitch(data.get('id'), data.get('alias'), data.get('tmi'), data.get('channels'), data.get('regularGroups'))

    if success:
        data['id'] = errorMsgOrDiscord.id
        await sio.emit('SaveTwitchInstance', {'success': success, 'data': data}, room=sid)
    else: await sio.emit('SaveTwitchInstance', {'success': success, 'message': errorMsgOrDiscord, 'data': data}, room=sid) 

@sio.on('DeleteTwitchInstance')
async def sio_deleteTwitchInstance(sid, data=''):
    if not isinstance(data, str) or len(data) == 0:
        await sio.emit('DeleteTwitchInstance', {'success': False, 'message': 'Have to pass the Discord instance ID as a string'}, room=sid)
        return
    
    success = extensions.removeTwitchInstance(data)
    if success: await sio.emit('DeleteTwitchInstance', {'success': success, 'id': data}, room=sid)
    else: await sio.emit('DeleteTwitchInstance', {'success': success, 'message': 'The Twitch instance ID does not exist', 'id': data}, room=sid) 

@sio.on('SaveStreamElementsInstance')
async def sio_saveTwitchInstance(sid, data=''):
    if not isinstance(data, dict):
        await sio.emit('SaveStreamElementsInstance', {'success': False}, room=sid)
        return
    
    success, errorMsgOrSE = await extensions.updateStreamElements(data.get('id'), data.get('alias'), data.get('jwt'))

    if success:
        data['id'] = errorMsgOrSE.id
        await sio.emit('SaveStreamElementsInstance', {'success': success, 'data': data}, room=sid)
    else: await sio.emit('SaveStreamElementsInstance', {'success': success, 'message': errorMsgOrSE, 'data': data}, room=sid) 

@sio.on('DeleteStreamElementsInstance')
async def sio_deleteDiscordInstance(sid, data=''):
    if not isinstance(data, str) or len(data) == 0:
        await sio.emit('DeleteStreamElementsInstance', {'success': False, 'message': 'Have to pass the Discord instance ID as a string'}, room=sid)
        return
    
    success = extensions.removeStreamElementsInstance(data)
    if success: await sio.emit('DeleteStreamElementsInstance', {'success': success, 'id': data}, room=sid)
    else: await sio.emit('DeleteStreamElementsInstance', {'success': success, 'message': 'The StreamElements instance ID does not exist', 'id': data}, room=sid) 

@sio.on('SaveDiscordInstance')
async def sio_saveDiscordInstance(sid, data=''):
    if not isinstance(data, dict):
        await sio.emit('SaveDiscordInstance', {'success': False}, room=sid)
        return
    
    success, errorMsgOrDiscord = await extensions.updateDiscord(data.get('id'), data.get('alias'), data.get('token'), data.get('regularGroups'), membersIntent=data.get('membersIntent'), presencesIntent=data.get('presencesIntent'), messageContentIntent=data.get('messageContentIntent'))

    if success:
        data['id'] = errorMsgOrDiscord.id
        await sio.emit('SaveDiscordInstance', {'success': success, 'data': data}, room=sid)
    else: await sio.emit('SaveDiscordInstance', {'success': success, 'message': errorMsgOrDiscord, 'data': data}, room=sid) 

@sio.on('DeleteDiscordInstance')
async def sio_deleteDiscordInstance(sid, data=''):
    if not isinstance(data, str) or len(data) == 0:
        await sio.emit('DeleteDiscordInstance', {'success': False, 'message': 'Have to pass the Discord instance ID as a string'}, room=sid)
        return
    
    success = extensions.removeDiscordInstance(data)
    if success: await sio.emit('DeleteDiscordInstance', {'success': success, 'id': data}, room=sid)
    else: await sio.emit('DeleteDiscordInstance', {'success': success, 'message': 'The Discord instance ID does not exist', 'id': data}, room=sid) 

@sio.on('SaveSettings')
async def sio_saveSettings(sid, data=''):
    if not isinstance(data, dict):
        await sio.emit('ToggleExtension', {'success': False}, room=sid)
        return
    extensions.updateSettings(data)
    data['success'] = True
    await sio.emit('SaveSettings', data, room=sid)

@sio.on('ClearEvents')
async def sio_clearEvents(sid, data=''):
    if not isinstance(data, dict):
        await sio.emit('ClearEvents', {'success': False, 'message': 'data has to be a dict'})
        return
    alias = data.get('alias', None)
    id_ = data.get('id', None)
    se = extensions.findStreamElements(alias=alias, id_=id_)
    if se == None:
        await sio.emit('ClearEvents', {'success': False, 'message': f'Unable to find StreamElements with the specified id ({alias}) or alias ({id_})'})
        return
    
    se.eventHistory.clear()
    await sio.emit('ClearEvents', {'success': True, 'data': {'alias': alias, 'id': id_}}, room=sid)

@sio.on('ClearMessages')
async def sio_clearMessages(sid, data=''):
    # clear messages (not implemented)
    pass

@sio.on('ClearLogs')
async def sio_clearLogs(sid, data=''):
    extensions.logs.clear()
    await sio.emit('ClearLogs', room=sid)

@sio.on('AddRegular')
async def sio_addRegular(sid, data=''):
    if isinstance(data, str):
        parsedData = {
            'alias': data,
            'userId': data,
            'groupName': 'default',
            'platform': 'twitch'
        }
    elif isinstance(data, dict):
        parsedData = {
            'alias': data.get('alias', None),
            'userId': data.get('userId', None),
            'groupName': data.get('groupName', None),
            'platform': data.get('platform', None)
        }
    else:
        await sio.emit('AddRegular', {'success': False, 'message': 'invalid data format (use a dict)'}, room=sid)
        return
    
    success, resp, createdGroup = extensions.regulars.addRegular(**parsedData)

    if success: await sio.emit('AddRegular', {'success': True, 'data': parsedData, 'createdGroup': createdGroup}, room=sid)
    else: await sio.emit('AddRegular', {'success': False, 'message': resp, 'data': parsedData}, room=sid)

@sio.on('DeleteRegular')
async def sio_deleteRegular(sid, data=''):
    if isinstance(data, str):
        parsedData = {
            'userId': data,
            'groupName': 'default',
            'platform': 'twitch'
        }
    if isinstance(data, dict):
        parsedData = {
            'userId': data.get('userId', None),
            'groupName': data.get('groupName', None),
            'platform': data.get('platform', None)
        }
    else:
        await sio.emit('DeleteRegular', {'success': False, 'message': 'invalid data format (use a dict)'}, room=sid)
        return
    
    success, resp, deletedGroup = extensions.regulars.removeRegular(**parsedData)

    if success: await sio.emit('DeleteRegular', {'success': True, 'data': parsedData, 'deletedGroup': deletedGroup}, room=sid)
    else: await sio.emit('DeleteRegular', {'success': False, 'message': resp, 'data': parsedData}, room=sid)

@sio.on('GetTwitchInstanceConfigs')
async def sio_GetTwitchInstanceChannels(sid, data=''):
    if not isinstance(data, str):
        await sio.emit('GetTwitchInstanceConfigs', {'success': False, 'message': 'Passed data have to be a string (of an existing Twitch instance ID)'}, room=sid)
        return
    
    foundTwitch = extensions.findTwitch(id_=data)
    if foundTwitch is None:
        await sio.emit('GetTwitchInstanceConfigs', {'success': False, 'message': 'Passed Twitch instance ID does not exist'}, room=sid)
        return
    
    await sio.emit('GetTwitchInstanceConfigs', {'success': True, 'channels': foundTwitch.allChannels, 'regularGroups': foundTwitch.regularGroups, 'alias': foundTwitch.alias, 'tmi': foundTwitch.tmi, 'id': foundTwitch.id}, room=sid)

@sio.on('GetStreamElementsInstanceConfigs')
async def sio_GetTwitchInstanceChannels(sid, data=''):
    if not isinstance(data, str):
        await sio.emit('GetStreamElementsInstanceConfigs', {'success': False, 'message': 'Passed data have to be a string (of an existing StreamElements instance ID)'}, room=sid)
        return
    
    foundStreamElements = extensions.findStreamElements(id_=data)
    if foundStreamElements is None:
        await sio.emit('GetStreamElementsInstanceConfigs', {'success': False, 'message': 'Passed StreamElements instance ID does not exist'}, room=sid)
        return
    
    await sio.emit('GetStreamElementsInstanceConfigs', {'success': True, 'alias': foundStreamElements.alias, 'jwt': foundStreamElements.jwt, 'id': foundStreamElements.id}, room=sid)

@sio.on('GetDiscordInstanceConfigs')
async def sio_GetTwitchInstanceChannels(sid, data=''):
    if not isinstance(data, str):
        await sio.emit('GetDiscordInstanceConfigs', {'success': False, 'message': 'Passed data have to be a string (of an existing Discord instance ID)'}, room=sid)
        return
    
    foundDiscord = extensions.findDiscord(id_=data)
    if foundDiscord is None:
        await sio.emit('GetDiscordInstanceConfigs', {'success': False, 'message': 'Passed Discord instance ID does not exist'}, room=sid)
        return
    
    await sio.emit('GetDiscordInstanceConfigs', {'success': True, 'alias': foundDiscord.alias, 'token': foundDiscord.token, 'id': foundDiscord.id, 'regularGrouns': foundDiscord.regularGroups, 'membersIntent': foundDiscord.intents.members, 'presencesIntent': foundDiscord.intents.presences, 'messagesContentIntent': foundDiscord.intents.message_content}, room=sid)

@sio.on('UpdateSettings')
async def sio_updateSettings(sid, data=''):
    if 'server_port' in data:
        extensions.settings.setPort(data['server_port'])
    if 'executions_per_second' in data:
        if extensions.settings.setTickrate(data['executions_per_second']):
            extensions.calculateTickrate()
    await sio.emit('UpdateSettings', room=sid)

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
    if not isinstance(data, dict):
        try:
            data : dict = json.loads(data)
            if not isinstance(data, dict): raise Exception()
        except Exception:
            await sio.emit('ScriptTalk', {'type': 'error', 'message': 'Please forward json... sio.emit("SendMessage", JSON_DATA)'}, room=sid)
            return
    
    success, resp = await handleScriptTalk(data)

    if success: await sio.emit('ScriptTalk', {'type': 'success', 'success': True}, room=sid)
    else: await sio.emit('ScriptTalk', {'type': 'error', 'message': resp}, room=sid)

@sio.on('CrossTalk')
async def sio_crossTalk(sid, data=''):
    if not isinstance(data, dict):
        try:
            data : dict = json.loads(data)
            if not isinstance(data, dict): raise Exception()
        except Exception:
            await sio.emit('CrossTalk', {'type': 'error', 'message': 'Please forward json... sio.emit("SendMessage", JSON_DATA)'}, room=sid)
            return
    
    success, resp = await handleCrossTalk(data)

    if success: await sio.emit('CrossTalk', {'type': 'success', 'success': True}, room=sid)
    else: await sio.emit('CrossTalk', {'type': 'error', 'message': resp}, room=sid)

@sio.on('TwitchMessage')
@sio.on('SendMessage')
async def sio_sendMessage(sid, data=''):
    if not isinstance(data, dict):
        try:
            data : dict = json.loads(data)
            if not isinstance(data, dict): raise Exception()
        except Exception:
            await sio.emit('SendMessage', {'type': 'error', 'message': 'Please forward json... sio.emit("SendMessage", JSON_DATA)'}, room=sid)
            return
    
    success, resp = await handleTwitchMessage(data)

    if success: await sio.emit('SendMessage', {'type': 'success', 'success': True}, room=sid)
    else: await sio.emit('SendMessage', {'type': 'error', 'message': resp}, room=sid)

@sio.on('GetRegularGroups')
async def sio_getRegularGroups(sid, data=''):
    if not isinstance(data, str):
        await sio.emit('GetRegularGroups', {'type': 'error', 'success': False, 'message': 'Please forward string... sio.emit("GetRegularGroups", "platform")'}, room=sid)
        return
    
    rgs = extensions.regulars.getGroups(data)
    if rgs is None:
        await sio.emit('GetRegularGroups', {'type': 'error', 'success': False, 'message': 'Platform does not exist'}, room=sid)
        return
    
    await sio.emit('GetRegularGroups', {'type': 'success', 'success': True, 'groups': rgs}, room=sid)

@sio.on('GetRegulars')
async def sio_getRegularGroups(sid, data=''):
    if not isinstance(data, dict) or not 'platform' in data or not 'group' in data:
        await sio.emit('GetRegulars', {'type': 'error', 'success': False, 'message': 'Please forward json... sio.emit("GetRegularGroups", {"platform": platform, "group": groupname})'}, room=sid)
        return
    
    regulars = extensions.regulars.getRegulars(data['platform'], data['group'])

    if regulars is None:
        await sio.emit('GetRegulars', {'type': 'error', 'success': False, 'message': 'Groupname or platform does not exist'}, room=sid)
        return

    await sio.emit('GetRegulars', {'type': 'success', 'success': True, 'regulars': regulars}, room=sid)

app.add_routes(routes=routes)

runner = web.AppRunner(app)

async def run():
    global site
    if site != None: return

    extensions.loadServices()

    with open('website.html', 'w') as f: f.write('<script>window.location = "http://localhost:' + str(extensions.settings.currentPort) + '"</script>')
    urlJsPath = Path('dependencies/data/url.js')
    urlJsPath.parent.mkdir(parents=True, exist_ok=True)
    with open(urlJsPath, 'w') as f: f.write('var server_url = \"http://' + Misc.getServerIP() + ':' + str(extensions.settings.currentPort) + '\";')

    print('starting website: http://localhost:' + str(extensions.settings.currentPort) + ' (Saving website shortcut to website.html)')

    await runner.setup()
    site = web.TCPSite(runner=runner, host='0.0.0.0', port=extensions.settings.currentPort)
    await site.start()

    while True:
        # run loop
        await asyncio.sleep(10)
