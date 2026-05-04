import logging
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import faculty_keyboard, group_selection_keyboard, main_menu_keyboard, year_keyboard, yes_no_keyboard
from app.bot.states import RegistrationFSM
from app.db import SessionLocal
from app.services.timetable_service import TimetableService

router = Router()

GROUP_SUGGESTIONS = ["IT-202", "IT-201", "ACCA-201", "FIN-102", "BUS-301"]


async def _ask_year_step(message: Message, state: FSMContext, group_name: str) -> None:
    await state.update_data(group_name=group_name)
    await state.set_state(RegistrationFSM.year)
    await message.answer(f"✅ Group selected: {group_name}")
    await message.answer("🎓 Select your year of study:", reply_markup=year_keyboard())


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    logging.info(
        "/start handler triggered: user_id=%s chat_id=%s text=%r",
        message.from_user.id if message.from_user else None,
        message.chat.id if message.chat else None,
        message.text,
    )
    try:
        await state.clear()
    except Exception:
        logging.exception("Failed to clear FSM state during /start for user=%s", message.from_user.id if message.from_user else None)
    try:
        try:
            async with SessionLocal() as db:
                service = TimetableService(db)
                user = await service.get_user(message.from_user.id)
        except Exception:
            logging.exception("Failed to load user during /start for user=%s", message.from_user.id)
            await message.answer(
                "⚠️ Temporary server issue. Please try again in a moment."
            )
            return

        if user:
            await message.answer(
                f"👋 Welcome back, {user.full_name}!\n\n"
                f"Current profile:\n"
                f"🏢 Faculty: {user.faculty}\n"
                f"🎓 Year: {user.year}\n"
                f"👥 Group: {user.group_name}\n\n"
                "You can update your profile in the ⚙️ Settings menu.",
                reply_markup=main_menu_keyboard(),
            )
            return

        await state.set_state(RegistrationFSM.full_name)
        await message.answer("👋 Hello! Let's register your profile.\n\n👤 Enter your full name:")
    except Exception:
        logging.exception("Unexpected error inside /start handler for user=%s", message.from_user.id if message.from_user else None)
        await message.answer("⚠️ Something went wrong while processing /start. Please try again.")


@router.message(F.text == "/start")
async def start_text_fallback(message: Message, state: FSMContext) -> None:
    logging.info("Raw text /start fallback triggered for user=%s", message.from_user.id if message.from_user else None)
    await start_command(message, state)


@router.message(Command("ping"))
async def ping_command(message: Message) -> None:
    await message.answer("pong")


@router.message(RegistrationFSM.full_name)
async def collect_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 3:
        await message.answer("Please enter a valid full name.")
        return
    await state.update_data(full_name=name)
    await state.set_state(RegistrationFSM.faculty)
    async with SessionLocal() as db:
        service = TimetableService(db)
        faculties = await service.get_available_faculties()
    logging.info("Loaded faculties for registration: %s", faculties)
    if not faculties:
        await message.answer("No faculties are available right now. Please try again later.")
        return
    await message.answer("🏢 Choose your faculty:", reply_markup=faculty_keyboard(faculties))


@router.message(RegistrationFSM.faculty)
async def collect_faculty_text_fallback(message: Message, state: FSMContext) -> None:
    await message.answer("Please use the buttons to select your faculty.")


@router.callback_query(RegistrationFSM.faculty, F.data.startswith("reg_faculty:"))
async def collect_faculty_callback(callback: CallbackQuery, state: FSMContext) -> None:
    logging.info("registration.callback user=%s data=%s", callback.from_user.id, callback.data)
    faculty = callback.data.split(":", 1)[1]
    logging.info("User %s selected faculty via callback: %s", callback.from_user.id, faculty)
    await state.update_data(faculty=faculty)

    async with SessionLocal() as db:
        service = TimetableService(db)
        groups, total = await service.get_groups_by_faculty(faculty, page=1)
    logging.info("Groups loaded for faculty %s: total=%s groups_sample=%s", faculty, total, groups[:10])

    await state.set_state(RegistrationFSM.group_name)
    if groups:
        await callback.message.edit_text(
            f"🏢 Faculty: {faculty}\n\n👥 Select your group:",
            reply_markup=group_selection_keyboard(groups, faculty, page=1, total=total),
        )
    else:
        suggestions = ", ".join(GROUP_SUGGESTIONS)
        await callback.message.edit_text(
            f"🏢 Faculty: {faculty}\n\n"
            "👥 No groups were found in current data.\n"
            "Please type your group manually (example: IT-202).\n\n"
            f"Suggestions: {suggestions}"
        )
    await callback.answer()


