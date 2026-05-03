from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI(title="University Timetable Admin API", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)
ADMIN_ROUTER_LOADED = False


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "admin_router_loaded": ADMIN_ROUTER_LOADED}


@app.get("/admin-panel", include_in_schema=False)
async def admin_panel() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "admin.html")


try:
    from app.api.routers.admin import router as admin_router
    app.include_router(admin_router)
    ADMIN_ROUTER_LOADED = True
except Exception:
    logger.exception("Failed to load admin router during startup")
