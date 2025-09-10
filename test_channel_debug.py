#!/usr/bin/env python3
"""
سكريبت تشخيص متقدم لمشكلة إضافة القنوات
يختبر جميع الحالات المحتملة ويوفر تقرير مفصل
"""

import asyncio
import logging
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
from pyrogram.enums import ChatMemberStatus
import os
from dotenv import load_dotenv

# إعداد logging مفصل
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تحميل المتغيرات البيئية
load_dotenv()

class ChannelDiagnostic:
    """أداة تشخيص مشاكل القنوات"""
    
    def __init__(self, api_id: int, api_hash: str, bot_token: str):
        self.client = Client(
            name="test_bot",
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token,
            in_memory=True
        )
        self.results = []
    
    async def diagnose_channel(self, channel_identifier: str):
        """تشخيص قناة واحدة بشكل مفصل"""
        print(f"\n{'='*60}")
        print(f"🔍 تشخيص: {channel_identifier}")
        print(f"{'='*60}")
        
        result = {
            "identifier": channel_identifier,
            "exists": False,
            "is_channel": False,
            "bot_is_member": False,
            "bot_is_admin": False,
            "error": None,
            "details": {}
        }
        
        try:
            # محاولة الحصول على معلومات القناة
            print(f"⏳ جاري البحث عن القناة...")
            chat = await self.client.get_chat(channel_identifier)
            result["exists"] = True
            result["details"]["chat_id"] = chat.id
            result["details"]["title"] = chat.title
            result["details"]["username"] = chat.username
            result["details"]["type"] = str(chat.type)
            
            print(f"✅ تم العثور على القناة:")
            print(f"   📌 الاسم: {chat.title}")
            print(f"   🆔 ID: {chat.id}")
            print(f"   👤 Username: @{chat.username}" if chat.username else "   ⚠️ بدون username")
            print(f"   📊 النوع: {chat.type}")
            
            # التحقق من نوع القناة
            if chat.type in ["channel", "supergroup"]:
                result["is_channel"] = True
                print(f"   ✅ هذه قناة صالحة")
            else:
                result["is_channel"] = False
                print(f"   ❌ هذه ليست قناة (النوع: {chat.type})")
                return result
            
            # التحقق من عضوية البوت
            print(f"\n⏳ التحقق من عضوية البوت...")
            try:
                bot_member = await self.client.get_chat_member(chat.id, "me")
                result["bot_is_member"] = True
                result["details"]["bot_status"] = str(bot_member.status)
                
                print(f"✅ البوت عضو في القناة")
                print(f"   📊 الحالة: {bot_member.status}")
                
                # التحقق من صلاحيات المشرف
                if bot_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    result["bot_is_admin"] = True
                    print(f"   ✅ البوت مشرف في القناة")
                    
                    # عرض الصلاحيات
                    if hasattr(bot_member, 'privileges') and bot_member.privileges:
                        print(f"   📋 الصلاحيات:")
                        privileges = bot_member.privileges
                        if hasattr(privileges, '__dict__'):
                            for perm, value in privileges.__dict__.items():
                                if not perm.startswith('_'):
                                    print(f"      • {perm}: {value}")
                else:
                    result["bot_is_admin"] = False
                    print(f"   ❌ البوت ليس مشرفاً (الحالة: {bot_member.status})")
                    
            except UserNotParticipant:
                result["bot_is_member"] = False
                result["error"] = "البوت ليس عضواً في القناة"
                print(f"❌ البوت ليس عضواً في القناة")
            except ChatAdminRequired:
                result["bot_is_member"] = True
                result["bot_is_admin"] = False
                result["error"] = "البوت ليس لديه صلاحيات كافية"
                print(f"❌ البوت ليس لديه صلاحيات كافية")
                
        except PeerIdInvalid:
            result["error"] = "معرف القناة غير صالح"
            print(f"❌ معرف القناة غير صالح")
        except UsernameNotOccupied:
            result["error"] = "اسم المستخدم غير موجود"
            print(f"❌ اسم المستخدم غير موجود")
        except UsernameInvalid:
            result["error"] = "اسم المستخدم غير صالح"
            print(f"❌ اسم المستخدم غير صالح")
        except ChannelPrivate:
            result["error"] = "القناة خاصة والبوت ليس عضواً"
            print(f"❌ القناة خاصة والبوت ليس عضواً")
        except ChannelInvalid:
            result["error"] = "القناة غير صالحة"
            print(f"❌ القناة غير صالحة")
        except ChatInvalid:
            result["error"] = "المحادثة غير صالحة"
            print(f"❌ المحادثة غير صالحة")
        except Exception as e:
            result["error"] = f"خطأ غير متوقع: {str(e)}"
            print(f"❌ خطأ غير متوقع: {e}")
            logger.exception("خطأ في تشخيص القناة")
        
        self.results.append(result)
        return result
    
    async def test_different_formats(self):
        """اختبار تنسيقات مختلفة لمعرف القناة"""
        test_cases = [
            ("@test1ye", "معرف بـ @"),
            ("test1ye", "معرف بدون @"),
            ("https://t.me/test1ye", "رابط كامل"),
            ("t.me/test1ye", "رابط مختصر"),
        ]
        
        print(f"\n{'='*60}")
        print("🧪 اختبار التنسيقات المختلفة")
        print(f"{'='*60}")
        
        for identifier, description in test_cases:
            print(f"\n📝 اختبار: {description}")
            print(f"   المعرف: {identifier}")
            await self.diagnose_channel(identifier)
    
    async def generate_report(self):
        """توليد تقرير نهائي"""
        print(f"\n{'='*60}")
        print("📊 التقرير النهائي")
        print(f"{'='*60}\n")
        
        successful = [r for r in self.results if r["bot_is_admin"]]
        failed = [r for r in self.results if not r["bot_is_admin"]]
        
        print(f"✅ القنوات الناجحة: {len(successful)}")
        for r in successful:
            print(f"   • {r['identifier']}: {r['details'].get('title', 'N/A')}")
        
        print(f"\n❌ القنوات الفاشلة: {len(failed)}")
        for r in failed:
            print(f"   • {r['identifier']}: {r['error'] or 'البوت ليس مشرفاً'}")
        
        # توصيات
        print(f"\n💡 التوصيات:")
        for r in failed:
            if not r["exists"]:
                print(f"   • {r['identifier']}: تحقق من صحة المعرف")
            elif not r["is_channel"]:
                print(f"   • {r['identifier']}: هذه ليست قناة")
            elif not r["bot_is_member"]:
                print(f"   • {r['identifier']}: أضف البوت للقناة أولاً")
            elif not r["bot_is_admin"]:
                print(f"   • {r['identifier']}: اجعل البوت مشرفاً في القناة")
    
    async def run(self, channel_identifiers: list):
        """تشغيل التشخيص"""
        try:
            print("🚀 بدء تشغيل البوت...")
            await self.client.start()
            print("✅ البوت جاهز للعمل\n")
            
            # معلومات البوت
            me = await self.client.get_me()
            print(f"🤖 معلومات البوت:")
            print(f"   الاسم: {me.first_name}")
            print(f"   المعرف: @{me.username}")
            print(f"   ID: {me.id}")
            
            # تشخيص القنوات
            for identifier in channel_identifiers:
                await self.diagnose_channel(identifier)
            
            # التقرير النهائي
            await self.generate_report()
            
        except Exception as e:
            logger.exception(f"خطأ في تشغيل التشخيص: {e}")
        finally:
            await self.client.stop()
            print("\n👋 تم إيقاف البوت")


