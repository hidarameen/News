import logging
from typing import Optional

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.enums import ParseMode

from app.db.pool import get_pool


logger = logging.getLogger(__name__)


class FooterManager:
    """Manage per-channel footer settings."""

    @staticmethod
    async def upsert(user_id: int, channel_id: int, text: Optional[str], enabled: bool, parse_mode: str = "markdown") -> None:
        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO channel_settings (user_id, channel_id, footer_enabled, footer_text, parse_mode)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, channel_id) DO UPDATE SET
                        footer_enabled = EXCLUDED.footer_enabled,
                        footer_text = EXCLUDED.footer_text,
                        parse_mode = EXCLUDED.parse_mode,
                        updated_at = NOW()
                    """,
                    (user_id, channel_id, enabled, text, parse_mode)
                )
                await conn.commit()

    @staticmethod
    async def get(user_id: int, channel_id: int) -> Optional[dict]:
        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT footer_enabled, footer_text, parse_mode
                    FROM channel_settings
                    WHERE user_id = %s AND channel_id = %s
                    """,
                    (user_id, channel_id)
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return {"footer_enabled": row[0], "footer_text": row[1], "parse_mode": row[2]}


async def footer_menu(client: Client, message: Message, user_id: int, channel_id: int) -> None:
    settings = await FooterManager.get(user_id, channel_id) or {"footer_enabled": False, "footer_text": None, "parse_mode": "markdown"}
    enabled = "✅ مفعّل" if settings["footer_enabled"] else "❌ معطّل"
    text_preview = settings["footer_text"] or "—"
    body = (
        f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
   🧩 إعدادات الفوتر
╰━━━━━━━━━━━━━━━━━━━━━╯

الحالة: {enabled}
النص الحالي:
{text_preview}

━━━━━━━━━━━━━━━━━━━━━
اختر إجراء:
"""
    )
    kb = [
        [InlineKeyboardButton("✏️ تعديل النص", callback_data=f"footer_edit_{channel_id}")],
        [InlineKeyboardButton("🔄 تبديل التفعيل", callback_data=f"footer_toggle_{channel_id}")],
        [InlineKeyboardButton("🗑 حذف النص", callback_data=f"footer_clear_{channel_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="settings_menu")],
    ]
    await message.edit_text(body, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)


async def handle_footer_callback(client: Client, callback_query: CallbackQuery) -> None:
    data = callback_query.data
    user_id = callback_query.from_user.id
    if data.startswith("footer_edit_"):
        channel_id = int(data.split("_")[-1])
        await callback_query.message.edit_text(
            """
أرسل نص الفوتر الجديد. لإلغاء: /cancel
""",
            parse_mode=ParseMode.MARKDOWN,
        )
        await client.set_user_state(user_id, f"footer_edit:{channel_id}")
    elif data.startswith("footer_toggle_"):
        channel_id = int(data.split("_")[-1])
        current = await FooterManager.get(user_id, channel_id) or {"footer_enabled": False, "footer_text": None, "parse_mode": "markdown"}
        await FooterManager.upsert(user_id, channel_id, current.get("footer_text"), not current.get("footer_enabled", False), current.get("parse_mode", "markdown"))
        await callback_query.answer("تم التبديل")
        await footer_menu(client, callback_query.message, user_id, channel_id)
    elif data.startswith("footer_clear_"):
        channel_id = int(data.split("_")[-1])
        current = await FooterManager.get(user_id, channel_id) or {"parse_mode": "markdown"}
        await FooterManager.upsert(user_id, channel_id, None, False, current.get("parse_mode", "markdown"))
        await callback_query.answer("تم حذف النص")
        await footer_menu(client, callback_query.message, user_id, channel_id)


async def handle_footer_text_input(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    state = await client.get_user_state(user_id)
    if not state or not state.startswith("footer_edit:"):
        return
    if message.text and message.text.startswith("/cancel"):
        await client.set_user_state(user_id, None)
        await message.reply_text("تم الإلغاء")
        return
    channel_id = int(state.split(":", 1)[1])
    text = message.text or ""
    await FooterManager.upsert(user_id, channel_id, text, True, "markdown")
    await client.set_user_state(user_id, None)
    await message.reply_text("تم حفظ نص الفوتر", parse_mode=ParseMode.MARKDOWN)


__all__ = [
    "FooterManager",
    "footer_menu",
    "handle_footer_callback",
    "handle_footer_text_input",
]

