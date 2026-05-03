import asyncio
import logging
import selectors
import sys

from aiogram import Bot, Dispatcher

from app.bot.handlers import admin, exams, notifications, room_finder, settings, start, teachers, timetable
from app.config import get_settings


async def run_bot() -> None:
    settings_obj = get_settings()
    bot = Bot(token=settings_obj.bot_token)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(timetable.router)
    dp.include_router(notifications.router)
    dp.include_router(exams.router)
    dp.include_router(room_finder.router)
    dp.include_router(settings.router)
    dp.include_router(teachers.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if sys.platform.startswith("win"):
        asyncio.run(run_bot(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        asyncio.run(run_bot())
