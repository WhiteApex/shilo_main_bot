from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )


async def send_admin_log(bot: Bot, chat_id: Optional[int], message: str) -> None:
    if not chat_id:
        return
    try:
        await bot.send_message(chat_id, message)
    except Exception:  # noqa: BLE001
        logging.exception("Failed to send log message to admin chat")
