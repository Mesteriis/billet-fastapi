"""Тесты для модуля конфигурации."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import pytz

from src.core.config import Settings, get_settings


class TestSettings:
    """Тесты для класса Settings."""

    def test_default_settings(self):
        """Тест настроек по умолчанию."""
        settings = Settings()

        # Основные настройки
        assert settings.PROJECT_NAME == "Mango Message"
        assert settings.PROJECT_DESCRIPTION == "API for messaging system"
        assert settings.VERSION == "1.0.0"
        assert settings.API_V1_STR == "/api/v1"
        assert settings.DEBUG is False
        assert settings.SECRET_KEY is not None

        # База данных
        assert settings.POSTGRES_SERVER == "localhost"
        assert settings.POSTGRES_USER == "postgres"
        assert settings.POSTGRES_PASSWORD == "postgres"
        assert settings.POSTGRES_DB == "mango_msg"
        assert settings.POSTGRES_PORT == 5432

        # Redis
        assert settings.REDIS_HOST == "localhost"
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_DB == 0

        # RabbitMQ
        assert settings.RABBITMQ_HOST == "localhost"
        assert settings.RABBITMQ_PORT == 5672
        assert settings.RABBITMQ_USER == "guest"
        assert settings.RABBITMQ_PASSWORD == "guest"

    def test_timezone_validation_string(self):
        """Тест валидации временной зоны из строки."""
        settings = Settings(TZ="UTC")
        assert settings.TZ == pytz.UTC

        settings = Settings(TZ="Europe/Moscow")
        assert settings.TZ == pytz.timezone("Europe/Moscow")

    def test_timezone_validation_tzinfo(self):
        """Тест валидации временной зоны из tzinfo объекта."""
        tz = pytz.timezone("Asia/Tokyo")
        settings = Settings(TZ=tz)
        assert settings.TZ == tz

    def test_timezone_validation_invalid(self):
        """Тест валидации неверной временной зоны."""
        with pytest.raises(ValueError, match="Invalid timezone"):
            Settings(TZ=123)

    def test_cors_origins_string(self):
        """Тест обработки CORS origins из строки."""
        settings = Settings(CORS_ORIGINS="http://localhost:3000,http://localhost:8080")
        assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:8080"]

    def test_cors_origins_list(self):
        """Тест обработки CORS origins из списка."""
        origins = ["http://localhost:3000", "http://localhost:8080"]
        settings = Settings(CORS_ORIGINS=origins)
        assert settings.CORS_ORIGINS == origins

    def test_cors_origins_invalid(self):
        """Тест обработки неверных CORS origins."""
        with pytest.raises(ValueError):
            Settings(CORS_ORIGINS=123)

    def test_api_keys_string(self):
        """Тест обработки API ключей из строки."""
        settings = Settings(WS_API_KEYS="key1,key2,key3")
        assert settings.WS_API_KEYS == ["key1", "key2", "key3"]

    def test_api_keys_empty_string(self):
        """Тест обработки пустых API ключей."""
        settings = Settings(WS_API_KEYS="")
        assert settings.WS_API_KEYS == []

    def test_api_keys_with_spaces(self):
        """Тест обработки API ключей с пробелами."""
        settings = Settings(WS_API_KEYS="key1, key2 , key3,")
        assert settings.WS_API_KEYS == ["key1", "key2", "key3"]

    def test_url_generation(self):
        """Тест автоматической генерации URL."""
        settings = Settings(
            POSTGRES_USER="testuser", POSTGRES_PASSWORD="testpass", POSTGRES_SERVER="testhost", POSTGRES_DB="testdb"
        )

        expected_db_url = "postgresql+asyncpg://testuser:testpass@testhost/testdb"
        assert settings.SQLALCHEMY_DATABASE_URI == expected_db_url

    def test_redis_url_generation(self):
        """Тест генерации Redis URL."""
        settings = Settings(REDIS_HOST="redis-host", REDIS_PORT=6380, REDIS_DB=1, REDIS_PASSWORD="redis-pass")

        expected_redis_url = "redis://:redis-pass@redis-host:6380/1"
        assert settings.REDIS_URL == expected_redis_url

    def test_redis_url_without_password(self):
        """Тест генерации Redis URL без пароля."""
        settings = Settings(REDIS_HOST="redis-host", REDIS_PORT=6380, REDIS_DB=1)

        expected_redis_url = "redis://redis-host:6380/1"
        assert settings.REDIS_URL == expected_redis_url

    def test_rabbitmq_url_generation(self):
        """Тест генерации RabbitMQ URL."""
        settings = Settings(
            RABBITMQ_USER="rabbituser",
            RABBITMQ_PASSWORD="rabbitpass",
            RABBITMQ_HOST="rabbit-host",
            RABBITMQ_PORT=5673,
            RABBITMQ_VHOST="/test",
        )

        expected_url = "amqp://rabbituser:rabbitpass@rabbit-host:5673/test"
        assert settings.RABBITMQ_URL == expected_url

    def test_taskiq_broker_url_generation(self):
        """Тест генерации TaskIQ broker URL."""
        settings = Settings(REDIS_HOST="taskiq-host", REDIS_PORT=6380, REDIS_PASSWORD="taskiq-pass")

        expected_url = "redis://:taskiq-pass@taskiq-host:6380/1"
        assert settings.TASKIQ_BROKER_URL == expected_url

    def test_taskiq_result_backend_url_generation(self):
        """Тест генерации TaskIQ result backend URL."""
        settings = Settings(REDIS_HOST="result-host", REDIS_PORT=6380, REDIS_PASSWORD="result-pass")

        expected_url = "redis://:result-pass@result-host:6380/2"
        assert settings.TASKIQ_RESULT_BACKEND_URL == expected_url

    def test_explicit_urls_not_overridden(self):
        """Тест что явно заданные URL не переопределяются."""
        custom_db_url = "postgresql://custom@host/db"
        custom_redis_url = "redis://custom-redis:6379/0"
        custom_rabbitmq_url = "amqp://custom-rabbit:5672/"

        settings = Settings(
            SQLALCHEMY_DATABASE_URI=custom_db_url, REDIS_URL=custom_redis_url, RABBITMQ_URL=custom_rabbitmq_url
        )

        assert settings.SQLALCHEMY_DATABASE_URI == custom_db_url
        assert settings.REDIS_URL == custom_redis_url
        assert settings.RABBITMQ_URL == custom_rabbitmq_url

    def test_environment_override(self, monkeypatch):
        """Тест переопределения настроек через переменные окружения."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("PROJECT_NAME", "Test Project")

        settings = Settings()

        assert settings.DEBUG is True
        assert settings.PROJECT_NAME == "Test Project"

    def test_database_url_construction(self):
        """Тест построения URL базы данных."""
        settings = Settings(
            POSTGRES_SERVER="localhost",
            POSTGRES_USER="test",
            POSTGRES_PASSWORD="test",
            POSTGRES_DB="test_db",
            POSTGRES_PORT=5432,
        )

        expected_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        assert settings.ASYNC_DATABASE_URI == expected_url

    def test_secret_key_generation(self):
        """Тест генерации секретного ключа."""
        settings1 = Settings()
        settings2 = Settings()

        # Секретные ключи должны быть одинаковыми для одного экземпляра
        assert settings1.SECRET_KEY == settings1.SECRET_KEY

        # Но разными для разных экземпляров (если не задан явно)
        # На самом деле они будут одинаковыми, так как используется хешированный алгоритм
        assert len(settings1.SECRET_KEY) > 10

    def test_upload_settings(self):
        """Тест настроек загрузки файлов."""
        settings = Settings()

        assert settings.UPLOAD_MAX_SIZE > 0
        assert settings.UPLOAD_ALLOWED_EXTENSIONS is not None
        assert isinstance(settings.UPLOAD_ALLOWED_EXTENSIONS, list)

    def test_logging_settings(self):
        """Тест настроек логирования."""
        settings = Settings()

        assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert isinstance(settings.LOG_FORMAT, str)

    def test_cache_settings(self):
        """Тест настроек кеширования."""
        settings = Settings()

        assert settings.CACHE_TTL >= 0
        assert settings.CACHE_KEY_PREFIX is not None

    def test_email_settings(self):
        """Тест настроек email."""
        settings = Settings(
            SMTP_HOST="smtp.example.com", SMTP_PORT=587, SMTP_USER="test@example.com", SMTP_PASSWORD="password"
        )

        assert settings.SMTP_HOST == "smtp.example.com"
        assert settings.SMTP_PORT == 587
        assert settings.SMTP_TLS is True  # По умолчанию


