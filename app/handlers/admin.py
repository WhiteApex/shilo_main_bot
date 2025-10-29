from __future__ import annotations

import datetime as dt
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import load_settings
from app.db import repositories
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.admin import admin_events_keyboard, admin_main_keyboard
from app.metrics.service import MetricType, track
from app.services import content, events as events_service
from app.services.backups import backup_and_send
from app.services.export import export_subscriptions_csv
from app.services.admins import add_admin
from app.utils.admin import ensure_admin, is_admin
from app.utils.logging import send_admin_log

router = Router()
logger = logging.getLogger(__name__)


class AddEventStates(StatesGroup):
    waiting_title = State()
    waiting_teaser = State()
    waiting_description = State()
    waiting_date = State()
    waiting_image = State()
    waiting_limit = State()
    confirm = State()


class EditEventStates(StatesGroup):
    waiting_event = State()
    waiting_field = State()
    waiting_value = State()


class ContentStates(StatesGroup):
    waiting_section = State()
    waiting_text = State()
    waiting_image = State()


class AdminManagementStates(StatesGroup):
    waiting_admin_id = State()


@router.message(F.text == "/admin")
async def cmd_admin(message: Message) -> None:
    if not ensure_admin(message):
        await message.answer("Доступ ограничен. Напишите главному администратору.")
        return
    await message.answer(
        "Привет, администратор! Что делаем?",
        reply_markup=admin_main_keyboard().as_markup(),
    )


@router.callback_query(F.data == "admin:home")
async def cb_admin_home(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=admin_main_keyboard().as_markup(),
    )
    await callback.answer()


async def _admin_events_keyboard(prefix: str) -> InlineKeyboardBuilder | None:
    events = await repositories.get_all_events()
    if not events:
        return None
    return admin_events_keyboard([(event.id, f"{event.title} ({event.status})") for event in events], prefix)


@router.callback_query(F.data == "admin:event:add")
async def cb_admin_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(AddEventStates.waiting_title)
    await callback.message.answer("Введите название события")
    await callback.answer()


@router.message(AddEventStates.waiting_title)
async def admin_add_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await message.answer("Напишите цепляющую фразу (teaser)")
    await state.set_state(AddEventStates.waiting_teaser)


@router.message(AddEventStates.waiting_teaser)
async def admin_add_teaser(message: Message, state: FSMContext) -> None:
    await state.update_data(teaser=message.text.strip())
    await message.answer("Теперь пришлите основное описание (2-3 предложения)")
    await state.set_state(AddEventStates.waiting_description)


@router.message(AddEventStates.waiting_description)
async def admin_add_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.html_text)
    await message.answer("Укажите дату и время в формате 25.03.2024 19:00")
    await state.set_state(AddEventStates.waiting_date)


