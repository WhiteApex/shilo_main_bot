from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import BaseModel, Field


class Settings(BaseModel):
    telegram_token: str = Field(alias="TELEGRAM_TOKEN")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")
    super_admin_id: int = Field(alias="SUPER_ADMIN_ID")
    database_url: str = Field(alias="DATABASE_URL")
    manager_username: str = Field(alias="MANAGER_USERNAME")
    backup_email: str = Field(alias="BACKUP_EMAIL")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    admin_log_chat_id: int | None = Field(default=None, alias="ADMIN_LOG_CHAT_ID")
    timezone: str = Field(default="Asia/Yekaterinburg", alias="TIMEZONE")

    class Config:
        allow_mutation = False


def _parse_admin_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


@lru_cache
def load_settings() -> Settings:
    env = {key: value for key, value in os.environ.items() if key.isupper()}
    env.setdefault("ADMIN_IDS", os.environ.get("ADMIN_IDS", ""))
    settings = Settings.model_validate(env)
    return settings.model_copy(update={"admin_ids": _parse_admin_ids(env.get("ADMIN_IDS"))})
