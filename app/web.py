from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .database import Database
from .config import Settings
from .runtime import RuntimeManager
from .settings_store import load_runtime_settings
from .arr_client import radarr_library_stats, sonarr_library_stats

BASE=Path(__file__).parent

def create_app(base: Settings, db: Database, runtime: RuntimeManager) -> FastAPI:
    app=FastAPI(title="ArrRelay", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=base.app_secret, same_site="lax", https_only=False)
    app.mount("/static", StaticFiles(directory=BASE/"static"), name="static")
    t=Jinja2Templates(directory=BASE/"templates")

    def authed(r): return bool(r.session.get("admin"))
    async def guard(r):
        if not await db.has_admin(): return RedirectResponse("/setup",303)
        if not authed(r): return RedirectResponse("/login",303)

    @app.get("/setup")
    async def setup_get(request:Request):
        if await db.has_admin(): return RedirectResponse("/login",303)
        return t.TemplateResponse("setup.html",{"request":request})
    @app.post("/setup")
    async def setup_post(request:Request, username:str=Form(...), password:str=Form(...), confirm:str=Form(...)):
        if await db.has_admin(): return RedirectResponse("/login",303)
        err=None
        if len(password)<8: err="Password must be at least 8 characters."
        elif password!=confirm: err="Passwords do not match."
        if err: return t.TemplateResponse("setup.html",{"request":request,"error":err},status_code=400)
        await db.create_admin(username.strip(),password); request.session["admin"]=username.strip(); return RedirectResponse("/settings",303)
    @app.get("/login")
    async def login_get(request:Request): return t.TemplateResponse("login.html",{"request":request})
    @app.post("/login")
    async def login_post(request:Request, username:str=Form(...), password:str=Form(...)):
        if await db.verify_admin(username,password): request.session["admin"]=username; return RedirectResponse("/",303)
        return t.TemplateResponse("login.html",{"request":request,"error":"Invalid username or password."},status_code=401)
    @app.get("/logout")
    async def logout(request:Request): request.session.clear(); return RedirectResponse("/login",303)

    @app.get("/")
    async def dashboard(request:Request):
        x=await guard(request)
        if x:return x
        s=await load_runtime_settings(base,db); req=await db.stats(); recent=await db.recent_requests()
        rad={"total":0,"downloaded":0}; son={"series_total":0,"episodes_downloaded":0,"episodes_total":0}; errors=[]
        try: rad=await radarr_library_stats(s.radarr_url,s.radarr_api_key)
        except Exception as e: errors.append(f"Radarr: {e}")
        try: son=await sonarr_library_stats(s.sonarr_url,s.sonarr_api_key)
        except Exception as e: errors.append(f"Sonarr: {e}")
        return t.TemplateResponse("dashboard.html",{"request":request,"req":req,"recent":recent,"rad":rad,"son":son,"runtime":runtime,"errors":errors})

    @app.get("/settings")
    async def settings_get(request:Request):
        x=await guard(request)
        if x:return x
        s=await load_runtime_settings(base,db)
        return t.TemplateResponse("settings.html",{"request":request,"s":s})
    @app.post("/settings")
    async def settings_post(request:Request):
        x=await guard(request)
        if x:return x
        f=await request.form(); keys=["discord_token","discord_guild_id","discord_channel_ids","discord_reply_mode","telegram_bot_token","telegram_admin_chat_id","radarr_url","radarr_api_key","radarr_root_folder","radarr_quality_profile_id","sonarr_url","sonarr_api_key","sonarr_root_folder","sonarr_quality_profile_id","auto_approve_confidence"]
        vals={k:str(f.get(k,"")) for k in keys}; vals["dry_run"]="true" if f.get("dry_run") else "false"
        await db.save_settings(vals); await runtime.restart()
        return RedirectResponse("/settings?saved=1",303)
    return app
