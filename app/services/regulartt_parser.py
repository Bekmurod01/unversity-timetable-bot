from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Any


DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def _table_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {t["id"]: t for t in payload["r"]["dbiAccessorRes"]["tables"]}


def _to_name_map(rows: Iterable[dict[str, Any]], value_field: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        key = str(row.get("id", ""))
        value = str(row.get(value_field, "")).strip() or key
        out[key] = value
    return out


def normalize_group_name(raw: str) -> str:
    text = (raw or "").strip().upper()
    if not text:
        return ""

    # EduPage class names can look like "*130 IT-202-24"; keep only the group token.
    token = text.split()[-1]
    token = token.strip("* ")
    return token


def canonical_group_alias(group_name: str) -> str:
    # Alias IT-202-24 -> IT-202 so user profile matching is resilient.
    return re.sub(r"-\d{2}$", "", group_name)


def parse_regulartt_lessons(payload: dict[str, Any], status: str = "active") -> list[dict[str, str]]:
    tables = _table_map(payload)

    periods = {str(x["period"]): x for x in tables["periods"]["data_rows"]}
    subjects = _to_name_map(tables["subjects"]["data_rows"], "name")
    teachers = _to_name_map(tables["teachers"]["data_rows"], "name")
    rooms = _to_name_map(tables["classrooms"]["data_rows"], "name")
    classes = {str(x["id"]): normalize_group_name(str(x.get("name", ""))) for x in tables["classes"]["data_rows"]}

    lessons_by_id = {str(x["id"]): x for x in tables["lessons"]["data_rows"]}
    cards = tables["cards"]["data_rows"]

    rows: list[dict[str, str]] = []

    for card in cards:
        lesson = lessons_by_id.get(str(card.get("lessonid", "")))
        if not lesson:
            continue

        period = periods.get(str(card.get("period", "")))
        if not period:
            continue

        subject = subjects.get(str(lesson.get("subjectid", "")), "UNKNOWN")

        teacher_ids = [str(x) for x in lesson.get("teacherids", [])]
        teacher = ", ".join(teachers.get(tid, tid) for tid in teacher_ids) if teacher_ids else "UNKNOWN"

        room_ids = [str(x) for x in card.get("classroomids", [])]
        room = ", ".join(rooms.get(rid, rid) for rid in room_ids) if room_ids else "UNKNOWN"

        lesson_groups: list[str] = []
        for class_id in lesson.get("classids", []):
            group_name = classes.get(str(class_id), "")
            if group_name:
                lesson_groups.append(group_name)

        if not lesson_groups:
            continue

        days_mask = str(card.get("days", ""))
        start = str(period.get("starttime", "09:00"))
        end = str(period.get("endtime", "10:00"))

        for idx, flag in enumerate(days_mask[: len(DAY_NAMES)]):
            if flag != "1":
                continue

            day_name = DAY_NAMES[idx]
            for group_name in lesson_groups:
                rows.append(
                    {
                        "group_name": group_name,
                        "subject": subject,
                        "teacher": teacher,
                        "room": room,
                        "day": day_name,
                        "start_time": start,
                        "end_time": end,
                        "status": status,
                    }
                )

                alias = canonical_group_alias(group_name)
                if alias and alias != group_name:
                    rows.append(
                        {
                            "group_name": alias,
                            "subject": subject,
                            "teacher": teacher,
                            "room": room,
                            "day": day_name,
                            "start_time": start,
                            "end_time": end,
                            "status": status,
                        }
                    )

    # Deduplicate by stable key to avoid uniqueness conflicts and duplicate aliases.
    uniq: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["group_name"], row["day"], row["start_time"], row["subject"])
        if key not in uniq:
            uniq[key] = row
    return list(uniq.values())