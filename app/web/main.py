import logging
from typing import Any, Dict, Optional
import httpx

from fastapi import FastAPI, Request, Response, status

from app.core.logging_config import configure_logging
from app.core.settings import get_settings
from app.core.background import BackgroundTaskQueue
from app.bot.client import get_bot_client
from app.db.migrate import run_migrations
from app.db.pool import get_pool, close_pool


configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
settings = get_settings()
bg_queue = BackgroundTaskQueue()


@app.on_event("startup")
async def on_startup() -> None:
    await run_migrations()
    await get_pool()
    await bg_queue.start()

    bot = get_bot_client()
    await bot.start()

    if settings.webhook_base and settings.bot_token:
        webhook_url = f"{settings.webhook_base.rstrip('/')}{settings.webhook_path}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                data = {
                    "url": webhook_url,
                    "allowed_updates": "[\"message\",\"callback_query\"]",
                    "drop_pending_updates": "true",
                    "max_connections": "40",
                }
                if settings.webhook_secret:
                    data["secret_token"] = settings.webhook_secret
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.bot_token}/setWebhook",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            ok = False
            try:
                payload = resp.json()
                ok = bool(payload.get("ok"))
            except Exception:
                payload = {"status_code": resp.status_code, "text": resp.text}
            if ok:
                logger.info("Webhook set to %s", webhook_url)
            else:
                logger.error("Failed to set webhook: %s", payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to call setWebhook: %s", exc)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    bot = get_bot_client()
    try:
        await bot.stop()
    except Exception:  # noqa: BLE001
        pass
    await bg_queue.stop()
    await close_pool()


@app.post(settings.webhook_path)
async def telegram_webhook(request: Request) -> Response:
    """Receive Telegram updates and handle minimal /start welcome via Pyrogram send_message."""
    bot = get_bot_client()
    # Optional verification of Telegram secret token header
    if settings.webhook_secret:
        received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if received_secret != settings.webhook_secret:
            return Response(status_code=status.HTTP_403_FORBIDDEN)

    try:
        update: Dict[str, Any] = await request.json()
    except Exception:  # noqa: BLE001
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    message: Optional[Dict[str, Any]] = update.get("message")
    if message is not None:
        chat = message.get("chat") or {}
        from_user = message.get("from") or {}
        chat_id = chat.get("id")
        text = message.get("text", "") or ""

        if chat_id is not None:
            # Enqueue background processing to avoid blocking webhook
            async def job() -> None:
                pool = await get_pool()
                await pool.execute(
                    """
                    INSERT INTO users (user_id, username, first_name, last_name, language_code)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        language_code = EXCLUDED.language_code
                    """,
                    int(from_user.get("id", chat_id)),
                    from_user.get("username"),
                    from_user.get("first_name"),
                    from_user.get("last_name"),
                    from_user.get("language_code"),
                )

                if text.startswith("/start"):
                    await bot.send_message(chat_id=chat_id, text="مرحبًا بك في البوت! ✨")

            bg_queue.enqueue(job)

    return Response(status_code=status.HTTP_200_OK)


@app.get("/")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

