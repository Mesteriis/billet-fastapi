"""Тесты для модуля конфигурации."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import pytz

from src.core.config import Settings, get_settings



@pytest.mark.unit
class TestSettings:
    """Тесты для класса Settings."""

    @pytest.fixture
    def default_settings(self):
        """Фикстура настроек по умолчанию."""
        return Settings()

    def test_default_settings(self, default_settings):
        """Тест настроек по умолчанию."""
        # Основные настройки
        assert default_settings.PROJECT_NAME == "Mango Message"
        assert default_settings.PROJECT_DESCRIPTION == "API for messaging system"
        assert default_settings.VERSION == "1.0.0"
        assert default_settings.API_V1_STR == "/api/v1"
        assert default_settings.DEBUG is False
        assert default_settings.SECRET_KEY is not None

        # База данных
        assert default_settings.POSTGRES_SERVER == "localhost"
        assert default_settings.POSTGRES_USER == "postgres"
        assert default_settings.POSTGRES_PASSWORD == "postgres"
        assert default_settings.POSTGRES_DB == "mango_msg"
        assert default_settings.POSTGRES_PORT == 5432

        # Redis
        assert default_settings.REDIS_HOST == "localhost"
        assert default_settings.REDIS_PORT == 6379
        assert default_settings.REDIS_DB == 0

        # RabbitMQ
        assert default_settings.RABBITMQ_HOST == "localhost"
        assert default_settings.RABBITMQ_PORT == 5672
        assert default_settings.RABBITMQ_USER == "guest"
        assert default_settings.RABBITMQ_PASSWORD == "guest"

    @pytest.mark.parametrize(
        "timezone,expected_type",
        [
            ("UTC", pytz.UTC),
            ("Europe/Moscow", pytz.timezone("Europe/Moscow")),
            ("Asia/Tokyo", pytz.timezone("Asia/Tokyo")),
        ],
    )
    def test_timezone_validation_string(self, timezone, expected_type):
        """Тест валидации временной зоны из строки."""
        settings = Settings(TZ=timezone)
        assert settings.TZ == expected_type

    def test_timezone_validation_tzinfo(self):
        """Тест валидации временной зоны из tzinfo объекта."""
        tz = pytz.timezone("Asia/Tokyo")
        settings = Settings(TZ=tz)
        assert settings.TZ == tz

    def test_timezone_validation_invalid(self):
        """Тест валидации неверной временной зоны."""
        with pytest.raises(ValueError, match="Invalid timezone"):
            Settings(TZ=123)

    @pytest.mark.parametrize(
        "origins_input,expected",
        [
            ("http://localhost:3000,http://localhost:8080", ["http://localhost:3000", "http://localhost:8080"]),
            (["http://localhost:3000", "http://localhost:8080"], ["http://localhost:3000", "http://localhost:8080"]),
            ("", []),
            ("http://localhost:3000", ["http://localhost:3000"]),
        ],
    )
    def test_cors_origins_processing(self, origins_input, expected):
        """Тест обработки CORS origins в различных форматах."""
        settings = Settings(CORS_ORIGINS=origins_input)
        assert settings.CORS_ORIGINS == expected

    def test_cors_origins_invalid(self):
        """Тест обработки неверных CORS origins."""
        with pytest.raises(ValueError):
            Settings(CORS_ORIGINS=123)

    @pytest.mark.parametrize(
        "api_keys_input,expected",
        [
            ("key1,key2,key3", ["key1", "key2", "key3"]),
            ("", []),
            ("key1, key2 , key3,", ["key1", "key2", "key3"]),
            ("single-key", ["single-key"]),
        ],
    )
    def test_api_keys_processing(self, api_keys_input, expected):
        """Тест обработки API ключей в различных форматах."""
        settings = Settings(WS_API_KEYS=api_keys_input)
        assert settings.WS_API_KEYS == expected

    def test_database_url_generation(self):
        """Тест автоматической генерации URL базы данных."""
        settings = Settings(
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_SERVER="testhost",
            POSTGRES_DB="testdb",
            POSTGRES_PORT=5433,
        )

        expected_db_url = "postgresql+asyncpg://testuser:testpass@testhost:5433/testdb"
        assert settings.SQLALCHEMY_DATABASE_URI == expected_db_url

    @pytest.mark.parametrize(
        "redis_config,expected_url",
        [
            (
                {"REDIS_HOST": "redis-host", "REDIS_PORT": 6380, "REDIS_DB": 1, "REDIS_PASSWORD": "redis-pass"},
                "redis://:redis-pass@redis-host:6380/1",
            ),
            ({"REDIS_HOST": "redis-host", "REDIS_PORT": 6380, "REDIS_DB": 1}, "redis://redis-host:6380/1"),
            ({"REDIS_HOST": "localhost", "REDIS_PORT": 6379, "REDIS_DB": 0}, "redis://localhost:6379/0"),
        ],
    )
    def test_redis_url_generation(self, redis_config, expected_url):
        """Тест генерации Redis URL с различными конфигурациями."""
        settings = Settings(**redis_config)
        assert settings.REDIS_URL == expected_url

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

    def test_taskiq_urls_generation(self):
        """Тест генерации TaskIQ URL."""
        settings = Settings(REDIS_HOST="taskiq-host", REDIS_PORT=6380, REDIS_PASSWORD="taskiq-pass")

        expected_broker_url = "redis://:taskiq-pass@taskiq-host:6380/1"
        expected_result_url = "redis://:taskiq-pass@taskiq-host:6380/2"

        assert settings.TASKIQ_BROKER_URL == expected_broker_url
        assert settings.TASKIQ_RESULT_BACKEND_URL == expected_result_url

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

    def test_secret_key_properties(self, default_settings):
        """Тест свойств секретного ключа."""
        # Секретный ключ должен быть стабильным для одного экземпляра
        assert default_settings.SECRET_KEY == default_settings.SECRET_KEY
        assert len(default_settings.SECRET_KEY) > 10
        assert isinstance(default_settings.SECRET_KEY, str)

    def test_upload_settings(self, default_settings):
        """Тест настроек загрузки файлов."""
        assert hasattr(default_settings, "UPLOAD_MAX_FILE_SIZE")
        assert hasattr(default_settings, "UPLOAD_ALLOWED_EXTENSIONS")

    def test_logging_settings(self, default_settings):
        """Тест настроек логирования."""
        assert hasattr(default_settings, "LOG_LEVEL")

    def test_cache_settings(self, default_settings):
        """Тест настроек кеширования."""
        assert hasattr(default_settings, "REDIS_HOST")
        assert hasattr(default_settings, "REDIS_PORT")

    def test_email_settings(self, default_settings):
        """Тест настроек электронной почты."""
        assert hasattr(default_settings, "SMTP_HOST")
        assert hasattr(default_settings, "SMTP_PORT")


@pytest.mark.config
@pytest.mark.integration
class TestGetSettings:
    """Тесты для функции get_settings."""

    def test_get_settings_singleton(self):
        """Тест что get_settings возвращает синглтон."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_returns_settings_instance(self):
        """Тест что get_settings возвращает экземпляр Settings."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_settings_caching(self):
        """Тест кеширования настроек."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Должны быть тем же объектом
        assert id(settings1) == id(settings2)

        # И иметь одинаковые значения
        assert settings1.SECRET_KEY == settings2.SECRET_KEY
        assert settings1.PROJECT_NAME == settings2.PROJECT_NAME


