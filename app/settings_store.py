from __future__ import annotations

from .config import Settings
from .database import Database

EDITABLE_KEYS = {
    "discord_token", "discord_guild_id", "discord_channel_ids", "discord_reply_mode",
    "telegram_bot_token", "telegram_admin_chat_id",
    "radarr_url", "radarr_api_key", "radarr_root_folder", "radarr_quality_profile_id",
    "sonarr_url", "sonarr_api_key", "sonarr_root_folder", "sonarr_quality_profile_id",
    "auto_approve_confidence", "dry_run",
}


async def load_runtime_settings(base: Settings, db: Database) -> Settings:
    saved = await db.get_settings()
    data = base.model_dump()
    for key, value in saved.items():
        if key not in EDITABLE_KEYS:
            continue
        if key in {"discord_guild_id", "telegram_admin_chat_id", "radarr_quality_profile_id", "sonarr_quality_profile_id"}:
            data[key] = int(value) if value else None
        elif key == "auto_approve_confidence":
            data[key] = float(value or 0.95)
        elif key == "dry_run":
            data[key] = value.lower() in {"1", "true", "yes", "on"}
        elif key == "discord_channel_ids":
            data[key] = [int(x.strip()) for x in value.split(",") if x.strip()]
        else:
            data[key] = value
    return Settings(**data)
