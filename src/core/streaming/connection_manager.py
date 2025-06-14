"""Менеджер соединений WebSocket и SSE."""

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import WebSocket

from core.config import get_settings

from .ws_models import HeartbeatMessage, MessageType, SSEConnectionStatus, SSEMessage, WSConnectionInfo, WSMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Менеджер WebSocket и SSE соединений."""

    def __init__(self):
        self.settings = get_settings()

        # WebSocket соединения
        self.ws_connections: dict[str, WebSocket] = {}
        self.ws_connection_info: dict[str, WSConnectionInfo] = {}
        self.ws_user_connections: dict[str, set[str]] = defaultdict(set)

        # SSE соединения (очереди сообщений)
        self.sse_connections: dict[str, asyncio.Queue] = {}
        self.sse_connection_info: dict[str, WSConnectionInfo] = {}
        self.sse_user_connections: dict[str, set[str]] = defaultdict(set)

        # Подписки на каналы
        self.channel_subscriptions: dict[str, set[str]] = defaultdict(set)
        self.connection_channels: dict[str, set[str]] = defaultdict(set)

        # Персистентные сообщения каналов
        self.channel_messages: dict[str, list[WSMessage]] = defaultdict(list)

        # Задачи heartbeat
        self.heartbeat_tasks: dict[str, asyncio.Task] = {}

        logger.info("Connection manager initialized")

    # WebSocket методы

    async def connect_websocket(
        self, websocket: WebSocket, connection_id: str, user_data: dict[str, Any]
    ) -> WSConnectionInfo:
        """Подключение WebSocket клиента."""
        await websocket.accept()

        # Проверяем лимит соединений
        if len(self.ws_connections) >= self.settings.WEBSOCKET_MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="Превышен лимит соединений")
            raise Exception("Превышен лимит соединений")

        # Создаем информацию о соединении
        connection_info = WSConnectionInfo(
            connection_id=connection_id,
            user_id=user_data.get("user", {}).get("sub") if user_data.get("authenticated") else None,
            status=SSEConnectionStatus.CONNECTED,
            ip_address=websocket.client.host if websocket.client else None,
            user_agent=websocket.headers.get("user-agent"),
            metadata={"auth_data": user_data},
        )

        # Сохраняем соединение
        self.ws_connections[connection_id] = websocket
        self.ws_connection_info[connection_id] = connection_info

        # Связываем с пользователем
        if connection_info.user_id:
            self.ws_user_connections[connection_info.user_id].add(connection_id)

        # Запускаем heartbeat
        if self.settings.WEBSOCKET_HEARTBEAT_INTERVAL > 0:
            task = asyncio.create_task(self._websocket_heartbeat(connection_id))
            self.heartbeat_tasks[connection_id] = task

        logger.info(f"WebSocket connected: {connection_id}, user: {connection_info.user_id}")
        return connection_info

    async def disconnect_websocket(self, connection_id: str) -> None:
        """Отключение WebSocket клиента."""
        if connection_id not in self.ws_connections:
            return

        connection_info = self.ws_connection_info.get(connection_id)

        # Убираем из подписок
        channels = self.connection_channels.get(connection_id, set()).copy()
        for channel in channels:
            await self.unsubscribe_from_channel(connection_id, channel)

        # Убираем из пользовательских соединений
        if connection_info and connection_info.user_id:
            self.ws_user_connections[connection_info.user_id].discard(connection_id)
            if not self.ws_user_connections[connection_info.user_id]:
                del self.ws_user_connections[connection_info.user_id]

        # Останавливаем heartbeat
        if connection_id in self.heartbeat_tasks:
            self.heartbeat_tasks[connection_id].cancel()
            del self.heartbeat_tasks[connection_id]

        # Удаляем соединение
        del self.ws_connections[connection_id]
        if connection_id in self.ws_connection_info:
            del self.ws_connection_info[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_to_websocket(self, connection_id: str, message: WSMessage) -> bool:
        """Отправка сообщения в WebSocket."""
        if connection_id not in self.ws_connections:
            return False

        websocket = self.ws_connections[connection_id]
        try:
            await websocket.send_json(message.dict())

            # Обновляем последнюю активность
            if connection_id in self.ws_connection_info:
                self.ws_connection_info[connection_id].last_activity = datetime.utcnow()

            return True
        except Exception as e:
            logger.error(f"Error sending WebSocket message to {connection_id}: {e}")
            await self.disconnect_websocket(connection_id)
            return False

    # SSE методы

    async def connect_sse(self, connection_id: str, user_data: dict[str, Any]) -> asyncio.Queue[SSEMessage]:
        """Подключение SSE клиента."""
        # Проверяем лимит соединений
        if len(self.sse_connections) >= self.settings.SSE_MAX_CONNECTIONS:
            raise Exception("Превышен лимит SSE соединений")

        # Создаем очередь сообщений
        message_queue: asyncio.Queue[SSEMessage] = asyncio.Queue(maxsize=self.settings.WEBSOCKET_MESSAGE_QUEUE_SIZE)

        # Создаем информацию о соединении
        connection_info = WSConnectionInfo(
            connection_id=connection_id,
            user_id=user_data.get("user", {}).get("sub") if user_data.get("authenticated") else None,
            status=SSEConnectionStatus.CONNECTED,
            metadata={"auth_data": user_data},
        )

        # Сохраняем соединение
        self.sse_connections[connection_id] = message_queue
        self.sse_connection_info[connection_id] = connection_info

        # Связываем с пользователем
        if connection_info.user_id:
            self.sse_user_connections[connection_info.user_id].add(connection_id)

        # Запускаем heartbeat
        if self.settings.SSE_HEARTBEAT_INTERVAL > 0:
            task = asyncio.create_task(self._sse_heartbeat(connection_id))
            self.heartbeat_tasks[connection_id] = task

        logger.info(f"SSE connected: {connection_id}, user: {connection_info.user_id}")
        return message_queue

    async def disconnect_sse(self, connection_id: str) -> None:
        """Отключение SSE клиента."""
        if connection_id not in self.sse_connections:
            return

        connection_info = self.sse_connection_info.get(connection_id)

        # Убираем из подписок
        channels = self.connection_channels.get(connection_id, set()).copy()
        for channel in channels:
            await self.unsubscribe_from_channel(connection_id, channel)

        # Убираем из пользовательских соединений
        if connection_info and connection_info.user_id:
            self.sse_user_connections[connection_info.user_id].discard(connection_id)
            if not self.sse_user_connections[connection_info.user_id]:
                del self.sse_user_connections[connection_info.user_id]

        # Останавливаем heartbeat
        if connection_id in self.heartbeat_tasks:
            self.heartbeat_tasks[connection_id].cancel()
            del self.heartbeat_tasks[connection_id]

        # Удаляем соединение
        del self.sse_connections[connection_id]
        if connection_id in self.sse_connection_info:
            del self.sse_connection_info[connection_id]

        logger.info(f"SSE disconnected: {connection_id}")

    async def send_to_sse(self, connection_id: str, message: SSEMessage) -> bool:
        """Отправка SSE сообщения."""
        if connection_id not in self.sse_connections:
            return False

        queue = self.sse_connections[connection_id]
        try:
            queue.put_nowait(message)

            # Обновляем последнюю активность
            if connection_id in self.sse_connection_info:
                self.sse_connection_info[connection_id].last_activity = datetime.utcnow()

            return True
        except asyncio.QueueFull:
            logger.warning(f"SSE queue full for connection {connection_id}")
            return False
        except Exception as e:
            logger.error(f"Error sending SSE message to {connection_id}: {e}")
            await self.disconnect_sse(connection_id)
            return False

    # Методы подписок на каналы

    async def subscribe_to_channel(self, connection_id: str, channel: str) -> bool:
        """Подписка соединения на канал."""
        # Добавляем в подписки канала
        self.channel_subscriptions[channel].add(connection_id)
        self.connection_channels[connection_id].add(channel)

        # Отправляем персистентные сообщения канала
        persistent_messages = self.channel_messages.get(channel, [])
        for message in persistent_messages:
            await self._send_to_connection(connection_id, message)

        logger.info(f"Connection {connection_id} subscribed to channel {channel}")
        return True

    async def unsubscribe_from_channel(self, connection_id: str, channel: str) -> bool:
        """Отписка соединения от канала."""
        self.channel_subscriptions[channel].discard(connection_id)
        self.connection_channels[connection_id].discard(channel)

        # Удаляем пустые каналы
        if not self.channel_subscriptions[channel]:
            del self.channel_subscriptions[channel]

        logger.info(f"Connection {connection_id} unsubscribed from channel {channel}")
        return True

    # Методы рассылки

    async def broadcast_to_channel(self, channel: str, message: WSMessage, persist: bool = False) -> int:
        """Широковещательная отправка в канал."""
        connection_ids = self.channel_subscriptions.get(channel, set())
        sent_count = 0

        # Сохраняем персистентное сообщение
        if persist:
            self.channel_messages[channel].append(message)
            # Ограничиваем количество персистентных сообщений
            if len(self.channel_messages[channel]) > self.settings.WEBSOCKET_MESSAGE_QUEUE_SIZE:
                self.channel_messages[channel] = self.channel_messages[channel][
                    -self.settings.WEBSOCKET_MESSAGE_QUEUE_SIZE :
                ]

        # Отправляем сообщение всем подписчикам
        for connection_id in connection_ids.copy():
            if await self._send_to_connection(connection_id, message):
                sent_count += 1

        logger.info(f"Broadcast to channel {channel}: {sent_count}/{len(connection_ids)} delivered")
        return sent_count

    async def send_to_user(self, user_id: str, message: WSMessage) -> int:
        """Отправка сообщения пользователю."""
        # Получаем все соединения пользователя
        ws_connections = self.ws_user_connections.get(user_id, set())
        sse_connections = self.sse_user_connections.get(user_id, set())
        all_connections = ws_connections | sse_connections

        sent_count = 0
        for connection_id in all_connections.copy():
            if await self._send_to_connection(connection_id, message):
                sent_count += 1

        logger.info(f"Message sent to user {user_id}: {sent_count}/{len(all_connections)} delivered")
        return sent_count

    async def broadcast_to_all(self, message: WSMessage, exclude_connections: list[str] | None = None) -> int:
        """Широковещательная отправка всем соединениям."""
        exclude_set = set(exclude_connections or [])
        all_connections = set(self.ws_connections.keys()) | set(self.sse_connections.keys())
        target_connections = all_connections - exclude_set

        sent_count = 0
        for connection_id in target_connections.copy():
            if await self._send_to_connection(connection_id, message):
                sent_count += 1

        logger.info(f"Broadcast to all: {sent_count}/{len(target_connections)} delivered")
        return sent_count

    # Heartbeat методы

    async def _websocket_heartbeat(self, connection_id: str) -> None:
        """Heartbeat для WebSocket соединения."""
        try:
            while connection_id in self.ws_connections:
                await asyncio.sleep(self.settings.WEBSOCKET_HEARTBEAT_INTERVAL)

                if connection_id not in self.ws_connections:
                    break

                heartbeat_message = WSMessage(
                    type=MessageType.HEARTBEAT,
                    data={"timestamp": datetime.utcnow().isoformat()},
                )

                success = await self.send_to_websocket(connection_id, heartbeat_message)
                if not success:
                    logger.warning(f"Heartbeat failed for WebSocket {connection_id}")
                    break

        except asyncio.CancelledError:
            logger.debug(f"WebSocket heartbeat cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket heartbeat error for {connection_id}: {e}")
            await self.disconnect_websocket(connection_id)

    async def _sse_heartbeat(self, connection_id: str) -> None:
        """Heartbeat для SSE соединения."""
        try:
            while connection_id in self.sse_connections:
                await asyncio.sleep(self.settings.SSE_HEARTBEAT_INTERVAL)

                if connection_id not in self.sse_connections:
                    break

                heartbeat_message = SSEMessage(
                    event="heartbeat",
                    data={"timestamp": datetime.utcnow().isoformat()},
                )

                success = await self.send_to_sse(connection_id, heartbeat_message)
                if not success:
                    logger.warning(f"Heartbeat failed for SSE {connection_id}")
                    break

        except asyncio.CancelledError:
            logger.debug(f"SSE heartbeat cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"SSE heartbeat error for {connection_id}: {e}")
            await self.disconnect_sse(connection_id)

    # Методы получения информации

    def get_connection_info(self, connection_id: str) -> WSConnectionInfo | None:
        """Получить информацию о соединении."""
        return self.ws_connection_info.get(connection_id) or self.sse_connection_info.get(connection_id)

    def get_connections_stats(self) -> dict[str, Any]:
        """Получить статистику соединений."""
        return {
            "websocket": {
                "total": len(self.ws_connections),
                "users": len(self.ws_user_connections),
                "channels": len(self.channel_subscriptions),
            },
            "sse": {
                "total": len(self.sse_connections),
                "users": len(self.sse_user_connections),
            },
            "limits": {
                "websocket_max": self.settings.WEBSOCKET_MAX_CONNECTIONS,
                "sse_max": self.settings.SSE_MAX_CONNECTIONS,
            },
            "heartbeat_tasks": len(self.heartbeat_tasks),
        }

    async def cleanup_inactive_connections(self) -> int:
        """Очистка неактивных соединений."""
        current_time = datetime.utcnow()
        inactive_connections = []

        # Проверяем WebSocket соединения
        for connection_id, info in self.ws_connection_info.items():
            if (current_time - info.last_activity).total_seconds() > self.settings.WEBSOCKET_TIMEOUT:
                inactive_connections.append(connection_id)

        # Проверяем SSE соединения
        for connection_id, info in self.sse_connection_info.items():
            if (current_time - info.last_activity).total_seconds() > self.settings.SSE_TIMEOUT:
                inactive_connections.append(connection_id)

        # Отключаем неактивные соединения
        for connection_id in inactive_connections:
            if connection_id in self.ws_connections:
                await self.disconnect_websocket(connection_id)
            elif connection_id in self.sse_connections:
                await self.disconnect_sse(connection_id)

        if inactive_connections:
            logger.info(f"Cleaned up {len(inactive_connections)} inactive connections")

        return len(inactive_connections)

    async def _send_to_connection(self, connection_id: str, message: WSMessage) -> bool:
        """Отправить сообщение в соединение (WebSocket или SSE).

        Args:
            connection_id: ID соединения
            message: Сообщение для отправки

        Returns:
            bool: True если отправлено успешно
        """
        # Попробуем WebSocket
        if connection_id in self.ws_connections:
            return await self.send_to_websocket(connection_id, message)

        # Попробуем SSE
        if connection_id in self.sse_connections:
            sse_message = SSEMessage(
                event="message",
                data=message.model_dump(),
            )
            return await self.send_to_sse(connection_id, sse_message)

        return False


# Глобальный экземпляр менеджера соединений
connection_manager = ConnectionManager()
