from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .arr_client import radarr_library_stats, sonarr_library_stats
from .config import Settings
from .database import Database
from .runtime import RuntimeManager
from .settings_store import load_runtime_settings

BASE = Path(__file__).parent

SETTING_KEYS = [
    "discord_token",
    "discord_guild_id",
    "discord_channel_ids",
    "discord_reply_mode",
    "telegram_bot_token",
    "telegram_admin_chat_id",
    "radarr_url",
    "radarr_api_key",
    "radarr_root_folder",
    "radarr_quality_profile_id",
    "sonarr_url",
    "sonarr_api_key",
    "sonarr_root_folder",
    "sonarr_quality_profile_id",
    "auto_approve_confidence",
]


def _form_settings(form) -> dict[str, str]:
    values = {key: str(form.get(key, "")).strip() for key in SETTING_KEYS}
    values["dry_run"] = "true" if form.get("dry_run") else "false"
    return values


def _validate_setup(form) -> list[str]:
    errors: list[str] = []

    required = {
        "discord_token": "Discord bot token",
        "discord_guild_id": "Discord server ID",
        "discord_channel_ids": "Discord channel ID",
        "telegram_bot_token": "Telegram bot token",
        "telegram_admin_chat_id": "Telegram admin chat ID",
        "radarr_url": "Radarr URL",
        "radarr_api_key": "Radarr API key",
        "radarr_root_folder": "Radarr root folder",
        "radarr_quality_profile_id": "Radarr quality profile ID",
        "sonarr_url": "Sonarr URL",
        "sonarr_api_key": "Sonarr API key",
        "sonarr_root_folder": "Sonarr root folder",
        "sonarr_quality_profile_id": "Sonarr quality profile ID",
    }

    for key, label in required.items():
        if not str(form.get(key, "")).strip():
            errors.append(f"{label} is required.")

    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    confirm = str(form.get("confirm", ""))

    if not username:
        errors.append("Admin username is required.")
    if len(password) < 8:
        errors.append("Admin password must be at least 8 characters.")
    if password != confirm:
        errors.append("Admin passwords do not match.")

    return errors


def create_app(base: Settings, db: Database, runtime: RuntimeManager) -> FastAPI:
    app = FastAPI(title="ArrRelay", docs_url=None, redoc_url=None)
    app.add_middleware(
        SessionMiddleware,
        secret_key=base.app_secret,
        same_site="lax",
        https_only=False,
    )
    app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
    templates = Jinja2Templates(directory=BASE / "templates")

    def authed(request: Request) -> bool:
        return bool(request.session.get("admin"))

    async def guard(request: Request):
        if not await db.has_admin():
            return RedirectResponse("/setup", 303)
        if not authed(request):
            return RedirectResponse("/login", 303)

    @app.get("/setup")
    async def setup_get(request: Request):
        if await db.has_admin():
            return RedirectResponse("/login", 303)
        return templates.TemplateResponse(
            "setup.html",
            {"request": request, "defaults": base},
        )

    @app.post("/setup")
    async def setup_post(request: Request):
        if await db.has_admin():
            return RedirectResponse("/login", 303)

        form = await request.form()
        errors = _validate_setup(form)

        if errors:
            return templates.TemplateResponse(
                "setup.html",
                {
                    "request": request,
                    "defaults": base,
                    "form": form,
                    "errors": errors,
                },
                status_code=400,
            )

        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))

        await db.create_admin(username, password)
        await db.save_settings(_form_settings(form))

        request.session["admin"] = username

        # Start Discord/Telegram immediately with the newly saved configuration.
        await runtime.restart()

        return RedirectResponse("/?setup=complete", 303)

    @app.get("/login")
    async def login_get(request: Request):
        if not await db.has_admin():
            return RedirectResponse("/setup", 303)
        return templates.TemplateResponse("login.html", {"request": request})

    @app.post("/login")
    async def login_post(request: Request):
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))

        if await db.verify_admin(username, password):
            request.session["admin"] = username
            return RedirectResponse("/", 303)

        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password."},
            status_code=401,
        )

    @app.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", 303)

    @app.get("/")
    async def dashboard(request: Request):
        redirect = await guard(request)
        if redirect:
            return redirect

        settings = await load_runtime_settings(base, db)
        req = await db.stats()
        recent = await db.recent_requests()

        radarr = {"total": 0, "downloaded": 0}
        sonarr = {
            "series_total": 0,
            "episodes_downloaded": 0,
            "episodes_total": 0,
        }
        errors: list[str] = []

        try:
            radarr = await radarr_library_stats(settings.radarr_url, settings.radarr_api_key)
        except Exception as exc:
            errors.append(f"Radarr: {exc}")

        try:
            sonarr = await sonarr_library_stats(settings.sonarr_url, settings.sonarr_api_key)
        except Exception as exc:
            errors.append(f"Sonarr: {exc}")

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "req": req,
                "recent": recent,
                "rad": radarr,
                "son": sonarr,
                "runtime": runtime,
                "errors": errors,
            },
        )

    @app.get("/settings")
    async def settings_get(request: Request):
        redirect = await guard(request)
        if redirect:
            return redirect

        settings = await load_runtime_settings(base, db)
        return templates.TemplateResponse(
            "settings.html",
            {"request": request, "s": settings},
        )

    @app.post("/settings")
    async def settings_post(request: Request):
        redirect = await guard(request)
        if redirect:
            return redirect

        form = await request.form()
        await db.save_settings(_form_settings(form))
        await runtime.restart()

        return RedirectResponse("/settings?saved=1", 303)

    return app
