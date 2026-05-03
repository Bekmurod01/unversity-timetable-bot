from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import get_settings
from app.db import SessionLocal
from app.services.timetable_service import TimetableService

router = Router()
settings = get_settings()


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


@router.message(Command("admin"))
async def admin_dashboard(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Access denied.")
        return

    async with SessionLocal() as db:
        service = TimetableService(db)
        stats = await service.get_dashboard_stats()

    lines = [
        "Admin dashboard",
        f"Total users: {stats['total_users']}",
        f"Active users: {stats['active_users']}",
        f"Groups count: {stats['groups_count']}",
        "Last updates:",
    ]
    for row in stats["last_updates"]:
        lines.append(f"- {row['group']} | {row['change_type']} | {row['details']}")

    await message.answer("\n".join(lines))
