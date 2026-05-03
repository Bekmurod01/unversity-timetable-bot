import asyncio
import logging
import selectors
import sys
from sqlalchemy import text
from app.db import engine, Base
from app.models import Teacher, FavoriteTeacher, RecentSearch, TimetableLesson
from app.services.timetable_service import TimetableService
from app.db import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_schema():
    async with engine.begin() as conn:
        # Create new tables (RecentSearch)
        await conn.run_sync(Base.metadata.create_all)
        
        # Add columns to Teacher if they don't exist
        try:
            await conn.execute(text("ALTER TABLE teachers ADD COLUMN faculty VARCHAR(120)"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE teachers ADD COLUMN last_synced DATETIME"))
        except Exception:
            pass

        # Migrate FavoriteTeacher
        # Since structure changed significantly (teacher_name -> teacher_id), 
        # it's safer to drop and recreate it if it's empty or we can afford to lose it.
        # For this dev project, we'll recreate it.
        await conn.execute(text("DROP TABLE IF EXISTS favorite_teachers"))
        
    # Re-run create_all to ensure everything is there
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def initial_sync():
    async with SessionLocal() as db:
        service = TimetableService(db)
        logger.info("Syncing teachers from timetable data...")
        await service.sync_teachers()
        logger.info("Sync complete.")

async def main():
    logger.info("Updating database schema...")
    await update_schema()
    logger.info("Schema updated.")
    await initial_sync()

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.run(main(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        asyncio.run(main())
