from pathlib import Path
import logging
import asyncio

from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI(title="University Timetable Admin API", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)
ADMIN_ROUTER_LOADED = False
BOT_TASK: asyncio.Task | None = None


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


@app.on_event("startup")
async def startup_tasks() -> None:
    global BOT_TASK
    try:
        from app.config import get_settings
        settings = get_settings()
        if settings.bot_token and BOT_TASK is None:
            from app.bot.main import run_bot
            BOT_TASK = asyncio.create_task(run_bot())
            logger.info("Bot polling started in background task")
        else:
            logger.warning("BOT_TOKEN is empty or bot task already exists; bot polling not started")
    except Exception:
        logger.exception("Failed to start bot polling during API startup")


@app.on_event("shutdown")
async def shutdown_tasks() -> None:
    global BOT_TASK
    if BOT_TASK is not None:
        BOT_TASK.cancel()
        BOT_TASK = None


try:
    from app.api.routers.admin import router as admin_router
    app.include_router(admin_router)
    ADMIN_ROUTER_LOADED = True
except Exception:
    logger.exception("Failed to load admin router during startup")
