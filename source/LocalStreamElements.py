from pathlib import Path
import os, asyncio

async def main():
    os.chdir(Path(__file__).parent.absolute())
    await update()
    
    from dependencies.modules import Core
    await Core.run()

async def update():
    pass

if __name__ == '__main__':
    asyncio.run(main())
