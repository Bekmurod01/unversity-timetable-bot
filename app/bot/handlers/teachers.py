import logging
from collections import defaultdict

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup

from app.bot.keyboards import main_menu_keyboard
from app.db import SessionLocal
from app.models import Teacher
from app.services.timetable_service import TimetableService

logger = logging.getLogger(__name__)
router = Router()

TEACHER_TIMETABLE_TEXT = "\U0001F468\u200d\U0001F3EB Teacher Timetable"
SEARCH_TEACHER_TEXT = "\U0001F50D Search Teacher"
ALL_TEACHERS_TEXT = "\U0001F4CB All Teachers"
FAVORITES_TEXT = "\u2B50 Favorite Teachers"
RECENT_TEXT = "\U0001F552 Recent Searches"
BACK_TEXT = "\u2B05\uFE0F Back"
MAIN_MENU_TEXT = "\U0001F3E0 Main Menu"
PREV_TEXT = "\u2B05\uFE0F Previous"
NEXT_TEXT = "Next \u27A1\uFE0F"

TEACHERS_PAGE_SIZE = 20


def teacher_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SEARCH_TEACHER_TEXT), KeyboardButton(text=ALL_TEACHERS_TEXT)],
            [KeyboardButton(text=FAVORITES_TEXT), KeyboardButton(text=RECENT_TEXT)],
            [KeyboardButton(text=BACK_TEXT), KeyboardButton(text=MAIN_MENU_TEXT)],
        ],
        resize_keyboard=True,
    )


def nav_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_TEXT), KeyboardButton(text=MAIN_MENU_TEXT)]],
        resize_keyboard=True,
    )


def teacher_list_inline_keyboard(teachers: list[Teacher], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=t.name, callback_data=f"teacher_pick:{t.id}")]
        for t in teachers
    ]
    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text=PREV_TEXT, callback_data=f"teacher_list_page:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text=NEXT_TEXT, callback_data=f"teacher_list_page:{page+1}"))
    if nav_row:
        rows.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _faculty_label(faculty_code: str) -> str:
    emoji_map = {
        "IT": "\U0001F4BB",
        "ACCA": "\U0001F4B0",
        "ECONOMICS": "\U0001F4CA",
        "ENGINEERING": "\u2699\uFE0F",
    }
    icon = emoji_map.get(faculty_code.upper(), "\U0001F3E2")
    pretty = faculty_code.title() if faculty_code.isalpha() and faculty_code != faculty_code.upper() else faculty_code
    if faculty_code.upper() == "ECONOMICS":
        pretty = "Economics"
    return f"{icon} {pretty}"


def _normalize_faculty_value(value: str) -> str:
    cleaned = (value or "").strip().upper()
    alias_map = {
        "IT": "IT",
        "ACCA": "ACCA",
        "ECONOMICS": "ECONOMICS",
        "ECONOMY": "ECONOMICS",
        "ENGINEERING": "ENGINEERING",
    }
    return alias_map.get(cleaned, cleaned)


