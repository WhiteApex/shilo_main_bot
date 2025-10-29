from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.config import load_settings

ADMINS_FILE = Path("data/admins.json")


def _load_file_ids() -> set[int]:
    if not ADMINS_FILE.exists():
        return set()
    data = json.loads(ADMINS_FILE.read_text(encoding="utf-8"))
    return {int(item) for item in data}


def _save_file_ids(ids: Iterable[int]) -> None:
    ADMINS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADMINS_FILE.write_text(
        json.dumps(sorted({int(i) for i in ids})),
        encoding="utf-8",
    )


def get_admin_ids() -> set[int]:
    settings = load_settings()
    base = set(settings.admin_ids)
    base.add(settings.super_admin_id)
    file_ids = _load_file_ids()
    return base.union(file_ids)


def add_admin(admin_id: int) -> None:
    current = _load_file_ids()
    current.add(admin_id)
    _save_file_ids(current)


def remove_admin(admin_id: int) -> None:
    current = _load_file_ids()
    current.discard(admin_id)
    _save_file_ids(current)
