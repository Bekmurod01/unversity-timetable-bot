import asyncio
import logging
from pathlib import Path
import selectors
import sys

from sqlalchemy import text
from app.db import Base, engine
from app import models  # noqa: F401
from sqlalchemy.exc import OperationalError


logger = logging.getLogger(__name__)
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


async def _ensure_migrations_table(conn) -> None:
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )


async def _apply_sql_migrations(conn) -> None:
    await _ensure_migrations_table(conn)
    if not MIGRATIONS_DIR.exists():
        logger.warning("Migrations directory not found: %s", MIGRATIONS_DIR)
        return

    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        filename = migration_file.name
        applied = await conn.execute(
            text("SELECT 1 FROM schema_migrations WHERE filename = :filename"),
            {"filename": filename},
        )
        if applied.scalar_one_or_none():
            continue

        sql_text = migration_file.read_text(encoding="utf-8").strip()
        if not sql_text:
            logger.info("Skipping empty migration file: %s", filename)
            await conn.execute(text("INSERT INTO schema_migrations (filename) VALUES (:filename)"), {"filename": filename})
            continue

        logger.info("Applying migration: %s", filename)
        await conn.execute(text(sql_text))
        await conn.execute(text("INSERT INTO schema_migrations (filename) VALUES (:filename)"), {"filename": filename})
        logger.info("Applied migration: %s", filename)


async def init_db() -> None:
    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await _apply_sql_migrations(conn)
            return
        except OperationalError as exc:
            if attempt == max_attempts:
                raise
            logger.warning("DB is not ready (attempt %s/%s): %s", attempt, max_attempts, exc)
            await asyncio.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if sys.platform.startswith("win"):
        asyncio.run(init_db(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        asyncio.run(init_db())
