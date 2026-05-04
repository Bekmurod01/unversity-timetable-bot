from datetime import datetime, timedelta

from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import day_picker_keyboard, main_menu_keyboard, timetable_mode_keyboard
from app.bot.states import NavigationFSM
from app.db import SessionLocal
from app.services.timetable_service import TimetableService
from app.services.date_utils import (
    day_name_to_next_date,
    format_date_with_day,
    group_lessons_by_date,
    get_current_date,
)

router = Router()


def _format_lesson_time(lesson) -> str:
    """Format lesson time with status icon and times."""
    status_icon = "✅" if lesson.status == "active" else "❌" if lesson.status == "cancelled" else "🔄"
    return f"{status_icon} ⏰ {lesson.start_time.strftime('%H:%M')}–{lesson.end_time.strftime('%H:%M')}"


def _format_lesson_details(lesson, show_group: bool = False) -> str:
    """Format lesson subject, room, and teacher."""
    group_suffix = f" | {lesson.group_name}" if show_group else ""
    return f"📚 {lesson.subject} | 🏫 {lesson.room} | 👨‍🏫 {lesson.teacher}{group_suffix}"


def _format_lessons(title: str, lessons: list, show_group: bool = False, group_by_date: bool = False) -> str:
    """
    Format lessons for display.
    
    Args:
        title: Header title
        lessons: List of TimetableLesson objects
        show_group: Include group name in output
        group_by_date: Group lessons by date with calendar dates
    """
    if not lessons:
        return f"{title}\nNo lessons found."

    rows = [title]
    
    if not group_by_date:
        # Original simple format (for custom day selection)
        for lesson in lessons:
            rows.append(f"{_format_lesson_time(lesson)} | {_format_lesson_details(lesson, show_group)}")
        return "\n".join(rows)
    
    # New grouped format with dates
    grouped = group_lessons_by_date(lessons, use_next_date=True)
    
    for date, date_lessons in grouped.items():
        rows.append("")  # Blank line for readability
        rows.append(format_date_with_day(date))
        
        for lesson in sorted(date_lessons, key=lambda x: x.start_time):
            rows.append(f"  {_format_lesson_time(lesson)}")
            rows.append(f"  {_format_lesson_details(lesson, show_group)}")
    
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
                    f"📅 Weekly schedule ({user.faculty} year {user.year}, group {user.group_name})",
                    lessons,
                    show_group=multiple_groups,
                    group_by_date=True,
                ),
                reply_markup=timetable_mode_keyboard(),
            )
            return

        if message.text == "Today":
            date = get_current_date()
            date_str = format_date_with_day(date)
        else:  # Tomorrow
            date = get_current_date() + timedelta(days=1)
            date_str = format_date_with_day(date)
        
        day = date.strftime("%A").lower()
        lessons = await service.get_timetable_for_user(user, day=day)
        await message.answer(
            _format_lessons(f"📅 {date_str}", lessons, group_by_date=False),
            reply_markup=timetable_mode_keyboard()
        )


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
        date = day_name_to_next_date(day)
        date_str = format_date_with_day(date)
        await message.answer(
            _format_lessons(f"📅 {date_str}", lessons, group_by_date=False),
            reply_markup=timetable_mode_keyboard()
        )


@router.message(NavigationFSM.timetable_menu, F.text == "⬅️ Back")
async def back_to_main(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Main menu", reply_markup=main_menu_keyboard())


@router.message(NavigationFSM.timetable_menu, F.text == "🏠 Main Menu")
async def main_menu_from_timetable(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Main menu", reply_markup=main_menu_keyboard())
