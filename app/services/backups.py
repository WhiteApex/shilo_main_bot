from __future__ import annotations

import datetime as dt
import os
import shutil
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from app.config import load_settings
from app.utils.logging import send_admin_log

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)


def create_backup_copy(database_path: str) -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"bot_backup_{timestamp}.db"
    shutil.copy(database_path, target)
    return target


async def send_backup(bot: Bot, file_path: Path) -> None:
    settings = load_settings()
    await send_admin_log(
        bot,
        settings.admin_log_chat_id,
        f"Отправляем резервную копию БД: {file_path.name}",
    )
    await bot.send_document(settings.super_admin_id, FSInputFile(file_path))


async def backup_and_send(bot: Bot, database_url: str) -> None:
    if database_url.startswith("sqlite"):
        db_path = Path(database_url.split("///")[-1]).resolve()
        if db_path.exists():
            file_path = create_backup_copy(str(db_path))
            await send_backup(bot, file_path)
