import logging
import asyncio
from typing import Optional

from pyrogram import Client, idle

from app.core.settings import get_settings
from app.db.migrate import run_migrations


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


async def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # تشغيل migrations
    logger.info("Running database migrations...")
    await run_migrations()
    
    # استيراد المعالجات (handlers)
    from app.bot import handlers  # noqa: F401
    
    # الحصول على البوت وتشغيله
    bot = get_bot_client()
    
    logger.info("Starting bot...")
    await bot.start()
    logger.info("Bot started successfully!")
    
    # إبقاء البوت يعمل
    await idle()
    
    # إيقاف البوت
    await bot.stop()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    # إعداد logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # تشغيل البوت
    asyncio.run(main())

