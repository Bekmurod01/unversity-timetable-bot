from dataclasses import dataclass


@dataclass
class ChangeItem:
    group_name: str
    change_type: str
    details: str


def _lesson_key(lesson: dict) -> tuple:
    return (
        lesson.get("group_name"),
        lesson.get("day"),
        lesson.get("start_time"),
        lesson.get("subject"),
    )


def detect_timetable_changes(old_lessons: list[dict], new_lessons: list[dict]) -> list[ChangeItem]:
    old_map = {_lesson_key(x): x for x in old_lessons}
    new_map = {_lesson_key(x): x for x in new_lessons}

    changes: list[ChangeItem] = []

    for key, old_item in old_map.items():
        if key not in new_map:
            changes.append(
                ChangeItem(
                    group_name=old_item["group_name"],
                    change_type="lesson_removed",
                    details=f"Removed {old_item['subject']} on {old_item['day']} at {old_item['start_time']}",
                )
            )
            continue

        new_item = new_map[key]
        room_changed = old_item.get("room") != new_item.get("room")
        teacher_changed = old_item.get("teacher") != new_item.get("teacher")
        end_changed = old_item.get("end_time") != new_item.get("end_time")

        if room_changed or teacher_changed or end_changed:
            changes.append(
                ChangeItem(
                    group_name=new_item["group_name"],
                    change_type="lesson_changed",
                    details=(
                        f"{new_item['subject']} {new_item['day']} {new_item['start_time']} updated: "
                        f"room {old_item.get('room')}->{new_item.get('room')}, "
                        f"teacher {old_item.get('teacher')}->{new_item.get('teacher')}"
                    ),
                )
            )

    for key, new_item in new_map.items():
        if key not in old_map:
            changes.append(
                ChangeItem(
                    group_name=new_item["group_name"],
                    change_type="lesson_added",
                    details=f"Added {new_item['subject']} on {new_item['day']} at {new_item['start_time']}",
                )
            )

    return changes
