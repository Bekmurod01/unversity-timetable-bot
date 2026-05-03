from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, BaseModel
import os
from dotenv import load_dotenv



BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")



class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "dev")
    database_url: str = os.getenv("DATABASE_URL", "")
    # Redis connection for FSM/session storage (e.g. redis://:pass@host:port/0)
    redis_url: str = os.getenv("REDIS_URL", os.getenv("REDIS_DSN", ""))
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_telegram_ids: str = os.getenv("ADMIN_TELEGRAM_IDS", "")
    snapshot_source: str = os.getenv("SNAPSHOT_SOURCE", "mock_data/timetable_snapshot.json")
    edupage_sync_enabled: bool = os.getenv("EDUPAGE_SYNC_ENABLED", "false").lower() == "true"
    edupage_regulartt_url: str = os.getenv("EDUPAGE_REGULARTT_URL", "")
    edupage_regulartt_term: str = os.getenv("EDUPAGE_REGULARTT_TERM", "13")
    edupage_cookie: str = os.getenv("EDUPAGE_COOKIE", "")
    edupage_extra_headers_json: str = os.getenv("EDUPAGE_EXTRA_HEADERS_JSON", "")
    edupage_ssl_verify: bool = os.getenv("EDUPAGE_SSL_VERIFY", "true").lower() == "true"
    polling_interval_seconds: int = int(os.getenv("POLLING_INTERVAL_SECONDS", "120"))
    timezone: str = os.getenv("TIMEZONE", "Asia/Tashkent")
    secret_key: str = os.getenv("SECRET_KEY", "change_me")
    webhook_base_url: str = os.getenv("WEBHOOK_BASE_URL", os.getenv("RENDER_EXTERNAL_URL", ""))
    webhook_path: str = os.getenv("WEBHOOK_PATH", "/webhook")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")


    @property
    def admin_ids(self) -> set[int]:
        if not self.admin_telegram_ids.strip():
            return set()
        return {int(x.strip()) for x in self.admin_telegram_ids.split(",") if x.strip()}


    @property
    def edupage_extra_headers(self) -> dict[str, str]:
        if not self.edupage_extra_headers_json.strip():
            return {}
        try:
            import json
            parsed: Any = json.loads(self.edupage_extra_headers_json)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            return {}
        return {}


    @property
    def webhook_url(self) -> str:
        base = (self.webhook_base_url or "").strip().rstrip("/")
        path = (self.webhook_path or "/webhook").strip()
        if not path.startswith("/"):
            path = f"/{path}"
        if not base:
            return ""
        return f"{base}{path}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
