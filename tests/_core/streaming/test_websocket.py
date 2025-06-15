"""Тесты для WebSocket клиента и соединений."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.streaming import WSClient, create_ws_client
from core.streaming import SSEConnectionStatus, MessageType, WSCommand, WSMessage, WSResponse


class TestWSClient:
    """Тесты для WebSocket клиента."""

    @pytest.fixture
    def mock_websocket(self):
        """Создание мокового WebSocket соединения."""
        websocket = AsyncMock()
        websocket.send = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def client(self):
        """Создание WSClient."""
        return WSClient("ws://localhost:8000/ws/connect")

    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Тест инициализации клиента."""
        assert client.uri == "ws://localhost:8000/ws/connect"
        assert client.status == SSEConnectionStatus.DISCONNECTED
        assert client.websocket is None
        assert client.connection_id is None

    @pytest.mark.asyncio
    async def test_build_uri_with_params(self, client):
        """Тест построения URI с параметрами."""
        client.token = "test_token"
        client.api_key = "test_key"
        client.user_id = "user123"
        client.subscribed_channels = {"channel1", "channel2"}

        uri = client._build_uri()
        assert "token=test_token" in uri
        assert "api_key=test_key" in uri
        assert "user_id=user123" in uri
        assert "channels=channel1,channel2" in uri or "channels=channel2,channel1" in uri

    @pytest.mark.asyncio
    async def test_successful_connection(self, client, mock_websocket):
        """Тест успешного подключения."""
        with patch("websockets.connect", return_value=mock_websocket):
            result = await client.connect()

            assert result is True
            assert client.status == SSEConnectionStatus.CONNECTED
            assert client.websocket == mock_websocket
            assert client.reconnect_attempts == 0

    @pytest.mark.asyncio
    async def test_failed_connection(self, client):
        """Тест неудачного подключения."""
        with patch("websockets.connect", side_effect=Exception("Connection failed")):
            result = await client.connect()

            assert result is False
            assert client.status == SSEConnectionStatus.ERROR

    @pytest.mark.asyncio
    async def test_disconnect(self, client, mock_websocket):
        """Тест отключения."""
        client.websocket = mock_websocket
        client.status = SSEConnectionStatus.CONNECTED
        client.receive_task = AsyncMock()
        client.ping_task = AsyncMock()

        await client.disconnect()

        assert client.status == SSEConnectionStatus.DISCONNECTED
        assert client.websocket is None
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message(self, client, mock_websocket):
        """Тест отправки сообщения."""
        client.websocket = mock_websocket
        client.status = SSEConnectionStatus.CONNECTED

        message_id = await client.send_message("Hello, world!", MessageType.TEXT)

        assert message_id is not None
        mock_websocket.send.assert_called_once()

        # Проверяем структуру отправленного сообщения
        call_args = mock_websocket.send.call_args[0][0]
        message_data = json.loads(call_args)
        assert message_data["type"] == MessageType.TEXT.value
        assert message_data["content"] == "Hello, world!"
        assert "id" in message_data

    @pytest.mark.asyncio
    async def test_send_command(self, client, mock_websocket):
        """Тест отправки команды."""
        client.websocket = mock_websocket
        client.status = SSEConnectionStatus.CONNECTED

        # Симулируем получение ответа
        async def mock_receive():
            await asyncio.sleep(0.1)
            # Симулируем ответ на команду
            response_data = {
                "type": "response",
                "content": {"request_id": "test_request_id", "success": True, "data": {"result": "ok"}},
            }

            # Найдем future для ответа и установим результат
            for request_id, future in client.command_responses.items():
                if not future.done():
                    future.set_result(response_data["content"])
                    break

        # Запускаем получение ответа в фоне
        asyncio.create_task(mock_receive())

        # Добавляем мок request_id для тестирования
        with patch("uuid.uuid4", return_value=MagicMock(spec=str)) as mock_uuid:
            mock_uuid.return_value.__str__ = lambda self: "test_request_id"

            response = await client.send_command("test_action", {"param": "value"}, timeout=1)

            assert response.success is True
            assert response.data == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_ping(self, client, mock_websocket):
        """Тест ping команды."""
        client.websocket = mock_websocket
        client.status = SSEConnectionStatus.CONNECTED

        # Симулируем успешный ping ответ
        async def mock_ping_response():
            await asyncio.sleep(0.1)
            for request_id, future in client.command_responses.items():
                if not future.done():
                    future.set_result({"request_id": request_id, "success": True, "data": {"pong": True}})
                    break

        asyncio.create_task(mock_ping_response())

        with patch("uuid.uuid4", return_value=MagicMock(spec=str)) as mock_uuid:
            mock_uuid.return_value.__str__ = lambda self: "ping_request_id"

            result = await client.ping()
            assert result is True
            assert client.last_ping is not None

    @pytest.mark.asyncio
    async def test_message_handlers(self, client):
        """Тест обработчиков сообщений."""
        handler_called = False
        received_data = None

        @client.on_message("test_message")
        async def test_handler(data):
            nonlocal handler_called, received_data
            handler_called = True
            received_data = data

        # Симулируем получение сообщения
        test_data = {"type": "test_message", "content": "test content"}
        await client._handle_message(test_data)

        assert handler_called is True
        assert received_data == test_data

    def test_status_methods(self, client):
        """Тест методов статуса."""
        # Проверяем начальное состояние
        assert not client.is_connected()

        status = client.get_status()
        assert status["status"] == SSEConnectionStatus.DISCONNECTED.value
        assert status["connection_id"] is None
        assert status["reconnect_attempts"] == 0

        # Симулируем подключенное состояние
        client.status = SSEConnectionStatus.CONNECTED
        client.connection_id = "test_connection"

        assert client.is_connected()

        status = client.get_status()
        assert status["status"] == SSEConnectionStatus.CONNECTED.value
        assert status["connection_id"] == "test_connection"


