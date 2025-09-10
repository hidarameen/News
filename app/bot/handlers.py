from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from app.bot.client import get_bot_client
from app.db.pool import get_pool
from app.bot.channels import (
    channels_menu,
    handle_channels_callback,
    handle_channel_input
)


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
    # إنشاء لوحة المفاتيح الرئيسية
    keyboard = [
        [InlineKeyboardButton("📡 القنوات", callback_data="channels_menu")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
    ]
    
    await message.reply_text(
        "مرحبًا بك في البوت! ✨\n\nاختر من القائمة أدناه:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# معالج أزرار Callback
@bot.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery) -> None:
    data = callback_query.data
    
    # معالجة أزرار القنوات
    if data == "channels_menu":
        await channels_menu(client, callback_query.message)
        await callback_query.answer()
    elif data.startswith("channels_") or data.startswith("delete_channel_"):
        await handle_channels_callback(client, callback_query)
        await callback_query.answer()
    elif data == "main_menu":
        # العودة للقائمة الرئيسية
        keyboard = [
            [InlineKeyboardButton("📡 القنوات", callback_data="channels_menu")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
        ]
        await callback_query.message.edit_text(
            "القائمة الرئيسية:\n\nاختر من القائمة أدناه:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await callback_query.answer()
    elif data == "settings":
        await callback_query.answer("قريباً...", show_alert=True)


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

