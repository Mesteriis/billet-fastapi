"""Тесты для WebSocket функциональности с бинарными данными и WebRTC."""

import base64

import pytest

from core.realtime import BinaryMessage, ConnectionManager, MessageType, WebRTCMessage, WebRTCSignalType, WSMessage
from core.realtime.models import WSCommand, WSResponse


class TestWebSocketModels:
    """Тесты для моделей WebSocket."""

    def test_ws_message_creation(self):
        """Тест создания WebSocket сообщения."""
        message = WSMessage(type=MessageType.TEXT, data="Hello World", channel="general", user_id="user123")

        assert message.type == MessageType.TEXT
        assert message.data == "Hello World"
        assert message.channel == "general"
        assert message.user_id == "user123"
        assert message.id is not None

    def test_binary_message_creation(self):
        """Тест создания бинарного сообщения."""
        test_data = b"Hello Binary World"
        message = BinaryMessage.from_bytes(data=test_data, content_type="text/plain", filename="test.txt")

        assert message.type == MessageType.BINARY
        assert message.content_type == "text/plain"
        assert message.filename == "test.txt"
        assert message.size == len(test_data)
        assert message.get_binary_data() == test_data
        assert message.checksum is not None

    def test_binary_message_base64_validation(self):
        """Тест валидации Base64 в бинарном сообщении."""
        # Валидный Base64
        valid_base64 = base64.b64encode(b"test data").decode("utf-8")
        message = BinaryMessage(binary_data=valid_base64, content_type="application/octet-stream")
        assert message.binary_data == valid_base64

        # Невалидный Base64
        with pytest.raises(ValueError, match="Invalid base64"):
            BinaryMessage(binary_data="invalid_base64!@#", content_type="application/octet-stream")

    def test_webrtc_message_creation(self):
        """Тест создания WebRTC сообщения."""
        message = WebRTCMessage(
            signal_type=WebRTCSignalType.OFFER,
            peer_id="peer1",
            target_peer_id="peer2",
            room_id="room123",
            sdp="v=0\r\no=- 123456 654321 IN IP4 127.0.0.1\r\n",
        )

        assert message.type == MessageType.WEBRTC
        assert message.signal_type == WebRTCSignalType.OFFER
        assert message.peer_id == "peer1"
        assert message.target_peer_id == "peer2"
        assert message.room_id == "room123"
        assert message.sdp is not None

    def test_ws_command_binary_data(self):
        """Тест команды WebSocket с бинарными данными."""
        test_data = b"Binary command data"
        command = WSCommand(action="send_binary")
        command.set_binary_data(test_data)

        assert command.binary_data is not None
        assert command.get_binary_data() == test_data

    def test_ws_response_creation(self):
        """Тест создания ответа WebSocket."""
        response = WSResponse(success=True, message="Operation successful", data={"result": "ok"})

        assert response.success is True
        assert response.message == "Operation successful"
        assert response.data["result"] == "ok"
        assert response.timestamp is not None


class TestConnectionManager:
    """Тесты для менеджера подключений."""

    @pytest.fixture
    def connection_manager(self):
        """Менеджер подключений для тестов."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Мок WebSocket соединения."""
        websocket = MagicMock()
        websocket.send_text = AsyncMock()
        websocket.send_bytes = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_add_connection(self, connection_manager, mock_websocket):
        """Тест добавления соединения."""
        connection_id = "test_conn_1"

        await connection_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id="user123",
            channels=["general"],
            supports_binary=True,
            supports_webrtc=True,
        )

        # Проверяем, что соединение добавлено
        connections = await connection_manager.get_connections_info()
        assert len(connections) == 1
        assert connections[0]["connection_id"] == connection_id
        assert connections[0]["user_id"] == "user123"
        assert connections[0]["supports_binary"] is True
        assert connections[0]["supports_webrtc"] is True

    @pytest.mark.asyncio
    async def test_remove_connection(self, connection_manager, mock_websocket):
        """Тест удаления соединения."""
        connection_id = "test_conn_1"

        await connection_manager.add_connection(
            connection_id=connection_id, websocket=mock_websocket, user_id="user123"
        )

        await connection_manager.remove_connection(connection_id)

        # Проверяем, что соединение удалено
        connections = await connection_manager.get_connections_info()
        assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_send_to_connection(self, connection_manager, mock_websocket):
        """Тест отправки сообщения конкретному соединению."""
        connection_id = "test_conn_1"

        await connection_manager.add_connection(
            connection_id=connection_id, websocket=mock_websocket, user_id="user123"
        )

        message = {"type": "test", "data": "hello"}
        await connection_manager.send_to_connection(connection_id, message)

        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "test"
        assert sent_data["data"] == "hello"

    @pytest.mark.asyncio
    async def test_send_binary_to_connection(self, connection_manager, mock_websocket):
        """Тест отправки бинарных данных соединению."""
        connection_id = "test_conn_1"

        await connection_manager.add_connection(
            connection_id=connection_id, websocket=mock_websocket, user_id="user123", supports_binary=True
        )

        test_data = b"Binary test data"
        binary_message = BinaryMessage.from_bytes(test_data)

        await connection_manager.send_to_connection(connection_id, binary_message.dict())

        # Должно отправиться как текст (JSON с Base64)
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_channel_subscription(self, connection_manager, mock_websocket):
        """Тест подписки на каналы."""
        connection_id = "test_conn_1"

        await connection_manager.add_connection(
            connection_id=connection_id, websocket=mock_websocket, user_id="user123"
        )

        # Подписываемся на канал
        await connection_manager.subscribe_to_channel(connection_id, "test_channel")

        # Отправляем сообщение в канал
        message = {"type": "channel_message", "data": "channel data"}
        sent_count = await connection_manager.send_to_channel("test_channel", message)

        assert sent_count == 1
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_message(self, connection_manager, mock_websocket):
        """Тест широковещательной отправки."""
        # Добавляем несколько соединений
        for i in range(3):
            await connection_manager.add_connection(
                connection_id=f"conn_{i}", websocket=mock_websocket, user_id=f"user_{i}"
            )

        message = {"type": "broadcast", "data": "broadcast data"}
        sent_count = await connection_manager.broadcast_message(message)

        assert sent_count == 3
        assert mock_websocket.send_text.call_count == 3

    @pytest.mark.asyncio
    async def test_get_user_connections(self, connection_manager, mock_websocket):
        """Тест получения соединений пользователя."""
        user_id = "user123"

        # Добавляем несколько соединений для одного пользователя
        for i in range(2):
            await connection_manager.add_connection(
                connection_id=f"conn_{i}", websocket=mock_websocket, user_id=user_id
            )

        connections = await connection_manager.get_user_connections(user_id)
        assert len(connections) == 2
        assert "conn_0" in connections
        assert "conn_1" in connections

    def test_stats(self, connection_manager):
        """Тест получения статистики."""
        stats = connection_manager.get_stats()

        assert "total_connections" in stats
        assert "active_connections" in stats
        assert "channels" in stats
        assert isinstance(stats["total_connections"], int)


