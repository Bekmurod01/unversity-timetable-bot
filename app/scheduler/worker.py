import asyncio
import logging
import selectors
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db import SessionLocal
from app.models import LessonReminderDispatch, TimetableLesson, User
from app.services.change_detector import detect_timetable_changes
from app.services.edupage_adapter import EduPageAdapter
from app.services.notification_service import NotificationService
from app.services.timetable_service import TimetableService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()
adapter = EduPageAdapter()
tz = ZoneInfo(settings.timezone)


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


def _format_lesson_reminder(subject: str, teacher: str, room: str, minutes: int) -> str:
    return (
        "🔔 Upcoming Lesson Reminder\n\n"
        f"📚 {subject}\n"
        f"👨‍🏫 {teacher}\n"
        f"🏫 {room}\n\n"
        f"⏰ Starts in {minutes} minutes"
    )


async def check_and_send_lesson_reminders() -> None:
    now = datetime.now(tz)
    today = now.date()
    day = now.strftime("%A").lower()
    window_end = now + timedelta(seconds=max(settings.polling_interval_seconds, 60))

    async with SessionLocal() as db:
        users = (
            await db.execute(
                select(User).where(
                    User.notifications_enabled.is_(True),
                    User.lesson_reminder_enabled.is_(True),
                    User.is_active.is_(True),
                )
            )
        ).scalars().all()

        if not users:
            return

        bot = Bot(token=settings.bot_token)
        service = TimetableService(db)

        try:
            for user in users:
                lessons = await service.get_timetable_for_user(user, day=day)
                if not lessons:
                    continue

                reminder_minutes = max(1, int(user.lesson_reminder_minutes))
                for lesson in lessons:
                    lesson_start = datetime.combine(today, lesson.start_time, tzinfo=tz)
                    reminder_at = lesson_start - timedelta(minutes=reminder_minutes)
                    if not (now <= reminder_at <= window_end):
                        continue

                    dispatch = LessonReminderDispatch(
                        user_id=user.id,
                        group_name=lesson.group_name,
                        day=today,
                        start_time=lesson.start_time,
                        reminder_minutes=reminder_minutes,
                    )
                    db.add(dispatch)
                    try:
                        await db.commit()
                    except IntegrityError:
                        await db.rollback()
                        continue

                    try:
                        await bot.send_message(
                            user.telegram_id,
                            _format_lesson_reminder(lesson.subject, lesson.teacher, lesson.room, reminder_minutes),
                        )
                    except Exception:
                        continue
        finally:
            await bot.session.close()


async def run_scheduler() -> None:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(check_and_notify_changes, "interval", seconds=settings.polling_interval_seconds)
    scheduler.add_job(check_and_send_lesson_reminders, "interval", seconds=60)
    scheduler.start()
    logger.info("Scheduler started")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.run(run_scheduler(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        asyncio.run(run_scheduler())