class TestWSClientFactory:
    """Тесты для фабричных функций создания клиентов."""

    def test_create_ws_client(self):
        """Тест создания WebSocket клиента."""
        client = create_ws_client(host="example.com", port=9000, use_ssl=True)

        assert client.uri == "wss://example.com:9000/ws/connect"

    def test_create_ws_client_default_params(self):
        """Тест создания клиента с параметрами по умолчанию."""
        client = create_ws_client()

        assert client.uri == "ws://localhost:8000/ws/connect"

    def test_create_authenticated_client(self):
        """Тест создания аутентифицированного клиента."""
        from core.streaming import create_authenticated_client

        client = create_authenticated_client(
            host="api.example.com", port=443, token="jwt_token", api_key="api_key_123", use_ssl=True
        )

        assert client.uri == "wss://api.example.com:443/ws/connect"
        assert client.token == "jwt_token"
        assert client.api_key == "api_key_123"


class TestWSModels:
    """Тесты для WebSocket моделей."""

    def test_ws_message_creation(self):
        """Тест создания WebSocket сообщения."""
        message = WSMessage(
            id="test_id", type=MessageType.JSON, content={"hello": "world"}, sender_id="user123", channel="general"
        )

        assert message.id == "test_id"
        assert message.type == MessageType.JSON
        assert message.content == {"hello": "world"}
        assert message.sender_id == "user123"
        assert message.channel == "general"
        assert message.timestamp is not None

    def test_ws_command_creation(self):
        """Тест создания WebSocket команды."""
        command = WSCommand(action="subscribe", data={"channel": "notifications"}, request_id="req_123")

        assert command.action == "subscribe"
        assert command.data == {"channel": "notifications"}
        assert command.request_id == "req_123"

    def test_ws_response_creation(self):
        """Тест создания WebSocket ответа."""
        response = WSResponse(request_id="req_123", success=True, data={"subscribed": True})

        assert response.request_id == "req_123"
        assert response.success is True
        assert response.data == {"subscribed": True}
        assert response.error is None


class TestReconnection:
    """Тесты для переподключения."""

    @pytest.mark.asyncio
    async def test_auto_reconnect_on_error(self, mock_websocket):
        """Тест автоматического переподключения при ошибке."""
        client = WSClient(
            "ws://localhost:8000/ws/connect",
            auto_reconnect=True,
            reconnect_interval=0.1,  # Быстрое переподключение для теста
            max_reconnect_attempts=2,
        )

        connection_attempts = 0

        async def mock_connect_with_failure(*args, **kwargs):
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts == 1:
                raise Exception("First connection failed")
            return mock_websocket

        with patch("websockets.connect", side_effect=mock_connect_with_failure):
            # Первая попытка подключения должна провалиться
            result = await client.connect()
            assert result is False

            # Ждем попытку переподключения
            await asyncio.sleep(0.2)

            # Проверяем что была попытка переподключения
            assert connection_attempts >= 2

    @pytest.mark.asyncio
    async def test_max_reconnect_attempts(self):
        """Тест ограничения количества попыток переподключения."""
        client = WSClient(
            "ws://localhost:8000/ws/connect", auto_reconnect=True, reconnect_interval=0.1, max_reconnect_attempts=2
        )

        connection_attempts = 0

        async def mock_failing_connect(*args, **kwargs):
            nonlocal connection_attempts
            connection_attempts += 1
            raise Exception("Connection always fails")

        with patch("websockets.connect", side_effect=mock_failing_connect):
            await client.connect()

            # Ждем завершения всех попыток переподключения
            await asyncio.sleep(0.5)

            # Должно быть не более max_reconnect_attempts + 1 (начальная попытка)
            assert connection_attempts <= 3  # 1 начальная + 2 переподключения
            assert client.reconnect_attempts <= 2
