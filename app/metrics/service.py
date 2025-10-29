from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import select

from app.db.base import session_factory
from app.db.models import Metric


class MetricType:
    START = "start"
    CLICK = "click"
    SUBSCRIPTION = "subscription"
    DELIVERY = "delivery"
    READ = "read"


async def track(metric_type: str, user_id: Optional[int] = None, event_id: Optional[int] = None, payload: dict[str, Any] | None = None) -> None:
    async with session_factory() as session:
        session.add(
            Metric(
                metric_type=metric_type,
                user_id=user_id,
                event_id=event_id,
                payload=json.dumps(payload, ensure_ascii=False) if payload else None,
            )
        )
        await session.commit()


async def count_metric(metric_type: str) -> int:
    async with session_factory() as session:
        result = await session.execute(
            select(Metric).where(Metric.metric_type == metric_type)
        )
        return len(result.scalars().all())
