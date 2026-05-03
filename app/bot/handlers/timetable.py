from datetime import datetime, timedelta

from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import day_picker_keyboard, main_menu_keyboard, timetable_mode_keyboard
from app.bot.states import NavigationFSM
from app.db import SessionLocal
from app.services.timetable_service import TimetableService

router = Router()


def _format_lessons(title: str, lessons: list, show_group: bool = False) -> str:
    if not lessons:
        return f"{title}\nNo lessons found."

    rows = [title]
    for lesson in lessons:
        status_icon = "✅" if lesson.status == "active" else "❌" if lesson.status == "cancelled" else "🔄"
        group_suffix = f" | {lesson.group_name}" if show_group else ""
        rows.append(
            f"{status_icon} {lesson.start_time.strftime('%H:%M')}-{lesson.end_time.strftime('%H:%M')} | "
            f"{lesson.subject} | {lesson.room} | {lesson.teacher}{group_suffix}"
        )
    return "\n".join(rows)


@router.message(F.text.func(lambda t: bool(t) and "My Timetable" in t))
async def my_timetable_menu(message: Message, state: FSMContext) -> None:
    await state.set_state(NavigationFSM.timetable_menu)
    await message.answer("Choose timetable mode:", reply_markup=timetable_mode_keyboard())


@router.message(F.text.in_({"Today", "Tomorrow", "Weekly"}))
async def timetable_mode(message: Message, state: FSMContext) -> None:
    await state.set_state(NavigationFSM.timetable_menu)
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await message.answer("Use /start to register first.")
            return

        if message.text == "Weekly":
            lessons = await service.get_timetable_for_user(user)
            multiple_groups = len({x.group_name for x in lessons}) > 1
            await message.answer(
                _format_lessons(
                    f"Weekly schedule ({user.faculty} year {user.year}, group {user.group_name})",
                    lessons,
                    show_group=multiple_groups,
                ),
                reply_markup=timetable_mode_keyboard(),
            )
            return

        date = datetime.now()
        if message.text == "Tomorrow":
            date += timedelta(days=1)
        day = date.strftime("%A").lower()
        lessons = await service.get_timetable_for_user(user, day=day)
        await message.answer(_format_lessons(f"{message.text} ({day.title()})", lessons), reply_markup=timetable_mode_keyboard())


@router.message(F.text == "Custom Day")
async def custom_day(message: Message, state: FSMContext) -> None:
    await state.set_state(NavigationFSM.timetable_menu)
    await message.answer("Pick a day:", reply_markup=day_picker_keyboard())


@router.message(F.text.regexp(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$"))
async def custom_day_result(message: Message, state: FSMContext) -> None:
    await state.set_state(NavigationFSM.timetable_menu)
    day = message.text.lower()
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await message.answer("Use /start to register first.")
            return
        lessons = await service.get_timetable_for_user(user, day=day)
        await message.answer(_format_lessons(f"{message.text} timetable", lessons), reply_markup=timetable_mode_keyboard())


@router.message(NavigationFSM.timetable_menu, F.text == "⬅️ Back")
async def back_to_main(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Main menu", reply_markup=main_menu_keyboard())


@router.message(NavigationFSM.timetable_menu, F.text == "🏠 Main Menu")
async def main_menu_from_timetable(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Main menu", reply_markup=main_menu_keyboard())
