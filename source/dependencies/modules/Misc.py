import asyncio, aiohttp, ipaddress, socket
import aiohttp.client_exceptions
from sys import argv
from pathlib import Path

def validPort(port : int): return port > -1 and port < 65354

def portOverride(defaultPort : int) -> tuple[bool, int]:
    argvLength = len(argv)
    for i in range(argvLength):
        if argv[i] == '--port' and i != argvLength - 1:
            try:
                port = int(argv[i + 1])
                if validPort(port): return True, port
            except Exception:
                pass
    return False, defaultPort

def localIP(environ, currentIP=None):
    if 'HTTP_X_FORWARDED_FOR' in environ and currentIP != None:
        return environ['HTTP_X_FORWARDED_FOR'] == currentIP
    
    if 'REMOTE_ADDR' in environ:
        try:
            ipObj = ipaddress.ip_address(environ['REMOTE_ADDR'])
        except ValueError:
            return False
        return ipObj.is_private

def getServerIP():
    return socket.gethostbyname(socket.gethostname())

async def fetchUrl(url, *, method='get', headers=None, body=None) -> tuple[str | None, int]:
    kwargs = {}
    if isinstance(headers, dict):
        parsedHeaders = {}
        for key in headers:
            if isinstance(headers[key], str):
                parsedHeaders[key] = headers[key]
        if len(parsedHeaders.items()) > 0:
            kwargs['headers'] = parsedHeaders
    
    if isinstance(body, str):
        kwargs['data'] = body
    
    try:
        async with aiohttp.ClientSession() as sesson:
            async with sesson.request(method, url, **kwargs) as response:
                text = await response.text()
    except aiohttp.ClientConnectorError:
        return None, -1
    except aiohttp.InvalidURL:
        return None, -2
    except Exception:
        return None, -2
    await asyncio.sleep(0.1)
    # asyncio.sleep(0.1) prevents RuntimeError from being raised if loop is closing too soon
    # aiohttp seem have a problem with asyncio.new_event_loop(), probably used by asyncio.run(), since using asyncio.get_event_loop() to get a new loop is depricated
    # Not a problem if asyncio.get_event_loop() + loop.run_until_complete(main()) is used explicitly, except that a DepricatedWarning print is visible (python 3.10)
    return text, 1

def isSubfolder(folder : Path, subfolder : Path):
    if (not isinstance(folder, Path)) or (not isinstance(subfolder, Path)): return False

    try:
        subfolder.resolve().relative_to(folder.resolve())
        return True
    except ValueError: return False
