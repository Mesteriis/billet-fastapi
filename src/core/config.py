"""Application Settings and Configuration.

This module provides comprehensive application configuration using Pydantic Settings.
Handles environment variables, validation, and default values for all application components.

Features:
    - Environment-based configuration
    - Automatic URL generation for databases
    - Type validation and conversion
    - Support for multiple services (PostgreSQL, Redis, RabbitMQ)
    - Security and authentication settings
    - Real-time features configuration

Example:
    Basic usage::

        from core.config import get_settings

        settings = get_settings()
        print(f"Database URL: {settings.SQLALCHEMY_DATABASE_URI}")
        print(f"Redis URL: {settings.REDIS_URL}")

    Environment configuration::

        # .env file
        POSTGRES_SERVER=localhost
        POSTGRES_DB=mydb
        SECRET_KEY=my-secret-key

        # Usage
        settings = get_settings()
        # URLs are automatically generated

    Custom timezone::

        settings = Settings(TZ="UTC")
        # or
        settings = Settings(TZ=pytz.timezone("Europe/London"))

Note:
    Settings are cached using @lru_cache for performance.
    Environment variables take precedence over default values.
"""

from __future__ import annotations

from datetime import tzinfo
from functools import lru_cache
from typing import Any, Self

import pytz
from pydantic import field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from constants import ENV_FILE
from core.exceptions import CoreConfigValueError
from tools.pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings configuration.

    Comprehensive configuration class for all application parameters including:
    - Core project settings
    - Database configurations (PostgreSQL, Redis, RabbitMQ)
    - Security and authentication settings
    - Real-time features (WebSocket, SSE, WebRTC)
    - TaskIQ and background tasks
    - Telegram bots integration
    - Logging and monitoring settings

    Attributes:
        PROJECT_NAME (str): Application name
        PROJECT_DESCRIPTION (str): Application description
        VERSION (str): Application version
        API_V1_STR (str): API v1 prefix path
        TZ (tzinfo): Application timezone

    Example:
        Basic initialization::

            settings = Settings()
            print(settings.PROJECT_NAME)  # "Mango Message"

        With environment variables::

            # Set in environment or .env file
            PROJECT_NAME="My App"
            POSTGRES_DB="myapp_db"

            settings = Settings()
            print(settings.PROJECT_NAME)  # "My App"

        Database URL auto-generation::

            settings = Settings(
                POSTGRES_SERVER="localhost",
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="mydb"
            )
            print(settings.SQLALCHEMY_DATABASE_URI)
            # "postgresql+asyncpg://user:pass@localhost/mydb"
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=True, extra="ignore", validate_default=True)

    PROJECT_NAME: str = "Mango Message"
    PROJECT_DESCRIPTION: str = "API for messaging system"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    TZ: Any = pytz.timezone("Europe/Moscow")

    @field_validator("TZ", mode="before")
    @classmethod
    def validate_timezone(cls, v: str | tzinfo) -> tzinfo:
        """Validate timezone correctness.

        Args:
            v (str | tzinfo): Timezone string or tzinfo object

        Returns:
            tzinfo: Validated timezone object

        Raises:
            ValueError: If timezone is invalid

        Example:
            String timezone::

                tz = validate_timezone("UTC")
                tz = validate_timezone("Europe/London")

            Timezone object::

                import pytz
                tz = validate_timezone(pytz.UTC)
        """
        if isinstance(v, str):
            return pytz.timezone(v)
        elif isinstance(v, pytz.BaseTzInfo):
            return v
        raise CoreConfigValueError(config_key="TZ", value=v, reason="Must be a valid timezone string or tzinfo object")

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
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Assemble CORS origins list.

        Args:
            v (str | list[str]): Comma-separated string or list of origins

        Returns:
            list[str]: List of CORS origins

        Example:
            String input::

                origins = assemble_cors_origins("http://localhost:3000,https://example.com")
                # ["http://localhost:3000", "https://example.com"]

            List input::

                origins = assemble_cors_origins(["http://localhost:3000"])
                # ["http://localhost:3000"]
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise CoreConfigValueError(
            config_key="CORS_ORIGINS", value=v, reason="Must be a comma-separated string or list of URLs"
        )

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

    # Telegram Bots settings (can be overridden in TelegramBotsConfig)
    TELEGRAM_BOTS_ENABLED: bool = False
    TELEGRAM_DEBUG: bool = False

    # WebSocket and SSE settings
    WEBSOCKET_ENABLED: bool = True
    SSE_ENABLED: bool = True
    WEBSOCKET_AUTH_REQUIRED: bool = False
    SSE_AUTH_REQUIRED: bool = False

    # WebSocket settings
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # seconds
    WEBSOCKET_MAX_CONNECTIONS: int = 1000
    WEBSOCKET_MESSAGE_QUEUE_SIZE: int = 100
    WEBSOCKET_DISCONNECT_TIMEOUT: int = 60

    # SSE settings
    SSE_HEARTBEAT_INTERVAL: int = 30  # seconds
    SSE_MAX_CONNECTIONS: int = 500
    SSE_RETRY_TIMEOUT: int = 3000  # milliseconds
    SSE_MAX_MESSAGE_SIZE: int = 1024 * 1024  # 1MB

    # WebSocket/SSE authentication settings
    WS_JWT_SECRET_KEY: str = "websocket-secret-key"
    WS_JWT_ALGORITHM: str = "HS256"
    WS_JWT_EXPIRE_MINUTES: int = 60
    WS_API_KEY_HEADER: str = "X-API-Key"
    WS_API_KEYS: list[str] = []  # List of allowed API keys

    WEBRTC_ENABLED: bool = False

    @field_validator("WS_API_KEYS", mode="before")
    @classmethod
    def assemble_api_keys(cls, v: str | list[str]) -> list[str]:
        """Assemble API keys list.

        Args:
            v (str | list[str]): Comma-separated string or list of API keys

        Returns:
            list[str]: List of API keys

        Example:
            String input::

                keys = assemble_api_keys("key1,key2,key3")
                # ["key1", "key2", "key3"]

            List input (no change)::

                keys = assemble_api_keys(["key1", "key2"])
                # ["key1", "key2"]
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    @model_validator(mode="after")
    def set_urls(self) -> Self:
        """Automatically configure connection URLs.

        Generates database URLs based on individual connection parameters.
        Called automatically after model initialization.

        Returns:
            Settings: Self instance with configured URLs

        Example:
            Automatic URL generation::

                settings = Settings(
                    POSTGRES_SERVER="db.example.com",
                    POSTGRES_USER="myuser",
                    POSTGRES_PASSWORD="mypass",
                    POSTGRES_DB="mydb"
                )
                # settings.SQLALCHEMY_DATABASE_URI will be:
                # "postgresql+asyncpg://myuser:mypass@db.example.com/mydb"
        """
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
            # Use Redis as broker for TaskIQ (separate database)
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.TASKIQ_BROKER_URL = f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        if not self.TASKIQ_RESULT_BACKEND_URL:
            # Use Redis as results backend (separate database)
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.TASKIQ_RESULT_BACKEND_URL = f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/2"
        return self


@lru_cache
def get_settings() -> Settings:
    """Get application settings instance.

    Returns cached settings instance for performance.

    Returns:
        Settings: Configured settings instance

    Example:
        Basic usage::

            from core.config import get_settings

            settings = get_settings()
            print(settings.PROJECT_NAME)

        Using in dependencies::

            from fastapi import Depends
            from core.config import get_settings, Settings

            async def my_endpoint(settings: Settings = Depends(get_settings)):
                return {"project": settings.PROJECT_NAME}

    Note:
        Settings are cached using @lru_cache for performance.
        The same instance is returned on subsequent calls.
    """
    return Settings()
