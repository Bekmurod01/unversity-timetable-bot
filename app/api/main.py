import logging
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.bot.main import create_bot_and_dispatcher, log_environment_validation
from app.config import get_settings
from app.db import engine, ensure_db_schema

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
ADMIN_ROUTER_LOADED = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not log_environment_validation(settings):
        raise RuntimeError("Critical environment variables are missing for webhook mode.")

    await ensure_db_schema()
    logger.info("Database schema ensured.")

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connectivity check passed.")
    except Exception:
        logger.exception("Database connectivity check failed.")

    bot, dp = await create_bot_and_dispatcher()
    app.state.bot = bot
    app.state.dp = dp

    me = await bot.get_me()
    logger.info("Bot authorized: @%s (id=%s)", me.username, me.id)

    webhook_url = settings.webhook_url
    await bot.set_webhook(url=webhook_url, secret_token=settings.webhook_secret or None)
    logger.info("Webhook configured: %s", webhook_url)

    try:
        yield
    finally:
        try:
            await bot.delete_webhook(drop_pending_updates=False)
            logger.info("Webhook removed on shutdown.")
        except Exception:
            logger.exception("Failed to remove webhook on shutdown.")

        try:
            await dp.storage.close()
        except Exception:
            logger.exception("Failed to close dispatcher storage on shutdown.")

        await bot.session.close()
        logger.info("Bot session closed.")


app = FastAPI(title="University Timetable Admin API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "admin_router_loaded": ADMIN_ROUTER_LOADED}


@app.get("/")
async def root() -> dict:
    return {
        "status": "ok",
        "message": "University Timetable API is running",
        "health": "/health",
        "admin_panel": "/admin-panel",
    }


@app.get("/admin-panel", include_in_schema=False)
async def admin_panel() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "admin.html")


@app.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    settings = get_settings()
    expected_secret = (settings.webhook_secret or "").strip()
    if expected_secret:
        provided_secret = request.headers.get("x-telegram-bot-api-secret-token", "")
        if provided_secret != expected_secret:
            logger.warning("Webhook secret token mismatch.")
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    payload = await request.json()
    update = Update.model_validate(payload)
    await app.state.dp.feed_update(app.state.bot, update)
    return {"ok": True}


try:
    from app.api.routers.admin import router as admin_router

    app.include_router(admin_router)
    ADMIN_ROUTER_LOADED = True
except Exception:
    logger.exception("Failed to load admin router during startup")
