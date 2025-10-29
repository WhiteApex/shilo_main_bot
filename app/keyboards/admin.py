from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_main_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить событие", callback_data="admin:event:add")
    builder.button(text="✏️ Редактировать", callback_data="admin:event:edit")
    builder.button(text="🗑 Удалить", callback_data="admin:event:delete")
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="📤 Экспорт CSV", callback_data="admin:export")
    builder.button(text="♻️ Бэкап сейчас", callback_data="admin:backup")
    builder.button(text="🖼 Контент стартовой страницы", callback_data="admin:content")
    builder.button(text="➕ Добавить администратора", callback_data="admin:add")
    builder.adjust(1)
    return builder


def admin_events_keyboard(events: list[tuple[int, str]], prefix: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for event_id, title in events:
        builder.button(text=title, callback_data=f"{prefix}:{event_id}")
    builder.button(text="⬅️ Назад", callback_data="admin:home")
    builder.adjust(1)
    return builder
