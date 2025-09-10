from pyrogram import filters
from pyrogram.types import Message

from app.bot.client import get_bot_client
from app.db.pool import get_pool


bot = get_bot_client()


@bot.on_message(filters.private & filters.command("start"))
async def start_handler(_, message: Message) -> None:
    user = message.from_user
    if user is None:
        return
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
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        user.language_code,
    )
    await message.reply_text("مرحبًا بك في البوت! ✨")