def faculty_inline_keyboard(faculties: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=_faculty_label(_normalize_faculty_value(code)),
                callback_data=f"teacher_faculty:{_normalize_faculty_value(code)}",
            )
        ]
        for code in faculties
    ]
    rows.append([InlineKeyboardButton(text=BACK_TEXT, callback_data="teacher_faculty_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def teacher_action_keyboard(is_favorite: bool, notifications_enabled: bool, teacher_id: int) -> InlineKeyboardMarkup:
    fav_text = "\u2B50 Remove Favorite" if is_favorite else "\u2B50 Add Favorite"
    notif_text = "\U0001F515 Disable Notifications" if notifications_enabled else "\U0001F514 Enable Notifications"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\U0001F4C5 View Schedule", callback_data=f"teacher_action:view:{teacher_id}")],
            [InlineKeyboardButton(text=fav_text, callback_data=f"teacher_action:fav:{teacher_id}")],
            [InlineKeyboardButton(text=notif_text, callback_data=f"teacher_action:notif:{teacher_id}")],
            [
                InlineKeyboardButton(text=BACK_TEXT, callback_data="teacher_action:back"),
                InlineKeyboardButton(text=MAIN_MENU_TEXT, callback_data="teacher_action:main"),
            ],
        ]
    )


def _format_teacher_card(teacher: Teacher) -> str:
    subjects = teacher.subject.split(", ") if teacher.subject else []
    subjects_str = "\n".join([f"- {s}" for s in subjects]) if subjects else "Not specified"
    return (
        f"\U0001F468\u200d\U0001F3EB {teacher.name}\n\n"
        f"\U0001F4DA Subjects:\n{subjects_str}\n\n"
        f"\U0001F3E2 Faculty: {teacher.faculty or 'General'}"
    )


def _format_teacher_schedule(teacher_name: str, lessons: list) -> str:
    if not lessons:
        return f"\U0001F4C5 Schedule for {teacher_name}\nNo lessons found."

    schedule = defaultdict(list)
    for lesson in lessons:
        schedule[lesson.day.title()].append(lesson)

    lines = [f"\U0001F4C5 Schedule: {teacher_name}\n"]
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
        day_lessons = schedule.get(day)
        if not day_lessons:
            continue
        lines.append(f"\U0001F4CC {day}")
        for item in day_lessons:
            lines.append(f"{item.start_time.strftime('%H:%M')} - {item.subject}")
            lines.append(f"\U0001F3EB Room {item.room}\n")
    return "\n".join(lines)


def _paginate(items: list, page: int, page_size: int) -> tuple[list, int, int]:
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    safe_page = max(1, min(page, total_pages))
    start = (safe_page - 1) * page_size
    end = start + page_size
    return items[start:end], safe_page, total_pages


async def _show_teacher_detail(message: Message, state: FSMContext, teacher: Teacher) -> None:
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)

        is_favorite = False
        notifications_enabled = False
        if user:
            favorites = await service.get_favorite_teachers(user.id)
            for fav in favorites:
                if fav.teacher_id == teacher.id:
                    is_favorite = True
                    notifications_enabled = fav.notifications_enabled
                    break

        await state.update_data(selected_teacher_id=teacher.id, last_screen="teacher_detail")
        await message.answer(
            _format_teacher_card(teacher),
            reply_markup=teacher_action_keyboard(is_favorite, notifications_enabled, teacher.id),
        )


async def _render_teacher_list_message(message: Message, state: FSMContext, heading: str, page: int) -> None:
    data = await state.get_data()
    teacher_ids = data.get("teacher_list") or []
    if not teacher_ids:
        await message.answer("No teachers available.", reply_markup=nav_keyboard())
        return

    async with SessionLocal() as db:
        service = TimetableService(db)
        teachers: list[Teacher] = []
        for teacher_id in teacher_ids:
            teacher = await service.get_teacher_by_id(teacher_id)
            if teacher:
                teachers.append(teacher)

    page_items, safe_page, total_pages = _paginate(teachers, page, TEACHERS_PAGE_SIZE)
    await state.update_data(teacher_page=safe_page, teacher_total_pages=total_pages)
    await message.answer(
        f"{heading} (Page {safe_page}/{total_pages})",
        reply_markup=teacher_list_inline_keyboard(page_items, safe_page, total_pages),
    )


@router.message(F.text.func(lambda t: bool(t) and "Teacher Timetable" in t))
async def teacher_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Teacher Timetable Menu", reply_markup=teacher_menu_keyboard())