@router.callback_query(RegistrationFSM.group_name, F.data.startswith("reg_group_page:"))
async def collect_group_pagination(callback: CallbackQuery, state: FSMContext) -> None:
    logging.info("registration.callback user=%s data=%s", callback.from_user.id, callback.data)
    parts = callback.data.split(":")
    faculty = parts[1]
    page = int(parts[2])
    logging.info("Pagination callback for faculty=%s page=%s user=%s", faculty, page, callback.from_user.id)

    async with SessionLocal() as db:
        service = TimetableService(db)
        groups, total = await service.get_groups_by_faculty(faculty, page=page)
    logging.info("Loaded groups page %s for %s: %s", page, faculty, groups)

    await callback.message.edit_reply_markup(reply_markup=group_selection_keyboard(groups, faculty, page=page, total=total))
    await callback.answer()


@router.callback_query(RegistrationFSM.group_name, F.data.startswith("reg_group:"))
async def collect_group_callback(callback: CallbackQuery, state: FSMContext) -> None:
    logging.info("registration.callback user=%s data=%s", callback.from_user.id, callback.data)
    group_name = callback.data.split(":", 1)[1]
    await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_year_step(callback.message, state, group_name)
    await callback.answer()


@router.message(RegistrationFSM.year)
async def collect_year(message: Message, state: FSMContext) -> None:
    if not (message.text or "").isdigit():
        await message.answer("Please select a numeric year from buttons.")
        return
    await state.update_data(year=int(message.text))

    data = await state.get_data()
    summary = (
        "📝 Please confirm your details:\n\n"
        f"👤 Name: {data['full_name']}\n"
        f"🏢 Faculty: {data['faculty']}\n"
        f"👥 Group: {data['group_name']}\n"
        f"🎓 Year: {data['year']}\n"
    )

    await state.set_state(RegistrationFSM.confirmation)
    await message.answer(summary, reply_markup=yes_no_keyboard())


@router.message(RegistrationFSM.group_name)
async def collect_group_text_fallback(message: Message, state: FSMContext) -> None:
    group_name = (message.text or "").strip().upper()
    if len(group_name) < 2:
        await message.answer("Please enter a valid group (example: IT-202).")
        return
    await _ask_year_step(message, state, group_name)


@router.message(RegistrationFSM.confirmation)
async def confirm_registration(message: Message, state: FSMContext) -> None:
    if message.text == "✏️ Edit":
        await state.set_state(RegistrationFSM.full_name)
        await message.answer("👤 Enter full name again:")
        return

    if message.text != "✅ Confirm":
        await message.answer("Please use the buttons: Confirm or Edit.")
        return

    data = await state.get_data()
    async with SessionLocal() as db:
        service = TimetableService(db)
        await service.upsert_user(
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            faculty=data["faculty"],
            group_name=data["group_name"],
            year=data["year"],
        )

    await state.clear()
    await message.answer("✅ Registration complete! Welcome to the University Timetable Bot.", reply_markup=main_menu_keyboard())


@router.message(F.text.func(lambda t: bool(t) and "Favorites" in t))
async def favorites_entry(message: Message) -> None:
    await message.answer("Open 👨‍🏫 Teacher Timetable → ⭐ Favorite Teachers to manage favorites.")


@router.message(F.text.func(lambda t: bool(t) and "Help" in t))
async def help_entry(message: Message) -> None:
    await message.answer(
        "ℹ️ Help\n\n"
        "Use /start to register.\n"
        "Use 📅 My Timetable for daily/weekly schedule.\n"
        "Use 👨‍🏫 Teacher Timetable to search teachers and favorites.\n"
        "Use 🔔 Notifications to set reminders."
    )


@router.message(F.text.func(lambda t: bool(t) and "Announcements" in t))
async def announcements_entry(message: Message) -> None:
    await message.answer("📢 Announcements are managed by admins and will appear here.")


@router.message(F.text == "🏠 Main Menu")
async def home_entry(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Main menu", reply_markup=main_menu_keyboard())
