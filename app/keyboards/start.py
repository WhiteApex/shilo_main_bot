from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder


def start_keyboard(manager_username: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Мероприятия", callback_data="events:list")
    builder.button(text="ℹ️ О нас", callback_data="info:about")
    builder.button(text="💬 Написать нам", url=f"https://t.me/{manager_username}")
    builder.adjust(1)
    return builder
