from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import load_settings
from app.services.backups import backup_and_send
from app.services.export import export_subscriptions_csv
from app.services.reminders import process_reminders


def setup_scheduler(bot) -> AsyncIOScheduler:
    settings = load_settings()
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    scheduler.add_job(process_reminders, "cron", minute="*/15", args=[bot], id="reminders")
    scheduler.add_job(
        export_subscriptions_csv,
        "cron",
        hour=20,
        minute=0,
        args=[bot, settings.super_admin_id],
        id="daily-export",
    )
    scheduler.add_job(
        backup_and_send,
        "cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        args=[bot, settings.database_url],
        id="weekly-backup",
    )
    return scheduler
