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


@router.message(F.text.regexp(r"(🔔\s*Notifications|Notifications|Enable\s*Notifications)$"))
async def notifications_menu(message: Message) -> None:
    logger.info("notifications_menu opened by user=%s", message.from_user.id)
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            logger.warning("notifications_menu: user not found user=%s", message.from_user.id)
            await message.answer("Please register with /start first.")
            return

        selected = user.lesson_reminder_minutes if user.lesson_reminder_enabled else None
        status = "Enabled" if user.lesson_reminder_enabled else "Disabled"
        current_display = f" ({user.lesson_reminder_minutes} min before)" if user.lesson_reminder_enabled else ""
        
        logger.info(
            "notifications_menu displayed user=%s enabled=%s minutes=%s",
            message.from_user.id,
            user.lesson_reminder_enabled,
            user.lesson_reminder_minutes
        )
        
        await message.answer(
            "🔔 Reminder Settings\n\n"
            "Choose when to receive lesson reminders:\n"
            f"Current: {status}{current_display}",
            reply_markup=reminder_settings_inline_keyboard(selected_minutes=selected),
        )


@router.callback_query(F.data.startswith("reminder:"))
async def reminder_callbacks(callback: CallbackQuery, state: FSMContext) -> None:
    logger.info("reminder_callback received user=%s data=%s", callback.from_user.id, callback.data)
    
    if not callback.message:
        logger.warning("reminder_callback: no message user=%s", callback.from_user.id)
        await callback.answer("Message not found.", show_alert=True)
        return

    try:
        async with SessionLocal() as db:
            service = TimetableService(db)
            user = await service.get_user(callback.from_user.id)
            if not user:
                logger.warning("reminder_callback: user not found user=%s data=%s", callback.from_user.id, callback.data)
                await callback.answer("Please register first.", show_alert=True)
                return

            data = callback.data or ""

            # Handle reminder time selection (e.g., reminder:set:5)
            if data.startswith("reminder:set:"):
                try:
                    minutes = int(data.split(":")[-1])
                except ValueError:
                    logger.error("reminder_callback: invalid minutes value user=%s data=%s", callback.from_user.id, data)
                    await callback.answer("Invalid reminder value.")
                    return
                
                logger.info(
                    "reminder_callback: setting reminder user=%s minutes=%s enabled=True",
                    callback.from_user.id,
                    minutes
                )
                await service.set_lesson_reminder_settings(user, enabled=True, minutes=minutes)
                
                await callback.message.edit_text(
                    "🔔 Reminder Settings\n\n"
                    f"Saved: reminders are ON, {minutes} minutes before lesson.",
                    reply_markup=reminder_settings_inline_keyboard(selected_minutes=minutes),
                )
                await callback.answer(f"✅ Reminder set to {minutes} minutes")
                return

            # Handle custom reminder input
            if data == "reminder:custom":
                logger.info("reminder_callback: entering custom reminder state user=%s", callback.from_user.id)
                await state.set_state(SettingsFSM.waiting_reminder_minutes)
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer("Enter reminder time in minutes:\nExample: 20")
                await callback.answer()
                return

            # Handle disable notifications
            if data == "reminder:disable":
                logger.info(
                    "reminder_callback: disabling notifications user=%s",
                    callback.from_user.id
                )
                await service.set_lesson_reminder_settings(user, enabled=False, minutes=user.lesson_reminder_minutes)
                
                await callback.message.edit_text(
                    "🔔 Reminder Settings\n\nLesson reminders are disabled.",
                    reply_markup=reminder_settings_inline_keyboard(selected_minutes=None),
                )
                await callback.answer("✅ Notifications disabled")
                return

            # Handle back navigation
            if data == "reminder:back":
                logger.info("reminder_callback: back to main menu user=%s", callback.from_user.id)
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer("Back", reply_markup=main_menu_keyboard())
                await callback.answer()
                return

            # Handle home navigation
            if data == "reminder:home":
                logger.info("reminder_callback: home btn user=%s", callback.from_user.id)
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer("Main menu", reply_markup=main_menu_keyboard())
                await callback.answer()
                return

            logger.warning("reminder_callback: unknown action user=%s data=%s", callback.from_user.id, data)
            await callback.answer()

    except Exception as e:
        logger.exception("reminder_callback failed user=%s data=%s error=%s", callback.from_user.id, callback.data, str(e))
        await callback.answer("Action failed. Please try again.", show_alert=True)


@router.message(SettingsFSM.waiting_reminder_minutes)
async def set_custom_reminder_minutes(message: Message, state: FSMContext) -> None:
    logger.info("custom_reminder_input received user=%s text=%s", message.from_user.id, message.text)
    text = (message.text or "").strip()
    if not text.isdigit():
        logger.warning("custom_reminder_input: invalid input (not digit) user=%s text=%s", message.from_user.id, text)
        await message.answer("Please enter a whole number in minutes. Example: 20")
        return

    minutes = int(text)
    if minutes < 1 or minutes > 720:
        logger.warning("custom_reminder_input: out of range user=%s minutes=%s", message.from_user.id, minutes)
        await message.answer("Please enter a value between 1 and 720 minutes.")
        return

    try:
        async with SessionLocal() as db:
            service = TimetableService(db)
            user = await service.get_user(message.from_user.id)
            if not user:
                logger.warning("custom_reminder_input: user not found user=%s", message.from_user.id)
                await state.clear()
                await message.answer("Please register with /start first.")
                return

            logger.info(
                "custom_reminder_input: saving user=%s minutes=%s enabled=True",
                message.from_user.id,
                minutes
            )
            await service.set_lesson_reminder_settings(user, enabled=True, minutes=minutes)

        await state.clear()
        await message.answer(
            f"✅ Saved: you will be reminded {minutes} minutes before every lesson.",
            reply_markup=reminder_settings_inline_keyboard(selected_minutes=minutes),
        )
    except Exception as e:
        logger.exception(
            "custom_reminder_input failed user=%s minutes=%s error=%s",
            message.from_user.id,
            minutes,
            str(e)
        )
        await state.clear()
        await message.answer("Failed to save reminder settings. Please try again.")
