from __future__ import annotations

import datetime as dt
import logging

from aiogram import Bot

from app.config import load_settings
from app.db import repositories
from app.metrics.service import MetricType, track
from app.utils.time import reminder_times

logger = logging.getLogger(__name__)


async def process_reminders(bot: Bot) -> None:
    settings = load_settings()
    now = dt.datetime.now(dt.timezone.utc)
    reminders = await repositories.subscriptions_for_reminders(now)
    for item in reminders:
        for reminder_time, flag in reminder_times(item.event_date, settings.timezone):
            reminder_utc = reminder_time.astimezone(dt.timezone.utc)
            already_sent = getattr(item, flag)
            if already_sent:
                continue
            if reminder_utc <= now:
                await _send_reminder(bot, item.telegram_id, item.event_title, reminder_time)
                await repositories.set_subscription_flag(item.subscription_id, flag)
                await track(
                    MetricType.DELIVERY,
                    user_id=item.user_id,
                    event_id=item.event_id,
                    payload={"reminder": flag},
                )


async def _send_reminder(bot: Bot, chat_id: int, event_title: str, reminder_time: dt.datetime) -> None:
    text = (
        f"Напоминаем: {event_title} уже совсем скоро!\n"
        f"⏰ Встречаемся {reminder_time.strftime('%d.%m %H:%M')} (Екатеринбург)"
    )
    try:
        await bot.send_message(chat_id, text)
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось отправить напоминание")
