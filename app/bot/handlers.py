from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ParseMode

from app.bot.client import get_bot_client
from app.db.pool import get_pool
from app.bot.channels import (
    channels_menu,
    handle_channels_callback,
    handle_channel_input
)
from app.bot.header import header_menu, handle_header_callback, handle_header_text_input
from app.bot.footer import footer_menu, handle_footer_callback, handle_footer_text_input


bot = get_bot_client()
# قاموس لتخزين حالات المستخدمين
user_states = {}


@bot.on_message(filters.private & filters.command("start"))
async def start_handler(_, message: Message) -> None:
    user = message.from_user
    if user is None:
        return
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
                (user.id, user.username, user.first_name, user.last_name, user.language_code)
            )
            await conn.commit()
            
            # الحصول على عدد القنوات
            await cur.execute(
                "SELECT COUNT(*) FROM channels WHERE user_id = %s",
                (user.id,)
            )
            channel_count = (await cur.fetchone())[0] or 0
    
    # إنشاء لوحة المفاتيح الرئيسية
    keyboard = [
        [
            InlineKeyboardButton("📡 إدارة القنوات", callback_data="channels_menu")
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
    
    # رسالة الترحيب المحسنة
    welcome_text = f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
    🤖 **مرحباً بك في بوت إدارة القنوات**
╰━━━━━━━━━━━━━━━━━━━━━╯

👤 **المستخدم:** {user.first_name}
🆔 **معرفك:** `{user.id}`
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
    
    await message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


# معالج أزرار Callback
@bot.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery) -> None:
    data = callback_query.data
    user = callback_query.from_user
    
    # معالجة أزرار القنوات
    if data == "channels_menu":
        await channels_menu(client, callback_query.message)
        await callback_query.answer()
    elif data.startswith("channels_") or data.startswith("delete_channel_"):
        await handle_channels_callback(client, callback_query)
        await callback_query.answer()
    elif data == "main_menu":
        # العودة للقائمة الرئيسية المحسنة
        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM channels WHERE user_id = %s",
                    (user.id,)
                )
                channel_count = (await cur.fetchone())[0] or 0
        
        keyboard = [
            [
                InlineKeyboardButton("📡 إدارة القنوات", callback_data="channels_menu")
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
        
        main_menu_text = f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
    🤖 **القائمة الرئيسية**
╰━━━━━━━━━━━━━━━━━━━━━╯

👤 **المستخدم:** {user.first_name}
📡 **القنوات المضافة:** {channel_count}

━━━━━━━━━━━━━━━━━━━━━
⬇️ **اختر من القائمة أدناه:**
"""
        
        await callback_query.message.edit_text(
            main_menu_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer()
    
    # معالجة الأزرار الجديدة
    elif data == "stats":
        # عرض الإحصائيات
        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # عدد القنوات
                await cur.execute(
                    "SELECT COUNT(*) FROM channels WHERE user_id = %s",
                    (user.id,)
                )
                channel_count = (await cur.fetchone())[0] or 0
                
                # تاريخ أول استخدام
                await cur.execute(
                    "SELECT created_at FROM users WHERE user_id = %s",
                    (user.id,)
                )
                user_data = await cur.fetchone()
                created_at = user_data[0] if user_data else None
        
        stats_text = f"""
📊 **الإحصائيات الخاصة بك**

👤 **الاسم:** {user.first_name}
🆔 **المعرف:** `{user.id}`
📡 **عدد القنوات:** {channel_count}
📅 **تاريخ التسجيل:** {created_at.strftime('%Y-%m-%d') if created_at else 'غير معروف'}

━━━━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        
        await callback_query.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer()
    
    elif data == "help":
        # عرض المساعدة
        help_text = """
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
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        
        await callback_query.message.edit_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer()
    
    elif data == "about":
        # معلومات عن البوت
        about_text = """
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
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        
        await callback_query.message.edit_text(
            about_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer()
    
    elif data == "settings":
        # فتح قائمة اختيار القناة لإدارة الإعدادات
        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT channel_id, channel_title FROM channels WHERE user_id = %s ORDER BY created_at DESC",
                    (user.id,)
                )
                rows = await cur.fetchall()
        if not rows:
            await callback_query.answer("لا توجد قنوات لإعدادها", show_alert=True)
            return
        keyboard = []
        for cid, title in rows:
            display = title or f"{cid}"
            keyboard.append([InlineKeyboardButton(f"⚙️ {display}", callback_data=f"settings_channel_{cid}")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
        await callback_query.message.edit_text(
            """
╭━━━━━━━━━━━━━━━━━━━━━╮
   ⚙️ إعدادات القنوات
╰━━━━━━━━━━━━━━━━━━━━━╯

اختر قناة لإدارة الهيدر/الفوتر
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )
        await callback_query.answer()
    elif data.startswith("settings_channel_"):
        channel_id = int(data.split("_")[-1])
        # قائمة إعدادات القناة
        keyboard = [
            [InlineKeyboardButton("🧩 الهيدر", callback_data=f"header_menu_{channel_id}")],
            [InlineKeyboardButton("🧩 الفوتر", callback_data=f"footer_menu_{channel_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="settings")],
        ]
        await callback_query.message.edit_text(
            f"""
إعدادات القناة: `{channel_id}`

اختر القسم:
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )
        await callback_query.answer()
    elif data.startswith("header_menu_"):
        channel_id = int(data.split("_")[-1])
        await header_menu(client, callback_query.message, user.id, channel_id)
        await callback_query.answer()
    elif data.startswith("footer_menu_"):
        channel_id = int(data.split("_")[-1])
        await footer_menu(client, callback_query.message, user.id, channel_id)
        await callback_query.answer()
    elif data.startswith("header_"):
        await handle_header_callback(client, callback_query)
    elif data.startswith("footer_"):
        await handle_footer_callback(client, callback_query)


# معالج أمر القنوات
@bot.on_message(filters.private & filters.command("channels"))
async def channels_command(client, message: Message) -> None:
    await channels_menu(client, message)


# معالج الرسائل النصية (لإدخال القنوات)
@bot.on_message(filters.private & ~filters.command(["start", "help", "channels"]))
async def text_handler(client, message: Message) -> None:
    user_id = message.from_user.id
    
    # التحقق من حالة المستخدم
    if user_id in user_states and user_states[user_id] == "waiting_channels":
        await handle_channel_input(client, message)
        return
    # التدفقات الخاصة بالهيدر/الفوتر
    await handle_header_text_input(client, message)
    await handle_footer_text_input(client, message)


# وظائف مساعدة لإدارة حالات المستخدمين
async def set_user_state(client, user_id: int, state: str) -> None:
    """تعيين حالة المستخدم"""
    if state:
        user_states[user_id] = state
    elif user_id in user_states:
        del user_states[user_id]


async def get_user_state(client, user_id: int) -> str:
    """الحصول على حالة المستخدم"""
    return user_states.get(user_id, None)


# إضافة الوظائف للـ client
bot.set_user_state = set_user_state
bot.get_user_state = get_user_state

