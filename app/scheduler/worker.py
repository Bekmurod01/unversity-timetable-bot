import asyncio
import logging
import selectors
import sys
from datetime import datetime

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import TimetableLesson
from app.services.change_detector import detect_timetable_changes
from app.services.edupage_adapter import EduPageAdapter
from app.services.notification_service import NotificationService
from app.services.timetable_service import TimetableService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()
adapter = EduPageAdapter()


async def check_and_notify_changes() -> None:
    async with SessionLocal() as db:
        old_lessons_rows = list((await db.execute(select(TimetableLesson))).scalars().all())
        old_lessons = [
            {
                "group_name": x.group_name,
                "subject": x.subject,
                "teacher": x.teacher,
                "room": x.room,
                "day": x.day,
                "start_time": x.start_time.strftime("%H:%M"),
                "end_time": x.end_time.strftime("%H:%M"),
                "status": x.status,
            }
            for x in old_lessons_rows
        ]

        fresh_lessons = await adapter.fetch_timetable_snapshot()
        if not fresh_lessons:
            logger.info("No snapshot data loaded; skipping")
            return

        changes = detect_timetable_changes(old_lessons, fresh_lessons)
        service = TimetableService(db)
        await service.replace_timetable(fresh_lessons)

        bot = Bot(token=settings.bot_token)
        notifier = NotificationService(bot, db)

        for change in changes:
            await service.add_update_log(change.group_name, change.change_type, change.details)
            await notifier.notify_group(change.group_name, f"Schedule update for {change.group_name}:\n{change.details}")

        await bot.session.close()

        if changes:
            logger.info("Applied %s timetable changes", len(changes))
        else:
            logger.info("No timetable changes detected")


async def run_scheduler() -> None:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(check_and_notify_changes, "interval", seconds=settings.polling_interval_seconds)
    scheduler.start()
    logger.info("Scheduler started")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.run(run_scheduler(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        asyncio.run(run_scheduler())
