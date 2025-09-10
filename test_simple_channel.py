#!/usr/bin/env python3
"""
سكريبت اختبار بسيط لفحص القناة @test1ye
"""

import asyncio
import os
from pyrogram import Client
from pyrogram.errors import (
    UserNotParticipant,
    ChatAdminRequired,
    PeerIdInvalid,
    UsernameNotOccupied,
    ChannelPrivate,
    UsernameInvalid,
    ChannelInvalid,
    ChatInvalid
)
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

async def test_channel():
    """اختبار القناة @test1ye"""
    
    # قراءة بيانات الاعتماد
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOT_TOKEN")
    
    if not all([api_id, api_hash, bot_token]):
        print("❌ خطأ: تأكد من وجود API_ID, API_HASH, BOT_TOKEN في ملف .env")
        return
    
    # إنشاء عميل البوت
    client = Client(
        name="test_bot",
        api_id=int(api_id),
        api_hash=api_hash,
        bot_token=bot_token,
        in_memory=True
    )
    
    try:
        await client.start()
        print("✅ البوت متصل\n")
        
        # معلومات البوت
        me = await client.get_me()
        print(f"🤖 البوت: @{me.username} (ID: {me.id})\n")
        
        # قائمة التنسيقات المختلفة للاختبار
        test_formats = [
            "@test1ye",
            "test1ye",
            "@Test1ye",
            "Test1ye",
            "https://t.me/test1ye",
            "t.me/test1ye"
        ]
        
        print("=" * 60)
        print("🧪 اختبار التنسيقات المختلفة للقناة")
        print("=" * 60)
        
        for format_str in test_formats:
            print(f"\n📝 اختبار: {format_str}")
            print("-" * 40)
            
            try:
                # محاولة الحصول على القناة
                chat = await client.get_chat(format_str)
                print(f"✅ تم العثور على القناة!")
                print(f"   📌 الاسم: {chat.title}")
                print(f"   🆔 ID: {chat.id}")
                print(f"   👤 Username: @{chat.username}" if chat.username else "   بدون username")
                print(f"   📊 النوع: {chat.type}")
                
                # التحقق من عضوية البوت
                try:
                    bot_member = await client.get_chat_member(chat.id, "me")
                    print(f"   ✅ البوت عضو في القناة")
                    print(f"   📊 الحالة: {bot_member.status}")
                    
                    if bot_member.status in ["administrator", "creator"]:
                        print(f"   ✅ البوت مشرف!")
                    else:
                        print(f"   ❌ البوت ليس مشرفاً")
                        
                except UserNotParticipant:
                    print(f"   ❌ البوت ليس عضواً في القناة")
                except ChatAdminRequired:
                    print(f"   ⚠️ البوت عضو لكن ليس لديه صلاحيات")
                    
            except PeerIdInvalid:
                print(f"❌ معرف القناة غير صالح")
            except UsernameNotOccupied:
                print(f"❌ اسم المستخدم غير موجود")
            except UsernameInvalid:
                print(f"❌ اسم المستخدم غير صالح")
            except ChannelPrivate:
                print(f"❌ القناة خاصة والبوت ليس عضواً")
            except ChannelInvalid:
                print(f"❌ القناة غير صالحة")
            except ChatInvalid:
                print(f"❌ المحادثة غير صالحة")
            except Exception as e:
                print(f"❌ خطأ: {type(e).__name__}: {e}")
        
        print("\n" + "=" * 60)
        print("📊 الخلاصة")
        print("=" * 60)
        print("\nإذا فشلت جميع المحاولات، تحقق من:")
        print("1. أن القناة موجودة فعلاً")
        print("2. أن اسم المستخدم صحيح")
        print("3. أن البوت مضاف للقناة")
        print("4. أن البوت مشرف في القناة")
        
    except Exception as e:
        print(f"❌ خطأ عام: {e}")
    finally:
        await client.stop()
        print("\n👋 تم إيقاف البوت")


if __name__ == "__main__":
    asyncio.run(test_channel())