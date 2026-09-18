from __future__ import annotations
import asyncio, logging
import uvicorn
from .config import get_settings
from .database import Database
from .runtime import RuntimeManager
from .web import create_app

async def main():
    base=get_settings(); logging.basicConfig(level=getattr(logging,base.log_level.upper(),logging.INFO),format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db=Database(base.database_path); await db.init(); runtime=RuntimeManager(base,db); await runtime.start()
    app=create_app(base,db,runtime); server=uvicorn.Server(uvicorn.Config(app,host=base.web_host,port=base.web_port,log_level=base.log_level.lower()))
    try: await server.serve()
    finally: await runtime.stop()
if __name__=="__main__": asyncio.run(main())
