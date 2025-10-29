from __future__ import annotations

import io
import pandas as pd
from aiogram import Bot
from aiogram.types import BufferedInputFile
from sqlalchemy import select

from app.db.base import session_factory
from app.db.models import Event, Subscription, User


async def export_subscriptions_csv(bot: Bot, chat_id: int) -> None:
    async with session_factory() as session:
        stmt = (
            select(
                Subscription.id.label("subscription_id"),
                Subscription.full_name,
                Subscription.phone,
                Subscription.email,
                Subscription.created_at,
                Subscription.reminder_3d_sent,
                Subscription.reminder_1d_sent,
                Subscription.reminder_day_sent,
                Event.id.label("event_id"),
                Event.title.label("event_title"),
                Event.date.label("event_date"),
                User.telegram_id.label("user_telegram_id"),
                User.username.label("username"),
                User.utm_source,
                User.utm_medium,
                User.utm_campaign,
            )
            .join(Event, Subscription.event_id == Event.id)
            .join(User, Subscription.user_id == User.id)
        )
        result = await session.execute(stmt)
        records = [dict(row._mapping) for row in result.all()]

    if not records:
        await bot.send_message(chat_id, "Пока нет данных для экспорта")
        return

    df = pd.DataFrame(records)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    file_bytes = csv_buffer.getvalue().encode("utf-8")
    input_file = BufferedInputFile(file_bytes, filename="subscriptions.csv")
    await bot.send_document(chat_id, document=input_file, caption="Экспорт подписок")
