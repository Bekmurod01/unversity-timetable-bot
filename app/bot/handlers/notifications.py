from aiogram import F, Router
from aiogram.types import Message

from app.bot.keyboards import notification_keyboard
from app.db import SessionLocal
from app.services.timetable_service import TimetableService

router = Router()


@router.message(F.text == "🔔 Notifications")
async def notifications_menu(message: Message) -> None:
    await message.answer("Manage notifications:", reply_markup=notification_keyboard())


@router.message(F.text.in_({"Toggle ON/OFF", "Only changes", "Daily reminders", "Exam alerts"}))
async def toggle_notifications(message: Message) -> None:
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await message.answer("Please register with /start first.")
            return

        if message.text == "Toggle ON/OFF":
            user.notifications_enabled = not user.notifications_enabled
        elif message.text == "Only changes":
            user.notify_changes_only = not user.notify_changes_only
        elif message.text == "Daily reminders":
            user.notify_daily_reminders = not user.notify_daily_reminders
        elif message.text == "Exam alerts":
            user.notify_exam_alerts = not user.notify_exam_alerts

        await db.commit()
        await message.answer(
            "Updated:\n"
            f"Notifications: {user.notifications_enabled}\n"
            f"Only changes: {user.notify_changes_only}\n"
            f"Daily reminders: {user.notify_daily_reminders}\n"
            f"Exam alerts: {user.notify_exam_alerts}"
        )
