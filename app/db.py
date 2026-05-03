from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import get_settings


settings = get_settings()
database_url = (settings.database_url or "").strip()
if not database_url:
    # Keep service bootable when DATABASE_URL is not set (e.g., fresh Render web service).
    # Web process can still bind PORT and serve /health while DB is configured.
    database_url = "sqlite+aiosqlite:///./university_bot.db"
elif database_url.startswith("postgres://"):
    database_url = "postgresql+psycopg://" + database_url[len("postgres://") :]
elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
    database_url = "postgresql+psycopg://" + database_url[len("postgresql://") :]
engine = create_async_engine(database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def ensure_db_schema() -> None:
    # Ensure model metadata is registered before create_all.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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

        if MIGRATIONS_DIR.exists():
            for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
                filename = migration_file.name
                already_applied = await conn.execute(
                    text("SELECT 1 FROM schema_migrations WHERE filename = :filename"),
                    {"filename": filename},
                )
                if already_applied.scalar_one_or_none():
                    continue

                sql_body = migration_file.read_text(encoding="utf-8").strip()
                if sql_body:
                    await conn.execute(text(sql_body))
                await conn.execute(
                    text("INSERT INTO schema_migrations (filename) VALUES (:filename)"),
                    {"filename": filename},
                )
