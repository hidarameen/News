#!/usr/bin/env python3
"""
سكريبت تحليل مشكلة إضافة القناة
يحلل الأسباب المحتملة ويقدم حلولاً
"""

import re

def analyze_channel_identifier(identifier: str):
    """تحليل معرف القناة"""
    print(f"\n🔍 تحليل المعرف: {identifier}")
    print("-" * 40)
    
    # تحليل النوع
    if identifier.startswith('@'):
        print("✅ النوع: معرف username")
        username = identifier[1:]
        
        # التحقق من صحة username
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', username):
            print(f"✅ Username صالح: {username}")
        else:
            print(f"❌ Username غير صالح: {username}")
            print("   📝 يجب أن يبدأ بحرف ويحتوي على 5-32 حرف/رقم/_")
            
    elif identifier.lstrip('-').isdigit():
        print("✅ النوع: معرف رقمي (Channel ID)")
        channel_id = int(identifier)
        
        if channel_id < 0:
            print(f"✅ معرف قناة صالح: {channel_id}")
        else:
            print(f"⚠️ معرف يحتاج تحويل: {channel_id}")
            print(f"   سيتم تحويله إلى: {-100 * abs(channel_id)}")
            
    elif 't.me/' in identifier or 'telegram.me/' in identifier:
        print("✅ النوع: رابط Telegram")
        match = re.search(r't(?:elegram)?\.me/([a-zA-Z0-9_]+)', identifier)
        
        if match:
            username = match.group(1)
            if username.startswith('joinchat'):
                print("❌ رابط دعوة - غير مدعوم")
            else:
                print(f"✅ Username مستخرج: @{username}")
        else:
            print("❌ لم أتمكن من استخراج username من الرابط")
            
    else:
        print("⚠️ النوع: غير محدد")
        # محاولة التعرف على username بدون @
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', identifier):
            print(f"💡 قد يكون username بدون @: {identifier}")
            print(f"   جرب: @{identifier}")
        else:
            print("❌ معرف غير صالح")


def suggest_solutions(error_message: str):
    """اقتراح حلول بناءً على رسالة الخطأ"""
    print("\n💡 الحلول المقترحة:")
    print("-" * 40)
    
    if "قناة غير موجودة" in error_message:
        print("1. تحقق من صحة معرف القناة (الإملاء)")
        print("2. تأكد من أن القناة موجودة وليست محذوفة")
        print("3. جرب استخدام معرف القناة الرقمي (Channel ID)")
        print("4. تأكد من أن القناة عامة أو أن البوت عضو فيها")
        
    elif "البوت ليس مشرفاً" in error_message:
        print("1. افتح إعدادات القناة")
        print("2. اذهب إلى قسم المشرفين")
        print("3. أضف البوت كمشرف")
        print("4. امنح البوت الصلاحيات المطلوبة")
        
    elif "البوت ليس عضواً" in error_message:
        print("1. أضف البوت للقناة أولاً")
        print("2. ثم اجعله مشرفاً")
        
    else:
        print("1. تحقق من سجلات الأخطاء للحصول على تفاصيل أكثر")
        print("2. تأكد من أن بيانات الاعتماد صحيحة")
        print("3. جرب مع قناة اختبارية أخرى")


def check_bot_requirements():
    """التحقق من متطلبات البوت"""
    print("\n✅ قائمة التحقق:")
    print("-" * 40)
    
    requirements = [
        "البوت يعمل ويستجيب للأوامر",
        "القناة موجودة وليست محذوفة",
        "معرف القناة صحيح",
        "البوت عضو في القناة",
        "البوت مشرف في القناة",
        "البوت لديه صلاحيات كافية",
        "بيانات الاعتماد صحيحة في ملف .env",
        "لا توجد قيود على البوت من Telegram"
    ]
    
    for i, req in enumerate(requirements, 1):
        print(f"{i}. [ ] {req}")


def main():
    """الدالة الرئيسية"""
    print("=" * 60)
    print("🔧 أداة تحليل مشكلة إضافة القنوات")
    print("=" * 60)
    
    # تحليل رسالة الخطأ الأصلية
    error_message = "@test1ye - قناة غير موجودة"
    channel_identifier = "@test1ye"
    
    print(f"\n📋 رسالة الخطأ: {error_message}")
    
    # تحليل المعرف
    analyze_channel_identifier(channel_identifier)
    
    # اقتراح الحلول
    suggest_solutions(error_message)
    
    # قائمة التحقق
    check_bot_requirements()
    
    # التنسيقات المدعومة
    print("\n📝 التنسيقات المدعومة:")
    print("-" * 40)
    supported_formats = [
        "@channel_username",
        "channel_username",
        "https://t.me/channel_username",
        "t.me/channel_username",
        "-1001234567890",
        "1234567890"
    ]
    
    for format_str in supported_formats:
        print(f"✅ {format_str}")
    
    print("\n❌ التنسيقات غير المدعومة:")
    print("-" * 40)
    unsupported_formats = [
        "https://t.me/joinchat/XXXXX (روابط الدعوة)",
        "اسم القناة بدون username"
    ]
    
    for format_str in unsupported_formats:
        print(f"❌ {format_str}")
    
    # الخطوات التالية
    print("\n🚀 الخطوات التالية:")
    print("-" * 40)
    print("1. تحقق من أن القناة @test1ye موجودة فعلاً")
    print("2. تأكد من أن البوت مضاف كمشرف في القناة")
    print("3. جرب إضافة القناة باستخدام معرفها الرقمي")
    print("4. راجع سجلات الأخطاء (logs) للحصول على تفاصيل أكثر")
    print("5. جرب مع قناة اختبارية أخرى للتأكد من عمل النظام")
    
    print("\n" + "=" * 60)
    print("📖 للمزيد من التفاصيل، راجع ملف CHANNEL_ERROR_SOLUTION.md")
    print("=" * 60)


if __name__ == "__main__":
    main()