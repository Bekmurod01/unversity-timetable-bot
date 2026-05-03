from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import get_settings


settings = get_settings()
database_url = (settings.database_url or "").strip()
if not database_url:
    # Keep service bootable when DATABASE_URL is not set (e.g., fresh Render web service).
    # Web process can still bind PORT and serve /health while DB is configured.
    database_url = "sqlite+aiosqlite:///./university_bot.db"
engine = create_async_engine(database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
