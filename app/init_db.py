import asyncio
import logging
import selectors
import sys

from app.db import Base, engine
from app import models  # noqa: F401
from sqlalchemy.exc import OperationalError


logger = logging.getLogger(__name__)


async def init_db() -> None:
    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
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
