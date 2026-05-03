import asyncio
import logging
import selectors
import sys

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import ErrorEvent
from sqlalchemy import text

from app.bot.handlers import admin, exams, notifications, room_finder, settings, start, teachers, timetable
from app.config import get_settings
from app.db import engine


class UpdateLogMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        update_id = getattr(event, "update_id", None)
        update_type = type(event).__name__
        logging.info("Incoming update: id=%s type=%s", update_id, update_type)
        return await handler(event, data)


async def create_storage(redis_url: str | None):
    if not redis_url:
        logging.warning("REDIS_URL is not set. Falling back to in-memory FSM storage (not restart-safe).")
        try:
            from aiogram.fsm.storage.memory import MemoryStorage

            return MemoryStorage()
        except Exception:
            return None
    try:
        # Lazy import to avoid hard dependency issues in environments without redis
        from redis.asyncio import Redis as AioredisClient
        from aiogram.fsm.storage.redis import RedisStorage

        redis_client = AioredisClient.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        storage = RedisStorage(redis=redis_client)
        logging.info("Using RedisStorage for FSM (REDIS_URL=%s)", redis_url)
        return storage
    except Exception as e:
        logging.exception("Failed to initialize RedisStorage, falling back to MemoryStorage: %s", e)
        try:
            from aiogram.fsm.storage.memory import MemoryStorage

            return MemoryStorage()
        except Exception:
            return None


async def run_bot() -> None:
    settings_obj = get_settings()
    if not settings_obj.bot_token.strip():
        raise RuntimeError("BOT_TOKEN is empty. Set BOT_TOKEN in Render environment variables.")

    bot = Bot(token=settings_obj.bot_token)

    storage = await create_storage(settings_obj.redis_url)
    if storage:
        dp = Dispatcher(storage=storage)
    else:
        dp = Dispatcher()
    dp.update.outer_middleware(UpdateLogMiddleware())

    @dp.error()
    async def on_error(event: ErrorEvent) -> None:
        logging.exception("Unhandled update error: %s", event.exception)

    # register routers
    dp.include_router(start.router)
    dp.include_router(timetable.router)
    dp.include_router(notifications.router)
    dp.include_router(exams.router)
    dp.include_router(room_finder.router)
    dp.include_router(settings.router)
    dp.include_router(teachers.router)
    dp.include_router(admin.router)

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logging.info("Database connectivity check passed.")
    except Exception:
        logging.exception("Database connectivity check failed.")

    while True:
        try:
            me = await bot.get_me()
            logging.info("Bot authorized successfully: @%s (id=%s)", me.username, me.id)
            break
        except Exception:
            logging.exception("Bot authorization check failed. Retrying in 5 seconds.")
            await asyncio.sleep(5)

    # Ensure polling works even if webhook had been set previously.
    await bot.delete_webhook(drop_pending_updates=False)
    logging.info("Webhook cleared. Starting bot polling.")

    while True:
        try:
            await dp.start_polling(bot, drop_pending_updates=True)
            break
        except Exception:
            logging.exception("Polling crashed. Restarting in 5 seconds.")
            await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    if sys.platform.startswith("win"):
        asyncio.run(run_bot(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        asyncio.run(run_bot())
