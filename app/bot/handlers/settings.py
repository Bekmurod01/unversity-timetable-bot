from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    faculty_keyboard, 
    group_selection_keyboard, 
    settings_keyboard, 
    year_keyboard
)
from app.bot.states import SettingsFSM
from app.db import SessionLocal
from app.services.timetable_service import TimetableService

router = Router()


@router.message(F.text == "⚙️ Settings")
async def settings_menu(message: Message) -> None:
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)

    if user:
        await message.answer(
            f"⚙️ Profile Settings:\n\n"
            f"👤 Name: {user.full_name}\n"
            f"🏢 Faculty: {user.faculty}\n"
            f"🎓 Year: {user.year}\n"
            f"👥 Group: {user.group_name}",
            reply_markup=settings_keyboard(),
        )
        return

    await message.answer("Settings:", reply_markup=settings_keyboard())


@router.message(F.text == "Reset profile")
async def reset_profile(message: Message) -> None:
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await message.answer("No profile found.")
            return

        await db.delete(user)
        await db.commit()

    await message.answer("Profile reset. Use /start to register again.")


@router.message(F.text == "Change name")
async def change_name_start(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsFSM.waiting_name)
    await message.answer("👤 Enter your new full name:")


@router.message(SettingsFSM.waiting_name)
async def change_name_apply(message: Message, state: FSMContext) -> None:
    new_name = message.text.strip()
    if len(new_name) < 3:
        await message.answer("Please enter a valid full name.")
        return
        
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await state.clear()
            await message.answer("No profile found. Use /start first.")
            return
        user.full_name = new_name
        await db.commit()

    await state.clear()
    await message.answer(f"✅ Name updated to {new_name}.", reply_markup=settings_keyboard())


@router.message(F.text == "Change group")
async def change_group_start(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsFSM.waiting_faculty)
    async with SessionLocal() as db:
        service = TimetableService(db)
        faculties = await service.get_available_faculties()
    await message.answer("🏢 Choose your faculty first:", reply_markup=faculty_keyboard(faculties, prefix="set_faculty"))


@router.callback_query(SettingsFSM.waiting_faculty, F.data.startswith("set_faculty:"))
async def change_faculty_for_group(callback: CallbackQuery, state: FSMContext) -> None:
    faculty = callback.data.split(":")[1]
    async with SessionLocal() as db:
        service = TimetableService(db)
        groups, total = await service.get_groups_by_faculty(faculty, page=1)
    
    await state.set_state(SettingsFSM.waiting_group)
    await callback.message.edit_text(
        f"🏢 Faculty: {faculty}\n\n👥 Select your new group:",
        reply_markup=group_selection_keyboard(groups, faculty, page=1, total=total, callback_prefix="set_group_page", select_prefix="set_group")
    )
    await callback.answer()


@router.callback_query(SettingsFSM.waiting_group, F.data.startswith("set_group_page:"))
async def change_group_pagination(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    faculty = parts[1]
    page = int(parts[2])
    
    async with SessionLocal() as db:
        service = TimetableService(db)
        groups, total = await service.get_groups_by_faculty(faculty, page=page)
    
    await callback.message.edit_reply_markup(
        reply_markup=group_selection_keyboard(groups, faculty, page=page, total=total, callback_prefix="set_group_page", select_prefix="set_group")
    )
    await callback.answer()


@router.callback_query(SettingsFSM.waiting_group, F.data.startswith("set_group:"))
async def change_group_apply(callback: CallbackQuery, state: FSMContext) -> None:
    group_name = callback.data.split(":")[1]
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(callback.from_user.id)
        if not user:
            await state.clear()
            await callback.message.answer("No profile found. Use /start first.")
            return
        user.group_name = group_name
        # Also update faculty based on group if needed, but here we explicitly chose faculty
        # Let's update user faculty too for consistency
        user.faculty = group_name.split("-")[0] 
        await db.commit()

    await state.clear()
    await callback.message.edit_text(f"✅ Group updated to {group_name}.")
    await callback.message.answer("⚙️ Settings updated.", reply_markup=settings_keyboard())
    await callback.answer()


@router.message(F.text == "Change faculty")
async def change_faculty_standalone(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsFSM.waiting_faculty)
    async with SessionLocal() as db:
        service = TimetableService(db)
        faculties = await service.get_available_faculties()
    # Using a different prefix or logic if we just want to change faculty without group?
    # Usually group implies faculty. Let's just reuse the flow but stop at faculty if needed?
    # The request said "Change group option in settings".
    await message.answer("🏢 Choose your new faculty:", reply_markup=faculty_keyboard(faculties, prefix="set_fac_only"))


@router.callback_query(SettingsFSM.waiting_faculty, F.data.startswith("set_fac_only:"))
async def change_faculty_apply(callback: CallbackQuery, state: FSMContext) -> None:
    faculty = callback.data.split(":")[1]
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(callback.from_user.id)
        if not user:
            await state.clear()
            await callback.answer("No profile found.")
            return
        user.faculty = faculty
        await db.commit()
    
    await state.clear()
    await callback.message.edit_text(f"✅ Faculty updated to {faculty}.")
    await callback.message.answer("⚙️ Settings updated.", reply_markup=settings_keyboard())
    await callback.answer()


@router.message(F.text == "Change year")
async def change_year_start(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsFSM.waiting_year)
    await message.answer("🎓 Select your year of study:", reply_markup=year_keyboard())


@router.message(SettingsFSM.waiting_year)
async def change_year_apply(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("Please choose a numeric year from buttons.")
        return

    year = int(message.text)
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await state.clear()
            await message.answer("No profile found. Use /start first.")
            return
        user.year = year
        await db.commit()

    await state.clear()
    await message.answer(f"✅ Year updated to {year}.", reply_markup=settings_keyboard())


@router.message(F.text == "Change language")
async def change_language(message: Message) -> None:
    await message.answer("🌐 Language module is future-ready and will be enabled in next version.")
