"""Тесты для SSE клиента и соединений."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.streaming.sse_client import SimpleSyncSSEClient, SSEClient, create_sse_client
from core.streaming import SSEConnectionStatus, SSEMessage


class TestSSEClient:
    """Тесты для SSE клиента."""

    @pytest.fixture
    def client(self):
        """Создание SSE клиента."""
        return SSEClient("http://localhost:8000/sse/connect")

    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Тест инициализации клиента."""
        assert client.uri == "http://localhost:8000/sse/connect"
        assert client.status == SSEConnectionStatus.DISCONNECTED
        assert client.connection_id is None
        assert client.last_event_id is None

    def test_build_params(self, client):
        """Тест построения параметров запроса."""
        client.token = "test_token"
        client.api_key = "test_key"
        client.user_id = "user123"
        client.subscribed_channels = {"channel1", "channel2"}
        client.last_event_id = "event_123"

        params = client._build_params()

        assert params["token"] == "test_token"
        assert params["api_key"] == "test_key"
        assert params["user_id"] == "user123"
        assert params["last_event_id"] == "event_123"
        assert "channels" in params

    def test_build_headers(self, client):
        """Тест построения заголовков."""
        client.token = "jwt_token"
        client.api_key = "api_key_123"
        client.last_event_id = "last_event"

        headers = client._build_headers()

        assert headers["Accept"] == "text/event-stream"
        assert headers["Cache-Control"] == "no-cache"
        assert headers["Authorization"] == "Bearer jwt_token"
        assert headers["X-API-Key"] == "api_key_123"
        assert headers["Last-Event-ID"] == "last_event"

    @pytest.mark.asyncio
    async def test_connect_success(self, client):
        """Тест успешного подключения."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Мокаем задачу прослушивания
            client._listen_loop = AsyncMock()

            result = await client.connect()

            assert result is True
            assert client.status == SSEConnectionStatus.CONNECTING
            assert client.http_client == mock_client

    @pytest.mark.asyncio
    async def test_disconnect(self, client):
        """Тест отключения."""
        mock_client = AsyncMock()
        client.http_client = mock_client
        client.listen_task = AsyncMock()
        client.reconnect_task = AsyncMock()
        client.status = SSEConnectionStatus.CONNECTED

        await client.disconnect()

        assert client.status == SSEConnectionStatus.DISCONNECTED
        assert client.connection_id is None
        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_channel(self, client):
        """Тест отправки сообщения в канал."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)

        client.http_client = mock_client

        result = await client.send_to_channel("test_channel", "test_event", {"message": "hello"})

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_user(self, client):
        """Тест отправки сообщения пользователю."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)

        client.http_client = mock_client

        result = await client.send_to_user("user123", "notification", {"title": "Test"})

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast(self, client):
        """Тест рассылки события."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)

        client.http_client = mock_client

        result = await client.broadcast("system_alert", {"message": "Server maintenance"})

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification(self, client):
        """Тест отправки уведомления."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)

        client.http_client = mock_client

        result = await client.send_notification(
            title="Test Notification", content="This is a test", notification_type="info", channel="general"
        )

        assert result is True
        mock_client.post.assert_called_once()

    def test_event_handlers(self, client):
        """Тест обработчиков событий."""
        handler_called = False
        received_data = None

        @client.on_event("test_event")
        def test_handler(data):
            nonlocal handler_called, received_data
            handler_called = True
            received_data = data

        # Проверяем что обработчик добавлен
        assert "test_event" in client.event_handlers
        assert len(client.event_handlers["test_event"]) == 1

        # Удаляем обработчик
        client.remove_event_handler("test_event", test_handler)
        assert len(client.event_handlers["test_event"]) == 0

    def test_connection_status(self, client):
        """Тест методов статуса соединения."""
        assert not client.is_connected()

        client.status = SSEConnectionStatus.CONNECTED
        assert client.is_connected()

        status = client.get_status()
        assert status["status"] == SSEConnectionStatus.CONNECTED.value

    @pytest.mark.asyncio
    async def test_handle_sse_event(self, client):
        """Тест обработки SSE события."""
        # Мокаем SSE событие
        mock_event = MagicMock()
        mock_event.id = "event_123"
        mock_event.event = "test_event"
        mock_event.data = '{"message": "test"}'
        mock_event.retry = None

        handler_called = False
        received_data = None

        async def test_handler(data):
            nonlocal handler_called, received_data
            handler_called = True
            received_data = data

        client.add_event_handler("test_event", test_handler)

        await client._handle_sse_event(mock_event)

        assert client.last_event_id == "event_123"
        assert handler_called is True
        assert received_data["event"] == "test_event"
        assert received_data["data"] == {"message": "test"}

    @pytest.mark.asyncio
    async def test_reconnection_logic(self, client):
        """Тест логики переподключения."""
        client.auto_reconnect = True
        client.max_reconnect_attempts = 2
        client.reconnect_interval = 0.1

        # Симулируем ошибку соединения
        client.status = SSEConnectionStatus.ERROR
        client.is_closing = False

        await client._schedule_reconnect()

        assert client.reconnect_attempts == 1

    @pytest.mark.asyncio
    async def test_call_handlers_async(self, client):
        """Тест вызова асинхронных обработчиков."""
        async_handler_called = False
        sync_handler_called = False

        async def async_handler(data):
            nonlocal async_handler_called
            async_handler_called = True

        def sync_handler(data):
            nonlocal sync_handler_called
            sync_handler_called = True

        client.add_event_handler("test", async_handler)
        client.add_event_handler("test", sync_handler)

        await client._call_handlers("test", {"message": "test"})

        assert async_handler_called is True
        assert sync_handler_called is True


class TestSimpleSyncSSEClient:
    """Тесты для синхронного SSE клиента."""

    def test_initialization(self):
        """Тест инициализации синхронного клиента."""
        client = SimpleSyncSSEClient("http://localhost:8000/sse/connect")

        assert client.uri == "http://localhost:8000/sse/connect"
        assert client.token is None
        assert client.api_key is None

    def test_build_headers(self):
        """Тест построения заголовков для синхронного клиента."""
        client = SimpleSyncSSEClient("http://localhost:8000/sse/connect", token="test_token", api_key="test_key")

        headers = client._build_headers()

        assert headers["Accept"] == "text/event-stream"
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["X-API-Key"] == "test_key"

    def test_listen_method_structure(self):
        """Тест структуры метода listen (без фактического подключения)."""
        client = SimpleSyncSSEClient("http://localhost:8000/sse/connect")

        # Проверяем что метод listen существует и принимает callable
        assert hasattr(client, "listen")
        assert callable(client.listen)


class TestSSEMessage:
    """Тесты для SSE сообщений."""

    def test_sse_message_creation(self):
        """Тест создания SSE сообщения."""
        message = SSEMessage(id="msg_123", event="notification", data={"title": "Test", "body": "Message"}, retry=5000)

        assert message.id == "msg_123"
        assert message.event == "notification"
        assert message.data == {"title": "Test", "body": "Message"}
        assert message.retry == 5000
        assert message.timestamp is not None

    def test_sse_format_conversion(self):
        """Тест преобразования в SSE формат."""
        message = SSEMessage(id="msg_123", event="test", data={"message": "hello"}, retry=3000)

        sse_format = message.to_sse_format()

        assert "id: msg_123" in sse_format
        assert "event: test" in sse_format
        assert "retry: 3000" in sse_format
        assert "data:" in sse_format
        assert sse_format.endswith("\n")

    def test_sse_format_with_string_data(self):
        """Тест SSE формата со строковыми данными."""
        message = SSEMessage(id="msg_456", event="message", data="Simple text message")

        sse_format = message.to_sse_format()

        assert "data: Simple text message" in sse_format

    def test_sse_format_multiline_data(self):
        """Тест SSE формата с многострочными данными."""
        message = SSEMessage(id="msg_789", event="message", data="Line 1\nLine 2\nLine 3")

        sse_format = message.to_sse_format()

        assert "data: Line 1" in sse_format
        assert "data: Line 2" in sse_format
        assert "data: Line 3" in sse_format


class TestSSEClientFactory:
    """Тесты для фабричных функций SSE клиентов."""

    def test_create_sse_client(self):
        """Тест создания SSE клиента."""
        client = create_sse_client(host="example.com", port=9000, use_ssl=True)

        assert client.uri == "https://example.com:9000/sse/connect"

    def test_create_sse_client_default_params(self):
        """Тест создания клиента с параметрами по умолчанию."""
        client = create_sse_client()

        assert client.uri == "http://localhost:8000/sse/connect"

    def test_create_authenticated_sse_client(self):
        """Тест создания аутентифицированного SSE клиента."""
        from core.streaming.sse_client import create_authenticated_sse_client

        client = create_authenticated_sse_client(
            host="api.example.com", port=443, token="jwt_token", api_key="api_key_123", use_ssl=True
        )

        assert client.uri == "https://api.example.com:443/sse/connect"
        assert client.token == "jwt_token"
        assert client.api_key == "api_key_123"

    def test_create_simple_sse_client(self):
        """Тест создания простого SSE клиента."""
        from core.streaming.sse_client import create_simple_sse_client

        client = create_simple_sse_client(host="test.com", port=8080)

        assert client.uri == "http://test.com:8080/sse/connect"


class TestConnectionManager:
    """Тесты для интеграции с менеджером соединений."""

    @pytest.mark.asyncio
    async def test_sse_connection_lifecycle(self):
        """Тест жизненного цикла SSE соединения."""
        from core.streaming.connection_manager import ConnectionManager

        manager = ConnectionManager()
        connection_id = "test_sse_conn"
        user_data = {"authenticated": True, "user": {"sub": "user123"}}

        # Подключение
        queue = await manager.connect_sse(connection_id, user_data)
        assert connection_id in manager.sse_connections
        assert isinstance(queue, asyncio.Queue)

        # Отправка сообщения
        from core.streaming import SSEMessage

        test_message = SSEMessage(id="test_id", event="test", data="test data")

        result = await manager.send_to_sse(connection_id, test_message)
        assert result is True

        # Проверка что сообщение в очереди
        assert not queue.empty()
        received_message = queue.get_nowait()
        assert received_message.id == "test_id"

        # Отключение
        await manager.disconnect_sse(connection_id)
        assert connection_id not in manager.sse_connections

    @pytest.mark.asyncio
    async def test_sse_channel_subscription(self):
        """Тест подписки SSE на каналы."""
        from core.streaming.connection_manager import ConnectionManager

        manager = ConnectionManager()
        connection_id = "test_sse_channel"
        user_data = {"authenticated": False, "user": None}

        # Подключение и подписка
        await manager.connect_sse(connection_id, user_data)
        await manager.subscribe_to_channel(connection_id, "test_channel")

        # Проверка подписки
        assert connection_id in manager.channel_subscriptions["test_channel"]
        assert "test_channel" in manager.connection_channels[connection_id]

        # Отписка
        await manager.unsubscribe_from_channel(connection_id, "test_channel")
        assert connection_id not in manager.channel_subscriptions.get("test_channel", set())

        # Очистка
        await manager.disconnect_sse(connection_id)