async def main():
    """الدالة الرئيسية"""
    # قراءة بيانات الاعتماد
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOT_TOKEN")
    
    if not all([api_id, api_hash, bot_token]):
        print("❌ خطأ: تأكد من وجود API_ID, API_HASH, BOT_TOKEN في ملف .env")
        return
    
    # القنوات المراد اختبارها
    channels_to_test = [
        "@test1ye",  # القناة المذكورة في الخطأ
        # يمكنك إضافة قنوات أخرى هنا
    ]
    
    print("="*60)
    print("🔧 أداة تشخيص مشاكل إضافة القنوات")
    print("="*60)
    
    # إنشاء وتشغيل أداة التشخيص
    diagnostic = ChannelDiagnostic(int(api_id), api_hash, bot_token)
    await diagnostic.run(channels_to_test)
    
    # اختبار التنسيقات المختلفة
    print("\n" + "="*60)
    print("هل تريد اختبار تنسيقات مختلفة للمعرف؟ (y/n)")
    if input().lower() == 'y':
        diagnostic2 = ChannelDiagnostic(int(api_id), api_hash, bot_token)
        await diagnostic2.client.start()
        await diagnostic2.test_different_formats()
        await diagnostic2.client.stop()


if __name__ == "__main__":
    asyncio.run(main())