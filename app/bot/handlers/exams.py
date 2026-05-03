from datetime import datetime

from aiogram import F, Router
from aiogram.types import Message

from app.db import SessionLocal
from app.services.timetable_service import TimetableService

router = Router()


@router.message(F.text == "\U0001F4CA Exams / Deadlines")
async def exams_deadlines(message: Message) -> None:
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await message.answer("Please register with /start first.")
            return

        rows = await service.list_exam_deadlines_for_user(user)
        lessons = await service.get_timetable_for_user(user)

    if not rows:
        if not lessons:
            await message.answer("No upcoming exams/deadlines yet.")
            return

        weekday_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_to_idx = {d: i for i, d in enumerate(weekday_order)}
        now = datetime.now()
        today_idx = now.weekday()

        def sort_key(lesson):
            lesson_idx = day_to_idx.get((lesson.day or "").lower(), 7)
            delta = (lesson_idx - today_idx) % 7
            is_past_today = delta == 0 and lesson.start_time <= now.time()
            if is_past_today:
                delta = 7
            return (delta, lesson.start_time)

        upcoming = sorted(lessons, key=sort_key)[:8]
        text = ["No upcoming exams/deadlines yet.", "", "Nearest classes:"]
        for item in upcoming:
            text.append(
                f"{item.day.title()} {item.start_time.strftime('%H:%M')} | "
                f"{item.subject} | {item.room} | {item.teacher}"
            )
        await message.answer("\n".join(text))
        return

    text = ["Upcoming exams / deadlines:"]
    for item in rows[:20]:
        text.append(f"{item.due_date.strftime('%Y-%m-%d %H:%M')} | {item.subject} | {item.type.upper()} | {item.title}")
    await message.answer("\n".join(text))
