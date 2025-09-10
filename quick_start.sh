#!/bin/bash

echo "=================================="
echo "🤖 Telegram Bot - Quick Start"
echo "=================================="

# التحقق من وجود ملف .env
if [ ! -f .env ]; then
    echo "❌ ملف .env غير موجود!"
    echo ""
    echo "📝 قم بإنشاء ملف .env وأضف:"
    echo ""
    echo "BOT_TOKEN=YOUR_BOT_TOKEN_HERE"
    echo "API_ID=YOUR_API_ID_HERE"
    echo "API_HASH=YOUR_API_HASH_HERE"
    echo "DATABASE_URL=postgresql://bot:bot@localhost:5432/botdb"
    echo ""
    exit 1
fi

# تحميل متغيرات البيئة
export $(cat .env | grep -v '^#' | xargs)

# التحقق من وجود BOT_TOKEN
if [ -z "$BOT_TOKEN" ] || [ "$BOT_TOKEN" = "YOUR_BOT_TOKEN_HERE" ]; then
    echo "❌ يجب تعيين BOT_TOKEN في ملف .env"
    exit 1
fi

# التحقق من وجود Docker
if command -v docker &> /dev/null; then
    echo "🐳 Docker متوفر، تشغيل قاعدة البيانات..."
    docker compose up -d postgres redis 2>/dev/null || docker-compose up -d postgres redis 2>/dev/null
    echo "⏳ انتظار 5 ثواني لبدء قاعدة البيانات..."
    sleep 5
else
    echo "⚠️ Docker غير متوفر، استخدام SQLite للاختبار..."
    export DATABASE_URL="sqlite:///test_bot.db"
fi

# تثبيت المكتبات إذا لزم الأمر
if ! python3 -c "import pyrogram" 2>/dev/null; then
    echo "📦 تثبيت المكتبات المطلوبة..."
    pip3 install --user -r requirements.txt
fi

echo ""
echo "🚀 بدء تشغيل البوت..."
echo "📡 الأوامر المتاحة:"
echo "  /start - بدء البوت"
echo "  /channels - إدارة القنوات"
echo ""
echo "اضغط Ctrl+C للإيقاف"
echo "=================================="
echo ""

# تشغيل البوت
python3 -m app.bot.client