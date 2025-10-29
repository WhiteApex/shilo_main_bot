from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo


def now_tz(timezone: str) -> dt.datetime:
    return dt.datetime.now(ZoneInfo(timezone))


def to_timezone(value: dt.datetime, timezone: str) -> dt.datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(ZoneInfo(timezone))


def reminder_times(event_date: dt.datetime, timezone: str) -> list[tuple[dt.datetime, str]]:
    tz_event = to_timezone(event_date, timezone)
    schedule = [
        (tz_event - dt.timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0),
        (tz_event - dt.timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0),
        tz_event.replace(hour=9, minute=0, second=0, microsecond=0),
    ]
    labels = ["reminder_3d_sent", "reminder_1d_sent", "reminder_day_sent"]
    return list(zip(schedule, labels, strict=False))
