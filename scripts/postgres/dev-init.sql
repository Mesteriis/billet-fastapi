-- =============================================================================
-- PostgreSQL инициализация для разработки
-- =============================================================================

-- Создаем тестовую базу данных
CREATE DATABASE mango_msg_test;

-- Создаем дополнительные БД для разных целей  
CREATE DATABASE mango_msg_dev;
CREATE DATABASE mango_msg_staging;

-- Создаем пользователя для разработки с дополнительными правами
CREATE USER dev_user WITH PASSWORD 'dev123';
GRANT ALL PRIVILEGES ON DATABASE mango_msg TO dev_user;
GRANT ALL PRIVILEGES ON DATABASE mango_msg_test TO dev_user;
GRANT ALL PRIVILEGES ON DATABASE mango_msg_dev TO dev_user;

-- Создаем пользователя только для чтения (для аналитики)
CREATE USER readonly_user WITH PASSWORD 'readonly123';
GRANT CONNECT ON DATABASE mango_msg TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO readonly_user;

-- Установка часового пояса
ALTER DATABASE mango_msg SET timezone TO 'Europe/Moscow';
ALTER DATABASE mango_msg_test SET timezone TO 'Europe/Moscow';
ALTER DATABASE mango_msg_dev SET timezone TO 'Europe/Moscow';

-- Включаем расширения
\c mango_msg;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

\c mango_msg_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

\c mango_msg_dev;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent"; 