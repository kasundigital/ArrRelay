from __future__ import annotations
import asyncio, logging
from .database import Database
from .settings_store import load_runtime_settings
from .telegram_bot import TelegramReviewBot
from .service import RequestService
from .discord_bot import DiscordRequestBot
from .config import Settings

log = logging.getLogger(__name__)

class RuntimeManager:
    def __init__(self, base: Settings, db: Database):
        self.base, self.db = base, db
        self.task = None
        self.discord = None
        self.telegram = None
        self.service = None
        self.settings = base
        self.error = None

    async def start(self):
        self.settings = await load_runtime_settings(self.base, self.db)
        if not self.settings.discord_token:
            return
        try:
            self.telegram = TelegramReviewBot(self.settings.telegram_bot_token, self.settings.telegram_admin_chat_id)
            self.service = RequestService(self.settings, self.db, self.telegram)
            self.discord = DiscordRequestBot(service=self.service, guild_id=self.settings.discord_guild_id, channel_ids=self.settings.discord_channel_ids, reply_mode=self.settings.discord_reply_mode)
            await self.telegram.start()
            self.task = asyncio.create_task(self.discord.start(self.settings.discord_token))
            self.error = None
        except Exception as exc:
            self.error = str(exc); log.exception("Failed to start integrations")

    async def stop(self):
        if self.discord:
            try: await self.discord.close()
            except Exception: pass
        if self.task:
            self.task.cancel()
            try: await self.task
            except BaseException: pass
        if self.telegram:
            try: await self.telegram.stop()
            except Exception: pass
        if self.service:
            try: await self.service.close()
            except Exception: pass
        self.task=self.discord=self.telegram=self.service=None

    async def restart(self):
        await self.stop(); await self.start()

    @property
    def running(self):
        return bool(self.task and not self.task.done())
