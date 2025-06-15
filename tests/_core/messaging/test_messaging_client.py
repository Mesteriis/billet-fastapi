"""Тесты для messaging клиента (FastStream)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.messaging import MessageClient, get_message_client
from core.messaging import MessageModel, OrderProcessingMessage, UserNotificationMessage


class TestMessageClient:
    """Тесты для MessageClient."""

    @pytest.fixture
    def mock_broker(self):
        """Мок брокера."""
        broker = MagicMock()
        broker.connect = AsyncMock()
        broker.close = AsyncMock()
        broker.publish = AsyncMock()
        return broker

    @pytest.fixture
    def client(self, mock_broker):
        """Клиент с мок брокером."""
        with patch("messaging.client.get_broker", return_value=mock_broker):
            return MessageClient()

    @pytest.mark.asyncio
    async def test_client_initialization(self, client, mock_broker):
        """Тест инициализации клиента."""
        assert client.broker == mock_broker
        assert not client._connected

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, client, mock_broker):
        """Тест подключения и отключения."""
        # Подключение
        await client.connect()
        mock_broker.connect.assert_called_once()
        assert client._connected

        # Отключение
        await client.disconnect()
        mock_broker.close.assert_called_once()
        assert not client._connected

    @pytest.mark.asyncio
    async def test_context_manager(self, client, mock_broker):
        """Тест использования как контекстный менеджер."""
        async with client.session():
            mock_broker.connect.assert_called_once()
            assert client._connected

        mock_broker.close.assert_called_once()
        assert not client._connected

    @pytest.mark.asyncio
    async def test_send_user_notification(self, client, mock_broker):
        """Тест отправки уведомления пользователю."""
        async with client.session():
            await client.send_user_notification(user_id=123, message="Тест", notification_type="info")

            mock_broker.publish.assert_called_once()
            call_args = mock_broker.publish.call_args[0][0]

            assert call_args["type"] == "user_notification"
            assert call_args["payload"]["user_id"] == 123
            assert call_args["payload"]["message"] == "Тест"
            assert call_args["payload"]["notification_type"] == "info"

    @pytest.mark.asyncio
    async def test_send_admin_notification(self, client, mock_broker):
        """Тест отправки админского уведомления."""
        async with client.session():
            await client.send_admin_notification(message="Админ сообщение", notification_type="warning")

            mock_broker.publish.assert_called_once()
            call_args = mock_broker.publish.call_args[0][0]

            assert call_args["type"] == "admin_notification"
            assert call_args["payload"]["message"] == "Админ сообщение"
            assert call_args["payload"]["notification_type"] == "warning"

    @pytest.mark.asyncio
    async def test_send_order_processing(self, client, mock_broker):
        """Тест отправки сообщения о заказе."""
        async with client.session():
            await client.send_order_processing(order_id=456, status="completed", details={"total": 1999.99})

            mock_broker.publish.assert_called_once()
            call_args = mock_broker.publish.call_args[0][0]

            assert call_args["type"] == "order_processing"
            assert call_args["payload"]["order_id"] == 456
            assert call_args["payload"]["status"] == "completed"
            assert call_args["payload"]["details"]["total"] == 1999.99

    @pytest.mark.asyncio
    async def test_send_system_event(self, client, mock_broker):
        """Тест отправки системного события."""
        async with client.session():
            await client.send_system_event(event_name="high_cpu", event_data={"cpu_percent": 85}, severity="warning")

            mock_broker.publish.assert_called_once()
            call_args = mock_broker.publish.call_args[0][0]

            assert call_args["type"] == "system_event"
            assert call_args["payload"]["event_name"] == "high_cpu"
            assert call_args["payload"]["event_data"]["cpu_percent"] == 85
            assert call_args["payload"]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_bulk_send(self, client, mock_broker):
        """Тест массовой отправки."""
        async with client.session():
            user_ids = [1, 2, 3, 4, 5]
            tasks = []

            for user_id in user_ids:
                task = client.send_user_notification(
                    user_id=user_id, message=f"Сообщение для {user_id}", notification_type="info"
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

            assert mock_broker.publish.call_count == len(user_ids)

    @pytest.mark.asyncio
    async def test_error_handling(self, client, mock_broker):
        """Тест обработки ошибок."""
        mock_broker.publish.side_effect = Exception("Broker error")

        async with client.session():
            with pytest.raises(Exception, match="Broker error"):
                await client.send_user_notification(user_id=123, message="Тест", notification_type="info")

    def test_get_message_client_singleton(self):
        """Тест singleton паттерна для get_message_client."""
        client1 = get_message_client()
        client2 = get_message_client()

        assert client1 is client2


class TestMessageModels:
    """Тесты для моделей сообщений."""

    def test_message_model_creation(self):
        """Тест создания базовой модели сообщения."""
        message = MessageModel(type="test_message", source="test_service", payload={"data": "test"})

        assert message.type == "test_message"
        assert message.source == "test_service"
        assert message.payload == {"data": "test"}
        assert message.id is not None
        assert message.timestamp is not None

    def test_user_notification_message(self):
        """Тест модели уведомления пользователя."""
        message = UserNotificationMessage(
            source="notification_service",
            payload=UserNotificationMessage.PayloadModel(
                user_id=123, message="Тест уведомления", notification_type="info"
            ),
        )

        assert message.type == "user_notification"
        assert message.payload.user_id == 123
        assert message.payload.message == "Тест уведомления"
        assert message.payload.notification_type == "info"

    def test_order_processing_message(self):
        """Тест модели сообщения о заказе."""
        message = OrderProcessingMessage(
            source="order_service",
            payload=OrderProcessingMessage.PayloadModel(order_id=456, status="completed", details={"total": 1999.99}),
        )

        assert message.type == "order_processing"
        assert message.payload.order_id == 456
        assert message.payload.status == "completed"
        assert message.payload.details["total"] == 1999.99

    def test_message_serialization(self):
        """Тест сериализации сообщений."""
        message = UserNotificationMessage(
            source="test",
            payload=UserNotificationMessage.PayloadModel(user_id=123, message="Тест", notification_type="info"),
        )

        # Сериализация в JSON
        json_data = message.json()
        assert isinstance(json_data, str)

        # Сериализация в dict
        dict_data = message.dict()
        assert isinstance(dict_data, dict)
        assert dict_data["type"] == "user_notification"
        assert dict_data["payload"]["user_id"] == 123


class TestBrokerIntegration:
    """Интеграционные тесты с брокером."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_message_flow(self):
        """Тест полного цикла отправки и получения сообщения."""
        # Этот тест требует запущенного RabbitMQ
        pytest.skip("Требует запущенного RabbitMQ для интеграционного тестирования")

        # Код для интеграционного тестирования:
        # client = MessageClient()
        # received_messages = []

        # async def handler(message):
        #     received_messages.append(message)

        # await client.connect()
        # await client.consume_user_notifications(handler)

        # await client.send_user_notification(
        #     user_id=123,
        #     message="Integration test",
        #     notification_type="info"
        # )

        # # Ждем получения сообщения
        # await asyncio.sleep(1)
        # assert len(received_messages) == 1

        # await client.disconnect()

    @pytest.mark.integration
    def test_broker_configuration(self):
        """Тест конфигурации брокера."""
        from core.messaging import get_broker

        broker = get_broker()
        assert broker is not None
        # Дополнительные проверки конфигурации брокера


if __name__ == "__main__":
    pytest.main([__file__])
