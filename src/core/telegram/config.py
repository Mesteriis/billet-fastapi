"""Конфигурация для Telegram ботов."""

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from core.exceptions.core_base import CoreTelegramValueError
from tools.pydantic import BaseModel, BaseSettings


class BotMode(str, Enum):
    """Режимы работы бота."""

    POLLING = "polling"
    WEBHOOK = "webhook"


class TelegramBotConfig(BaseModel):
    """Конфигурация одного Telegram бота."""

    name: str = Field(..., description="Имя бота для идентификации")
    token: str = Field(..., description="API токен бота")
    mode: BotMode = Field(default=BotMode.POLLING, description="Режим работы бота")

    # Webhook настройки
    webhook_url: str | None = Field(default=None, description="URL для webhook")
    webhook_path: str | None = Field(default=None, description="Путь для webhook endpoint")
    webhook_secret: str | None = Field(default=None, description="Секрет для webhook")

    # Polling настройки
    polling_timeout: int = Field(default=20, description="Таймаут для polling")
    polling_limit: int = Field(default=100, description="Лимит сообщений за раз")
    polling_allowed_updates: list[str] | None = Field(default=None, description="Разрешенные типы обновлений")

    # Общие настройки
    parse_mode: str | None = Field(default="HTML", description="Режим парсинга по умолчанию")
    drop_pending_updates: bool = Field(default=True, description="Пропускать накопившиеся обновления при старте")

    # Лимиты и таймауты
    request_timeout: int = Field(default=30, description="Таймаут запросов к API")
    max_retries: int = Field(default=3, description="Максимальное количество повторов")
    retry_delay: float = Field(default=1.0, description="Задержка между повторами")

    # Дополнительные настройки
    commands_scope: str = Field(default="default", description="Область действия команд")
    middleware_enabled: bool = Field(default=True, description="Включить middleware")
    fsm_enabled: bool = Field(default=True, description="Включить FSM для диалогов")

    @field_validator("webhook_path")
    def validate_webhook_path(cls, v: str | None, info) -> str | None:
        """Валидация пути webhook."""
        if v and not v.startswith("/"):
            return f"/{v}"
        return v

    @field_validator("webhook_url")
    def validate_webhook_url(cls, v: str | None, info) -> str | None:
        """Валидация URL webhook."""
        if v and not v.startswith(("http://", "https://")):
            raise CoreTelegramValueError("webhook_validation", "webhook_url", v)
        return v


class TelegramBotsConfig(BaseSettings):
    """Конфигурация всех Telegram ботов."""

    # Общие настройки
    TELEGRAM_BOTS_ENABLED: bool = Field(default=False, description="Включить Telegram ботов")
    TELEGRAM_DEBUG: bool = Field(default=False, description="Отладочный режим")
    TELEGRAM_LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")

    # Настройки шаблонов
    TELEGRAM_TEMPLATES_DIR: str = Field(default="telegram/templates", description="Директория с шаблонами сообщений")
    TELEGRAM_TEMPLATES_AUTO_RELOAD: bool = Field(
        default=False, description="Автоперезагрузка шаблонов в режиме разработки"
    )

    # Настройки middleware
    TELEGRAM_RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Лимит сообщений от пользователя в минуту")
    TELEGRAM_RATE_LIMIT_PER_HOUR: int = Field(default=500, description="Лимит сообщений от пользователя в час")

    # Настройки Redis для FSM и кеширования
    TELEGRAM_REDIS_HOST: str | None = Field(default=None, description="Redis хост для FSM")
    TELEGRAM_REDIS_PORT: int = Field(default=6379, description="Redis порт")
    TELEGRAM_REDIS_DB: int = Field(default=3, description="Redis база данных для ботов")
    TELEGRAM_REDIS_PASSWORD: str | None = Field(default=None, description="Redis пароль")

    # Настройки безопасности
    TELEGRAM_ALLOWED_USERS: list[int] | None = Field(default=None, description="Список разрешенных пользователей (ID)")
    TELEGRAM_ALLOWED_CHATS: list[int] | None = Field(default=None, description="Список разрешенных чатов (ID)")
    TELEGRAM_ADMIN_USERS: list[int] | None = Field(default=None, description="Список администраторов (ID)")

    # Настройки веб-сервера для webhook
    TELEGRAM_WEBHOOK_HOST: str = Field(default="0.0.0.0", description="Хост для webhook")
    TELEGRAM_WEBHOOK_PORT: int = Field(default=8443, description="Порт для webhook")
    TELEGRAM_WEBHOOK_BASE_URL: str | None = Field(default=None, description="Базовый URL для webhook")

    # Конфигурации ботов
    bots: dict[str, TelegramBotConfig] = Field(default_factory=dict, description="Конфигурации ботов")

    @field_validator("bots", mode="before")
    def parse_bots_config(cls, v: Any) -> dict[str, TelegramBotConfig]:
        """Парсинг конфигурации ботов из переменных окружения."""
        if isinstance(v, dict):
            # Если уже словарь конфигураций
            return {
                name: TelegramBotConfig(**config) if isinstance(config, dict) else config for name, config in v.items()
            }

        # Парсинг из переменных окружения
        # Формат: TELEGRAM_BOT_<NAME>_TOKEN, TELEGRAM_BOT_<NAME>_MODE и т.д.
        import os

        bots_config = {}

        # Находим все токены ботов
        bot_tokens = {}
        for key, value in os.environ.items():
            if key.startswith("TELEGRAM_BOT_") and key.endswith("_TOKEN"):
                bot_name = key.replace("TELEGRAM_BOT_", "").replace("_TOKEN", "").lower()
                bot_tokens[bot_name] = value

        # Создаем конфигурации для каждого бота
        for bot_name, token in bot_tokens.items():
            bot_config = {"name": bot_name, "token": token}

            # Ищем дополнительные настройки для этого бота
            prefix = f"TELEGRAM_BOT_{bot_name.upper()}_"
            for key, value in os.environ.items():
                if key.startswith(prefix) and not key.endswith("_TOKEN"):
                    setting_name = key.replace(prefix, "").lower()
                    bot_config[setting_name] = value

            bots_config[bot_name] = TelegramBotConfig(**bot_config)

        return bots_config

    def get_bot_config(self, bot_name: str) -> TelegramBotConfig | None:
        """Получить конфигурацию конкретного бота."""
        return self.bots.get(bot_name)

    def get_enabled_bots(self) -> dict[str, TelegramBotConfig]:
        """Получить все включенные боты."""
        if not self.TELEGRAM_BOTS_ENABLED:
            return {}
        return self.bots

    def is_user_allowed(self, user_id: int) -> bool:
        """Проверить, разрешен ли пользователь."""
        if self.TELEGRAM_ALLOWED_USERS is None:
            return True
        return user_id in self.TELEGRAM_ALLOWED_USERS

    def is_chat_allowed(self, chat_id: int) -> bool:
        """Проверить, разрешен ли чат."""
        if self.TELEGRAM_ALLOWED_CHATS is None:
            return True
        return chat_id in self.TELEGRAM_ALLOWED_CHATS

    def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором."""
        if self.TELEGRAM_ADMIN_USERS is None:
            return False
        return user_id in self.TELEGRAM_ADMIN_USERS
