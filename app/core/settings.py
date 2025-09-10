import os
from functools import lru_cache
from typing import Optional

try:
    # Optional: enable .env in local dev; harmless in prod
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


class Settings:
    def __init__(self) -> None:
        self.api_id: int = int(os.getenv("API_ID", "0"))
        self.api_hash: str = os.getenv("API_HASH", "")
        self.bot_token: str = os.getenv("BOT_TOKEN", "")
        self.database_url: str = os.getenv("DATABASE_URL", "")
        self.webhook_base: str = os.getenv("WEBHOOK_BASE", "")
        self.port: int = int(os.getenv("PORT", "8080"))
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")
        self.webhook_path: str = os.getenv("WEBHOOK_PATH", "/telegram/webhook")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