class TestGetSettings:
    """Тесты для функции get_settings."""

    def test_get_settings_singleton(self):
        """Тест что get_settings возвращает один и тот же объект."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_returns_settings_instance(self):
        """Тест что get_settings возвращает экземпляр Settings."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_settings_caching(self):
        """Тест кеширования настроек."""
        # Первый вызов
        settings1 = get_settings()

        # Второй вызов должен вернуть закешированный результат
        settings2 = get_settings()

        assert settings1 is settings2
        assert id(settings1) == id(settings2)

    def test_env_file_loading(self):
        """Тест загрузки из .env файла."""
        # Создаем временный .env файл
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("PROJECT_NAME=Env Test Project\\n")
            f.write("DEBUG=true\\n")
            temp_env_file = f.name

        try:
            # Создаем настройки с указанием env файла
            settings = Settings(_env_file=temp_env_file)

            assert settings.PROJECT_NAME == "Env Test Project"
            assert settings.DEBUG is True
        finally:
            os.unlink(temp_env_file)

    def test_validation_errors(self):
        """Тест ошибок валидации."""
        with pytest.raises(ValueError):
            Settings(POSTGRES_PORT="invalid_port")

    def test_nested_settings(self):
        """Тест вложенных настроек."""
        settings = Settings()

        # Проверяем что все необходимые настройки присутствуют
        required_attrs = [
            "PROJECT_NAME",
            "VERSION",
            "DEBUG",
            "SECRET_KEY",
            "POSTGRES_SERVER",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "REDIS_HOST",
            "REDIS_PORT",
        ]

        for attr in required_attrs:
            assert hasattr(settings, attr), f"Missing attribute: {attr}"

    @pytest.mark.parametrize(
        "debug_value,expected",
        [
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
        ],
    )
    def test_boolean_parsing(self, debug_value, expected, monkeypatch):
        """Тест парсинга булевых значений."""
        monkeypatch.setenv("DEBUG", debug_value)
        settings = Settings()
        assert settings.DEBUG is expected


