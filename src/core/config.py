"""Настройки приложения."""

from __future__ import annotations

from datetime import tzinfo
from functools import lru_cache
from typing import Any

import pytz
from pydantic import field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from constants import ENV_FILE
from tools.pydantic import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения.

    Класс для конфигурации всех параметров приложения включая:
    - Основные настройки проекта
    - Настройки базы данных (PostgreSQL, Redis, RabbitMQ)
    - Настройки безопасности и авторизации
    - Настройки WebSocket, SSE и WebRTC
    - Настройки TaskIQ
    - Настройки телеграм ботов
    - Настройки логирования и мониторинга
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=True, extra="ignore", validate_default=True)

    PROJECT_NAME: str = "Mango Message"
    PROJECT_DESCRIPTION: str = "API for messaging system"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    TZ: Any = pytz.timezone("Europe/Moscow")

    @field_validator("TZ", mode="before")
    def validate_timezone(cls, v: str | tzinfo) -> tzinfo:  # noqa
        """Валидация корректности временной зоны."""
        if isinstance(v, str):
            return pytz.timezone(v)
        elif isinstance(v, pytz.BaseTzInfo):
            return v
        raise ValueError(f"Invalid timezone: {v}")

    # Database settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "mango_msg"
    SQLALCHEMY_DATABASE_URI: str = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_URL: str | None = None

    # RabbitMQ settings
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_URL: str | None = None

    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    CORS_ORIGINS: list[str] = ["http://localhost:8000", "https://api.sh-inc.ru"]
    CORS_MAX_AGE: int = 600

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:  # noqa
        """Сборка списка разрешенных CORS origins."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "Lax"
    COOKIE_MAX_AGE: int = 3600

    CACHE_TTL: int = 300  # 5 minutes
    CACHE_PREFIX: str = "mango_msg:"

    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "app.log"
    LOG_MAX_BYTES: int = 10485760  # 10 MB
    LOG_BACKUP_COUNT: int = 5

    ENABLE_ALERTS: bool = False
    ALERT_EMAIL: str | None = None
    ALERT_SLACK_WEBHOOK: str | None = None

    ENABLE_BACKGROUND_TASKS: bool = True
    MAX_BACKGROUND_WORKERS: int = 4

    # TaskIQ settings
    TASKIQ_BROKER_URL: str | None = None
    TASKIQ_RESULT_BACKEND_URL: str | None = None
    TASKIQ_MAX_RETRIES: int = 3
    TASKIQ_RETRY_DELAY: int = 5
    TASKIQ_TASK_TIMEOUT: int = 300

    TRACING_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "localhost:4317"
    OTEL_EXPORTER_OTLP_INSECURE: bool = True

    # Telegram Bots settings (можно переопределить в TelegramBotsConfig)
    TELEGRAM_BOTS_ENABLED: bool = False
    TELEGRAM_DEBUG: bool = False

    # WebSocket и SSE настройки
    WEBSOCKET_ENABLED: bool = True
    SSE_ENABLED: bool = True
    WEBSOCKET_AUTH_REQUIRED: bool = False
    SSE_AUTH_REQUIRED: bool = False

    # Настройки WebSocket
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # секунды
    WEBSOCKET_MAX_CONNECTIONS: int = 1000
    WEBSOCKET_MESSAGE_QUEUE_SIZE: int = 100
    WEBSOCKET_DISCONNECT_TIMEOUT: int = 60

    # Настройки SSE
    SSE_HEARTBEAT_INTERVAL: int = 30  # секунды
    SSE_MAX_CONNECTIONS: int = 500
    SSE_RETRY_TIMEOUT: int = 3000  # миллисекунды
    SSE_MAX_MESSAGE_SIZE: int = 1024 * 1024  # 1MB

    # Настройки авторизации для WebSocket/SSE
    WS_JWT_SECRET_KEY: str = "websocket-secret-key"
    WS_JWT_ALGORITHM: str = "HS256"
    WS_JWT_EXPIRE_MINUTES: int = 60
    WS_API_KEY_HEADER: str = "X-API-Key"
    WS_API_KEYS: list[str] = []  # Список разрешенных API ключей

    @field_validator("WS_API_KEYS", mode="before")
    def assemble_api_keys(cls, v: str | list[str]) -> list[str]:  # noqa
        """Сборка списка разрешенных API ключей."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    @model_validator(mode="after")
    def set_urls(self) -> Settings:
        """Автоматическая настройка URL подключений."""
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )
        if not self.REDIS_URL:
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.REDIS_URL = f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        if not self.RABBITMQ_URL:
            self.RABBITMQ_URL = (
                f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
                f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
            )
        if not self.TASKIQ_BROKER_URL:
            # Используем Redis как брокер для TaskIQ (отдельная база данных)
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.TASKIQ_BROKER_URL = f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        if not self.TASKIQ_RESULT_BACKEND_URL:
            # Используем Redis как бэкенд для результатов (отдельная база данных)
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.TASKIQ_RESULT_BACKEND_URL = f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/2"
        return self


@lru_cache
def get_settings() -> Settings:
    """Получить настройки приложения."""
    return Settings()
