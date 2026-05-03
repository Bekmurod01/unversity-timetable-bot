from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db


async def get_db_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    return db


def admin_guard(x_admin_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if x_admin_key != settings.secret_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")
