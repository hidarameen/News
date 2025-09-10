# Pyrogram Bot Template (FastAPI Webhook + PostgreSQL)

قالب بوت Pyrogram فارغ يدعم:
- FastAPI webhook وتشغيل تلقائي عند الإقلاع
- PostgreSQL عبر asyncpg مع ترحيل مبدئي
- دعم عدة مستخدمين وتخزين بياناتهم
- طابور مهام داخلي غير متزامن لتجنب تجمّد البوت
- رسالة ترحيب فقط الآن

## المتطلبات
- Python 3.11+
- Docker (اختياري) و docker-compose

## الإعداد السريع (Docker)
1. أنشئ ملف `.env` استنادًا إلى المثال أدناه.
2. شغّل:
```bash
docker compose up --build
```
سيفتح الخادم على المنفذ 8080.

## الإعداد المحلي
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' .env | xargs)  # اختياري لتحميل المتغيرات
uvicorn app.web.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

## متغيرات البيئة (.env)
- API_ID: من my.telegram.org
- API_HASH: من my.telegram.org
- BOT_TOKEN: من BotFather
- WEBHOOK_BASE: عنوان HTTPS العام مثل https://example.com
- WEBHOOK_PATH: المسار (افتراضي /telegram/webhook)
- WEBHOOK_SECRET: قيمة سرية اختيارية لتطابق هيدر Telegram
- DATABASE_URL: مثل postgresql://bot:bot@postgres:5432/botdb
- REDIS_URL: اختياري (مستخدم للطابور داخليًا)
- PORT: افتراضي 8080

### مثال .env
```env
API_ID=123456
API_HASH=your_api_hash
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
WEBHOOK_BASE=https://your.domain
WEBHOOK_PATH=/telegram/webhook
WEBHOOK_SECRET=optional-secret
DATABASE_URL=postgresql://bot:bot@localhost:5432/botdb
REDIS_URL=redis://localhost:6379/0
PORT=8080
```

## كيف يعمل
- عند الإقلاع: يجري ترحيل قاعدة البيانات، إنشاء تجمع الاتصال، بدء طابور الخلفية، وبدء عميل Pyrogram.
- إذا تم ضبط `WEBHOOK_BASE`، يتم استدعاء `setWebhook` تلقائيًا.
- نقطة استقبال Telegram: `POST ${WEBHOOK_PATH}`.
- يتم إدراج/تحديث المستخدمين عند أي رسالة، وإذا كانت `/start` يتم إرسال رسالة ترحيب.

## توسيع البوت
- أضف معالجات في `app/bot/handlers.py` (إذا استخدمت polling لاحقًا).
- أضف جداول/وظائف في `app/db/migrate.py` وطبقة وصول البيانات.