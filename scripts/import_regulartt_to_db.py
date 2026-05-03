import argparse
import json
from pathlib import Path
import re

import psycopg

from app.services.regulartt_parser import parse_regulartt_lessons


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import regulartt lesson slots into timetable_lessons")
    parser.add_argument("--input", default="mock_data/regulartt_live.json", help="Path to regulartt JSON")
    parser.add_argument("--all-groups", action="store_true", help="Import all groups found in payload")
    parser.add_argument("--class-contains", help="Substring to match class name, e.g. IT-202")
    parser.add_argument("--target-group", help="Group name to store in DB, e.g. IT-202")
    parser.add_argument(
        "--database-url",
        default="postgresql://postgres:postgres@localhost:5432/university_bot",
        help="Postgres URL reachable from host",
    )
    return parser.parse_args()


def _canonical_token(raw_name: str) -> str:
    text = (raw_name or "").strip().upper()
    token = text.split()[-1] if text else ""
    return token.strip("* ")


def _is_target_group(row_group: str, target_group: str) -> bool:
    rg = (row_group or "").strip().upper()
    tg = (target_group or "").strip().upper()
    if not rg or not tg:
        return False
    return rg == tg or re.sub(r"-\d{2}$", "", rg) == tg


def main() -> int:
    args = parse_args()

    if not args.all_groups and not (args.class_contains and args.target_group):
        raise SystemExit("Provide --all-groups OR both --class-contains and --target-group")

    raw = Path(args.input).read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    converted = parse_regulartt_lessons(data)

    if not converted:
        raise SystemExit("No lesson cards were parsed from regulartt payload")

    filtered = converted
    if not args.all_groups:
        class_rows = data["r"]["dbiAccessorRes"]["tables"]
        classes_table = next((x for x in class_rows if x.get("id") == "classes"), {"data_rows": []})
        class_matches = [
            x for x in classes_table["data_rows"] if args.class_contains.lower() in str(x.get("name", "")).lower()
        ]
        if not class_matches:
            raise SystemExit(f"No class found containing: {args.class_contains}")

        target_groups = {_canonical_token(str(x.get("name", ""))) for x in class_matches}
        target_groups.add((args.target_group or "").strip().upper())
        filtered = [x for x in converted if any(_is_target_group(x["group_name"], g) for g in target_groups if g)]

        # Rebind all selected rows to explicit target group for backward compatibility.
        filtered = [{**x, "group_name": (args.target_group or "").strip().upper()} for x in filtered]

    if not filtered:
        raise SystemExit("No lesson cards matched selected target")

    dedup_map: dict[tuple[str, str, str, str], tuple[str, str, str, str, str, str, str, str]] = {}
    for x in filtered:
        key = (x["group_name"], x["day"], x["start_time"], x["subject"])
        dedup_map.setdefault(
            key,
            (
                x["group_name"],
                x["subject"],
                x["teacher"],
                x["room"],
                x["day"],
                x["start_time"],
                x["end_time"],
                x["status"],
            ),
        )
    dedup = list(dedup_map.values())

    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            if args.all_groups:
                cur.execute("DELETE FROM timetable_lessons")
            else:
                cur.execute("DELETE FROM timetable_lessons WHERE group_name = %s", ((args.target_group or "").strip().upper(),))
            cur.executemany(
                """
                INSERT INTO timetable_lessons (group_name, subject, teacher, room, day, start_time, end_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                dedup,
            )
        conn.commit()

    print(f"Inserted lessons: {len(dedup)}")
    if args.all_groups:
        print("Mode: all groups")
    else:
        print(f"Mode: single group -> {(args.target_group or '').strip().upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())