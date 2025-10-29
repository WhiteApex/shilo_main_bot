from __future__ import annotations

import datetime as dt
from typing import Optional

from dateutil.parser import parse
from sqlalchemy.exc import NoResultFound
from zoneinfo import ZoneInfo

from app.config import load_settings
from app.db import repositories
from app.db.models import Event
from app.utils.time import to_timezone


async def list_active_events() -> list[Event]:
    return await repositories.get_active_events()


async def get_event(event_id: int) -> Event:
    event = await repositories.get_event(event_id)
    now = dt.datetime.now(dt.timezone.utc)
    if event.date < now and event.status == "active":
        event = await repositories.update_event(event_id, status="archive")
    return event


async def create_event(
    title: str,
    teaser: str,
    description: str,
    date_text: str,
    image_id: str,
    limit: int = 200,
    status: str = "active",
) -> Event:
    tz = ZoneInfo(load_settings().timezone)
    date = parse(date_text)
    if date.tzinfo is None:
        date = date.replace(tzinfo=tz)
    date = date.astimezone(dt.timezone.utc)
    return await repositories.create_event(
        title=title,
        teaser=teaser,
        description=description,
        date=date,
        image_id=image_id,
        limit=limit,
        status=status,
    )


async def update_event(
    event_id: int,
    *,
    title: Optional[str] = None,
    teaser: Optional[str] = None,
    description: Optional[str] = None,
    date_text: Optional[str] = None,
    image_id: Optional[str] = None,
    limit: Optional[int] = None,
    status: Optional[str] = None,
    report_media_id: Optional[str] = None,
) -> Event:
    data: dict[str, object] = {}
    if title is not None:
        data["title"] = title
    if teaser is not None:
        data["teaser"] = teaser
    if description is not None:
        data["description"] = description
    if date_text is not None:
        tz = ZoneInfo(load_settings().timezone)
        date = parse(date_text)
        if date.tzinfo is None:
            date = date.replace(tzinfo=tz)
        data["date"] = date.astimezone(dt.timezone.utc)
    if image_id is not None:
        data["image_id"] = image_id
    if limit is not None:
        data["limit"] = limit
    if status is not None:
        data["status"] = status
    if report_media_id is not None:
        data["report_media_id"] = report_media_id
    if not data:
        raise ValueError("No data provided for update")
    return await repositories.update_event(event_id, **data)


async def delete_event(event_id: int) -> None:
    await repositories.delete_event(event_id)


async def format_event_card(event: Event, timezone: str) -> str:
    date_local = to_timezone(event.date, timezone)
    return (
        f"<b>{event.title}</b>\n"
        f"{event.teaser}\n\n"
        f"{event.description}\n\n"
        f"🗓 {date_local.strftime('%d.%m.%Y %H:%M (%Z)')}"
    )


async def ensure_event(event_id: int) -> Event:
    try:
        return await get_event(event_id)
    except NoResultFound as exc:
        raise ValueError("Событие не найдено") from exc
