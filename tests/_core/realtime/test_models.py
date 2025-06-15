"""
Тесты для моделей realtime системы.
"""

from enum import Enum

import pytest

from core.realtime.models import ConnectionStatus, MessageType, WSCommand, WSMessage, WSResponse


@pytest.mark.unit
@pytest.mark.realtime
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


@pytest.mark.unit
@pytest.mark.realtime
class TestMessageType:
    """Тесты для MessageType enum."""

    def test_message_type_values(self):
        """Тест значений типов сообщений."""
        assert MessageType.TEXT.value == "text"
        assert MessageType.BINARY.value == "binary"
        assert MessageType.JSON.value == "json"
        assert MessageType.COMMAND.value == "command"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.ERROR.value == "error"
        assert MessageType.HEARTBEAT.value == "heartbeat"

    def test_message_type_is_enum(self):
        """Тест что MessageType является Enum."""
        assert issubclass(MessageType, Enum)


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

    def test_ws_command_binary_data(self):
        """Тест работы с бинарными данными в команде."""
        command = WSCommand(action="upload")
        test_data = b"test binary data"

        command.set_binary_data(test_data)

        assert command.binary_data is not None
        retrieved_data = command.get_binary_data()
        assert retrieved_data == test_data


class TestWSMessage:
    """Тесты для WSMessage модели."""

    def test_ws_message_creation(self):
        """Тест создания WebSocket сообщения."""
        message = WSMessage(type=MessageType.TEXT, data="test message", channel="test_channel")

        assert message.type == MessageType.TEXT
        assert message.data == "test message"
        assert message.channel == "test_channel"
        assert message.timestamp is not None
        assert message.id is not None

    def test_ws_message_auto_timestamp(self):
        """Тест автоматического создания timestamp."""
        import time

        before = time.time()

        message = WSMessage(type=MessageType.TEXT, data="test")

        after = time.time()
        assert before <= message.timestamp.timestamp() <= after

    def test_ws_message_json_data(self):
        """Тест создания сообщения с JSON данными."""
        json_data = {"key": "value", "number": 42}
        message = WSMessage(type=MessageType.JSON, data=json_data)

        assert message.type == MessageType.JSON
        assert message.data == json_data

    def test_ws_message_binary_data(self):
        """Тест работы с бинарными данными."""
        message = WSMessage(type=MessageType.BINARY)
        test_data = b"test binary content"

        message.set_binary_data(test_data)

        assert message.type == MessageType.BINARY
        assert message.binary_data is not None
        retrieved_data = message.get_binary_data()
        assert retrieved_data == test_data


class TestWSResponse:
    """Тесты для WSResponse модели."""

    def test_ws_response_success(self):
        """Тест создания успешного WebSocket ответа."""
        response = WSResponse(success=True, message="Operation successful", data={"result": "ok"})

        assert response.success is True
        assert response.message == "Operation successful"
        assert response.data == {"result": "ok"}
        assert response.timestamp is not None

    def test_ws_response_error(self):
        """Тест создания ответа с ошибкой."""
        response = WSResponse(success=False, message="Operation failed", error_code="INVALID_DATA")

        assert response.success is False
        assert response.message == "Operation failed"
        assert response.error_code == "INVALID_DATA"
        assert response.data is None

    def test_ws_response_minimal(self):
        """Тест создания ответа только с обязательными полями."""
        response = WSResponse(success=True)

        assert response.success is True
        assert response.message is None
        assert response.data is None
        assert response.error_code is None
        assert response.timestamp is not None

    def test_ws_response_error_with_data(self):
        """Тест создания ответа с ошибкой и дополнительными данными."""
        error_data = {"field": "email", "code": "INVALID_FORMAT"}
        response = WSResponse(
            success=False, message="Validation failed", error_code="VALIDATION_ERROR", data=error_data
        )

        assert response.success is False
        assert response.message == "Validation failed"
        assert response.error_code == "VALIDATION_ERROR"
        assert response.data == error_data
