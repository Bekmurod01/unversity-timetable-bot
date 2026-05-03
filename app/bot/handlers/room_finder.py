from datetime import datetime
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards import main_menu_keyboard, timetable_mode_keyboard
from app.bot.states import RoomFinderFSM
from app.db import SessionLocal
from app.services.timetable_service import TimetableService

router = Router()


def room_finder_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Today's Empty Rooms", callback_data="room_today")],
            [InlineKeyboardButton(text="📆 Weekly Empty Rooms", callback_data="room_week")],
            [
                InlineKeyboardButton(text="⬅️ Back", callback_data="room_back"),
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="room_home"),
            ],
        ]
    )


@router.message(F.text.func(lambda t: bool(t) and "Room Finder" in t))
async def room_finder_prompt(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🏫 Room Finder\nChoose an option:", reply_markup=room_finder_main_keyboard())


@router.callback_query(F.data == "room_back")
async def room_back(callback: CallbackQuery, state: FSMContext):
    logging.info("room_back clicked by user=%s", callback.from_user.id)
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Main menu", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "room_home")
async def room_home(callback: CallbackQuery, state: FSMContext):
    logging.info("room_home clicked by user=%s", callback.from_user.id)
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Main menu", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "room_today")
async def room_today(callback: CallbackQuery, state: FSMContext):
    logging.info("room_today callback data=%s user=%s", callback.data, callback.from_user.id)
    now = datetime.now()
    day = now.strftime("%A").lower()
    current_time = now.time().replace(second=0, microsecond=0)
    async with SessionLocal() as db:
        service = TimetableService(db)
        lessons = await service.get_timetable(None, day=day)
        occupied = set()
        for l in lessons:
            if l.start_time <= current_time <= l.end_time:
                occupied.add(l.room)
        all_rooms = set(l.room for l in lessons if l.room)
        available = all_rooms - occupied
        blocks = {}
        for room in available:
            block = room[0].upper() if room and room[0].isalpha() else "Other"
            blocks.setdefault(block, []).append(room)
        if not available:
            text = "No available rooms found for today."
        else:
            text = "🏫 Today's Available Rooms\n"
            for block in sorted(blocks.keys()):
                text += f"\n📍 {block} Block\n"
                for r in sorted(blocks[block]):
                    text += f"• Room {r}\n"
    await callback.message.edit_text(text, reply_markup=room_finder_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "room_week")
async def room_week(callback: CallbackQuery, state: FSMContext):
    logging.info("room_week clicked by user=%s", callback.from_user.id)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=day, callback_data=f"room_week_day:{day}")] for day in days]
        + [[InlineKeyboardButton(text="⬅️ Back", callback_data="room_back"), InlineKeyboardButton(text="🏠 Main Menu", callback_data="room_home")]]
    )
    await callback.message.edit_text("Select day of week:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("room_week_day:"))
async def room_week_day(callback: CallbackQuery, state: FSMContext):
    logging.info("room_week_day callback data=%s user=%s", callback.data, callback.from_user.id)
    day = callback.data.split(":", 1)[1].lower()
    async with SessionLocal() as db:
        service = TimetableService(db)
        lessons = await service.get_timetable(None, day=day)
        time_slots = sorted(set((l.start_time, l.end_time) for l in lessons))
        if not time_slots:
            await callback.message.edit_text("No lessons found for this day.", reply_markup=room_finder_main_keyboard())
            await callback.answer()
            return
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{s.strftime('%H:%M')} - {e.strftime('%H:%M')}", callback_data=f"room_week_time:{day}:{s.strftime('%H:%M')}-{e.strftime('%H:%M')}")]
                for s, e in time_slots
            ]
            + [[InlineKeyboardButton(text="⬅️ Back", callback_data="room_week"), InlineKeyboardButton(text="🏠 Main Menu", callback_data="room_home")]]
        )
        await callback.message.edit_text("Select time slot:", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("room_week_time:"))
async def room_week_time(callback: CallbackQuery, state: FSMContext):
    logging.info("room_week_time callback data=%s user=%s", callback.data, callback.from_user.id)
    import datetime as dt

    _, day, time_range = callback.data.split(":")
    start_str, end_str = time_range.split("-")
    start_time = dt.datetime.strptime(start_str, "%H:%M").time()
    end_time = dt.datetime.strptime(end_str, "%H:%M").time()
    async with SessionLocal() as db:
        service = TimetableService(db)
        lessons = await service.get_timetable(None, day=day)
        occupied = set()
        for l in lessons:
            if not (l.end_time <= start_time or l.start_time >= end_time):
                occupied.add(l.room)
        all_rooms = set(l.room for l in lessons if l.room)
        available = all_rooms - occupied
        blocks = {}
        for room in available:
            block = room[0].upper() if room and room[0].isalpha() else "Other"
            blocks.setdefault(block, []).append(room)
        if not available:
            text = f"No available rooms found for {day.title()} {start_str}-{end_str}."
        else:
            text = f"🏫 Available Rooms for {day.title()} {start_str}-{end_str}\n"
            for block in sorted(blocks.keys()):
                text += f"\n📍 {block} Block\n"
                for r in sorted(blocks[block]):
                    text += f"• Room {r}\n"
    await callback.message.edit_text(text, reply_markup=room_finder_main_keyboard())
    await callback.answer()


@router.message(RoomFinderFSM.waiting_room)
async def room_finder_result(message: Message, state: FSMContext) -> None:
    logging.info("room_finder manual lookup by user=%s room=%s", message.from_user.id, message.text)
    room = message.text.strip()
    now = datetime.now()
    day = now.strftime("%A").lower()
    current_time = now.time().replace(second=0, microsecond=0)

    async with SessionLocal() as db:
        service = TimetableService(db)
        lesson = await service.room_lookup_now(room=room, day=day, current_time=current_time)

    await state.clear()

    if not lesson:
        await message.answer("No active class in this room right now.")
        return

    await message.answer(
        f"Room {room}\n"
        f"Current class: {lesson.subject}\n"
        f"Teacher: {lesson.teacher}\n"
        f"Time: {lesson.start_time.strftime('%H:%M')} - {lesson.end_time.strftime('%H:%M')}"
    )
