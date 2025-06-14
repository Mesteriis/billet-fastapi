"""Менеджер соединений WebSocket и SSE."""

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import WebSocket

from core.config import get_settings
from core.realtime.models import (
    BroadcastMessage,
    ChannelMessage,
    ConnectionStatus,
    MessageType,
    NotificationMessage,
    SSEMessage,
    WSConnectionInfo,
    WSMessage,
)
from core.streaming.ws_models import SSEConnectionStatus

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
            status=ConnectionStatus.CONNECTED,
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

    async def disconnect_websocket(self, connection_id: str):
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

    async def connect_sse(self, connection_id: str, user_data: dict[str, Any]) -> asyncio.Queue:
        """Подключение SSE клиента."""
        # Проверяем лимит соединений
        if len(self.sse_connections) >= self.settings.SSE_MAX_CONNECTIONS:
            raise Exception("Превышен лимит SSE соединений")

        # Создаем очередь сообщений
        message_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=self.settings.WEBSOCKET_MESSAGE_QUEUE_SIZE)

        # Создаем информацию о соединении
        connection_info = WSConnectionInfo(
            connection_id=connection_id,
            user_id=user_data.get("user", {}).get("sub") if user_data.get("authenticated") else None,
            status=ConnectionStatus.CONNECTED,
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

    async def disconnect_sse(self, connection_id: str):
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

    async def subscribe_to_channel(self, connection_id: str, channel: str):
        """Подписка на канал."""
        self.channel_subscriptions[channel].add(connection_id)
        self.connection_channels[connection_id].add(channel)

        # Отправляем персистентные сообщения канала
        if channel in self.channel_messages:
            for message in self.channel_messages[channel]:
                if connection_id in self.ws_connections:
                    await self.send_to_websocket(connection_id, message)
                elif connection_id in self.sse_connections:
                    sse_message = SSEMessage(id=message.id, event="channel_message", data=message.dict())
                    await self.send_to_sse(connection_id, sse_message)

        logger.info(f"Connection {connection_id} subscribed to channel {channel}")

    async def unsubscribe_from_channel(self, connection_id: str, channel: str):
        """Отписка от канала."""
        self.channel_subscriptions[channel].discard(connection_id)
        self.connection_channels[connection_id].discard(channel)

        # Удаляем канал если нет подписчиков
        if not self.channel_subscriptions[channel]:
            del self.channel_subscriptions[channel]

        logger.info(f"Connection {connection_id} unsubscribed from channel {channel}")

    # Методы рассылки

    async def broadcast_to_channel(self, channel: str, message: WSMessage, persist: bool = False):
        """Рассылка сообщения в канал."""
        if persist:
            self.channel_messages[channel].append(message)
            # Ограничиваем количество персистентных сообщений
            if len(self.channel_messages[channel]) > 100:
                self.channel_messages[channel] = self.channel_messages[channel][-100:]

        subscribers = self.channel_subscriptions.get(channel, set()).copy()

        for connection_id in subscribers:
            if connection_id in self.ws_connections:
                await self.send_to_websocket(connection_id, message)
            elif connection_id in self.sse_connections:
                sse_message = SSEMessage(id=message.id, event="channel_message", data=message.dict())
                await self.send_to_sse(connection_id, sse_message)

        logger.info(f"Broadcasted message to channel {channel}, {len(subscribers)} recipients")

    async def send_to_user(self, user_id: str, message: WSMessage) -> int:
        """Отправка сообщения пользователю во все его соединения."""
        sent_count = 0

        # WebSocket соединения
        ws_connections = self.ws_user_connections.get(user_id, set()).copy()
        for connection_id in ws_connections:
            if await self.send_to_websocket(connection_id, message):
                sent_count += 1

        # SSE соединения
        sse_connections = self.sse_user_connections.get(user_id, set()).copy()
        for connection_id in sse_connections:
            sse_message = SSEMessage(id=message.id, event="user_message", data=message.dict())
            if await self.send_to_sse(connection_id, sse_message):
                sent_count += 1

        return sent_count

    async def broadcast_to_all(self, message: WSMessage, exclude_connections: list[str] = None):
        """Рассылка сообщения всем соединениям."""
        exclude_set = set(exclude_connections or [])

        # WebSocket соединения
        for connection_id in list(self.ws_connections.keys()):
            if connection_id not in exclude_set:
                await self.send_to_websocket(connection_id, message)

        # SSE соединения
        sse_message = SSEMessage(id=message.id, event="broadcast", data=message.dict())
        for connection_id in list(self.sse_connections.keys()):
            if connection_id not in exclude_set:
                await self.send_to_sse(connection_id, sse_message)

    # Heartbeat методы

    async def _websocket_heartbeat(self, connection_id: str):
        """Отправка heartbeat сообщений для WebSocket."""
        try:
            while connection_id in self.ws_connections:
                heartbeat = WSMessage(
                    id=str(uuid.uuid4()), type=MessageType.HEARTBEAT, content=HeartbeatMessage().dict()
                )

                if not await self.send_to_websocket(connection_id, heartbeat):
                    break

                await asyncio.sleep(self.settings.WEBSOCKET_HEARTBEAT_INTERVAL)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"WebSocket heartbeat error for {connection_id}: {e}")

    async def _sse_heartbeat(self, connection_id: str):
        """Отправка heartbeat сообщений для SSE."""
        try:
            while connection_id in self.sse_connections:
                heartbeat = SSEMessage(id=str(uuid.uuid4()), event="heartbeat", data=HeartbeatMessage().dict())

                if not await self.send_to_sse(connection_id, heartbeat):
                    break

                await asyncio.sleep(self.settings.SSE_HEARTBEAT_INTERVAL)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"SSE heartbeat error for {connection_id}: {e}")

    # Методы получения информации

    def get_connection_info(self, connection_id: str) -> WSConnectionInfo | None:
        """Получение информации о соединении."""
        return self.ws_connection_info.get(connection_id) or self.sse_connection_info.get(connection_id)

    def get_connections_stats(self) -> dict[str, Any]:
        """Получение статистики соединений."""
        return {
            "websocket": {
                "total": len(self.ws_connections),
                "max": self.settings.WEBSOCKET_MAX_CONNECTIONS,
                "users": len(self.ws_user_connections),
            },
            "sse": {
                "total": len(self.sse_connections),
                "max": self.settings.SSE_MAX_CONNECTIONS,
                "users": len(self.sse_user_connections),
            },
            "channels": {
                "total": len(self.channel_subscriptions),
                "subscriptions": sum(len(subs) for subs in self.channel_subscriptions.values()),
            },
            "total_connections": len(self.ws_connections) + len(self.sse_connections),
        }

    async def cleanup_inactive_connections(self):
        """Очистка неактивных соединений."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.settings.WEBSOCKET_DISCONNECT_TIMEOUT)

        # Проверяем WebSocket соединения
        inactive_ws = [conn_id for conn_id, info in self.ws_connection_info.items() if info.last_activity < cutoff_time]

        for conn_id in inactive_ws:
            logger.info(f"Cleaning up inactive WebSocket connection: {conn_id}")
            await self.disconnect_websocket(conn_id)

        # Проверяем SSE соединения
        inactive_sse = [
            conn_id for conn_id, info in self.sse_connection_info.items() if info.last_activity < cutoff_time
        ]

        for conn_id in inactive_sse:
            logger.info(f"Cleaning up inactive SSE connection: {conn_id}")
            await self.disconnect_sse(conn_id)


# Глобальный экземпляр менеджера соединений
connection_manager = ConnectionManager()
