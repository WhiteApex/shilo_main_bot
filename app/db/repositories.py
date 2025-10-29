from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import NoResultFound

from app.db.base import session_factory
from app.db.models import Event, Log, Metric, Subscription, User


@dataclass
class ReminderItem:
    subscription_id: int
    event_id: int
    user_id: int
    telegram_id: int
    event_title: str
    event_date: dt.datetime
    reminder_3d_sent: bool
    reminder_1d_sent: bool
    reminder_day_sent: bool


async def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    start_payload: Optional[str] = None,
    utm: Optional[dict[str, Optional[str]]] = None,
) -> User:
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return user

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            start_payload=start_payload,
        )
        if utm:
            user.utm_source = utm.get("utm_source")
            user.utm_medium = utm.get("utm_medium")
            user.utm_campaign = utm.get("utm_campaign")
            user.utm_content = utm.get("utm_content")
            user.utm_term = utm.get("utm_term")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def update_user_contacts(user_id: int, phone: Optional[str], email: Optional[str]) -> None:
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return
        user.phone = phone or user.phone
        user.email = email or user.email
        await session.commit()


async def get_active_events() -> list[Event]:
    async with session_factory() as session:
        result = await session.execute(
            select(Event).where(Event.status == "active").order_by(Event.date.asc())
        )
        return list(result.scalars().all())


async def get_all_events() -> list[Event]:
    async with session_factory() as session:
        result = await session.execute(select(Event).order_by(Event.date.desc()))
        return list(result.scalars().all())


async def get_event(event_id: int) -> Event:
    async with session_factory() as session:
        result = await session.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise NoResultFound
        return event


async def create_event(**data) -> Event:
    async with session_factory() as session:
        event = Event(**data)
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event


async def update_event(event_id: int, **data) -> Event:
    async with session_factory() as session:
        result = await session.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one()
        for key, value in data.items():
            setattr(event, key, value)
        await session.commit()
        await session.refresh(event)
        return event


async def delete_event(event_id: int) -> None:
    async with session_factory() as session:
        result = await session.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one()
        await session.delete(event)
        await session.commit()


async def create_subscription(
    user_id: int,
    event_id: int,
    full_name: str,
    phone: str,
    email: str,
) -> Subscription:
    async with session_factory() as session:
        existing = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id, Subscription.event_id == event_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("already_subscribed")
        event = await session.get(Event, event_id)
        if not event:
            raise ValueError("event_not_found")
        if event.subscribed_count >= event.limit:
            raise ValueError("limit_reached")
        subscription = Subscription(
            user_id=user_id,
            event_id=event_id,
            full_name=full_name,
            phone=phone,
            email=email,
        )
        session.add(subscription)
        event.subscribed_count += 1
        await session.commit()
        await session.refresh(subscription)
        return subscription


async def get_subscription_by_telegram(telegram_id: int, event_id: int) -> Subscription | None:
    async with session_factory() as session:
        stmt = (
            select(Subscription)
            .join(User, Subscription.user_id == User.id)
            .where(User.telegram_id == telegram_id, Subscription.event_id == event_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def subscriptions_for_reminders(now: dt.datetime) -> list[ReminderItem]:
    async with session_factory() as session:
        stmt = (
            select(
                Subscription.id,
                Subscription.event_id,
                Subscription.user_id,
                Subscription.reminder_3d_sent,
                Subscription.reminder_1d_sent,
                Subscription.reminder_day_sent,
                Event.title,
                Event.date,
                User.telegram_id,
            )
            .join(Event, Subscription.event_id == Event.id)
            .join(User, Subscription.user_id == User.id)
            .where(Event.status == "active")
            .where(Event.date >= now)
        )
        result = await session.execute(stmt)
        rows = result.all()
        return [
            ReminderItem(
                subscription_id=row.id,
                event_id=row.event_id,
                user_id=row.user_id,
                telegram_id=row.telegram_id,
                event_title=row.title,
                event_date=row.date,
                reminder_3d_sent=row.reminder_3d_sent,
                reminder_1d_sent=row.reminder_1d_sent,
                reminder_day_sent=row.reminder_day_sent,
            )
            for row in rows
        ]


async def set_subscription_flag(subscription_id: int, flag: str) -> None:
    async with session_factory() as session:
        await session.execute(
            update(Subscription)
            .where(Subscription.id == subscription_id)
            .values({flag: True})
        )
        await session.commit()


async def log_admin_action(admin_id: int, action: str, details: Optional[str] = None) -> None:
    async with session_factory() as session:
        session.add(Log(admin_id=admin_id, action=action, details=details))
        await session.commit()


async def get_metrics_summary() -> dict[str, int]:
    async with session_factory() as session:
        stmt = select(Metric.metric_type, func.count(Metric.id)).group_by(Metric.metric_type)
        result = await session.execute(stmt)
        return {metric: count for metric, count in result.all()}
