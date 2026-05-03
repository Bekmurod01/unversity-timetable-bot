from datetime import datetime, time

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    faculty: Mapped[str] = mapped_column(String(80))
    group_name: Mapped[str] = mapped_column(String(40), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    lesson_reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    lesson_reminder_minutes: Mapped[int] = mapped_column(Integer, default=5)
    notify_changes_only: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_daily_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_exam_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True, unique=True)
    subject: Mapped[str] = mapped_column(String(120), nullable=True)
    faculty: Mapped[str] = mapped_column(String(120), nullable=True)
    last_synced: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TimetableLesson(Base):
    __tablename__ = "timetable_lessons"
    __table_args__ = (
        UniqueConstraint("group_name", "day", "start_time", "subject", name="uq_lesson_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_name: Mapped[str] = mapped_column(String(40), index=True)
    subject: Mapped[str] = mapped_column(String(120))
    teacher: Mapped[str] = mapped_column(String(120), index=True)
    room: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(16), index=True)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(20), default="active")


class ExamDeadline(Base):
    __tablename__ = "exam_deadlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_name: Mapped[str] = mapped_column(String(40), index=True)
    subject: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(200))
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    type: Mapped[str] = mapped_column(String(20), default="exam")


class UpdateLog(Base):
    __tablename__ = "updates_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_name: Mapped[str] = mapped_column(String(40), index=True)
    change_type: Mapped[str] = mapped_column(String(40))
    details: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class LessonReminderDispatch(Base):
    __tablename__ = "lesson_reminder_dispatches"
    __table_args__ = (
        UniqueConstraint("user_id", "group_name", "day", "start_time", "reminder_minutes", name="uq_reminder_dispatch"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_name: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[Date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    reminder_minutes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class FavoriteTeacher(Base):
    __tablename__ = "favorite_teachers"
    __table_args__ = (
        UniqueConstraint("user_id", "teacher_id", name="uq_user_teacher_favorite"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    teacher = relationship("Teacher")


class RecentSearch(Base):
    __tablename__ = "recent_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    teacher = relationship("Teacher")
