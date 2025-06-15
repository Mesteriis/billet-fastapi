"""Тесты для RabbitMQ клиента (перенести в messaging)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faststream.rabbit import RabbitBroker

from core.messaging.core import MessageClient, get_message_client
from core.messaging import MessageModel, OrderProcessingMessage, SystemEventMessage, UserNotificationMessage


class TestMessageModels:
    """Тесты для моделей сообщений."""

    def test_message_model_creation(self):
        """Тест создания базовой модели сообщения."""
        message = MessageModel(type="test_message", source="test_service", payload={"key": "value"})

        assert message.type == "test_message"
        assert message.source == "test_service"
        assert message.payload == {"key": "value"}
        assert message.id is not None
        assert message.timestamp is not None

    def test_user_notification_message(self):
        """Тест модели уведомления пользователя."""
        payload = UserNotificationMessage.PayloadModel(
            user_id=123, message="Test notification", notification_type="info"
        )

        notification = UserNotificationMessage(source="api", payload=payload)

        assert notification.type == "user_notification"
        assert notification.payload.user_id == 123
        assert notification.payload.message == "Test notification"
        assert notification.payload.notification_type == "info"

    def test_order_processing_message(self):
        """Тест модели сообщения о заказе."""
        payload = OrderProcessingMessage.PayloadModel(order_id=456, status="processing", details={"priority": "high"})

        order_msg = OrderProcessingMessage(source="order_service", payload=payload)

        assert order_msg.type == "order_processing"
        assert order_msg.payload.order_id == 456
        assert order_msg.payload.status == "processing"
        assert order_msg.payload.details == {"priority": "high"}

    def test_system_event_message(self):
        """Тест модели системного события."""
        payload = SystemEventMessage.PayloadModel(
            event_name="service_started", event_data={"service": "test"}, severity="info"
        )

        event = SystemEventMessage(source="system", payload=payload)

        assert event.type == "system_event"
        assert event.payload.event_name == "service_started"
        assert event.payload.severity == "info"


class TestMessageClient:
    """Тесты для клиента сообщений."""

    @pytest.fixture
    def mock_broker(self):
        """Создание мокового брокера."""
        broker = MagicMock(spec=RabbitBroker)
        broker.connect = AsyncMock()
        broker.close = AsyncMock()
        broker.publish = AsyncMock()
        return broker

    @pytest.fixture
    def client(self, mock_broker):
        """Создание клиента с моковым брокером."""
        return MessageClient(broker=mock_broker)

    @pytest.mark.asyncio
    async def test_client_connection(self, client, mock_broker):
        """Тест подключения клиента."""
        await client.connect()

        assert client._is_connected is True
        mock_broker.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_disconnection(self, client, mock_broker):
        """Тест отключения клиента."""
        client._is_connected = True
        await client.disconnect()

        assert client._is_connected is False
        mock_broker.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_session_context_manager(self, client, mock_broker):
        """Тест контекстного менеджера."""
        async with client.session():
            assert client._is_connected is True
            mock_broker.connect.assert_called_once()

        mock_broker.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_user_notification(self, client, mock_broker):
        """Тест отправки уведомления пользователю."""
        await client.send_user_notification(user_id=123, message="Test message", notification_type="info")

        mock_broker.publish.assert_called_once()
        call_args = mock_broker.publish.call_args

        # Проверяем что сообщение корректно сформировано
        message_data = call_args[0][0]
        assert message_data["type"] == "user_notification"
        assert message_data["payload"]["user_id"] == 123
        assert message_data["payload"]["message"] == "Test message"

    @pytest.mark.asyncio
    async def test_send_admin_notification(self, client, mock_broker):
        """Тест отправки админского уведомления."""
        await client.send_admin_notification(message="Admin alert", notification_type="warning")

        mock_broker.publish.assert_called_once()
        call_args = mock_broker.publish.call_args

        message_data = call_args[0][0]
        assert message_data["type"] == "user_notification"
        assert message_data["payload"]["user_id"] == 0  # 0 для админских уведомлений
        assert message_data["payload"]["message"] == "Admin alert"
        assert message_data["payload"]["notification_type"] == "warning"

    @pytest.mark.asyncio
    async def test_send_order_processing(self, client, mock_broker):
        """Тест отправки сообщения о заказе."""
        await client.send_order_processing(order_id=456, status="processing", details={"priority": "high"})

        mock_broker.publish.assert_called_once()
        call_args = mock_broker.publish.call_args

        message_data = call_args[0][0]
        assert message_data["type"] == "order_processing"
        assert message_data["payload"]["order_id"] == 456
        assert message_data["payload"]["status"] == "processing"
        assert message_data["payload"]["details"] == {"priority": "high"}

    @pytest.mark.asyncio
    async def test_send_system_event(self, client, mock_broker):
        """Тест отправки системного события."""
        await client.send_system_event(event_name="service_started", event_data={"version": "1.0"}, severity="info")

        mock_broker.publish.assert_called_once()
        call_args = mock_broker.publish.call_args

        message_data = call_args[0][0]
        assert message_data["type"] == "system_event"
        assert message_data["payload"]["event_name"] == "service_started"
        assert message_data["payload"]["severity"] == "info"

    @pytest.mark.asyncio
    async def test_send_custom_message_with_model(self, client, mock_broker):
        """Тест отправки произвольного сообщения с моделью."""
        custom_message = MessageModel(type="custom_event", source="test", payload={"test": "data"})

        await client.send_custom_message(message=custom_message, exchange_name="system", routing_key="test.event")

        mock_broker.publish.assert_called_once()
        call_args = mock_broker.publish.call_args

        message_data = call_args[0][0]
        assert message_data["type"] == "custom_event"
        assert message_data["source"] == "test"
        assert message_data["payload"] == {"test": "data"}

    @pytest.mark.asyncio
    async def test_send_custom_message_with_dict(self, client, mock_broker):
        """Тест отправки произвольного сообщения с словарем."""
        message_dict = {"type": "custom_event", "data": {"key": "value"}}

        await client.send_custom_message(message=message_dict, exchange_name="notifications", routing_key="custom")

        mock_broker.publish.assert_called_once()
        call_args = mock_broker.publish.call_args

        message_data = call_args[0][0]
        assert message_data == message_dict

    @pytest.mark.asyncio
    async def test_send_custom_message_invalid_exchange(self, client, mock_broker):
        """Тест отправки сообщения с неизвестным exchange."""
        with pytest.raises(ValueError, match="Неизвестный exchange"):
            await client.send_custom_message(message={"test": "data"}, exchange_name="unknown_exchange")


class TestGetMessageClient:
    """Тесты для глобального клиента."""

    def test_get_message_client_singleton(self):
        """Тест что get_message_client возвращает один и тот же экземпляр."""
        client1 = get_message_client()
        client2 = get_message_client()

        assert client1 is client2

    @patch("src.streaming.client._client", None)
    def test_get_message_client_creates_new_instance(self):
        """Тест создания нового экземпляра клиента."""
        with patch("src.streaming.client.MessageClient") as MockClient:
            mock_instance = MagicMock()
            MockClient.return_value = mock_instance

            client = get_message_client()

            MockClient.assert_called_once()
            assert client is mock_instance


class TestIntegration:
    """Интеграционные тесты."""

    @pytest.mark.asyncio
    @patch("src.streaming.broker.get_broker")
    async def test_end_to_end_message_flow(self, mock_get_broker):
        """Тест полного цикла отправки сообщения."""
        # Настраиваем мок брокера
        mock_broker = MagicMock(spec=RabbitBroker)
        mock_broker.connect = AsyncMock()
        mock_broker.close = AsyncMock()
        mock_broker.publish = AsyncMock()
        mock_get_broker.return_value = mock_broker

        # Создаем клиента и отправляем сообщение
        client = MessageClient()

        async with client.session():
            await client.send_user_notification(user_id=123, message="Integration test", notification_type="info")

        # Проверяем что брокер был использован корректно
        mock_broker.connect.assert_called_once()
        mock_broker.publish.assert_called_once()
        mock_broker.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_message_sending(self):
        """Тест массовой отправки сообщений."""
        mock_broker = MagicMock(spec=RabbitBroker)
        mock_broker.connect = AsyncMock()
        mock_broker.close = AsyncMock()
        mock_broker.publish = AsyncMock()

        client = MessageClient(broker=mock_broker)

        # Отправляем несколько сообщений параллельно
        user_ids = [1, 2, 3, 4, 5]

        async with client.session():
            tasks = []
            for user_id in user_ids:
                task = client.send_user_notification(
                    user_id=user_id, message=f"Message for user {user_id}", notification_type="info"
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

        # Проверяем что все сообщения были отправлены
        assert mock_broker.publish.call_count == len(user_ids)

    @pytest.mark.asyncio
    async def test_error_handling_in_message_sending(self):
        """Тест обработки ошибок при отправке сообщений."""
        mock_broker = MagicMock(spec=RabbitBroker)
        mock_broker.connect = AsyncMock()
        mock_broker.close = AsyncMock()
        mock_broker.publish = AsyncMock(side_effect=Exception("Connection error"))

        client = MessageClient(broker=mock_broker)

        async with client.session():
            with pytest.raises(Exception, match="Connection error"):
                await client.send_user_notification(user_id=123, message="Test message", notification_type="info")
