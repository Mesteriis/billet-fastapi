"""
Мокирование Telegram Bot API.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


class TelegramBotMocker:
    """Класс для мокирования Telegram бота."""

    def __init__(self):
        self.sent_messages = []
        self.bot_mock = None

    def add_sent_message(self, chat_id: int, text: str, **kwargs):
        """Добавляет отправленное сообщение в историю."""
        self.sent_messages.append({"chat_id": chat_id, "text": text, **kwargs})

    def get_sent_messages(self) -> list[dict[str, Any]]:
        """Возвращает все отправленные сообщения."""
        return self.sent_messages

    def clear_history(self):
        """Очищает историю сообщений."""
        self.sent_messages.clear()


@pytest.fixture
def telegram_bot_mocker():
    """Фикстура для мокирования Telegram бота."""
    return TelegramBotMocker()


@pytest.fixture
def mock_telegram_bot():
    """Мокирование aiogram Bot."""
    with patch("aiogram.Bot") as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot

        # Мокируем основные методы
        mock_bot.send_message = AsyncMock(
            return_value={
                "message_id": 123,
                "chat": {"id": 12345, "type": "private"},
                "date": 1640995200,
                "text": "Test message",
            }
        )

        mock_bot.send_photo = AsyncMock(
            return_value={
                "message_id": 124,
                "chat": {"id": 12345, "type": "private"},
                "date": 1640995201,
                "photo": [{"file_id": "photo123"}],
            }
        )

        mock_bot.send_document = AsyncMock(
            return_value={
                "message_id": 125,
                "chat": {"id": 12345, "type": "private"},
                "date": 1640995202,
                "document": {"file_id": "doc123"},
            }
        )

        mock_bot.edit_message_text = AsyncMock(
            return_value={
                "message_id": 123,
                "chat": {"id": 12345, "type": "private"},
                "date": 1640995200,
                "text": "Edited message",
            }
        )

        mock_bot.delete_message = AsyncMock(return_value=True)

        mock_bot.get_me = AsyncMock(
            return_value={"id": 123456789, "is_bot": True, "first_name": "Test Bot", "username": "test_bot"}
        )

        mock_bot.get_chat = AsyncMock(return_value={"id": 12345, "type": "private", "first_name": "Test User"})

        yield mock_bot


# Утилиты для создания Telegram объектов


def create_telegram_user(**kwargs) -> dict[str, Any]:
    """Создает тестовые данные пользователя Telegram."""
    defaults = {
        "id": 12345,
        "is_bot": False,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "language_code": "ru",
    }
    defaults.update(kwargs)
    return defaults


def create_telegram_chat(**kwargs) -> dict[str, Any]:
    """Создает тестовые данные чата Telegram."""
    defaults = {"id": 12345, "type": "private", "first_name": "Test User"}
    defaults.update(kwargs)
    return defaults


def create_telegram_message(**kwargs) -> dict[str, Any]:
    """Создает тестовые данные сообщения Telegram."""
    defaults = {
        "message_id": 123,
        "from": create_telegram_user(),
        "chat": create_telegram_chat(),
        "date": 1640995200,
        "text": "Test message",
    }
    defaults.update(kwargs)
    return defaults


def create_telegram_callback_query(**kwargs) -> dict[str, Any]:
    """Создает тестовые данные callback query."""
    defaults = {
        "id": "callback123",
        "from": create_telegram_user(),
        "message": create_telegram_message(),
        "data": "test_callback",
    }
    defaults.update(kwargs)
    return defaults


# Контекстный менеджер для мокирования


class MockedTelegramAPI:
    """Контекстный менеджер для мокирования Telegram API."""

    def __init__(self):
        self.sent_messages = []
        self.responses = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add_response(self, method: str, response: dict[str, Any]):
        """Добавляет ответ для метода API."""
        self.responses[method] = response

    def get_response(self, method: str) -> dict[str, Any]:
        """Получает ответ для метода API."""
        return self.responses.get(method, {})


# Примеры использования в тестах:
"""
@pytest.mark.mocked
async def test_telegram_bot_send_message(mock_telegram_bot):
    # Тест отправки сообщения
    result = await mock_telegram_bot.send_message(
        chat_id=12345,
        text="Hello, World!"
    )

    assert result["message_id"] == 123
    assert result["text"] == "Test message"

    # Проверяем что метод был вызван
    mock_telegram_bot.send_message.assert_called_once_with(
        chat_id=12345,
        text="Hello, World!"
    )


@pytest.mark.mocked
def test_telegram_message_processing():
    # Создаем тестовое сообщение
    message_data = create_telegram_message(
        text="/start",
        from=create_telegram_user(id=12345, username="testuser")
    )

    # Тестируем обработку сообщения
    # process_message(message_data)
    pass
"""
