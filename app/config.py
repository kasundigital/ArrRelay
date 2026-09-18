from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_path: str = "/data/arrrelay.db"
    web_host: str = "0.0.0.0"
    web_port: int = 3032
    app_secret: str = "change-me-in-production"
    log_level: str = "INFO"

    discord_token: str = ""
    discord_guild_id: int | None = None
    discord_channel_ids: List[int] = Field(default_factory=list)
    discord_reply_mode: str = "reply"

    telegram_bot_token: str = ""
    telegram_admin_chat_id: int | None = None

    radarr_url: str = "http://radarr:7878"
    radarr_api_key: str = ""
    radarr_root_folder: str = "/movies"
    radarr_quality_profile_id: int = 1

    sonarr_url: str = "http://sonarr:8989"
    sonarr_api_key: str = ""
    sonarr_root_folder: str = "/tv"
    sonarr_quality_profile_id: int = 1

    auto_approve_confidence: float = 0.95
    dry_run: bool = True

    @field_validator("discord_channel_ids", mode="before")
    @classmethod
    def parse_channel_ids(cls, value):
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return value
        return [int(v.strip()) for v in str(value).split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
