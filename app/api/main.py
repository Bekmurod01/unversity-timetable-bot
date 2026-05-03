from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.routers.admin import router as admin_router

app = FastAPI(title="University Timetable Admin API", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/admin-panel", include_in_schema=False)
async def admin_panel() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "admin.html")


app.include_router(admin_router)