@router.message(AddEventStates.waiting_date)
async def admin_add_date(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    try:
        date = dt.datetime.strptime(text, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("Не получилось распознать дату. Используйте формат 25.03.2024 19:00")
        return
    tz = ZoneInfo(load_settings().timezone)
    date = date.replace(tzinfo=tz)
    await state.update_data(date=date.isoformat())
    await message.answer("Пришлите изображение события или отправьте file_id")
    await state.set_state(AddEventStates.waiting_image)


@router.message(AddEventStates.waiting_image)
async def admin_add_image(message: Message, state: FSMContext) -> None:
    if message.photo:
        image_id = message.photo[-1].file_id
    else:
        image_id = message.text.strip()
    await state.update_data(image_id=image_id)
    await message.answer("Укажите лимит участников (по умолчанию 200). Если всё ок, отправьте число или напишите 'пропустить'.")
    await state.set_state(AddEventStates.waiting_limit)


@router.message(AddEventStates.waiting_limit)
async def admin_add_limit(message: Message, state: FSMContext) -> None:
    limit_text = message.text.strip().lower()
    limit = 200
    if limit_text not in {"пропустить", "skip"}:
        try:
            limit = int(limit_text)
        except ValueError:
            await message.answer("Введите число или напишите 'пропустить'")
            return
    await state.update_data(limit=limit)
    data = await state.get_data()
    tz = ZoneInfo(load_settings().timezone)
    preview_date = dt.datetime.fromisoformat(data["date"]).astimezone(tz)
    preview = (
        f"<b>{data['title']}</b>\n"
        f"{data['teaser']}\n\n"
        f"{data['description']}\n\n"
        f"🗓 {preview_date.strftime('%d.%m.%Y %H:%M')} ({preview_date.tzname()})\n"
        f"Лимит: {data['limit']}"
    )
    await message.answer("Вот как будет выглядеть карточка:", parse_mode=ParseMode.HTML)
    await message.answer_photo(data["image_id"], caption=preview, parse_mode=ParseMode.HTML)
    await message.answer("Если всё верно, напишите 'опубликовать', иначе 'отмена'.")
    await state.set_state(AddEventStates.confirm)


@router.message(AddEventStates.confirm)
async def admin_add_confirm(message: Message, state: FSMContext, bot: Bot) -> None:
    text = message.text.strip().lower()
    if text not in {"опубликовать", "ok", "да"}:
        await message.answer("Отменено. Запустите /admin, чтобы начать заново.")
        await state.clear()
        return
    data = await state.get_data()
    event = await events_service.create_event(
        title=data["title"],
        teaser=data["teaser"],
        description=data["description"],
        date_text=data["date"],
        image_id=data["image_id"],
        limit=data["limit"],
    )
    await repositories.log_admin_action(message.from_user.id, "create_event", str(data))
    await send_admin_log(
        bot,
        load_settings().admin_log_chat_id,
        f"Админ @{message.from_user.username} создал событие #{event.id}",
    )
    await backup_and_send(bot, load_settings().database_url)
    await message.answer("Готово! Событие опубликовано.")
    await state.clear()


@router.callback_query(F.data == "admin:event:edit")
async def cb_admin_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    keyboard = await _admin_events_keyboard("admin:event:edit:pick")
    if not keyboard:
        await callback.message.answer("Нет событий для редактирования")
        await callback.answer()
        return
    await state.set_state(EditEventStates.waiting_event)
    await callback.message.answer("Выберите событие", reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:event:edit:pick"))
async def cb_admin_edit_pick(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, _, _, event_id_str = callback.data.split(":", 4)
    event_id = int(event_id_str)
    await state.update_data(event_id=event_id)
    await state.set_state(EditEventStates.waiting_field)
    await callback.message.answer(
        "Что меняем? Напишите одно из: title, teaser, description, date, image, status, report",
    )
    await callback.answer()


@router.message(EditEventStates.waiting_field)
async def admin_edit_field(message: Message, state: FSMContext) -> None:
    field = message.text.strip().lower()
    valid = {"title", "teaser", "description", "date", "image", "status", "report"}
    if field not in valid:
        await message.answer("Не понял. Используйте: title, teaser, description, date, image, status, report")
        return
    await state.update_data(field=field)
    prompt = {
        "title": "Новое название:",
        "teaser": "Новая цепляющая фраза:",
        "description": "Новое описание (можно с HTML):",
        "date": "Новая дата в формате 25.03.2024 19:00:",
        "image": "Пришлите новое изображение или file_id:",
        "status": "Укажите статус (active/archive/report):",
        "report": "Пришлите file_id отчёта (фото или видео):",
    }[field]
    await message.answer(prompt)
    await state.set_state(EditEventStates.waiting_value)


@router.message(EditEventStates.waiting_value)
async def admin_edit_value(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    event_id = data["event_id"]
    field = data["field"]
    value = message.text.strip()
    update_kwargs: dict[str, str | int] = {}
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    elif getattr(message, "video", None):
        file_id = message.video.file_id
    else:
        file_id = None

    if field == "image" and file_id:
        value = file_id
    if field == "report" and file_id:
        value = file_id
    if field == "date":
        try:
            dt.datetime.strptime(value, "%d.%m.%Y %H:%M")
        except ValueError:
            await message.answer("Дата не распознана. Формат 25.03.2024 19:00")
            return
        update_kwargs["date_text"] = value
    elif field == "image":
        update_kwargs["image_id"] = value
    elif field == "status":
        if value not in {"active", "archive", "report"}:
            await message.answer("Статус должен быть active, archive или report")
            return
        update_kwargs["status"] = value
    elif field == "report":
        update_kwargs["report_media_id"] = value
    else:
        update_kwargs[field] = value
    event = await events_service.update_event(event_id, **update_kwargs)
    await repositories.log_admin_action(message.from_user.id, "update_event", f"{field} -> {value}")
    await send_admin_log(
        bot,
        load_settings().admin_log_chat_id,
        f"Админ @{message.from_user.username} обновил {field} события #{event.id}",
    )
    await backup_and_send(bot, load_settings().database_url)
    await message.answer("Изменения сохранены")
    await state.clear()


@router.callback_query(F.data == "admin:event:delete")
async def cb_admin_delete(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    keyboard = await _admin_events_keyboard("admin:event:delete:pick")
    if not keyboard:
        await callback.message.answer("Нет событий для удаления")
        await callback.answer()
        return
    await callback.message.answer("Выберите событие для удаления", reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:event:delete:pick"))
async def cb_admin_delete_pick(callback: CallbackQuery, bot: Bot) -> None:
    _, _, _, _, event_id_str = callback.data.split(":", 4)
    event_id = int(event_id_str)
    await events_service.delete_event(event_id)
    await repositories.log_admin_action(callback.from_user.id, "delete_event", str(event_id))
    await send_admin_log(
        bot,
        load_settings().admin_log_chat_id,
        f"Админ @{callback.from_user.username} удалил событие #{event_id}",
    )
    await backup_and_send(bot, load_settings().database_url)
    await callback.message.answer("Событие удалено")
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    metrics = await repositories.get_metrics_summary()
    lines = ["Статистика по действиям:"]
    for key in [MetricType.START, MetricType.CLICK, MetricType.SUBSCRIPTION, MetricType.DELIVERY, MetricType.READ]:
        lines.append(f"• {key}: {metrics.get(key, 0)}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "admin:export")
async def cb_admin_export(callback: CallbackQuery, bot: Bot) -> None:
    await export_subscriptions_csv(bot, callback.from_user.id)
    await callback.answer("Готово")


@router.callback_query(F.data == "admin:backup")
async def cb_admin_backup(callback: CallbackQuery, bot: Bot) -> None:
    settings = load_settings()
    await backup_and_send(bot, settings.database_url)
    await callback.answer("Бэкап отправлен")


@router.callback_query(F.data == "admin:content")
async def cb_admin_content(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(ContentStates.waiting_section)
    await callback.message.answer("Что обновляем? Напишите 'start' или 'about'.")
    await callback.answer()


@router.callback_query(F.data == "admin:add")
async def cb_admin_add_admin(callback: CallbackQuery, state: FSMContext) -> None:
    settings = load_settings()
    if callback.from_user.id != settings.super_admin_id:
        await callback.answer("Только главный админ может добавлять новых", show_alert=True)
        return
    await state.set_state(AdminManagementStates.waiting_admin_id)
    await callback.message.answer("Пришлите ID пользователя, которого нужно сделать администратором")
    await callback.answer()


@router.message(AdminManagementStates.waiting_admin_id)
async def admin_add_admin_id(message: Message, state: FSMContext, bot: Bot) -> None:
    try:
        new_admin_id = int(message.text.strip())
    except (TypeError, ValueError):
        await message.answer("Нужно отправить числовой ID")
        return
    add_admin(new_admin_id)
    await repositories.log_admin_action(message.from_user.id, "add_admin", str(new_admin_id))
    await send_admin_log(
        bot,
        load_settings().admin_log_chat_id,
        f"Главный админ добавил нового администратора: {new_admin_id}",
    )
    await backup_and_send(bot, load_settings().database_url)
    await message.answer("Администратор добавлен. Попросите его перезапустить бота командой /start")
    await state.clear()


@router.message(ContentStates.waiting_section)
async def admin_content_section(message: Message, state: FSMContext) -> None:
    section = message.text.strip().lower()
    if section not in {"start", "about"}:
        await message.answer("Нужно написать 'start' или 'about'")
        return
    await state.update_data(section=section)
    if section == "start":
        await message.answer("Пришлите новый текст для стартового экрана")
    else:
        await message.answer("Напишите текст блока 'О нас'")
    await state.set_state(ContentStates.waiting_text)


@router.message(ContentStates.waiting_text)
async def admin_content_text(message: Message, state: FSMContext) -> None:
    await state.update_data(text=message.html_text)
    data = await state.get_data()
    if data["section"] == "start":
        await message.answer("Пришлите изображение (или отправьте file_id). Если менять не нужно, напишите 'пропустить'.")
        await state.set_state(ContentStates.waiting_image)
    else:
        content.save_content("about", {"text": message.html_text})
        await repositories.log_admin_action(message.from_user.id, "update_content", "about")
        await backup_and_send(message.bot, load_settings().database_url)
        await message.answer("Описание обновлено")
        await state.clear()


@router.message(ContentStates.waiting_image)
async def admin_content_image(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    text = data["text"]
    if message.text and message.text.strip().lower() in {"пропустить", "skip"}:
        image_id = content.get_section("start", {}).get("image_id")
    elif message.photo:
        image_id = message.photo[-1].file_id
    else:
        image_id = message.text.strip()
    content.save_content("start", {"text": text, "image_id": image_id})
    await repositories.log_admin_action(message.from_user.id, "update_content", "start")
    await backup_and_send(message.bot, load_settings().database_url)
    await message.answer("Стартовый экран обновлён")
    await state.clear()
