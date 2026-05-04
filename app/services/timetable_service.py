from datetime import datetime, time
import re
import logging

from sqlalchemy import Select, and_, delete, distinct, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExamDeadline, FavoriteTeacher, RecentSearch, Teacher, TimetableLesson, UpdateLog, User


WEEK_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
logger = logging.getLogger(__name__)


def _parse_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def _normalize_group(value: str) -> str:
    return (value or "").strip().upper()


def _canonical_group(value: str) -> str:
    return re.sub(r"-\d{2}$", "", _normalize_group(value))


class TimetableService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_user(self, telegram_id: int, full_name: str, faculty: str, group_name: str, year: int) -> User:
        query: Select[tuple[User]] = select(User).where(User.telegram_id == telegram_id)
        existing = (await self.db.execute(query)).scalar_one_or_none()
        if existing:
            existing.full_name = full_name
            existing.faculty = faculty
            existing.group_name = group_name
            existing.year = year
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            faculty=faculty,
            group_name=group_name,
            year=year,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_user(self, telegram_id: int) -> User | None:
        return (await self.db.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()

    async def set_lesson_reminder_settings(self, user: User, enabled: bool, minutes: int) -> User:
        user.lesson_reminder_enabled = enabled
        user.lesson_reminder_minutes = minutes
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_timetable(self, group_name: str, day: str | None = None) -> list[TimetableLesson]:
        query = select(TimetableLesson).where(TimetableLesson.group_name == group_name)
        if day:
            query = query.where(TimetableLesson.day == day.lower())
        query = query.order_by(TimetableLesson.day, TimetableLesson.start_time)
        return list((await self.db.execute(query)).scalars().all())

    async def get_timetable_for_user(self, user: User, day: str | None = None) -> list[TimetableLesson]:
        raw_group = _normalize_group(user.group_name)
        if not raw_group:
            return []

        # 1) Exact group match from profile.
        lessons = await self.get_timetable(raw_group, day=day)
        if lessons:
            return lessons

        # 2) Alias/prefix match (e.g. IT-202 -> IT-202-24).
        canonical = _canonical_group(raw_group)
        alias_candidates = {raw_group, canonical}
        alias_candidates = {x for x in alias_candidates if x}
        if alias_candidates:
            filters = [TimetableLesson.group_name.ilike(f"{x}%") for x in alias_candidates]
            query = select(TimetableLesson).where(or_(*filters))
            if day:
                query = query.where(TimetableLesson.day == day.lower())
            query = query.order_by(TimetableLesson.group_name, TimetableLesson.day, TimetableLesson.start_time)
            prefixed = list((await self.db.execute(query)).scalars().all())
            if prefixed:
                return prefixed

        # 3) Fallback: faculty + year pattern (e.g. IT-2xx).
        faculty = (user.faculty or "").strip().upper()
        if not faculty:
            return []

        pattern = f"{faculty}-{user.year}%"
        query = select(TimetableLesson).where(TimetableLesson.group_name.ilike(pattern))
        if day:
            query = query.where(TimetableLesson.day == day.lower())
        query = query.order_by(TimetableLesson.group_name, TimetableLesson.day, TimetableLesson.start_time)
        return list((await self.db.execute(query)).scalars().all())

    async def replace_timetable(self, lessons: list[dict]) -> None:
        await self.db.execute(delete(TimetableLesson))
        skipped_rows = 0
        for row in lessons:
            try:
                lesson = TimetableLesson(
                    group_name=row["group_name"],
                    subject=row["subject"],
                    teacher=row["teacher"],
                    room=row["room"],
                    day=row["day"].lower(),
                    start_time=_parse_time(row["start_time"]),
                    end_time=_parse_time(row["end_time"]),
                    status=row.get("status", "active"),
                )
                self.db.add(lesson)
            except Exception:
                skipped_rows += 1
                logger.exception("Skipping invalid timetable lesson row: %s", row)
        await self.db.commit()
        if skipped_rows:
            logger.warning("replace_timetable skipped %s invalid lesson rows", skipped_rows)
        await self.sync_teachers()

    async def sync_teachers(self) -> None:
        # Extract teacher->subjects and teacher->faculty candidates from timetable rows.
        stmt = select(TimetableLesson.teacher, TimetableLesson.subject, TimetableLesson.group_name)
        rows = (await self.db.execute(stmt)).all()

        teacher_subjects: dict[str, set[str]] = {}
        teacher_faculty_counts: dict[str, dict[str, int]] = {}
        skipped_source_rows = 0
        for teacher_name, subject, group_name in rows:
            clean_name = str(teacher_name or "").strip()
            if not clean_name:
                skipped_source_rows += 1
                logger.warning(
                    "Skipping teacher source row with empty teacher name: teacher=%r subject=%r group=%r",
                    teacher_name,
                    subject,
                    group_name,
                )
                continue

            if clean_name not in teacher_subjects:
                teacher_subjects[clean_name] = set()
            if subject:
                teacher_subjects[clean_name].add(str(subject).strip())

            token = str(group_name or "").strip().upper().split("-", 1)[0]
            if token:
                if clean_name not in teacher_faculty_counts:
                    teacher_faculty_counts[clean_name] = {}
                teacher_faculty_counts[clean_name][token] = teacher_faculty_counts[clean_name].get(token, 0) + 1

        failed_teacher_records = 0
        for name, subjects in teacher_subjects.items():
            subject_str = ", ".join(sorted(subjects))
            # Truncate subject string to 300 chars to prevent excessive data storage
            if len(subject_str) > 300:
                subject_str = subject_str[:297] + "..."
            
            faculty_votes = teacher_faculty_counts.get(name, {})
            inferred_faculty = max(faculty_votes, key=faculty_votes.get) if faculty_votes else None

            try:
                # Savepoint isolates a single teacher write failure and keeps overall sync progressing.
                async with self.db.begin_nested():
                    stmt = select(Teacher).where(Teacher.name == name)
                    teacher = (await self.db.execute(stmt)).scalar_one_or_none()
                    if teacher:
                        teacher.subject = subject_str
                        if inferred_faculty:
                            teacher.faculty = inferred_faculty
                    else:
                        teacher = Teacher(name=name, subject=subject_str, faculty=inferred_faculty)
                        self.db.add(teacher)
                    await self.db.flush()
            except Exception:
                failed_teacher_records += 1
                logger.exception("Failed syncing teacher record and continued: teacher=%s", name)
        await self.db.commit()
        logger.info(
            "sync_teachers completed: source_rows=%s teachers_processed=%s source_rows_skipped=%s teacher_records_failed=%s",
            len(rows),
            len(teacher_subjects),
            skipped_source_rows,
            failed_teacher_records,
        )

    async def get_teacher_by_name(self, name: str) -> Teacher | None:
        stmt = select(Teacher).where(Teacher.name == name)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_teacher_by_id(self, teacher_id: int) -> Teacher | None:
        return (await self.db.execute(select(Teacher).where(Teacher.id == teacher_id))).scalar_one_or_none()

    async def get_teachers(self, query: str | None = None) -> list[Teacher]:
        stmt = select(Teacher).order_by(Teacher.name)
        if query:
            stmt = stmt.where(Teacher.name.ilike(f"%{query}%"))
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_available_faculties(self) -> list[str]:
        rows = (await self.db.execute(select(distinct(TimetableLesson.group_name)))).scalars().all()
        faculties: set[str] = set()
        for group_name in rows:
            if not group_name:
                continue
            token = str(group_name).strip().upper().split("-", 1)[0]
            if token:
                faculties.add(token)
        result = sorted(faculties)
        logger.info("get_available_faculties rows=%s faculties=%s", len(rows), result)
        return result

    async def get_teacher_faculties(self) -> list[str]:
        rows = (
            await self.db.execute(
                select(distinct(Teacher.faculty))
                .where(Teacher.faculty.is_not(None))
                .order_by(Teacher.faculty)
            )
        ).scalars().all()
        return [str(x).strip().upper() for x in rows if str(x).strip()]

    async def get_teachers_by_faculty(self, faculty: str) -> list[Teacher]:
        normalized = (faculty or "").strip().upper()
        if not normalized:
            return []
        stmt = (
            select(Teacher)
            .where(Teacher.faculty.is_not(None))
            .where(func.upper(func.trim(Teacher.faculty)) == normalized)
            .order_by(Teacher.name)
        )
        teachers = list((await self.db.execute(stmt)).scalars().all())
        if teachers:
            return teachers

        # Fallback: derive teacher names from timetable groups for this faculty,
        # then map them to teacher cards by exact name.
        names_stmt = (
            select(distinct(TimetableLesson.teacher))
            .where(TimetableLesson.teacher.is_not(None))
            .where(func.trim(TimetableLesson.teacher) != "")
            .where(func.upper(func.trim(TimetableLesson.group_name)).like(f"{normalized}-%"))
        )
        names = [str(x).strip() for x in (await self.db.execute(names_stmt)).scalars().all() if str(x).strip()]
        if not names:
            return []

        teacher_stmt = select(Teacher).where(Teacher.name.in_(names)).order_by(Teacher.name)
        return list((await self.db.execute(teacher_stmt)).scalars().all())

    async def get_groups_by_faculty(self, faculty: str, page: int = 1, page_size: int = 20) -> tuple[list[str], int]:
        normalized = (faculty or "").strip().upper()
        if not normalized:
            return [], 0
        like_pattern = f"{normalized}-%"
        stmt = (
            select(distinct(TimetableLesson.group_name))
            .where(func.upper(func.trim(TimetableLesson.group_name)).like(like_pattern))
            .order_by(TimetableLesson.group_name)
        )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(stmt)).scalars().all()
        groups = [str(x).strip().upper() for x in rows if str(x).strip()]
        logger.info(
            "get_groups_by_faculty faculty=%s pattern=%s page=%s page_size=%s total=%s groups=%s",
            normalized,
            like_pattern,
            page,
            page_size,
            total,
            groups[:10],
        )
        return groups, total

    async def search_teachers(self, query: str | None = None, limit: int | None = 30) -> list[Teacher]:
        stmt = select(Teacher).order_by(Teacher.name)
        if query:
            stmt = stmt.where(Teacher.name.ilike(f"%{query}%"))
        if limit:
            stmt = stmt.limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def search_teachers_paginated(self, query: str | None = None, letter: str | None = None, page: int = 1, page_size: int = 50) -> tuple[list[Teacher], int]:
        stmt = select(Teacher).order_by(Teacher.name)
        if query:
            stmt = stmt.where(Teacher.name.ilike(f"%{query}%"))
        if letter:
            stmt = stmt.where(Teacher.name.ilike(f"{letter}%"))
        
        # Count total
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0
        
        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        results = list((await self.db.execute(stmt)).scalars().all())
        return results, total

    async def get_teacher_timetable(self, teacher_name: str, day: str | None = None) -> list[TimetableLesson]:
        teacher_query = (teacher_name or "").strip()
        if not teacher_query:
            return []

        # First try exact match for deterministic results.
        stmt = select(TimetableLesson).where(TimetableLesson.teacher == teacher_query)
        if day:
            stmt = stmt.where(TimetableLesson.day == day.lower())
        stmt = stmt.order_by(TimetableLesson.day, TimetableLesson.start_time, TimetableLesson.group_name)
        lessons = list((await self.db.execute(stmt)).scalars().all())
        if lessons:
            return lessons

        # Fallback to partial match.
        stmt = select(TimetableLesson).where(TimetableLesson.teacher.ilike(f"%{teacher_query}%"))
        if day:
            stmt = stmt.where(TimetableLesson.day == day.lower())
        stmt = stmt.order_by(TimetableLesson.teacher, TimetableLesson.day, TimetableLesson.start_time, TimetableLesson.group_name)
        lessons = list((await self.db.execute(stmt)).scalars().all())
        if lessons:
            return lessons

        # Last fallback: token-based contains matching regardless of name word order.
        tokens = [x for x in teacher_query.split() if x]
        if not tokens:
            return []
        token_filters = [TimetableLesson.teacher.ilike(f"%{token}%") for token in tokens]
        stmt = select(TimetableLesson).where(and_(*token_filters))
        if day:
            stmt = stmt.where(TimetableLesson.day == day.lower())
        stmt = stmt.order_by(TimetableLesson.teacher, TimetableLesson.day, TimetableLesson.start_time, TimetableLesson.group_name)
        return list((await self.db.execute(stmt)).scalars().all())

    async def toggle_favorite_teacher(self, user_id: int, teacher_id: int) -> bool:
        """Returns True if added, False if removed."""
        stmt = select(FavoriteTeacher).where(FavoriteTeacher.user_id == user_id, FavoriteTeacher.teacher_id == teacher_id)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            await self.db.delete(existing)
            await self.db.commit()
            return False
        
        favorite = FavoriteTeacher(user_id=user_id, teacher_id=teacher_id)
        self.db.add(favorite)
        await self.db.commit()
        return True

    async def toggle_teacher_notifications(self, user_id: int, teacher_id: int) -> bool:
        stmt = select(FavoriteTeacher).where(FavoriteTeacher.user_id == user_id, FavoriteTeacher.teacher_id == teacher_id)
        fav = (await self.db.execute(stmt)).scalar_one_or_none()
        if fav:
            fav.notifications_enabled = not fav.notifications_enabled
            await self.db.commit()
            return fav.notifications_enabled
        return False

    async def toggle_teacher_pin(self, user_id: int, teacher_id: int) -> bool:
        stmt = select(FavoriteTeacher).where(FavoriteTeacher.user_id == user_id, FavoriteTeacher.teacher_id == teacher_id)
        fav = (await self.db.execute(stmt)).scalar_one_or_none()
        if fav:
            fav.pinned = not fav.pinned
            await self.db.commit()
            return fav.pinned
        return False

    async def get_favorite_teachers(self, user_id: int) -> list[FavoriteTeacher]:
        stmt = (
            select(FavoriteTeacher)
            .options(selectinload(FavoriteTeacher.teacher))
            .where(FavoriteTeacher.user_id == user_id)
            .order_by(FavoriteTeacher.pinned.desc(), FavoriteTeacher.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def add_recent_search(self, user_id: int, teacher_id: int) -> None:
        # Check if already in recent searches
        stmt = select(RecentSearch).where(RecentSearch.user_id == user_id, RecentSearch.teacher_id == teacher_id)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.created_at = datetime.now() # Update timestamp
        else:
            new_search = RecentSearch(user_id=user_id, teacher_id=teacher_id)
            self.db.add(new_search)
        
        await self.db.commit()
        
        # Trim to last 5
        stmt = select(RecentSearch).where(RecentSearch.user_id == user_id).order_by(RecentSearch.created_at.desc())
        all_searches = (await self.db.execute(stmt)).scalars().all()
        if len(all_searches) > 5:
            for s in all_searches[5:]:
                await self.db.delete(s)
            await self.db.commit()

    async def get_recent_searches(self, user_id: int) -> list[Teacher]:
        stmt = (
            select(Teacher)
            .join(RecentSearch, RecentSearch.teacher_id == Teacher.id)
            .where(RecentSearch.user_id == user_id)
            .order_by(RecentSearch.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def room_lookup_now(self, room: str, day: str, current_time: time) -> TimetableLesson | None:
        stmt = (
            select(TimetableLesson)
            .where(TimetableLesson.room == room)
            .where(TimetableLesson.day == day)
            .where(TimetableLesson.start_time <= current_time)
            .where(TimetableLesson.end_time >= current_time)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_exam_deadlines(self, group_name: str, subject: str | None = None) -> list[ExamDeadline]:
        raw_group = _normalize_group(group_name)
        canonical = _canonical_group(raw_group)
        alias_candidates = {raw_group, canonical}
        alias_candidates = {x for x in alias_candidates if x}

        if alias_candidates:
            filters = [ExamDeadline.group_name.ilike(f"{x}%") for x in alias_candidates]
            stmt = select(ExamDeadline).where(or_(*filters)).order_by(ExamDeadline.due_date)
        else:
            stmt = select(ExamDeadline).order_by(ExamDeadline.due_date)

        if subject:
            stmt = stmt.where(ExamDeadline.subject.ilike(f"%{subject}%"))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_exam_deadlines_for_user(self, user: User, subject: str | None = None) -> list[ExamDeadline]:
        raw_group = _normalize_group(user.group_name)
        canonical = _canonical_group(raw_group)
        faculty = (user.faculty or "").strip().upper()
        year = user.year

        filters = []
        for token in {raw_group, canonical}:
            if token:
                filters.append(ExamDeadline.group_name.ilike(f"{token}%"))
        if faculty and year:
            filters.append(ExamDeadline.group_name.ilike(f"{faculty}-{year}%"))

        stmt = select(ExamDeadline)
        if filters:
            stmt = stmt.where(or_(*filters))
        if subject:
            stmt = stmt.where(ExamDeadline.subject.ilike(f"%{subject}%"))
        stmt = stmt.order_by(ExamDeadline.due_date)

        return list((await self.db.execute(stmt)).scalars().all())

    async def add_update_log(self, group_name: str, change_type: str, details: str) -> None:
        self.db.add(UpdateLog(group_name=group_name, change_type=change_type, details=details))
        await self.db.commit()

    async def get_dashboard_stats(self) -> dict:
        total_users = len((await self.db.execute(select(User.id))).scalars().all())
        active_users = len((await self.db.execute(select(User.id).where(User.is_active.is_(True)))).scalars().all())
        groups_count = len(set((await self.db.execute(select(User.group_name))).scalars().all()))
        updates = list((await self.db.execute(select(UpdateLog).order_by(UpdateLog.created_at.desc()).limit(10))).scalars().all())
        return {
            "total_users": total_users,
            "active_users": active_users,
            "groups_count": groups_count,
            "last_updates": [
                {
                    "group": x.group_name,
                    "change_type": x.change_type,
                    "details": x.details,
                    "created_at": x.created_at.isoformat() if x.created_at else None,
                }
                for x in updates
            ],
        }
