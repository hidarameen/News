import logging
from typing import Optional

from pyrogram import Client

from app.core.settings import get_settings


logger = logging.getLogger(__name__)


_client: Optional[Client] = None


def get_bot_client() -> Client:
    global _client
    if _client is None:
        settings = get_settings()
        _client = Client(
            name="bot",
            api_id=settings.api_id,
            api_hash=settings.api_hash,
            bot_token=settings.bot_token,
            workdir="/app/.pyrogram",
            in_memory=True,
        )
    return _client

