import logging
from typing import Any, Dict, Optional
import httpx

from fastapi import FastAPI, Request, Response, status
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ParseMode

from app.core.logging_config import configure_logging
from app.core.settings import get_settings
from app.core.background import BackgroundTaskQueue
from app.bot.client import get_bot_client
from app.db.migrate import run_migrations
from app.bot.channels import ChannelManager
from app.bot.header import header_menu, handle_header_callback, handle_header_text_input
from app.bot.footer import footer_menu, handle_footer_callback, handle_footer_text_input
from app.db.pool import get_pool, close_pool


configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
settings = get_settings()
bg_queue = BackgroundTaskQueue()

# حالات المستخدمين للإدخال التفاعلي عبر webhook
user_states: Dict[int, str] = {}


async def set_user_state(client: Any, user_id: int, state: Optional[str]) -> None:
    if state:
        user_states[user_id] = state
    else:
        user_states.pop(user_id, None)


async def get_user_state(client: Any, user_id: int) -> Optional[str]:
    return user_states.get(user_id)


@app.on_event("startup")
async def on_startup() -> None:
    await run_migrations()
    await get_pool()
    await bg_queue.start()

    bot = get_bot_client()
    await bot.start()

    # إرفاق دوال إدارة الحالة بالعميل لاستخدامها مع منطق القنوات
    import functools
    setattr(bot, "set_user_state", functools.partial(set_user_state, bot))
    setattr(bot, "get_user_state", functools.partial(get_user_state, bot))

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
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO users (user_id, username, first_name, last_name, language_code)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (user_id) DO UPDATE SET
                                username = EXCLUDED.username,
                                first_name = EXCLUDED.first_name,
                                last_name = EXCLUDED.last_name,
                                language_code = EXCLUDED.language_code
                            """,
                            (
                                int(from_user.get("id", chat_id)),
                                from_user.get("username"),
                                from_user.get("first_name"),
                                from_user.get("last_name"),
                                from_user.get("language_code"),
                            ),
                        )

                if text.startswith("/start"):
                    # احصاء القنوات للمستخدم
                    user_id = int(from_user.get("id", chat_id))
                    channel_count = 0
                    pool2 = await get_pool()
                    async with pool2.connection() as conn2:
                        async with conn2.cursor() as cur2:
                            await cur2.execute(
                                "SELECT COUNT(*) FROM channels WHERE user_id = %s",
                                (user_id,)
                            )
                            row = await cur2.fetchone()
                            channel_count = (row[0] if row else 0) or 0

                    # لوحة المفاتيح الرئيسية
                    keyboard = [
                        [
                            InlineKeyboardButton("📡 قنواتي", callback_data="channels_menu"),
                            InlineKeyboardButton("➕ إضافة قناة", callback_data="channels_add")
                        ],
                        [
                            InlineKeyboardButton("📋 عرض القنوات", callback_data="channels_list"),
                            InlineKeyboardButton("🗑 حذف قناة", callback_data="channels_delete")
                        ],
                        [
                            InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
                            InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")
                        ],
                        [
                            InlineKeyboardButton("📖 المساعدة", callback_data="help"),
                            InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")
                        ]
                    ]

                    # رسالة ترحيب مع إحصائيات مختصرة
                    first_name = from_user.get("first_name") or ""
                    welcome_text = f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
    🤖 **مرحباً بك في بوت إدارة القنوات**
╰━━━━━━━━━━━━━━━━━━━━━╯

👤 **المستخدم:** {first_name}
🆔 **معرفك:** `{user_id}`
📡 **القنوات المضافة:** {channel_count}

━━━━━━━━━━━━━━━━━━━━━
🎯 **الميزات المتاحة:**

• إدارة قنواتك بسهولة
• إضافة وحذف القنوات
• عرض إحصائيات مفصلة
• واجهة سهلة الاستخدام

━━━━━━━━━━━━━━━━━━━━━
⬇️ **اختر من القائمة أدناه:**
"""

                    await bot.send_message(
                        chat_id=chat_id,
                        text=welcome_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    # معالجة إدخال القنوات عندما يكون المستخدم في حالة انتظار
                    user_id = int(from_user.get("id", chat_id)) if from_user.get("id") else None
                    current_state = await get_user_state(bot, user_id) if user_id is not None else None

                    # أمر /channels لفتح قائمة القنوات مباشرة
                    if text.startswith("/channels"):
                        count = await ChannelManager.get_channel_count(user_id)
                        keyboard = [
                            [
                                InlineKeyboardButton("➕ إضافة قناة", callback_data="channels_add"),
                                InlineKeyboardButton("📋 عرض القنوات", callback_data="channels_list")
                            ],
                            [
                                InlineKeyboardButton("🗑 حذف قناة", callback_data="channels_delete"),
                                InlineKeyboardButton("📊 الإحصائيات", callback_data="channel_stats")
                            ],
                            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
                        ]
                        text_menu = f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
    📡 **إدارة القنوات**
╰━━━━━━━━━━━━━━━━━━━━━╯

📊 **الإحصائيات:**
• القنوات المضافة: **{count}**
• الحد الأقصى: **50** قناة

━━━━━━━━━━━━━━━━━━━━━
📝 **طرق إضافة القنوات:**

• معرف القناة: @username
• رابط القناة: t.me/username
• معرف رقمي: -100xxxxxxxxx
• توجيه رسالة من القناة

━━━━━━━━━━━━━━━━━━━━━
⚠️ **تنبيه:** يجب أن يكون البوت مشرفاً في القناة

⬇️ **اختر من القائمة:**
"""
                        await bot.send_message(
                            chat_id=chat_id,
                            text=text_menu,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    # إلغاء العملية
                    elif current_state == "waiting_channels" and text.startswith("/cancel"):
                        await set_user_state(bot, user_id, None)
                        await bot.send_message(chat_id=chat_id, text="❌ تم إلغاء العملية")
                    # معالجة الإدخال عندما يكون بانتظار القنوات
                    elif current_state == "waiting_channels":
                        # تدفقات إدخال نص الهيدر/الفوتر
                        await handle_header_text_input(bot, type("obj", (), {"from_user": type("u", (), {"id": user_id}), "text": text, "reply_text": lambda **kwargs: bot.send_message(chat_id=chat_id, **kwargs)})())
                        await handle_footer_text_input(bot, type("obj", (), {"from_user": type("u", (), {"id": user_id}), "text": text, "reply_text": lambda **kwargs: bot.send_message(chat_id=chat_id, **kwargs)})())
                        channels_to_check = []
                        # معالجة الرسائل المحولة
                        fwd_chat = message.get("forward_from_chat")
                        if fwd_chat and fwd_chat.get("type") in ["channel", "supergroup"]:
                            channels_to_check = [int(fwd_chat.get("id"))]
                        elif text:
                            channels_to_check = await ChannelManager.extract_channel_info(text)
                            if not channels_to_check:
                                await bot.send_message(chat_id=chat_id, text="⚠️ لم أتمكن من استخراج أي قنوات من النص المرسل!")
                                return
                        else:
                            await bot.send_message(chat_id=chat_id, text="⚠️ يرجى إرسال نص أو توجيه رسالة من قناة!")
                            return

                        processing = await bot.send_message(chat_id=chat_id, text="⏳ جاري معالجة القنوات...")

                        added_channels = []
                        failed_channels = []
                        for channel_info in channels_to_check:
                            is_admin, chat_obj = await ChannelManager.check_bot_admin(bot, channel_info)
                            if not chat_obj:
                                failed_channels.append(f"{channel_info} - قناة غير موجودة")
                                continue
                            if not is_admin:
                                failed_channels.append(f"{chat_obj.title} - البوت ليس مشرفاً")
                                continue
                            success = await ChannelManager.add_channel(
                                user_id,
                                chat_obj.id,
                                chat_obj.username,
                                chat_obj.title
                            )
                            if success:
                                added_channels.append(chat_obj.title)
                            else:
                                failed_channels.append(f"{chat_obj.title} - خطأ في الحفظ")

                        result_text = """╭━━━━━━━━━━━━━━━━━━━━━╮
    📊 **نتيجة العملية**
╰━━━━━━━━━━━━━━━━━━━━━╯

"""
                        if added_channels:
                            result_text += f"✅ **تم إضافة بنجاح: {len(added_channels)}**\n"
                            for ch in added_channels:
                                result_text += f"  └ {ch}\n"
                            result_text += "\n"
                        if failed_channels:
                            result_text += f"❌ **فشل الإضافة: {len(failed_channels)}**\n"
                            for ch in failed_channels:
                                result_text += f"  └ {ch}\n"
                            result_text += "\n"
                        if not added_channels and not failed_channels:
                            result_text += "⚠️ **لم يتم إضافة أي قناة!**\n"
                        result_text += "━━━━━━━━━━━━━━━━━━━━━"

                        await set_user_state(bot, user_id, None)
                        keyboard = [[InlineKeyboardButton("🔙 رجوع للقنوات", callback_data="channels_menu")]]
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=processing.id,
                            text=result_text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )

            bg_queue.enqueue(job)

    # معالجة أزرار الـ CallbackQuery
    callback_query: Optional[Dict[str, Any]] = update.get("callback_query")
    if callback_query is not None:
        callback_id = callback_query.get("id")
        data = callback_query.get("data", "") or ""
        from_user = callback_query.get("from") or {}
        origin_message = callback_query.get("message") or {}
        origin_chat = origin_message.get("chat") or {}
        chat_id = origin_chat.get("id")
        message_id = origin_message.get("message_id")
        user_id = int(from_user.get("id")) if from_user.get("id") is not None else None

        async def answer_cbq(text: Optional[str] = None, show_alert: bool = False) -> None:
            try:
                if callback_id:
                    await bot.answer_callback_query(callback_id, text=text, show_alert=show_alert)
            except Exception:
                pass

        if chat_id is not None and message_id is not None and user_id is not None:
            try:
                if data == "channels_menu":
                    # إظهار قائمة القنوات
                    count = await ChannelManager.get_channel_count(user_id)
                    keyboard = [
                        [
                            InlineKeyboardButton("➕ إضافة قناة", callback_data="channels_add"),
                            InlineKeyboardButton("📋 عرض القنوات", callback_data="channels_list")
                        ],
                        [
                            InlineKeyboardButton("🗑 حذف قناة", callback_data="channels_delete"),
                            InlineKeyboardButton("📊 الإحصائيات", callback_data="channel_stats")
                        ],
                        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
                    ]
                    text = f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
    📡 **إدارة القنوات**
╰━━━━━━━━━━━━━━━━━━━━━╯

📊 **الإحصائيات:**
• القنوات المضافة: **{count}**
• الحد الأقصى: **50** قناة

━━━━━━━━━━━━━━━━━━━━━
📝 **طرق إضافة القنوات:**

• معرف القناة: @username
• رابط القناة: t.me/username
• معرف رقمي: -100xxxxxxxxx
• توجيه رسالة من القناة

━━━━━━━━━━━━━━━━━━━━━
⚠️ **تنبيه:** يجب أن يكون البوت مشرفاً في القناة

⬇️ **اختر من القائمة:**
"""
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await answer_cbq()

                elif data == "main_menu":
                    # العودة للقائمة الرئيسية
                    first_name = from_user.get("first_name") or ""
                    pool2 = await get_pool()
                    async with pool2.connection() as conn2:
                        async with conn2.cursor() as cur2:
                            await cur2.execute(
                                "SELECT COUNT(*) FROM channels WHERE user_id = %s",
                                (user_id,)
                            )
                            row = await cur2.fetchone()
                            channel_count = (row[0] if row else 0) or 0

                    keyboard = [
                        [
                            InlineKeyboardButton("📡 قنواتي", callback_data="channels_menu"),
                            InlineKeyboardButton("➕ إضافة قناة", callback_data="channels_add")
                        ],
                        [
                            InlineKeyboardButton("📋 عرض القنوات", callback_data="channels_list"),
                            InlineKeyboardButton("🗑 حذف قناة", callback_data="channels_delete")
                        ],
                        [
                            InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
                            InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")
                        ],
                        [
                            InlineKeyboardButton("📖 المساعدة", callback_data="help"),
                            InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")
                        ]
                    ]

                    main_text = f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
    🤖 **القائمة الرئيسية**
╰━━━━━━━━━━━━━━━━━━━━━╯

👤 **المستخدم:** {first_name}
📡 **القنوات المضافة:** {channel_count}

━━━━━━━━━━━━━━━━━━━━━
⬇️ **اختر من القائمة أدناه:**
"""
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=main_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await answer_cbq()

                elif data == "channels_list":
                    channels = await ChannelManager.get_user_channels(user_id)
                    if not channels:
                        await answer_cbq("لا توجد قنوات مضافة بعد!", show_alert=True)
                    else:
                        text = """╭━━━━━━━━━━━━━━━━━━━━━╮
    📋 **قنواتك المضافة**
╰━━━━━━━━━━━━━━━━━━━━━╯\n\n"""
                        for i, channel in enumerate(channels, 1):
                            title = channel.get("channel_title") or "بدون اسم"
                            username = channel.get("channel_username") or ""
                            channel_id_val = channel.get("channel_id")
                            text += f"**{i}.** {title}\n"
                            if username:
                                text += f"   └ @{username}\n"
                            text += f"   └ ID: `{channel_id_val}`\n"
                            text += "━━━━━━━━━━━━━━━━━━━━━\n"

                        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="channels_menu")]]
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        await answer_cbq()

                elif data == "channels_add":
                    # عرض تعليمات إضافة القنوات وتعيين حالة انتظار
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=(
                            """
╭━━━━━━━━━━━━━━━━━━━━━╮
    ➕ **إضافة قنوات جديدة**
╰━━━━━━━━━━━━━━━━━━━━━╯

📝 **أرسل القنوات بإحدى الطرق:**

1️⃣ معرف القناة: @channel_username
2️⃣ رابط القناة: t.me/channel_username
3️⃣ معرف رقمي: -1001234567890
4️⃣ توجيه رسالة من القناة

━━━━━━━━━━━━━━━━━━━━━
💡 **نصائح:**
• يمكنك إرسال عدة قنوات دفعة واحدة
• ضع كل قناة في سطر منفصل
• تأكد من أن البوت مشرف في القناة

━━━━━━━━━━━━━━━━━━━━━
❌ للإلغاء أرسل: /cancel
"""
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await set_user_state(bot, user_id, "waiting_channels")
                    await answer_cbq()

                elif data == "channels_delete":
                    channels = await ChannelManager.get_user_channels(user_id)
                    if not channels:
                        await answer_cbq("لا توجد قنوات لحذفها!", show_alert=True)
                    else:
                        keyboard = []
                        for ch in channels:
                            title = ch.get("channel_title") or f"ID: {ch.get('channel_id')}"
                            keyboard.append([
                                InlineKeyboardButton(
                                    f"🗑 {title}",
                                    callback_data=f"delete_channel_{ch.get('channel_id')}"
                                )
                            ])
                        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="channels_menu")])
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=(
                                """╭━━━━━━━━━━━━━━━━━━━━━╮
    🗑 **حذف القنوات**
╰━━━━━━━━━━━━━━━━━━━━━╯

⚠️ **اختر القناة التي تريد حذفها:**
"""
                            ),
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        await answer_cbq()

                elif data.startswith("delete_channel_"):
                    channel_id_val = int(data.replace("delete_channel_", ""))
                    if await ChannelManager.remove_channel(user_id, channel_id_val):
                        await answer_cbq("✅ تم حذف القناة بنجاح!", show_alert=True)
                    else:
                        await answer_cbq("❌ فشل حذف القناة!", show_alert=True)
                    # إعادة فتح قائمة الحذف لتحديثها
                    channels = await ChannelManager.get_user_channels(user_id)
                    if not channels:
                        # العودة للقائمة إذا لم يتبق قنوات
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text="لا توجد قنوات متبقية.",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="channels_menu")]])
                        )
                    else:
                        keyboard = []
                        for ch in channels:
                            title = ch.get("channel_title") or f"ID: {ch.get('channel_id')}"
                            keyboard.append([
                                InlineKeyboardButton(
                                    f"🗑 {title}",
                                    callback_data=f"delete_channel_{ch.get('channel_id')}"
                                )
                            ])
                        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="channels_menu")])
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=(
                                """╭━━━━━━━━━━━━━━━━━━━━━╮
    🗑 **حذف القنوات**
╰━━━━━━━━━━━━━━━━━━━━━╯

⚠️ **اختر القناة التي تريد حذفها:**
"""
                            ),
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )

                elif data == "channel_stats":
                    channels = await ChannelManager.get_user_channels(user_id)
                    count = len(channels)
                    stats_text = f"""╭━━━━━━━━━━━━━━━━━━━━━╮
    📊 **إحصائيات القنوات**
╰━━━━━━━━━━━━━━━━━━━━━╯

📈 **الملخص:**
• إجمالي القنوات: **{count}**
• القنوات النشطة: **{count}**
• الحد الأقصى: **50** قناة
• المتبقي: **{50 - count}** قناة

━━━━━━━━━━━━━━━━━━━━━
"""
                    if channels:
                        stats_text += "\n📋 **تفاصيل القنوات:**\n\n"
                        for i, ch in enumerate(channels[:5], 1):
                            title = ch.get("channel_title") or "بدون اسم"
                            stats_text += f"{i}. {title}\n"
                        if count > 5:
                            stats_text += f"\n... و {count - 5} قناة أخرى"
                    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="channels_menu")]]
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=stats_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await answer_cbq()

                elif data == "stats":
                    # إحصائيات المستخدم العامة
                    pool2 = await get_pool()
                    async with pool2.connection() as conn2:
                        async with conn2.cursor() as cur2:
                            await cur2.execute(
                                "SELECT COUNT(*) FROM channels WHERE user_id = %s",
                                (user_id,)
                            )
                            row = await cur2.fetchone()
                            channel_count = (row[0] if row else 0) or 0
                            await cur2.execute(
                                "SELECT created_at FROM users WHERE user_id = %s",
                                (user_id,)
                            )
                            urow = await cur2.fetchone()
                            created_at = urow[0] if urow else None

                    stats_text = f"""
📊 **الإحصائيات الخاصة بك**

👤 **الاسم:** {from_user.get('first_name') or ''}
🆔 **المعرف:** `{user_id}`
📡 **عدد القنوات:** {channel_count}
📅 **تاريخ التسجيل:** {created_at.strftime('%Y-%m-%d') if created_at else 'غير معروف'}

━━━━━━━━━━━━━━━━━━━━━
"""
                    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=stats_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await answer_cbq()

                elif data == "help":
                    help_text = (
                        """
📖 **دليل الاستخدام**

━━━━━━━━━━━━━━━━━━━━━
🔹 **الأوامر المتاحة:**

• /start - بدء البوت وعرض القائمة
• /channels - إدارة القنوات
• /cancel - إلغاء العملية الحالية

━━━━━━━━━━━━━━━━━━━━━
🔹 **كيفية إضافة قناة:**

1. اضغط على "➕ إضافة قناة"
2. أرسل معرف القناة بإحدى الطرق:
   • @username
   • رابط القناة
   • ID القناة
   • توجيه رسالة من القناة

⚠️ **ملاحظة:** يجب أن يكون البوت مشرفاً في القناة

━━━━━━━━━━━━━━━━━━━━━
🔹 **للدعم والمساعدة:**
تواصل مع المطور: @YourUsername
"""
                    )
                    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=help_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await answer_cbq()

                elif data == "about":
                    about_text = (
                        """
ℹ️ **حول البوت**

━━━━━━━━━━━━━━━━━━━━━
🤖 **بوت إدارة القنوات**
الإصدار: 1.0.0

هذا البوت يساعدك في:
• إدارة قنواتك بسهولة
• تنظيم المحتوى
• متابعة الإحصائيات

━━━━━━━━━━━━━━━━━━━━━
👨‍💻 **تطوير:**
تم التطوير بواسطة فريق التطوير

📅 **آخر تحديث:**
2025-09-10

━━━━━━━━━━━━━━━━━━━━━
"""
                    )
                    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=about_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await answer_cbq()

                elif data == "settings":
                    # عرض اختيار قناة لإدارة الإعدادات
                    pool2 = await get_pool()
                    async with pool2.connection() as conn2:
                        async with conn2.cursor() as cur2:
                            await cur2.execute(
                                "SELECT channel_id, channel_title FROM channels WHERE user_id = %s ORDER BY created_at DESC",
                                (user_id,)
                            )
                            rows = await cur2.fetchall()
                    if not rows:
                        await answer_cbq("لا توجد قنوات لإعدادها", show_alert=True)
                    else:
                        kb = []
                        for cid, title in rows:
                            display = title or f"{cid}"
                            kb.append([InlineKeyboardButton(f"⚙️ {display}", callback_data=f"settings_channel_{cid}")])
                        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=(
                                """
╭━━━━━━━━━━━━━━━━━━━━━╮
   ⚙️ إعدادات القنوات
╰━━━━━━━━━━━━━━━━━━━━━╯

اختر قناة لإدارة الهيدر/الفوتر
"""
                            ),
                            reply_markup=InlineKeyboardMarkup(kb),
                            parse_mode=ParseMode.MARKDOWN,
                        )
                        await answer_cbq()
                elif data.startswith("settings_channel_"):
                    cid = int(data.split("_")[-1])
                    kb = [
                        [InlineKeyboardButton("🧩 الهيدر", callback_data=f"header_menu_{cid}")],
                        [InlineKeyboardButton("🧩 الفوتر", callback_data=f"footer_menu_{cid}")],
                        [InlineKeyboardButton("🔙 رجوع", callback_data="settings")],
                    ]
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"إعدادات القناة: `{cid}`\n\nاختر القسم:",
                        reply_markup=InlineKeyboardMarkup(kb),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    await answer_cbq()
                elif data.startswith("header_menu_"):
                    cid = int(data.split("_")[-1])
                    await header_menu(bot, type("obj", (), {"edit_text": lambda *args, **kwargs: bot.edit_message_text(chat_id=chat_id, message_id=message_id, *args, **kwargs)})(), user_id, cid)
                    await answer_cbq()
                elif data.startswith("footer_menu_"):
                    cid = int(data.split("_")[-1])
                    await footer_menu(bot, type("obj", (), {"edit_text": lambda *args, **kwargs: bot.edit_message_text(chat_id=chat_id, message_id=message_id, *args, **kwargs)})(), user_id, cid)
                    await answer_cbq()
                elif data.startswith("header_"):
                    await handle_header_callback(bot, type("obj", (), {"data": data, "from_user": type("u", (), {"id": user_id}), "message": type("m", (), {"edit_text": lambda *args, **kwargs: bot.edit_message_text(chat_id=chat_id, message_id=message_id, *args, **kwargs)})()})())
                elif data.startswith("footer_"):
                    await handle_footer_callback(bot, type("obj", (), {"data": data, "from_user": type("u", (), {"id": user_id}), "message": type("m", (), {"edit_text": lambda *args, **kwargs: bot.edit_message_text(chat_id=chat_id, message_id=message_id, *args, **kwargs)})()})())
                else:
                    await answer_cbq()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Callback handling error: %s", exc)
                await answer_cbq("حدث خطأ غير متوقع", show_alert=True)

    return Response(status_code=status.HTTP_200_OK)


@app.get("/")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

