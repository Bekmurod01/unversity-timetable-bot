import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db import SessionLocal
from app.models import ExamDeadline, Teacher


TEACHERS = [
    ("Dr. A. Karimov", "Data Structures"),
    ("Ms. N. Rakhimova", "Database Systems"),
    ("Mr. J. Lee", "Financial Reporting"),
]


async def seed() -> None:
    async with SessionLocal() as db:
        for name, subject in TEACHERS:
            exists = (await db.execute(select(Teacher).where(Teacher.name == name))).scalar_one_or_none()
            if not exists:
                db.add(Teacher(name=name, subject=subject))

        exam = ExamDeadline(
            group_name="IT-202",
            subject="Data Structures",
            title="Midterm Exam",
            due_date=datetime.utcnow() + timedelta(days=5),
            type="exam",
        )
        db.add(exam)

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
