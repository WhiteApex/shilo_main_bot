from __future__ import annotations

from typing import Iterable

from aiogram.types import Message

from app.services.admins import get_admin_ids


def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()


def ensure_admin(message: Message) -> bool:
    if not message.from_user:
        return False
    return is_admin(message.from_user.id)
