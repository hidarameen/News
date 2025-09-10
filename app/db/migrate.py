import logging
import asyncio
import psycopg

from app.core.settings import get_settings


logger = logging.getLogger(__name__)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'users_set_updated_at'
  ) THEN
    CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
  END IF;
END$$;

-- جدول القنوات
CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    channel_username TEXT,
    channel_title TEXT,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, channel_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'channels_set_updated_at'
  ) THEN
    CREATE TRIGGER channels_set_updated_at
    BEFORE UPDATE ON channels
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
  END IF;
END$$;

-- إنشاء فهرس للبحث السريع
CREATE INDEX IF NOT EXISTS idx_channels_user_id ON channels(user_id);
"""


async def run_migrations() -> None:
    settings = get_settings()
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(SCHEMA_SQL)
            await conn.commit()
            logger.info("Database schema ensured")


if __name__ == "__main__":
    asyncio.run(run_migrations())

