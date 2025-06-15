"""
Тесты для конфигурации Telegram ботов.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.telegram.config import BotMode, TelegramBotConfig, TelegramBotsConfig


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

    def test_bot_config_webhook_settings(self):
        """Тест настроек вебхука."""
        config = TelegramBotConfig(
            token="test_token",
            name="test_bot",
            mode=BotMode.WEBHOOK,
            webhook_url="https://example.com/webhook",
            webhook_path="/webhook/bot",
            webhook_secret="secret123",
        )

        assert config.webhook_url == "https://example.com/webhook"
        assert config.webhook_path == "/webhook/bot"
        assert config.webhook_secret == "secret123"

    def test_webhook_path_validation(self):
        """Тест валидации пути вебхука."""
        config = TelegramBotConfig(
            token="test_token",
            name="test_bot",
            webhook_path="webhook/bot",  # без слеша в начале
        )

        # Путь должен автоматически добавить слеш
        assert config.webhook_path == "/webhook/bot"

    def test_webhook_url_validation_invalid(self):
        """Тест валидации некорректного URL вебхука."""
        with pytest.raises(ValueError, match="Webhook URL должен начинаться с http:// или https://"):
            TelegramBotConfig(token="test_token", name="test_bot", webhook_url="invalid-url")

    def test_webhook_url_validation_valid(self):
        """Тест валидации корректного URL вебхука."""
        config = TelegramBotConfig(token="test_token", name="test_bot", webhook_url="https://example.com")
        assert config.webhook_url == "https://example.com"


class TestTelegramBotsConfig:
    """Тесты для конфигурации всех ботов."""

    def test_empty_bots_config(self):
        """Тест создания пустой конфигурации."""
        config = TelegramBotsConfig()

        assert len(config.bots) == 0
        assert config.TELEGRAM_BOTS_ENABLED is False

    def test_bots_config_with_dict(self):
        """Тест конфигурации с словарем ботов."""
        bot_config = TelegramBotConfig(token="test_token", name="test_bot")

        config = TelegramBotsConfig(bots={"test_bot": bot_config})

        assert len(config.bots) == 1
        assert "test_bot" in config.bots
        assert config.bots["test_bot"].name == "test_bot"

    def test_get_bot_config(self):
        """Тест получения конфигурации бота по имени."""
        bot_config = TelegramBotConfig(token="test_token", name="test_bot")
        config = TelegramBotsConfig(bots={"test_bot": bot_config})

        found_bot = config.get_bot_config("test_bot")
        assert found_bot is not None
        assert found_bot.name == "test_bot"
        assert found_bot.token == "test_token"

    def test_get_bot_config_not_found(self):
        """Тест получения несуществующего бота."""
        config = TelegramBotsConfig()

        found_bot = config.get_bot_config("nonexistent")
        assert found_bot is None

    def test_get_enabled_bots_disabled(self):
        """Тест получения включенных ботов когда они отключены."""
        bot_config = TelegramBotConfig(token="test_token", name="test_bot")
        config = TelegramBotsConfig(bots={"test_bot": bot_config}, TELEGRAM_BOTS_ENABLED=False)

        enabled_bots = config.get_enabled_bots()
        assert len(enabled_bots) == 0

    def test_get_enabled_bots_enabled(self):
        """Тест получения включенных ботов когда они включены."""
        bot_config = TelegramBotConfig(token="test_token", name="test_bot")
        config = TelegramBotsConfig(bots={"test_bot": bot_config}, TELEGRAM_BOTS_ENABLED=True)

        enabled_bots = config.get_enabled_bots()
        assert len(enabled_bots) == 1
        assert "test_bot" in enabled_bots

    def test_is_user_allowed_no_restrictions(self):
        """Тест проверки пользователя без ограничений."""
        config = TelegramBotsConfig()

        assert config.is_user_allowed(12345) is True

    def test_is_user_allowed_with_restrictions(self):
        """Тест проверки пользователя с ограничениями."""
        config = TelegramBotsConfig(TELEGRAM_ALLOWED_USERS=[12345, 67890])

        assert config.is_user_allowed(12345) is True
        assert config.is_user_allowed(99999) is False

    def test_is_admin(self):
        """Тест проверки администратора."""
        config = TelegramBotsConfig(TELEGRAM_ADMIN_USERS=[12345])

        assert config.is_admin(12345) is True
        assert config.is_admin(67890) is False

    @patch.dict(
        "os.environ",
        {
            "TELEGRAM_BOT_TESTBOT_TOKEN": "test_token_123",
            "TELEGRAM_BOT_TESTBOT_MODE": "webhook",
            "TELEGRAM_BOT_TESTBOT_WEBHOOK_URL": "https://example.com",
        },
    )
    def test_parse_bots_from_env(self):
        """Тест парсинга ботов из переменных окружения."""
        config = TelegramBotsConfig()

        # Проверяем что бот был создан из переменных окружения
        assert "testbot" in config.bots
        bot = config.bots["testbot"]
        assert bot.token == "test_token_123"
        assert bot.mode == BotMode.WEBHOOK
        assert bot.webhook_url == "https://example.com"
