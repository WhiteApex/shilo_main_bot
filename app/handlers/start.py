from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.config import load_settings
from app.db import repositories
from app.keyboards.start import start_keyboard
from app.metrics.service import MetricType, track
from app.services import content, events as events_service
from app.utils.utm import parse_start_payload

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.startswith("/start"))
async def cmd_start(message: Message, bot: Bot) -> None:
    settings = load_settings()
    payload = message.text.split(" ", 1)[1] if " " in message.text else None
    utm = parse_start_payload(payload)
    user = await repositories.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        start_payload=payload,
        utm=utm,
    )
    await track(MetricType.START, user_id=user.id, payload={"payload": payload})

    start_section = content.get_section("start", {})
    image_id = start_section.get("image_id")
    text = start_section.get("text", "Добро пожаловать!")

    keyboard = start_keyboard(settings.manager_username).as_markup()

    if image_id:
        await message.answer_photo(
            image_id,
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "start:home")
async def cb_home(callback: CallbackQuery, bot: Bot) -> None:
    settings = load_settings()
    start_section = content.get_section("start", {})
    image_id = start_section.get("image_id")
    text = start_section.get("text", "Добро пожаловать!")
    markup: InlineKeyboardMarkup = start_keyboard(settings.manager_username).as_markup()
    await callback.answer()
    if image_id:
        await bot.send_photo(callback.from_user.id, image_id, caption=text, reply_markup=markup)
    else:
        await bot.send_message(callback.from_user.id, text, reply_markup=markup)


@router.callback_query(F.data == "info:about")
async def cb_about(callback: CallbackQuery) -> None:
    about_section = content.get_section("about", {})
    text = about_section.get(
        "text",
        "Мы команда онлайн-мероприятий. Совсем скоро здесь появится больше информации!",
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "events:list")
async def cb_events(callback: CallbackQuery) -> None:
    events = await events_service.list_active_events()
    if not events:
        await callback.message.answer("Скоро появятся новые события. Заглядывай позже!")
        await callback.answer()
        return

    from app.keyboards.events import events_list_keyboard

    tz = ZoneInfo(settings.timezone)
    keyboard = events_list_keyboard(
        [
            (event.id, f"{event.title} — {event.date.astimezone(tz):%d.%m}")
            for event in events
        ]
    )
    await callback.message.answer("Выбирай событие:", reply_markup=keyboard.as_markup())
    await callback.answer()