@router.message(F.text == SEARCH_TEACHER_TEXT)
async def search_teacher_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(last_screen="faculty_select")
    async with SessionLocal() as db:
        service = TimetableService(db)
        teacher_faculties = [_normalize_faculty_value(x) for x in await service.get_teacher_faculties()]
        group_faculties = [_normalize_faculty_value(x) for x in await service.get_available_faculties()]
        teachers = await service.get_teachers()

    faculties = sorted(set(teacher_faculties or group_faculties))
    missing_faculty_count = sum(1 for t in teachers if not (t.faculty or "").strip())
    logger.debug(
        "Teacher faculty picker source stats: teachers_total=%d missing_faculty=%d teacher_faculties=%d group_faculties=%d final=%s",
        len(teachers),
        missing_faculty_count,
        len(teacher_faculties),
        len(group_faculties),
        faculties,
    )
    if set(group_faculties) - set(teacher_faculties):
        logger.debug(
            "Faculty completeness gap detected. Missing_in_teacher_table=%s",
            sorted(set(group_faculties) - set(teacher_faculties)),
        )

    if not faculties:
        await message.answer("No faculties found in database.", reply_markup=nav_keyboard())
        return

    await state.update_data(faculty_codes=faculties)
    await message.answer("Select faculty:", reply_markup=faculty_inline_keyboard(faculties))


@router.callback_query(F.data == "teacher_faculty_back")
async def faculty_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Teacher Timetable Menu", reply_markup=teacher_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("teacher_faculty:"))
async def faculty_selected(callback: CallbackQuery, state: FSMContext) -> None:
    faculty = _normalize_faculty_value(callback.data.split(":", 1)[1])

    async with SessionLocal() as db:
        service = TimetableService(db)
        filtered = await service.get_teachers_by_faculty(faculty)
    logger.debug("Faculty selected=%s, matched_teachers=%d", faculty, len(filtered))

    await callback.message.edit_reply_markup(reply_markup=None)

    if not filtered:
        await state.update_data(last_screen="teacher_list", teacher_list=[], teacher_page=1, teacher_total_pages=1)
        await callback.message.answer(f"No teachers found for {faculty} faculty.", reply_markup=nav_keyboard())
        await callback.answer()
        return

    heading = f"\U0001F468\u200d\U0001F3EB {faculty.title()} Faculty Teachers"
    await state.update_data(
        last_screen="teacher_list",
        teacher_list=[t.id for t in filtered],
        teacher_page=1,
        teacher_total_pages=1,
        teacher_list_heading=heading,
    )
    await _render_teacher_list_message(callback.message, state, heading, page=1)
    await callback.answer()


