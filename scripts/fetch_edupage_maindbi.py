import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch EduPage mainDBI timetable data")
    parser.add_argument("--school", default="ciu", help="EduPage school subdomain")
    parser.add_argument("--year", type=int, default=2025, help="School year DBI id")
    parser.add_argument("--datefrom", required=True, help="Date from, format YYYY-MM-DD")
    parser.add_argument("--dateto", required=True, help="Date to, format YYYY-MM-DD")
    parser.add_argument("--cookie", required=True, help="Browser cookie header value, e.g. PHPSESSID=...")
    parser.add_argument("--gsh", default="00000000", help="EduPage __gsh value")
    parser.add_argument("--output", default="mock_data/edupage_maindbi.json", help="Output JSON file")
    return parser.parse_args()


def build_payload(year: int, datefrom: str, dateto: str, gsh: str) -> dict:
    return {
        "__args": [
            None,
            year,
            {"vt_filter": {"datefrom": datefrom, "dateto": dateto}},
            {
                "op": "fetch",
                "needed_part": {
                    "teachers": ["short", "name", "firstname", "lastname", "callname", "subname", "code", "cb_hidden", "expired"],
                    "classes": ["short", "name", "firstname", "lastname", "callname", "subname", "code", "classroomid"],
                    "classrooms": ["short", "name", "firstname", "lastname", "callname", "subname", "code"],
                    "igroups": ["short", "name", "firstname", "lastname", "callname", "subname", "code"],
                    "students": ["short", "name", "firstname", "lastname", "callname", "subname", "code", "classid"],
                    "subjects": ["short", "name", "firstname", "lastname", "callname", "subname", "code"],
                    "events": ["typ", "name"],
                    "event_types": ["name", "icon"],
                    "subst_absents": ["date", "absent_typeid", "groupname"],
                    "periods": ["short", "name", "firstname", "lastname", "callname", "subname", "code", "period", "starttime", "endtime"],
                    "dayparts": ["starttime", "endtime"],
                    "dates": ["tt_num", "tt_day"],
                },
                "needed_combos": {},
            },
        ],
        "__gsh": gsh,
    }


def main() -> int:
    args = parse_args()
    url = f"https://{args.school}.edupage.org/rpr/server/maindbi.js?__func=mainDBIAccessor"
    payload = build_payload(args.year, args.datefrom, args.dateto, args.gsh)
    body = json.dumps(payload).encode("utf-8")

    headers = {
        "accept": "*/*",
        "content-type": "application/json; charset=UTF-8",
        "origin": f"https://{args.school}.edupage.org",
        "referer": f"https://{args.school}.edupage.org/",
        "user-agent": "Mozilla/5.0",
        "Cookie": args.cookie,
    }

    request = Request(url=url, data=body, method="POST", headers=headers)
    with urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8", errors="replace")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    parsed = json.loads(text)
    output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")

    if isinstance(parsed, dict) and "r" in parsed and isinstance(parsed["r"], dict):
        tables = parsed["r"].get("tables", [])
        print(f"Saved data to {output_path}")
        print(f"Tables returned: {len(tables)}")
    else:
        print(f"Saved response to {output_path}")
        print(f"Top-level keys: {', '.join(parsed.keys()) if isinstance(parsed, dict) else 'non-dict response'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())