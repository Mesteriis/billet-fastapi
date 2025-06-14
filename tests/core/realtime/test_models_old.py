"""
Тесты для моделей realtime системы.
"""

from enum import Enum

import pytest

from core.realtime.models import ConnectionStatus, MessageType, WSCommand, WSMessage, WSResponse


class TestConnectionStatus:
    """Тесты для ConnectionStatus enum."""

    def test_connection_status_values(self):
        """Тест значений статуса подключения."""
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.ERROR.value == "error"

    def test_connection_status_is_enum(self):
        """Тест что ConnectionStatus является Enum."""
        assert issubclass(ConnectionStatus, Enum)


class TestMessageType:
    """Тесты для MessageType enum."""

    def test_message_type_values(self):
        """Тест значений типов сообщений."""
        assert MessageType.TEXT.value == "text"
        assert MessageType.JSON.value == "json"
        assert MessageType.COMMAND.value == "command"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.ERROR.value == "error"


class TestWSCommand:
    """Тесты для WSCommand модели."""

    def test_ws_command_creation(self):
        """Тест создания WebSocket команды."""
        command = WSCommand(action="test_action", data={"key": "value"}, channel="test_channel")

        assert command.action == "test_action"
        assert command.data == {"key": "value"}
        assert command.channel == "test_channel"

    def test_ws_command_optional_fields(self):
        """Тест создания команды только с обязательными полями."""
        command = WSCommand(action="test_action")

        assert command.action == "test_action"
        assert command.data is None
        assert command.channel is None


class TestWSMessage:
    """Тесты для WSMessage модели."""

    def test_ws_message_creation(self):
        """Тест создания WebSocket сообщения."""
        message = WSMessage(type=MessageType.MESSAGE, data="test message", channel="test_channel")

        assert message.type == MessageType.MESSAGE
        assert message.data == "test message"
        assert message.channel == "test_channel"
        assert message.timestamp is not None

    def test_ws_message_auto_timestamp(self):
        """Тест автоматического создания timestamp."""
        import time

        before = time.time()

        message = WSMessage(type=MessageType.MESSAGE, data="test")

        after = time.time()
        assert before <= message.timestamp.timestamp() <= after


class TestWSResponse:
    """Тесты для WSResponse модели."""

    def test_ws_response_creation(self):
        """Тест создания WebSocket ответа."""
        response = WSResponse(success=True, message="Operation successful", data={"result": "ok"})

        assert response.success is True
        assert response.message == "Operation successful"
        assert response.data == {"result": "ok"}

    def test_ws_response_error(self):
        """Тест создания ответа с ошибкой."""
        response = WSResponse(success=False, message="Operation failed", error="Something went wrong")

        assert response.success is False
        assert response.message == "Operation failed"
        assert response.error == "Something went wrong"
        assert response.data is None

    def test_ws_response_optional_fields(self):
        """Тест создания ответа только с обязательными полями."""
        response = WSResponse(success=True)

        assert response.success is True
        assert response.message is None
        assert response.data is None
        assert response.error is None