@router.message(F.text == ALL_TEACHERS_TEXT)
async def all_teachers(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as db:
        service = TimetableService(db)
        teachers = await service.get_teachers()

    if not teachers:
        await state.update_data(last_screen="all_teachers")
        await message.answer("No teachers available.", reply_markup=nav_keyboard())
        return

    heading = "\U0001F4CB All Teachers"
    await state.update_data(
        last_screen="all_teachers",
        teacher_list=[t.id for t in teachers],
        teacher_page=1,
        teacher_total_pages=1,
        teacher_list_heading=heading,
    )
    await _render_teacher_list_message(message, state, heading, page=1)


@router.message(F.text == FAVORITES_TEXT)
async def favorite_teachers(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await state.update_data(last_screen="favorites")
            await message.answer("Please register first.", reply_markup=nav_keyboard())
            return

        favorites = await service.get_favorite_teachers(user.id)
        teachers = [fav.teacher for fav in favorites if fav.teacher]

    await state.update_data(last_screen="favorites")
    if not teachers:
        await message.answer("\u2B50 Favorite list is empty. Use Search Teacher and tap Add Favorite.", reply_markup=nav_keyboard())
        return

    heading = "\u2B50 Favorite Teachers"
    await state.update_data(teacher_list=[t.id for t in teachers], teacher_page=1, teacher_total_pages=1, teacher_list_heading=heading)
    await _render_teacher_list_message(message, state, heading, page=1)


@router.message(F.text == RECENT_TEXT)
async def recent_searches(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(message.from_user.id)
        if not user:
            await state.update_data(last_screen="recent")
            await message.answer("Please register first.", reply_markup=nav_keyboard())
            return

        recent = await service.get_recent_searches(user.id)

    await state.update_data(last_screen="recent")
    if not recent:
        await message.answer("\U0001F552 Recent searches are empty.", reply_markup=nav_keyboard())
        return

    heading = "\U0001F552 Recent Searches"
    await state.update_data(teacher_list=[t.id for t in recent], teacher_page=1, teacher_total_pages=1, teacher_list_heading=heading)
    await _render_teacher_list_message(message, state, heading, page=1)


@router.callback_query(F.data.startswith("teacher_list_page:"))
async def paginate_teacher_list_callback(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        page = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Invalid page.")
        return

    data = await state.get_data()
    heading = data.get("teacher_list_heading", "Teachers")
    if not (data.get("teacher_list") or []):
        await callback.answer("No active list.")
        return

    await _render_teacher_list_message(callback.message, state, heading, page=page)
    await callback.answer()


@router.callback_query(F.data.startswith("teacher_pick:"))
async def teacher_pick_callback(callback: CallbackQuery, state: FSMContext) -> None:
    teacher_id = int(callback.data.split(":", 1)[1])
    async with SessionLocal() as db:
        service = TimetableService(db)
        teacher = await service.get_teacher_by_id(teacher_id)
        if not teacher:
            await callback.answer("Teacher not found.")
            return
        user = await service.get_user(callback.from_user.id)
        if user:
            await service.add_recent_search(user.id, teacher.id)

    await callback.answer()
    await _show_teacher_detail(callback.message, state, teacher)


@router.callback_query(F.data.startswith("teacher_action:view:"))
async def teacher_view_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    teacher_id = int(callback.data.split(":")[-1])
    async with SessionLocal() as db:
        service = TimetableService(db)
        teacher = await service.get_teacher_by_id(teacher_id)
        if not teacher:
            await callback.answer("Teacher not found.")
            return
        lessons = await service.get_teacher_timetable(teacher.name)

    await callback.message.answer(_format_teacher_schedule(teacher.name, lessons), reply_markup=nav_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("teacher_action:fav:"))
async def teacher_toggle_favorite(callback: CallbackQuery, state: FSMContext) -> None:
    teacher_id = int(callback.data.split(":")[-1])
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(callback.from_user.id)
        if not user:
            await callback.answer("Please register first.")
            return

        added = await service.toggle_favorite_teacher(user.id, teacher_id)
        teacher = await service.get_teacher_by_id(teacher_id)

    await callback.answer("\u2B50 Added to favorites." if added else "\u274C Removed from favorites.")
    if teacher:
        await _show_teacher_detail(callback.message, state, teacher)


@router.callback_query(F.data.startswith("teacher_action:notif:"))
async def teacher_toggle_notifications(callback: CallbackQuery, state: FSMContext) -> None:
    teacher_id = int(callback.data.split(":")[-1])
    async with SessionLocal() as db:
        service = TimetableService(db)
        user = await service.get_user(callback.from_user.id)
        if not user:
            await callback.answer("Please register first.")
            return

        enabled = await service.toggle_teacher_notifications(user.id, teacher_id)
        teacher = await service.get_teacher_by_id(teacher_id)

    await callback.answer("\U0001F514 Notifications enabled." if enabled else "\U0001F515 Notifications disabled.")
    if teacher:
        await _show_teacher_detail(callback.message, state, teacher)


@router.callback_query(F.data == "teacher_action:back")
async def teacher_action_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Teacher Timetable Menu", reply_markup=teacher_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "teacher_action:main")
async def teacher_action_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Main Menu", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(F.text == BACK_TEXT)
async def back_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Teacher Timetable Menu", reply_markup=teacher_menu_keyboard())


@router.message(F.text == MAIN_MENU_TEXT)
async def main_menu_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Main Menu", reply_markup=main_menu_keyboard())
