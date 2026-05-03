import asyncio
import logging
import selectors
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent

from app.bot.handlers import admin, exams, notifications, room_finder, settings, start, teachers, timetable
from app.config import get_settings


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

    # Ensure polling works even if webhook had been set previously.
    await bot.delete_webhook(drop_pending_updates=False)
    logging.info("Webhook cleared. Starting bot polling.")
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    if sys.platform.startswith("win"):
        asyncio.run(run_bot(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        asyncio.run(run_bot())
