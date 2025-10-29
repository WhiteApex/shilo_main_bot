from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv
import sentry_sdk

from app.config import load_settings
from app.db.base import init_engine
from app.handlers import admin, events, start
from app.scheduler import setup_scheduler
from app.utils.logging import setup_logging


async def set_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Начать"),
        BotCommand(command="admin", description="Админ-панель"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    if os.path.exists(".env"):
        load_dotenv()
    setup_logging()
    settings = load_settings()

    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

    init_engine(settings.database_url)

    bot = Bot(token=settings.telegram_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(events.router)
    dp.include_router(admin.router)

    scheduler = setup_scheduler(bot)
    scheduler.start()

    await set_commands(bot)
    logging.info("Bot started")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
