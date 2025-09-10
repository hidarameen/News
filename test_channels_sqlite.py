#!/usr/bin/env python3
"""
سكريبت اختبار نظام إدارة القنوات باستخدام SQLite
للاختبار السريع بدون الحاجة لـ PostgreSQL
"""

import asyncio
import sqlite3
import os
from datetime import datetime

# إنشاء قاعدة بيانات SQLite للاختبار
def setup_sqlite_db():
    """إنشاء جداول SQLite للاختبار"""
    conn = sqlite3.connect('test_bot.db')
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول القنوات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            channel_username TEXT,
            channel_title TEXT,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, channel_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # إنشاء فهرس
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_channels_user_id ON channels(user_id)')
    
    conn.commit()
    conn.close()
    print("✅ تم إنشاء قاعدة البيانات SQLite للاختبار")

# محاكاة وظائف إدارة القنوات
class TestChannelManager:
    @staticmethod
    def add_channel(user_id: int, channel_id: int, channel_username: str, channel_title: str) -> bool:
        """إضافة قناة للمستخدم"""
        try:
            conn = sqlite3.connect('test_bot.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO channels (user_id, channel_id, channel_username, channel_title, is_admin)
                VALUES (?, ?, ?, ?, 1)
            ''', (user_id, channel_id, channel_username, channel_title))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ خطأ في إضافة القناة: {e}")
            return False
    
    @staticmethod
    def get_user_channels(user_id: int) -> list:
        """الحصول على قنوات المستخدم"""
        try:
            conn = sqlite3.connect('test_bot.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT channel_id, channel_username, channel_title, is_admin, created_at
                FROM channels
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"❌ خطأ في جلب القنوات: {e}")
            return []
    
    @staticmethod
    def remove_channel(user_id: int, channel_id: int) -> bool:
        """حذف قناة من قائمة المستخدم"""
        try:
            conn = sqlite3.connect('test_bot.db')
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM channels WHERE user_id = ? AND channel_id = ?', (user_id, channel_id))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected > 0
        except Exception as e:
            print(f"❌ خطأ في حذف القناة: {e}")
            return False
    
    @staticmethod
    def get_channel_count(user_id: int) -> int:
        """الحصول على عدد قنوات المستخدم"""
        try:
            conn = sqlite3.connect('test_bot.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM channels WHERE user_id = ?', (user_id,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
        except Exception as e:
            print(f"❌ خطأ في حساب القنوات: {e}")
            return 0

def test_channel_functions():
    """اختبار وظائف إدارة القنوات"""
    print("\n🧪 بدء اختبار وظائف إدارة القنوات...")
    
    # بيانات اختبارية
    test_user_id = 123456789
    test_channels = [
        (-1001234567890, "channel1", "قناة الأخبار"),
        (-1001234567891, "channel2", "قناة التقنية"),
        (-1001234567892, "channel3", "قناة التعليم"),
    ]
    
    manager = TestChannelManager()
    
    # اختبار إضافة القنوات
    print("\n📝 اختبار إضافة القنوات...")
    for channel_id, username, title in test_channels:
        success = manager.add_channel(test_user_id, channel_id, username, title)
        if success:
            print(f"  ✅ تم إضافة: {title} (@{username})")
        else:
            print(f"  ❌ فشل إضافة: {title}")
    
    # اختبار عدد القنوات
    print("\n📊 اختبار عدد القنوات...")
    count = manager.get_channel_count(test_user_id)
    print(f"  عدد القنوات: {count}")
    
    # اختبار عرض القنوات
    print("\n📋 اختبار عرض القنوات...")
    channels = manager.get_user_channels(test_user_id)
    for i, channel in enumerate(channels, 1):
        print(f"  {i}. {channel['channel_title']} (@{channel['channel_username']})")
        print(f"     ID: {channel['channel_id']}")
    
    # اختبار حذف قناة
    print("\n🗑 اختبار حذف قناة...")
    if channels:
        channel_to_delete = channels[0]['channel_id']
        success = manager.remove_channel(test_user_id, channel_to_delete)
        if success:
            print(f"  ✅ تم حذف القناة: {channels[0]['channel_title']}")
        else:
            print(f"  ❌ فشل حذف القناة")
        
        # التحقق من العدد بعد الحذف
        new_count = manager.get_channel_count(test_user_id)
        print(f"  عدد القنوات بعد الحذف: {new_count}")
    
    # اختبار إضافة قناة مكررة
    print("\n🔄 اختبار إضافة قناة مكررة...")
    if test_channels:
        channel_id, username, title = test_channels[0]
        success = manager.add_channel(test_user_id, channel_id, username, title + " (محدث)")
        if success:
            print(f"  ✅ تم تحديث القناة: {title}")
        
        # عرض القنوات بعد التحديث
        channels = manager.get_user_channels(test_user_id)
        updated_channel = next((ch for ch in channels if ch['channel_id'] == channel_id), None)
        if updated_channel:
            print(f"  الاسم الجديد: {updated_channel['channel_title']}")

def test_channel_extraction():
    """اختبار استخراج معرفات القنوات من النص"""
    print("\n🔍 اختبار استخراج معرفات القنوات...")
    
    test_inputs = [
        "@channel_username",
        "https://t.me/channel_name",
        "http://telegram.me/another_channel",
        "-1001234567890",
        "1234567890",  # سيتم تحويله إلى ID قناة سالب
        "https://t.me/joinchat/XXXXX",  # رابط دعوة - يجب تجاهله
        "نص عادي بدون قناة",
    ]
    
    import re
    
    for input_text in test_inputs:
        print(f"\n  إدخال: {input_text}")
        
        # محاكاة استخراج القناة
        if input_text.startswith('@'):
            print(f"    ← معرف قناة: {input_text}")
        elif 't.me/' in input_text or 'telegram.me/' in input_text:
            match = re.search(r't(?:elegram)?\.me/([a-zA-Z0-9_]+)', input_text)
            if match and not match.group(1).startswith('joinchat'):
                print(f"    ← معرف قناة: @{match.group(1)}")
            else:
                print(f"    ← ليس قناة صالحة")
        elif input_text.lstrip('-').isdigit():
            channel_id = int(input_text)
            if channel_id > 0:
                channel_id = -100 * abs(channel_id)
            print(f"    ← ID قناة: {channel_id}")
        else:
            print(f"    ← ليس قناة")

def main():
    """الدالة الرئيسية للاختبار"""
    print("=" * 60)
    print("🤖 اختبار نظام إدارة القنوات للبوت")
    print("=" * 60)
    
    # إنشاء قاعدة البيانات
    setup_sqlite_db()
    
    # اختبار الوظائف
    test_channel_functions()
    
    # اختبار استخراج القنوات
    test_channel_extraction()
    
    print("\n" + "=" * 60)
    print("✅ اكتمل الاختبار بنجاح!")
    print("=" * 60)
    
    # حذف ملف قاعدة البيانات الاختبارية
    if os.path.exists('test_bot.db'):
        os.remove('test_bot.db')
        print("\n🗑 تم حذف ملف قاعدة البيانات الاختبارية")

if __name__ == "__main__":
    main()