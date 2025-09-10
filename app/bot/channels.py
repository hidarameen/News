"""
نظام إدارة القنوات للبوت
يسمح للمستخدمين بإضافة وحذف وعرض قنواتهم الخاصة
"""

import re
import logging
from typing import List, Optional, Union
from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    CallbackQuery,
    Chat
)
from pyrogram.enums import ParseMode
from pyrogram.errors import (
    UserNotParticipant,
    ChatAdminRequired,
    PeerIdInvalid,
    UsernameNotOccupied,
    ChannelPrivate
)

from app.db.pool import get_pool
from app.bot.header import HeaderManager
from app.bot.footer import FooterManager

logger = logging.getLogger(__name__)


class ChannelManager:
    """مدير القنوات للمستخدمين"""
    
    @staticmethod
    async def extract_channel_info(text: str) -> List[Union[int, str]]:
        """استخراج معرفات القنوات من النص"""
        channels = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # التحقق من ID رقمي
            if line.lstrip('-').isdigit():
                channel_id = int(line)
                # التأكد من أن الـ ID سالب (قناة)
                if channel_id > 0:
                    channel_id = -100 * abs(channel_id)
                channels.append(channel_id)
                
            # التحقق من معرف القناة @username
            elif line.startswith('@'):
                channels.append(line)
                
            # التحقق من رابط القناة
            elif 't.me/' in line or 'telegram.me/' in line:
                # استخراج المعرف من الرابط
                match = re.search(r't(?:elegram)?\.me/([a-zA-Z0-9_]+)', line)
                if match:
                    username = match.group(1)
                    if not username.startswith('joinchat'):
                        channels.append(f"@{username}")
                        
        return channels
    
    @staticmethod
    async def check_bot_admin(client: Client, channel_id: Union[int, str]) -> tuple[bool, Optional[Chat]]:
        """التحقق من أن البوت مشرف في القناة"""
        try:
            chat = await client.get_chat(channel_id)
            
            # التحقق من أن هذه قناة وليست مجموعة عادية
            if chat.type not in ["channel", "supergroup"]:
                return False, None
                
            # التحقق من صلاحيات البوت
            bot_member = await client.get_chat_member(chat.id, "me")
            
            # التحقق من أن البوت مشرف
            if bot_member.status in ["administrator", "creator"]:
                return True, chat
            
            return False, chat
            
        except (UserNotParticipant, ChatAdminRequired):
            return False, None
        except (PeerIdInvalid, UsernameNotOccupied, ChannelPrivate):
            return False, None
        except Exception as e:
            logger.error(f"خطأ في التحقق من القناة {channel_id}: {e}")
            return False, None
    
    @staticmethod
    async def add_channel(user_id: int, channel_id: int, channel_username: str, channel_title: str) -> bool:
        """إضافة قناة للمستخدم"""
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO channels (user_id, channel_id, channel_username, channel_title, is_admin)
                        VALUES (%s, %s, %s, %s, TRUE)
                        ON CONFLICT (user_id, channel_id) DO UPDATE SET
                            channel_username = EXCLUDED.channel_username,
                            channel_title = EXCLUDED.channel_title,
                            is_admin = TRUE,
                            updated_at = NOW()
                        """,
                        (user_id, channel_id, channel_username, channel_title)
                    )
                    await conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطأ في إضافة القناة: {e}")
            return False
    
    @staticmethod
    async def remove_channel(user_id: int, channel_id: int) -> bool:
        """حذف قناة من قائمة المستخدم"""
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM channels WHERE user_id = %s AND channel_id = %s",
                        (user_id, channel_id)
                    )
                    await conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في حذف القناة: {e}")
            return False
    
    @staticmethod
    async def get_user_channels(user_id: int) -> List[dict]:
        """الحصول على قنوات المستخدم"""
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT channel_id, channel_username, channel_title, is_admin, created_at
                        FROM channels
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        """,
                        (user_id,)
                    )
                    rows = await cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"خطأ في جلب القنوات: {e}")
            return []
    
    @staticmethod
    async def get_channel_count(user_id: int) -> int:
        """الحصول على عدد قنوات المستخدم"""
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT COUNT(*) FROM channels WHERE user_id = %s",
                        (user_id,)
                    )
                    result = await cur.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"خطأ في حساب القنوات: {e}")
            return 0


