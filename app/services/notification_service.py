from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class NotificationService:
    def __init__(self, bot: Bot, db: AsyncSession) -> None:
        self.bot = bot
        self.db = db

    async def notify_group(self, group_name: str, text: str) -> int:
        users = (
            await self.db.execute(
                select(User).where(User.group_name == group_name, User.notifications_enabled.is_(True))
            )
        ).scalars().all()
        sent = 0
        for user in users:
            try:
                await self.bot.send_message(user.telegram_id, text)
                sent += 1
            except Exception:
                continue
        return sent

    async def broadcast(self, text: str, group_name: str | None = None, year: int | None = None) -> int:
        query = select(User).where(User.notifications_enabled.is_(True))
        if group_name:
            query = query.where(User.group_name == group_name)
        if year:
            query = query.where(User.year == year)

        users = (await self.db.execute(query)).scalars().all()
        sent = 0
        for user in users:
            try:
                await self.bot.send_message(user.telegram_id, text)
                sent += 1
            except Exception:
                continue
        return sent
