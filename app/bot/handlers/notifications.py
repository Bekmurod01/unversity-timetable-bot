import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_menu_keyboard, reminder_settings_inline_keyboard
from app.bot.states import SettingsFSM
from app.db import SessionLocal
from app.services.timetable_service import TimetableService

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.regexp(r"(Notifications|Enable Notifications)$"))
async def notifications_menu(message: Message) -> None:
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await message.answer("Please register with /start first.")
            return

        selected = user.lesson_reminder_minutes if user.lesson_reminder_enabled else None
        status = "Enabled" if user.lesson_reminder_enabled else "Disabled"
        await message.answer(
            "🔔 Reminder Settings\n\n"
            "Choose when to receive lesson reminders:\n"
            f"Current: {status}" + (f" ({user.lesson_reminder_minutes} min before)" if user.lesson_reminder_enabled else ""),
            reply_markup=reminder_settings_inline_keyboard(selected_minutes=selected),
        )


@router.callback_query(F.data.startswith("reminder:"))
async def reminder_callbacks(callback: CallbackQuery, state: FSMContext) -> None:
    logger.info("notifications.callback user=%s data=%s", callback.from_user.id, callback.data)
    if not callback.message:
        await callback.answer()
        return

    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(callback.from_user.id)
        if not user:
            await callback.answer("Please register first.", show_alert=True)
            return

        data = callback.data or ""

        if data.startswith("reminder:set:"):
            try:
                minutes = int(data.split(":")[-1])
            except ValueError:
                await callback.answer("Invalid reminder value.")
                return
            await service.set_lesson_reminder_settings(user, enabled=True, minutes=minutes)
            await callback.message.edit_text(
                "🔔 Reminder Settings\n\n"
                f"Saved: reminders are ON, {minutes} minutes before lesson.",
                reply_markup=reminder_settings_inline_keyboard(selected_minutes=minutes),
            )
            await callback.answer("Saved")
            return

        if data == "reminder:custom":
            await state.set_state(SettingsFSM.waiting_reminder_minutes)
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Enter reminder time in minutes:\nExample: 20")
            await callback.answer()
            return

        if data == "reminder:disable":
            await service.set_lesson_reminder_settings(user, enabled=False, minutes=user.lesson_reminder_minutes)
            await callback.message.edit_text(
                "🔔 Reminder Settings\n\nLesson reminders are disabled.",
                reply_markup=reminder_settings_inline_keyboard(selected_minutes=None),
            )
            await callback.answer("Disabled")
            return

        if data == "reminder:back":
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Back", reply_markup=main_menu_keyboard())
            await callback.answer()
            return

        if data == "reminder:home":
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Main menu", reply_markup=main_menu_keyboard())
            await callback.answer()
            return

    await callback.answer()


@router.message(SettingsFSM.waiting_reminder_minutes)
async def set_custom_reminder_minutes(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Please enter a whole number in minutes. Example: 20")
        return

    minutes = int(text)
    if minutes < 1 or minutes > 720:
        await message.answer("Please enter a value between 1 and 720 minutes.")
        return

    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await state.clear()
            await message.answer("Please register with /start first.")
            return

        await service.set_lesson_reminder_settings(user, enabled=True, minutes=minutes)

    await state.clear()
    await message.answer(
        f"Saved: you will be reminded {minutes} minutes before every lesson.",
        reply_markup=reminder_settings_inline_keyboard(selected_minutes=minutes),
    )
