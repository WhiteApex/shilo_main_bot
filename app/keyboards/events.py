from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder


def events_list_keyboard(events: list[tuple[int, str]]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for event_id, title in events:
        builder.button(text=title, callback_data=f"events:view:{event_id}")
    builder.button(text="🏠 На главную", callback_data="start:home")
    builder.adjust(1)
    return builder


def event_card_keyboard(event_id: int, subscribed: bool) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    if subscribed:
        builder.button(text="Вы записаны ✅", callback_data="noop")
    else:
        builder.button(text="📅 Записаться", callback_data=f"events:subscribe:{event_id}")
    builder.button(text="🏠 На главную", callback_data="start:home")
    builder.adjust(1)
    return builder
