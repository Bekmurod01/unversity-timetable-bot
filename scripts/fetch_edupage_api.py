import argparse
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch raw data from EduPage RPC API")
    parser.add_argument("--school", default="ciu", help="EduPage school subdomain, e.g. ciu")
    parser.add_argument(
        "--module-path",
        default="timetable/server/ttdbi.js",
        help="RPC module path, e.g. timetable/server/ttdbi.js or rpr/server/maindbi.js",
    )
    parser.add_argument("--func", default="timetableDBIAccessor", help="RPC function name")
    parser.add_argument(
        "--args-json",
        default='["1", {}]',
        help='JSON array for __args, e.g. "[\"1\", {}]"',
    )
    parser.add_argument("--gsh", default="00000000", help="EduPage __gsh value")
    parser.add_argument("--esid", default="", help="Optional ESID query value")
    parser.add_argument("--cookie", default="", help="Optional Cookie header from browser session")
    parser.add_argument(
        "--output",
        default="mock_data/edupage_api_response.json",
        help="Path to write raw API response JSON",
    )
    return parser.parse_args()


def build_url(school: str, module_path: str, func: str, esid: str) -> str:
    base = f"https://{school}.edupage.org/{module_path}?__func={func}"
    if esid:
        return f"{base}&ESID={esid}"
    return base


def main() -> int:
    args = parse_args()
    try:
        rpc_args = json.loads(args.args_json)
    except json.JSONDecodeError as exc:
        print(f"Invalid --args-json: {exc}")
        return 2

    if not isinstance(rpc_args, list):
        print("--args-json must decode to a JSON array")
        return 2

    url = build_url(args.school, args.module_path, args.func, args.esid)
    payload: dict[str, Any] = {
        "__args": rpc_args,
        "__gsh": args.gsh,
    }
    body = json.dumps(payload).encode("utf-8")

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0",
    }
    if args.cookie:
        headers["Cookie"] = args.cookie

    request = Request(url=url, data=body, method="POST", headers=headers)

    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        print(f"HTTP error: {exc.code}")
        print(err)
        return 1
    except URLError as exc:
        print(f"Request error: {exc}")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        parsed = json.loads(raw)
        output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved parsed JSON to {output_path}")
        if isinstance(parsed, dict):
            print(f"Top-level keys: {', '.join(parsed.keys())}")
            if "em" in parsed:
                print(f"Server message: {parsed['em']}")
    except json.JSONDecodeError:
        output_path.write_text(raw, encoding="utf-8")
        print(f"Saved raw text response to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())