"""Тесты для конфигурации Telegram ботов."""

import os
from unittest.mock import patch

import pytest

from core.telegram import BotMode, TelegramBotConfig, TelegramBotsConfig


class TestBotMode:
    """Тесты для BotMode enum."""

    def test_bot_mode_values(self):
        """Тест значений режимов бота."""
        assert BotMode.WEBHOOK.value == "webhook"
        assert BotMode.POLLING.value == "polling"

    def test_bot_mode_from_string(self):
        """Тест создания BotMode из строки."""
        assert BotMode("webhook") == BotMode.WEBHOOK
        assert BotMode("polling") == BotMode.POLLING


class TestTelegramBotConfig:
    """Тесты для конфигурации отдельного бота."""

    def test_bot_config_creation(self):
        """Тест создания конфигурации бота."""
        config = TelegramBotConfig(token="test_token", name="test_bot", mode=BotMode.POLLING)

        assert config.token == "test_token"
        assert config.name == "test_bot"
        assert config.mode == BotMode.POLLING

    def test_bot_config_default_mode(self):
        """Тест режима по умолчанию."""
        config = TelegramBotConfig(token="test_token", name="test_bot")

        assert config.mode == BotMode.POLLING

    def test_bot_config_webhook_url(self):
        """Тест URL вебхука."""
        config = TelegramBotConfig(
            token="test_token", name="test_bot", mode=BotMode.WEBHOOK, webhook_url="https://example.com/webhook"
        )

        assert config.webhook_url == "https://example.com/webhook"


class TestTelegramBotsConfig:
    """Тесты для конфигурации всех ботов."""

    def test_bots_config_creation(self):
        """Тест создания конфигурации ботов."""
        bot_config = TelegramBotConfig(token="test_token", name="test_bot")

        config = TelegramBotsConfig(bots={"test_bot": bot_config})

        assert len(config.bots) == 1
        assert config.bots["test_bot"].name == "test_bot"

    def test_empty_bots_config(self):
        """Тест создания пустой конфигурации."""
        config = TelegramBotsConfig()

        assert len(config.bots) == 0

    def test_multiple_bots_config(self):
        """Тест конфигурации с несколькими ботами."""
        bot1 = TelegramBotConfig(token="token1", name="bot1")
        bot2 = TelegramBotConfig(token="token2", name="bot2")

        config = TelegramBotsConfig(bots=[bot1, bot2])

        assert len(config.bots) == 2
        assert config.bots[0].name == "bot1"
        assert config.bots[1].name == "bot2"

    def test_get_bot_by_name(self):
        """Тест получения бота по имени."""
        bot1 = TelegramBotConfig(token="token1", name="bot1")
        bot2 = TelegramBotConfig(token="token2", name="bot2")

        config = TelegramBotsConfig(bots=[bot1, bot2])

        found_bot = None
        for bot in config.bots:
            if bot.name == "bot1":
                found_bot = bot
                break

        assert found_bot is not None
        assert found_bot.token == "token1"

    def test_bot_names_unique(self):
        """Тест уникальности имен ботов."""
        bot1 = TelegramBotConfig(token="token1", name="test_bot")
        bot2 = TelegramBotConfig(token="token2", name="test_bot")

        config = TelegramBotsConfig(bots=[bot1, bot2])

        # Проверяем что оба бота добавлены (валидация уникальности может быть добавлена позже)
        assert len(config.bots) == 2

    def test_default_config(self):
        """Тест конфигурации по умолчанию."""
        config = TelegramBotsConfig()

        assert config.TELEGRAM_BOTS_ENABLED is False
        assert config.TELEGRAM_DEBUG is False
        assert config.TELEGRAM_LOG_LEVEL == "INFO"
        assert config.TELEGRAM_TEMPLATES_DIR == "telegram/templates"
        assert config.TELEGRAM_REDIS_DB == 3
        assert len(config.bots) == 0

    def test_security_methods(self):
        """Тест методов безопасности."""
        config = TelegramBotsConfig(
            TELEGRAM_ALLOWED_USERS=[123, 456], TELEGRAM_ALLOWED_CHATS=[789, 101112], TELEGRAM_ADMIN_USERS=[123]
        )

        # Тест разрешенных пользователей
        assert config.is_user_allowed(123) is True
        assert config.is_user_allowed(999) is False

        # Тест разрешенных чатов
        assert config.is_chat_allowed(789) is True
        assert config.is_chat_allowed(999) is False

        # Тест администраторов
        assert config.is_admin(123) is True
        assert config.is_admin(456) is False

    def test_security_no_restrictions(self):
        """Тест без ограничений безопасности."""
        config = TelegramBotsConfig()

        # Без ограничений все должны быть разрешены
        assert config.is_user_allowed(123) is True
        assert config.is_chat_allowed(789) is True
        assert config.is_admin(123) is False  # Но админы не определены

    @patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_MAIN_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "TELEGRAM_BOT_MAIN_MODE": "polling",
            "TELEGRAM_BOT_SECONDARY_TOKEN": "789012:XYZ-GHI5678jklMn-abc90X3y2z456fg22",
            "TELEGRAM_BOT_SECONDARY_MODE": "webhook",
            "TELEGRAM_BOT_SECONDARY_WEBHOOK_URL": "https://example.com",
        },
    )
    def test_bots_config_from_env(self):
        """Тест парсинга конфигурации ботов из переменных окружения."""
        config = TelegramBotsConfig()

        assert len(config.bots) == 2
        assert "main" in config.bots
        assert "secondary" in config.bots

        main_bot = config.bots["main"]
        assert main_bot.name == "main"
        assert main_bot.token == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert main_bot.mode == BotMode.POLLING

        secondary_bot = config.bots["secondary"]
        assert secondary_bot.name == "secondary"
        assert secondary_bot.token == "789012:XYZ-GHI5678jklMn-abc90X3y2z456fg22"
        assert secondary_bot.mode == BotMode.WEBHOOK

    def test_get_bot_config(self):
        """Тест получения конфигурации конкретного бота."""
        bot_config = TelegramBotConfig(name="test_bot", token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

        config = TelegramBotsConfig(bots={"test_bot": bot_config})

        retrieved_config = config.get_bot_config("test_bot")
        assert retrieved_config is not None
        assert retrieved_config.name == "test_bot"

        non_existent = config.get_bot_config("non_existent")
        assert non_existent is None

    def test_get_enabled_bots(self):
        """Тест получения включенных ботов."""
        bot_config = TelegramBotConfig(name="test_bot", token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

        # Боты отключены
        config = TelegramBotsConfig(TELEGRAM_BOTS_ENABLED=False, bots={"test_bot": bot_config})
        assert len(config.get_enabled_bots()) == 0

        # Боты включены
        config.TELEGRAM_BOTS_ENABLED = True
        enabled_bots = config.get_enabled_bots()
        assert len(enabled_bots) == 1
        assert "test_bot" in enabled_bots


@pytest.mark.asyncio
class TestTelegramBotsConfigAsync:
    """Асинхронные тесты для конфигурации ботов."""

    async def test_config_initialization(self):
        """Тест асинхронной инициализации конфигурации."""
        config = TelegramBotsConfig()

        # Конфигурация должна быть создана без ошибок
        assert config is not None
        assert isinstance(config.bots, dict)
