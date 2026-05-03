from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    telegram_id: int
    full_name: str
    faculty: str
    group_name: str
    year: int


class UserRead(BaseModel):
    id: int
    telegram_id: int
    full_name: str
    faculty: str
    group_name: str
    year: int
    notifications_enabled: bool


class LessonRead(BaseModel):
    subject: str
    teacher: str
    room: str
    day: str
    start_time: time
    end_time: time
    status: str


class TimetableUploadRow(BaseModel):
    group_name: str
    subject: str
    teacher: str
    room: str
    day: str
    start_time: str
    end_time: str
    status: str = "active"


class TeacherUpsert(BaseModel):
    name: str
    subject: str


class BroadcastRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    group_name: str | None = None
    year: int | None = None


class ExamCreate(BaseModel):
    group_name: str
    subject: str
    title: str
    due_date: datetime
    type: Literal["exam", "deadline"] = "exam"


class RoomLookupResponse(BaseModel):
    room: str
    current_subject: str | None = None
    teacher: str | None = None
    time_window: str | None = None
