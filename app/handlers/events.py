from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import load_settings
from app.db import repositories
from app.keyboards.events import event_card_keyboard
from app.metrics.service import MetricType, track
from app.services import events as events_service
from app.utils.logging import send_admin_log

router = Router()
logger = logging.getLogger(__name__)


class SubscriptionForm(StatesGroup):
    waiting_full_name = State()
    waiting_phone = State()
    waiting_email = State()


@router.callback_query(F.data.startswith("events:view:"))
async def cb_event_view(callback: CallbackQuery, state: FSMContext) -> None:
    settings = load_settings()
    _, _, event_id_str = callback.data.partition("events:view:")
    event_id = int(event_id_str)
    user = await repositories.get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    event = await events_service.get_event(event_id)
    subscription = await repositories.get_subscription_by_telegram(
        callback.from_user.id, event_id
    )
    markup = event_card_keyboard(event_id, subscribed=subscription is not None).as_markup()
    caption = await events_service.format_event_card(event, settings.timezone)

    if event.status == "archive":
        caption += "\n\nСобытие прошло. Скоро мы покажем отчёт!"
    elif event.status == "report" and event.report_media_id:
        caption += "\n\nСобытие прошло. Делимся материалами!"

    if event.image_id:
        await callback.message.answer_photo(
            event.image_id,
            caption=caption,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
        )
    else:
        await callback.message.answer(caption, reply_markup=markup, parse_mode=ParseMode.HTML)
    if event.status == "report" and event.report_media_id:
        try:
            await callback.message.answer_photo(event.report_media_id, caption="Фотоотчёт")
        except Exception:
            try:
                await callback.message.answer_video(event.report_media_id, caption="Видеоотчёт")
            except Exception:
                await callback.message.answer(
                    "Событие прошло! Отчёт не удалось показать автоматически, обратитесь к менеджеру."
                )
    await track(MetricType.CLICK, user_id=user.id, event_id=event_id)
    await callback.answer()


@router.callback_query(F.data.startswith("events:subscribe:"))
async def cb_event_subscribe(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, event_id_str = callback.data.partition("events:subscribe:")
    event_id = int(event_id_str)
    event = await events_service.ensure_event(event_id)
    if event.subscribed_count >= event.limit:
        await callback.message.answer("Лимит участников уже достигнут. Напишите менеджеру, чтобы попасть в лист ожидания.")
        await callback.answer()
        return
    await state.update_data(event_id=event_id)
    await callback.message.answer("Как к вам обращаться? Напишите ФИО или имя.")
    await state.set_state(SubscriptionForm.waiting_full_name)
    await callback.answer()


@router.message(SubscriptionForm.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=message.text.strip())
    await message.answer("Оставьте, пожалуйста, номер телефона.")
    await state.set_state(SubscriptionForm.waiting_phone)


@router.message(SubscriptionForm.waiting_phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.text.strip())
    await message.answer("Теперь укажите email для отправки напоминаний.")
    await state.set_state(SubscriptionForm.waiting_email)


@router.message(SubscriptionForm.waiting_email)
async def process_email(message: Message, state: FSMContext, bot: Bot) -> None:
    settings = load_settings()
    data = await state.get_data()
    event_id = data["event_id"]
    user = await repositories.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    try:
        subscription = await repositories.create_subscription(
            user_id=user.id,
            event_id=event_id,
            full_name=data["full_name"],
            phone=data["phone"],
            email=message.text.strip(),
        )
    except ValueError as err:
        reason = str(err)
        if reason == "already_subscribed":
            text = "Вы уже записаны на это событие. Если хотите изменить данные — напишите менеджеру."
        elif reason == "limit_reached":
            text = "К сожалению, лимит участников достигнут. Напишите менеджеру, чтобы попасть в лист ожидания."
        else:
            text = "Не удалось сохранить запись. Попробуйте позже или свяжитесь с менеджером."
        await message.answer(text)
        await state.clear()
        return
    await repositories.update_user_contacts(user.id, data["phone"], message.text.strip())
    await track(MetricType.SUBSCRIPTION, user_id=user.id, event_id=event_id)
    await send_admin_log(
        bot,
        settings.admin_log_chat_id,
        f"Новая запись на событие #{event_id} от @{message.from_user.username or message.from_user.id}",
    )

    await message.answer("Спасибо! Мы записали вас и пришлём напоминания ближе к событию.")
    await state.clear()
