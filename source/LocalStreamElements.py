from pathlib import Path
import os, asyncio, aiohttp, json

async def fetchUrl(url):
    try:
        async with aiohttp.ClientSession() as sesson:
            async with sesson.get(url) as response:
                text = await response.text()
    except aiohttp.client_exceptions.ClientConnectorError:
        return None, -1
    except aiohttp.client_exceptions.InvalidURL:
        return None, -2
    except Exception:
        return None, -3
    await asyncio.sleep(0.1)
    # asyncio.sleep(0.1) prevents RuntimeError from being raised if loop is closing too soon
    # aiohttp seem have a problem with asyncio.new_event_loop(), probably used by asyncio.run(), since using asyncio.get_event_loop() to get a new loop is depricated
    # Not a problem if asyncio.get_event_loop() + loop.run_until_complete(main()) is used explicitly, except that a DepricatedWarning print is visible (python 3.10)
    return text, 1

async def main():
    os.chdir(Path(__file__).parent.absolute())
    await update()

    from dependencies.modules import Core
    await Core.run()

async def update():

    text, errorCode = await fetchUrl('https://raw.githubusercontent.com/Yazaar/StreamElements-Local-Cloudbot/master/LatestVersion.json')
    if errorCode < 0:
        print('[Error] Unable to check for updates. No internet connection? (trying to launch anyways)')
        return
    
    try: respJson = json.loads(text)
    except Exception: return

if __name__ == '__main__':
    asyncio.run(main())