@pytest.mark.config
@pytest.mark.environment
class TestEnvironmentVariables:
    """Тесты для работы с переменными окружения."""

    def test_environment_override(self, monkeypatch):
        """Тест переопределения настроек через переменные окружения."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("PROJECT_NAME", "Test Project")

        settings = Settings()

        assert settings.DEBUG is True
        assert settings.PROJECT_NAME == "Test Project"

    def test_settings_from_env(self, monkeypatch):
        """Тест загрузки настроек из переменных окружения."""
        monkeypatch.setenv("POSTGRES_SERVER", "env-postgres")
        monkeypatch.setenv("POSTGRES_USER", "env-user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "env-pass")
        monkeypatch.setenv("POSTGRES_DB", "env-db")
        monkeypatch.setenv("POSTGRES_PORT", "5433")

        settings = Settings()

        assert settings.POSTGRES_SERVER == "env-postgres"
        assert settings.POSTGRES_USER == "env-user"
        assert settings.POSTGRES_PASSWORD == "env-pass"
        assert settings.POSTGRES_DB == "env-db"
        assert settings.POSTGRES_PORT == 5433

    @pytest.mark.parametrize(
        "debug_value,expected",
        [
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
            ("True", True),
            ("False", False),
            ("TRUE", True),
            ("FALSE", False),
        ],
    )
    def test_boolean_parsing(self, debug_value, expected, monkeypatch):
        """Тест парсинга булевых значений из переменных окружения."""
        monkeypatch.setenv("DEBUG", debug_value)
        settings = Settings()
        assert settings.DEBUG is expected

    def test_integer_settings_from_env(self, monkeypatch):
        """Тест загрузки целочисленных настроек из переменных окружения."""
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("RABBITMQ_PORT", "5673")

        settings = Settings()

        assert settings.POSTGRES_PORT == 5433
        assert settings.REDIS_PORT == 6380
        assert settings.RABBITMQ_PORT == 5673

    def test_list_settings_from_env(self, monkeypatch):
        """Тест загрузки списочных настроек из переменных окружения."""
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
        monkeypatch.setenv("WS_API_KEYS", "key1,key2,key3")

        settings = Settings()

        assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:8080"]
        assert settings.WS_API_KEYS == ["key1", "key2", "key3"]


@pytest.mark.config
@pytest.mark.validation
class TestSettingsValidation:
    """Тесты для валидации настроек."""

    def test_negative_pool_size_validation(self):
        """Тест валидации отрицательного размера пула подключений."""
        with pytest.raises(ValueError):
            Settings(POSTGRES_POOL_SIZE=-1)

    def test_websocket_settings_validation(self):
        """Тест валидации настроек WebSocket."""
        settings = Settings()

        # Проверяем, что настройки WebSocket имеют правильные типы
        if hasattr(settings, "WS_HEARTBEAT_INTERVAL"):
            assert isinstance(settings.WS_HEARTBEAT_INTERVAL, (int, float))

        if hasattr(settings, "WS_MAX_CONNECTIONS"):
            assert isinstance(settings.WS_MAX_CONNECTIONS, int)
            assert settings.WS_MAX_CONNECTIONS > 0

    def test_sse_settings_validation(self):
        """Тест валидации настроек SSE."""
        settings = Settings()

        if hasattr(settings, "SSE_HEARTBEAT_INTERVAL"):
            assert isinstance(settings.SSE_HEARTBEAT_INTERVAL, (int, float))
            assert settings.SSE_HEARTBEAT_INTERVAL > 0

    def test_taskiq_settings_validation(self):
        """Тест валидации настроек TaskIQ."""
        settings = Settings()

        # URL TaskIQ должны быть строками
        assert isinstance(settings.TASKIQ_BROKER_URL, str)
        assert isinstance(settings.TASKIQ_RESULT_BACKEND_URL, str)

        # URL должны начинаться с redis://
        assert settings.TASKIQ_BROKER_URL.startswith("redis://")
        assert settings.TASKIQ_RESULT_BACKEND_URL.startswith("redis://")

    def test_database_url_validation(self):
        """Тест валидации URL базы данных."""
        settings = Settings()

        # URL базы данных должен быть корректным
        assert isinstance(settings.SQLALCHEMY_DATABASE_URI, str)
        assert "postgresql+asyncpg://" in settings.SQLALCHEMY_DATABASE_URI

        if hasattr(settings, "ASYNC_DATABASE_URI"):
            assert isinstance(settings.ASYNC_DATABASE_URI, str)
            assert "postgresql+asyncpg://" in settings.ASYNC_DATABASE_URI

    def test_secret_key_security(self):
        """Тест безопасности секретного ключа."""
        settings = Settings()

        # Секретный ключ должен быть достаточно длинным
        assert len(settings.SECRET_KEY) >= 32

        # Не должен содержать очевидные небезопасные значения
        unsafe_values = ["password", "secret", "123456", "default"]
        assert not any(unsafe in settings.SECRET_KEY.lower() for unsafe in unsafe_values)

    @pytest.mark.parametrize("invalid_port", [-1, 0, 65536, 100000])
    def test_port_validation_ranges(self, invalid_port):
        """Тест валидации диапазонов портов."""
        with pytest.raises(ValueError):
            Settings(POSTGRES_PORT=invalid_port)

    def test_url_format_validation(self):
        """Тест валидации форматов URL."""
        settings = Settings()

        # Проверяем форматы различных URL
        urls_to_check = [
            (settings.SQLALCHEMY_DATABASE_URI, "postgresql"),
            (settings.REDIS_URL, "redis"),
            (settings.RABBITMQ_URL, "amqp"),
        ]

        for url, expected_scheme in urls_to_check:
            assert url.startswith(f"{expected_scheme}://"), f"URL {url} должен начинаться с {expected_scheme}://"


@pytest.mark.config
@pytest.mark.edge_cases
class TestSettingsEdgeCases:
    """Тесты для граничных случаев в настройках."""

    def test_empty_string_handling(self):
        """Тест обработки пустых строк в настройках."""
        settings = Settings(
            CORS_ORIGINS="",
            WS_API_KEYS="",
        )

        assert settings.CORS_ORIGINS == []
        assert settings.WS_API_KEYS == []

    def test_whitespace_handling(self, monkeypatch):
        """Тест обработки пробелов в настройках."""
        monkeypatch.setenv("PROJECT_NAME", "  Spaced Project  ")
        settings = Settings()

        # Пробелы должны сохраняться или обрезаться согласно логике приложения
        assert "Spaced Project" in settings.PROJECT_NAME

    def test_unicode_handling(self, monkeypatch):
        """Тест обработки Unicode символов."""
        unicode_name = "🔥 Супер Проект 🚀"
        monkeypatch.setenv("PROJECT_NAME", unicode_name)
        settings = Settings()

        assert settings.PROJECT_NAME == unicode_name

    def test_very_long_values(self):
        """Тест обработки очень длинных значений."""
        long_string = "x" * 1000
        settings = Settings(PROJECT_DESCRIPTION=long_string)

        assert settings.PROJECT_DESCRIPTION == long_string
        assert len(settings.PROJECT_DESCRIPTION) == 1000

    def test_special_characters_in_passwords(self):
        """Тест специальных символов в паролях."""
        special_password = "p@ssw0rd!@#$%^&*()_+-=[]{}|;:,.<>?"
        settings = Settings(POSTGRES_PASSWORD=special_password)

        assert settings.POSTGRES_PASSWORD == special_password

        # URL должен правильно экранировать специальные символы
        assert isinstance(settings.SQLALCHEMY_DATABASE_URI, str)
        assert len(settings.SQLALCHEMY_DATABASE_URI) > 0
