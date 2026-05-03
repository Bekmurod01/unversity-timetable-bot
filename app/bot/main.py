import logging
from typing import Any

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import ErrorEvent

from app.bot.handlers import admin, exams, notifications, room_finder, settings, start, teachers, timetable
from app.config import Settings, get_settings


class UpdateLogMiddleware(BaseMiddleware):
    async def __call__(self, handler: Any, event: Any, data: dict[str, Any]) -> Any:
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
        from redis.asyncio import Redis as AioredisClient
        from aiogram.fsm.storage.redis import RedisStorage

        redis_client = AioredisClient.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        storage = RedisStorage(redis=redis_client)
        logging.info("Using RedisStorage for FSM.")
        return storage
    except Exception:
        logging.exception("Failed to initialize RedisStorage. Falling back to MemoryStorage.")
        try:
            from aiogram.fsm.storage.memory import MemoryStorage

            return MemoryStorage()
        except Exception:
            return None


def log_environment_validation(settings_obj: Settings) -> bool:
    bot_token_ok = bool((settings_obj.bot_token or "").strip())
    redis_present = bool((settings_obj.redis_url or "").strip())
    database_present = bool((settings_obj.database_url or "").strip())
    webhook_url_present = bool((settings_obj.webhook_url or "").strip())

    logging.info(
        "Environment validation: BOT_TOKEN=%s REDIS_URL=%s DATABASE_URL=%s WEBHOOK_URL=%s",
        bot_token_ok,
        redis_present,
        database_present,
        webhook_url_present,
    )
    if not bot_token_ok:
        logging.error("BOT_TOKEN is missing.")
    if not webhook_url_present:
        logging.error("WEBHOOK_URL is missing. Set WEBHOOK_BASE_URL or RENDER_EXTERNAL_URL.")
    return bot_token_ok and webhook_url_present


async def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    settings_obj = get_settings()
    storage = await create_storage(settings_obj.redis_url)
    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    dp.update.outer_middleware(UpdateLogMiddleware())

    @dp.error()
    async def on_error(event: ErrorEvent) -> None:
        logging.exception("Unhandled update error: %s", event.exception)

    dp.include_router(start.router)
    dp.include_router(timetable.router)
    dp.include_router(notifications.router)
    dp.include_router(exams.router)
    dp.include_router(room_finder.router)
    dp.include_router(settings.router)
    dp.include_router(teachers.router)
    dp.include_router(admin.router)

    bot = Bot(token=settings_obj.bot_token)
    return bot, dp