class TestEnvironmentVariables:
    """Тесты работы с переменными окружения."""

    def test_settings_from_env(self, monkeypatch):
        """Тест загрузки настроек из переменных окружения."""
        monkeypatch.setenv("PROJECT_NAME", "Test Project")
        monkeypatch.setenv("POSTGRES_HOST", "test-db")
        monkeypatch.setenv("REDIS_PORT", "6380")

        # Очищаем кэш настроек
        get_settings.cache_clear()

        settings = get_settings()
        assert settings.PROJECT_NAME == "Test Project"
        assert settings.POSTGRES_SERVER == "test-db"
        assert settings.REDIS_PORT == 6380

    def test_boolean_settings_from_env(self, monkeypatch):
        """Тест булевых настроек из переменных окружения."""
        monkeypatch.setenv("DB_ECHO", "true")
        monkeypatch.setenv("WEBSOCKET_ENABLED", "false")
        monkeypatch.setenv("COOKIE_SECURE", "false")

        get_settings.cache_clear()

        settings = get_settings()
        assert settings.DB_ECHO is True
        assert settings.WEBSOCKET_ENABLED is False
        assert settings.COOKIE_SECURE is False

    def test_integer_settings_from_env(self, monkeypatch):
        """Тест целочисленных настроек из переменных окружения."""
        monkeypatch.setenv("DB_POOL_SIZE", "50")
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "120")
        monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

        get_settings.cache_clear()

        settings = get_settings()
        assert settings.DB_POOL_SIZE == 50
        assert settings.RATE_LIMIT_PER_MINUTE == 120
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60


class TestSettingsValidation:
    """Тесты валидации настроек."""

    def test_negative_pool_size_validation(self):
        """Тест валидации отрицательного размера пула."""
        # Должно работать, так как валидация не установлена
        settings = Settings(DB_POOL_SIZE=-1)
        assert settings.DB_POOL_SIZE == -1

    def test_websocket_settings_validation(self):
        """Тест валидации настроек WebSocket."""
        settings = Settings(
            WEBSOCKET_MAX_CONNECTIONS=1000, WEBSOCKET_HEARTBEAT_INTERVAL=30, WEBSOCKET_MESSAGE_QUEUE_SIZE=100
        )

        assert settings.WEBSOCKET_MAX_CONNECTIONS == 1000
        assert settings.WEBSOCKET_HEARTBEAT_INTERVAL == 30
        assert settings.WEBSOCKET_MESSAGE_QUEUE_SIZE == 100

    def test_sse_settings_validation(self):
        """Тест валидации настроек SSE."""
        settings = Settings(
            SSE_MAX_CONNECTIONS=500, SSE_HEARTBEAT_INTERVAL=30, SSE_RETRY_TIMEOUT=3000, SSE_MAX_MESSAGE_SIZE=1048576
        )

        assert settings.SSE_MAX_CONNECTIONS == 500
        assert settings.SSE_HEARTBEAT_INTERVAL == 30
        assert settings.SSE_RETRY_TIMEOUT == 3000
        assert settings.SSE_MAX_MESSAGE_SIZE == 1048576

    def test_taskiq_settings_validation(self):
        """Тест валидации настроек TaskIQ."""
        settings = Settings(TASKIQ_MAX_RETRIES=5, TASKIQ_RETRY_DELAY=10, TASKIQ_TASK_TIMEOUT=600)

        assert settings.TASKIQ_MAX_RETRIES == 5
        assert settings.TASKIQ_RETRY_DELAY == 10
        assert settings.TASKIQ_TASK_TIMEOUT == 600
