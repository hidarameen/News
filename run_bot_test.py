#!/usr/bin/env python3
"""
سكريبت تشغيل البوت للاختبار باستخدام SQLite
يسمح بتجربة البوت بدون الحاجة لـ PostgreSQL
"""

import os
import sys
import asyncio
import logging

# تعيين متغيرات البيئة للاختبار
os.environ['DATABASE_URL'] = 'sqlite:///test_bot.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

# التحقق من وجود التوكن
if not os.environ.get('BOT_TOKEN'):
    print("❌ خطأ: يجب تعيين BOT_TOKEN في متغيرات البيئة أو ملف .env")
    print("\nكيفية الاستخدام:")
    print("1. أنشئ ملف .env وأضف:")
    print("   BOT_TOKEN=YOUR_BOT_TOKEN_HERE")
    print("   API_ID=YOUR_API_ID_HERE")
    print("   API_HASH=YOUR_API_HASH_HERE")
    print("\n2. أو قم بتعيينها مباشرة:")
    print("   export BOT_TOKEN=YOUR_BOT_TOKEN_HERE")
    print("   export API_ID=YOUR_API_ID_HERE")
    print("   export API_HASH=YOUR_API_HASH_HERE")
    sys.exit(1)

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 60)
print("🤖 تشغيل البوت في وضع الاختبار (SQLite)")
print("=" * 60)
print("\n⚠️ تنبيه: هذا الوضع للاختبار فقط!")
print("للإنتاج، استخدم PostgreSQL كما هو موضح في README.md\n")

# محاولة استيراد وتشغيل البوت
try:
    from app.bot.client import main
    
    print("🚀 بدء تشغيل البوت...")
    print("📡 الأوامر المتاحة:")
    print("  /start - بدء البوت")
    print("  /channels - إدارة القنوات")
    print("\nاضغط Ctrl+C للإيقاف\n")
    
    asyncio.run(main())
    
except ImportError as e:
    print(f"❌ خطأ في الاستيراد: {e}")
    print("\nتأكد من تثبيت المكتبات المطلوبة:")
    print("pip install -r requirements.txt")
    
except KeyboardInterrupt:
    print("\n\n👋 تم إيقاف البوت")
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()