class TestWebRTCFunctionality:
    """Тесты для WebRTC функциональности."""

    def test_webrtc_signal_types(self):
        """Тест типов WebRTC сигналов."""
        # Проверяем все доступные типы сигналов
        assert WebRTCSignalType.OFFER == "offer"
        assert WebRTCSignalType.ANSWER == "answer"
        assert WebRTCSignalType.ICE_CANDIDATE == "ice-candidate"
        assert WebRTCSignalType.ICE_GATHERING_STATE == "ice-gathering-state"
        assert WebRTCSignalType.CONNECTION_STATE == "connection-state"
        assert WebRTCSignalType.DATA_CHANNEL == "data-channel"

    def test_webrtc_message_with_ice_candidate(self):
        """Тест WebRTC сообщения с ICE кандидатом."""
        ice_candidate = {
            "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54400 typ host",
            "sdpMLineIndex": 0,
            "sdpMid": "0",
        }

        message = WebRTCMessage(
            signal_type=WebRTCSignalType.ICE_CANDIDATE,
            peer_id="peer1",
            target_peer_id="peer2",
            ice_candidate=ice_candidate,
        )

        assert message.signal_type == WebRTCSignalType.ICE_CANDIDATE
        assert message.ice_candidate == ice_candidate
        assert "candidate:" in message.ice_candidate["candidate"]

    def test_webrtc_room_management(self):
        """Тест управления WebRTC комнатами."""
        from core.realtime.models import WebRTCRoom

        room = WebRTCRoom(room_id="room_123", name="Test Room", max_participants=5, created_by="user1")

        assert room.room_id == "room_123"
        assert room.name == "Test Room"
        assert room.max_participants == 5
        assert room.created_by == "user1"
        assert len(room.participants) == 0

    def test_webrtc_peer_connection_info(self):
        """Тест информации о WebRTC соединении между пирами."""
        from core.realtime.models import WebRTCPeerConnection

        connection = WebRTCPeerConnection(peer_id="peer1", target_peer_id="peer2", room_id="room_123")

        assert connection.peer_id == "peer1"
        assert connection.target_peer_id == "peer2"
        assert connection.room_id == "room_123"
        assert connection.connection_state == "new"
        assert connection.ice_gathering_state == "new"


class TestBinaryDataHandling:
    """Тесты для обработки бинарных данных."""

    def test_binary_data_encoding_decoding(self):
        """Тест кодирования и декодирования бинарных данных."""
        original_data = b"Hello Binary World! \x00\x01\x02\x03"

        # Создаем бинарное сообщение
        message = BinaryMessage.from_bytes(original_data)

        # Проверяем, что данные правильно закодированы и декодированы
        decoded_data = message.get_binary_data()
        assert decoded_data == original_data

    def test_large_binary_data(self):
        """Тест обработки больших бинарных данных."""
        # Создаем данные размером 1MB
        large_data = b"x" * (1024 * 1024)

        message = BinaryMessage.from_bytes(large_data)

        assert message.size == len(large_data)
        assert message.get_binary_data() == large_data
        assert len(message.binary_data) > 0  # Base64 должен быть больше 0

    def test_binary_data_with_metadata(self):
        """Тест бинарных данных с метаданными."""
        image_data = b"\x89PNG\r\n\x1a\n"  # PNG header

        message = BinaryMessage.from_bytes(data=image_data, content_type="image/png", filename="test.png")

        assert message.content_type == "image/png"
        assert message.filename == "test.png"
        assert message.size == len(image_data)
        assert message.checksum is not None

    def test_binary_message_checksum(self):
        """Тест контрольной суммы бинарных данных."""
        data1 = b"test data 1"
        data2 = b"test data 2"

        message1 = BinaryMessage.from_bytes(data1)
        message2 = BinaryMessage.from_bytes(data2)
        message3 = BinaryMessage.from_bytes(data1)  # те же данные что и в message1

        # Разные данные должны иметь разные контрольные суммы
        assert message1.checksum != message2.checksum

        # Одинаковые данные должны иметь одинаковые контрольные суммы
        assert message1.checksum == message3.checksum


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


if __name__ == "__main__":
    pytest.main([__file__])