# معالجات الأوامر والأزرار
async def channels_menu(client: Client, message: Message) -> None:
    """عرض قائمة إدارة القنوات"""
    user_id = message.from_user.id
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
    
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_channels_callback(client: Client, callback_query: CallbackQuery) -> None:
    """معالج أزرار القنوات"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "channels_add":
        await callback_query.message.edit_text(
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
""",
            parse_mode=ParseMode.MARKDOWN
        )
        # تعيين حالة المستخدم لانتظار القنوات
        await client.set_user_state(user_id, "waiting_channels")
        
    elif data == "channels_list":
        channels = await ChannelManager.get_user_channels(user_id)
        
        if not channels:
            await callback_query.answer("لا توجد قنوات مضافة بعد!", show_alert=True)
            return
        
        text = """╭━━━━━━━━━━━━━━━━━━━━━╮
    📋 **قنواتك المضافة**
╰━━━━━━━━━━━━━━━━━━━━━╯\n\n"""
        
        for i, channel in enumerate(channels, 1):
            title = channel['channel_title'] or "بدون اسم"
            username = channel['channel_username'] or ""
            channel_id = channel['channel_id']
            
            text += f"**{i}.** {title}\n"
            if username:
                text += f"   └ @{username}\n"
            text += f"   └ ID: `{channel_id}`\n"
            text += "━━━━━━━━━━━━━━━━━━━━━\n"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="channels_menu")]]
        
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
    elif data == "channels_delete":
        channels = await ChannelManager.get_user_channels(user_id)
        
        if not channels:
            await callback_query.answer("لا توجد قنوات لحذفها!", show_alert=True)
            return
        
        keyboard = []
        for channel in channels:
            title = channel['channel_title'] or f"ID: {channel['channel_id']}"
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑 {title}",
                    callback_data=f"delete_channel_{channel['channel_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="channels_menu")])
        
        await callback_query.message.edit_text(
            """╭━━━━━━━━━━━━━━━━━━━━━╮
    🗑 **حذف القنوات**
╰━━━━━━━━━━━━━━━━━━━━━╯

⚠️ **اختر القناة التي تريد حذفها:**
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
    elif data.startswith("delete_channel_"):
        channel_id = int(data.replace("delete_channel_", ""))
        
        if await ChannelManager.remove_channel(user_id, channel_id):
            await callback_query.answer("✅ تم حذف القناة بنجاح!", show_alert=True)
        else:
            await callback_query.answer("❌ فشل حذف القناة!", show_alert=True)
        
        # العودة لقائمة الحذف
        await handle_channels_callback(client, callback_query)
        
    elif data == "channel_stats":
        # عرض إحصائيات القنوات
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
            for i, channel in enumerate(channels[:5], 1):
                title = channel['channel_title'] or "بدون اسم"
                stats_text += f"{i}. {title}\n"
            
            if count > 5:
                stats_text += f"\n... و {count - 5} قناة أخرى"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="channels_menu")]]
        
        await callback_query.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
    elif data == "channels_menu":
        await channels_menu(client, callback_query.message)


async def handle_channel_input(client: Client, message: Message) -> None:
    """معالج إدخال القنوات من المستخدم"""
    user_id = message.from_user.id
    
    # التحقق من حالة المستخدم
    user_state = await client.get_user_state(user_id)
    if user_state != "waiting_channels":
        return
    
    # إلغاء العملية
    if message.text and message.text.startswith("/cancel"):
        await client.set_user_state(user_id, None)
        await message.reply_text("❌ تم إلغاء العملية")
        return
    
    added_channels = []
    failed_channels = []
    
    # معالجة الرسائل المحولة
    if message.forward_from_chat:
        chat = message.forward_from_chat
        if chat.type in ["channel", "supergroup"]:
            channels_to_check = [chat.id]
        else:
            await message.reply_text("⚠️ هذه ليست قناة! يرجى توجيه رسالة من قناة.")
            return
    
    # معالجة النص المدخل
    elif message.text:
        channels_to_check = await ChannelManager.extract_channel_info(message.text)
        
        if not channels_to_check:
            await message.reply_text("⚠️ لم أتمكن من استخراج أي قنوات من النص المرسل!")
            return
    else:
        await message.reply_text("⚠️ يرجى إرسال نص أو توجيه رسالة من قناة!")
        return
    
    # معالجة القنوات
    processing_msg = await message.reply_text("⏳ جاري معالجة القنوات...")
    
    for channel_info in channels_to_check:
        is_admin, chat = await ChannelManager.check_bot_admin(client, channel_info)
        
        if not chat:
            failed_channels.append(f"{channel_info} - قناة غير موجودة")
            continue
        
        if not is_admin:
            failed_channels.append(f"{chat.title} - البوت ليس مشرفاً")
            continue
        
        # إضافة القناة
        success = await ChannelManager.add_channel(
            user_id,
            chat.id,
            chat.username,
            chat.title
        )
        
        if success:
            added_channels.append(chat.title)
            # تهيئة افتراضية للهيدر/الفوتر للسجل الجديد
            try:
                await HeaderManager.upsert(user_id, chat.id, None, False, "markdown")
                await FooterManager.upsert(user_id, chat.id, None, False, "markdown")
            except Exception as e:
                logger.warning(f"تعذر تهيئة إعدادات القناة {chat.id}: {e}")
        else:
            failed_channels.append(f"{chat.title} - خطأ في الحفظ")
    
    # إنشاء رسالة النتيجة
    result_text = """╭━━━━━━━━━━━━━━━━━━━━━╮
    📊 **نتيجة العملية**
╰━━━━━━━━━━━━━━━━━━━━━╯

"""
    
    if added_channels:
        result_text += f"✅ **تم إضافة بنجاح: {len(added_channels)}**\n"
        for channel in added_channels:
            result_text += f"  └ {channel}\n"
        result_text += "\n"
    
    if failed_channels:
        result_text += f"❌ **فشل الإضافة: {len(failed_channels)}**\n"
        for channel in failed_channels:
            result_text += f"  └ {channel}\n"
        result_text += "\n"
    
    if not added_channels and not failed_channels:
        result_text += "⚠️ **لم يتم إضافة أي قناة!**\n"
    
    result_text += "━━━━━━━━━━━━━━━━━━━━━"
    
    # إعادة تعيين حالة المستخدم
    await client.set_user_state(user_id, None)
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للقنوات", callback_data="channels_menu")]]
    
    await processing_msg.edit_text(
        result_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


# تصدير المعالجات للاستخدام في handlers.py
__all__ = [
    'ChannelManager',
    'channels_menu',
    'handle_channels_callback',
    'handle_channel_input'
]