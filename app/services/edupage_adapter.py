import asyncio
import json
import logging
from pathlib import Path
import ssl
from typing import Any
from urllib import request

from app.config import get_settings
from app.services.regulartt_parser import parse_regulartt_lessons


class EduPageAdapter:
    """Adapter boundary for future EduPage API or scraping integration."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)

    def _load_local_snapshot(self) -> list[dict[str, Any]]:
        source = Path(self.settings.snapshot_source)
        if not source.exists():
            self.logger.warning("Snapshot source not found: %s", source)
            return []

        with source.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)

        if isinstance(data, dict) and "r" in data and "dbiAccessorRes" in data.get("r", {}):
            lessons = parse_regulartt_lessons(data)
            self.logger.info("Loaded %s lessons from EduPage-style local snapshot", len(lessons))
            return lessons
        if isinstance(data, dict) and "lessons" in data:
            lessons = data["lessons"]
            self.logger.info("Loaded %s lessons from normalized local snapshot", len(lessons))
            return lessons
        if isinstance(data, list):
            self.logger.info("Loaded %s lessons from list local snapshot", len(data))
            return data
        self.logger.warning("Unsupported snapshot format in %s", source)
        return []

    async def _fetch_regulartt_live(self) -> list[dict[str, Any]]:
        if not self.settings.edupage_sync_enabled:
            return []
        if not self.settings.edupage_regulartt_url.strip():
            return []

        body = json.dumps({"__args": [None, self.settings.edupage_regulartt_term], "__gsh": "00000000"}).encode("utf-8")
        headers = {
            "content-type": "application/json",
            "x-requested-with": "XMLHttpRequest",
            "user-agent": "Mozilla/5.0",
        }
        if self.settings.edupage_cookie.strip():
            headers["cookie"] = self.settings.edupage_cookie
        headers.update(self.settings.edupage_extra_headers)

        req = request.Request(self.settings.edupage_regulartt_url, data=body, headers=headers, method="POST")
        context = None
        if not self.settings.edupage_ssl_verify:
            context = ssl._create_unverified_context()

        def _do_request() -> dict[str, Any]:
            self.logger.info(
                "EduPage request: url=%s term=%s cookie=%s ssl_verify=%s",
                self.settings.edupage_regulartt_url,
                self.settings.edupage_regulartt_term,
                bool(self.settings.edupage_cookie.strip()),
                self.settings.edupage_ssl_verify,
            )
            with request.urlopen(req, timeout=30, context=context) as resp:
                self.logger.info("EduPage response status=%s", getattr(resp, "status", "unknown"))
                payload = resp.read().decode("utf-8-sig")
            return json.loads(payload)

        payload = await asyncio.to_thread(_do_request)
        lessons = parse_regulartt_lessons(payload)
        self.logger.info("Parsed %s lessons from EduPage live payload", len(lessons))

        if lessons:
            source = Path(self.settings.snapshot_source)
            source.parent.mkdir(parents=True, exist_ok=True)
            with source.open("w", encoding="utf-8") as f:
                json.dump({"lessons": lessons}, f, ensure_ascii=False)
            self.logger.info("Updated local snapshot at %s", source)

        return lessons

    async def fetch_timetable_snapshot(self) -> list[dict[str, Any]]:
        try:
            live = await self._fetch_regulartt_live()
            if live:
                return live
            self.logger.warning("EduPage live fetch returned empty result, falling back to local snapshot")
        except Exception:
            self.logger.exception("EduPage live fetch failed, falling back to local snapshot")
        return self._load_local_snapshot()
