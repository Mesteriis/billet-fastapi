"""WebSocket клиент для подключения к серверу."""

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import websockets
from websockets.exceptions import ConnectionClosed

from .ws_models import MessageType, SSEConnectionStatus, WSCommand, WSMessage, WSResponse

if TYPE_CHECKING:
    from websockets.legacy.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class ReconnectPolicy(str, Enum):
    """Политика переподключения."""

    NEVER = "never"
    ALWAYS = "always"
    ON_ERROR = "on_error"


class WSClient:
    """WebSocket клиент с автоматическим переподключением."""

    def __init__(
        self,
        uri: str,
        token: str | None = None,
        api_key: str | None = None,
        user_id: str | None = None,
        auto_reconnect: bool = True,
        reconnect_policy: ReconnectPolicy = ReconnectPolicy.ALWAYS,
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = 10,
        ping_interval: int = 30,
        ping_timeout: int = 10,
    ):
        """
        Инициализация WebSocket клиента.

        Args:
            uri: URI для подключения (ws://localhost:8000/ws/connect)
            token: JWT токен для авторизации
            api_key: API ключ для авторизации
            user_id: ID пользователя
            auto_reconnect: Автоматическое переподключение
            reconnect_policy: Политика переподключения
            reconnect_interval: Интервал между попытками переподключения (сек)
            max_reconnect_attempts: Максимальное количество попыток переподключения
            ping_interval: Интервал ping сообщений (сек)
            ping_timeout: Таймаут ping сообщений (сек)
        """
        self.uri = uri
        self.token = token
        self.api_key = api_key
        self.user_id = user_id
        self.auto_reconnect = auto_reconnect
        self.reconnect_policy = reconnect_policy
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout

        # Состояние соединения
        self.websocket: Any = None
        self.status = SSEConnectionStatus.DISCONNECTED
        self.connection_id: str | None = None
        self.last_ping: datetime | None = None
        self.reconnect_attempts = 0
        self.is_closing = False

        # Подписки и обработчики
        self.subscribed_channels: set[str] = set()
        self.message_handlers: dict[str, list[Callable]] = {}
        self.command_responses: dict[str, asyncio.Future] = {}

        # Задачи
        self.receive_task: asyncio.Task | None = None
        self.ping_task: asyncio.Task | None = None
        self.reconnect_task: asyncio.Task | None = None

    def _build_uri(self) -> str:
        """Построение URI с параметрами."""
        params = []

        if self.token:
            params.append(f"token={self.token}")
        if self.api_key:
            params.append(f"api_key={self.api_key}")
        if self.user_id:
            params.append(f"user_id={self.user_id}")
        if self.subscribed_channels:
            channels = ",".join(self.subscribed_channels)
            params.append(f"channels={channels}")

        if params:
            return f"{self.uri}?{'&'.join(params)}"
        return self.uri

    async def connect(self) -> bool:
        """Подключение к WebSocket серверу."""
        if self.status == SSEConnectionStatus.CONNECTED:
            return True

        try:
            self.status = SSEConnectionStatus.CONNECTING
            self.is_closing = False

            uri = self._build_uri()
            logger.info(f"Connecting to WebSocket: {uri}")

            self.websocket = await websockets.connect(
                uri, ping_interval=self.ping_interval, ping_timeout=self.ping_timeout
            )

            self.status = SSEConnectionStatus.CONNECTED
            self.reconnect_attempts = 0

            # Запускаем задачи
            self.receive_task = asyncio.create_task(self._receive_loop())
            if self.ping_interval > 0:
                self.ping_task = asyncio.create_task(self._ping_loop())

            logger.info("WebSocket connected successfully")
            await self._call_handlers("connected", {"status": "connected"})

            return True

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            self.status = SSEConnectionStatus.ERROR
            await self._call_handlers("error", {"error": str(e), "type": "connection"})

            if self.auto_reconnect and not self.is_closing:
                await self._schedule_reconnect()

            return False

    async def disconnect(self):
        """Отключение от WebSocket сервера."""
        self.is_closing = True
        self.auto_reconnect = False

        # Отменяем задачи
        if self.receive_task:
            self.receive_task.cancel()
        if self.ping_task:
            self.ping_task.cancel()
        if self.reconnect_task:
            self.reconnect_task.cancel()

        # Закрываем соединение
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")

        self.status = SSEConnectionStatus.DISCONNECTED
        self.websocket = None
        self.connection_id = None

        await self._call_handlers("disconnected", {"status": "disconnected"})
        logger.info("WebSocket disconnected")

    async def send_message(self, content: Any, message_type: MessageType = MessageType.TEXT) -> str:
        """Отправка сообщения."""
        if not self.is_connected():
            raise ConnectionError("WebSocket не подключен")

        message = WSMessage(id=str(uuid.uuid4()), type=message_type, content=content)

        try:
            await self.websocket.send(json.dumps(message.dict()))
            return message.id
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    async def send_command(self, action: str, data: dict[str, Any] = None, timeout: int = 10) -> WSResponse:
        """Отправка команды с ожиданием ответа."""
        if not self.is_connected():
            raise ConnectionError("WebSocket не подключен")

        request_id = str(uuid.uuid4())
        command = WSCommand(action=action, data=data or {}, request_id=request_id)

        # Создаем Future для ответа
        response_future: asyncio.Future[dict[str, Any]] = asyncio.Future()
        self.command_responses[request_id] = response_future

        try:
            # Отправляем команду
            await self.websocket.send(json.dumps(command.dict()))

            # Ждем ответ
            response_data = await asyncio.wait_for(response_future, timeout=timeout)
            return WSResponse(**response_data)

        except TimeoutError:
            raise TimeoutError(f"Команда {action} не выполнена за {timeout} секунд")
        except Exception as e:
            logger.error(f"Error sending command {action}: {e}")
            raise
        finally:
            self.command_responses.pop(request_id, None)

    async def ping(self) -> bool:
        """Отправка ping команды."""
        try:
            response = await self.send_command("ping", timeout=5)
            self.last_ping = datetime.now(tz=utc)()
            return response.success
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False

    async def subscribe_to_channel(self, channel: str) -> bool:
        """Подписка на канал."""
        try:
            response = await self.send_command("subscribe", {"channel": channel})
            if response.success:
                self.subscribed_channels.add(channel)
            return response.success
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            return False

    async def unsubscribe_from_channel(self, channel: str) -> bool:
        """Отписка от канала."""
        try:
            response = await self.send_command("unsubscribe", {"channel": channel})
            if response.success:
                self.subscribed_channels.discard(channel)
            return response.success
        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel {channel}: {e}")
            return False

    async def send_to_channel(self, channel: str, content: Any) -> bool:
        """Отправка сообщения в канал."""
        try:
            response = await self.send_command("send_to_channel", {"channel": channel, "content": content})
            return response.success
        except Exception as e:
            logger.error(f"Failed to send message to channel {channel}: {e}")
            return False

    async def send_to_user(self, user_id: str, content: Any) -> bool:
        """Отправка сообщения пользователю."""
        try:
            response = await self.send_command("send_to_user", {"user_id": user_id, "content": content})
            return response.success
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            return False

    def on_message(self, message_type: str = "message"):
        """Декоратор для регистрации обработчика сообщений."""

        def decorator(func: Callable):
            self.add_message_handler(message_type, func)
            return func

        return decorator

    def add_message_handler(self, message_type: str, handler: Callable):
        """Добавление обработчика сообщений."""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)

    def remove_message_handler(self, message_type: str, handler: Callable):
        """Удаление обработчика сообщений."""
        if message_type in self.message_handlers:
            try:
                self.message_handlers[message_type].remove(handler)
            except ValueError:
                pass

    def is_connected(self) -> bool:
        """Проверка состояния соединения."""
        return self.status == SSEConnectionStatus.CONNECTED and self.websocket is not None

    def get_status(self) -> dict[str, Any]:
        """Получение статуса соединения."""
        return {
            "status": self.status.value,
            "connection_id": self.connection_id,
            "reconnect_attempts": self.reconnect_attempts,
            "subscribed_channels": list(self.subscribed_channels),
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "is_closing": self.is_closing,
        }

    async def _receive_loop(self):
        """Основной цикл получения сообщений."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            self.status = SSEConnectionStatus.DISCONNECTED

            if not self.is_closing and self.auto_reconnect:
                await self._schedule_reconnect()

        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            self.status = SSEConnectionStatus.ERROR

            if not self.is_closing and self.auto_reconnect:
                await self._schedule_reconnect()

    async def _handle_message(self, data: dict[str, Any]):
        """Обработка полученного сообщения."""
        try:
            # Проверяем, является ли сообщение ответом на команду
            if "request_id" in data.get("content", {}):
                request_id = data["content"]["request_id"]
                if request_id in self.command_responses:
                    future = self.command_responses[request_id]
                    if not future.done():
                        future.set_result(data["content"])
                    return

            # Извлекаем информацию о соединении из системных сообщений
            if data.get("type") == MessageType.SYSTEM.value:
                content = data.get("content", {})
                if "connection_id" in content:
                    self.connection_id = content["connection_id"]

            # Вызываем обработчики
            message_type = data.get("type", "message")
            await self._call_handlers(message_type, data)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _call_handlers(self, message_type: str, data: dict[str, Any]):
        """Вызов обработчиков сообщений."""
        handlers = self.message_handlers.get(message_type, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    async def _ping_loop(self):
        """Цикл отправки ping сообщений."""
        try:
            while self.is_connected():
                await asyncio.sleep(self.ping_interval)
                if self.is_connected():
                    await self.ping()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in ping loop: {e}")

    async def _schedule_reconnect(self):
        """Планирование переподключения."""
        if self.is_closing or self.reconnect_attempts >= self.max_reconnect_attempts:
            return

        if self.reconnect_policy == ReconnectPolicy.NEVER:
            return

        if self.reconnect_policy == ReconnectPolicy.ON_ERROR and self.status != SSEConnectionStatus.ERROR:
            return

        self.reconnect_attempts += 1
        delay = min(self.reconnect_interval * self.reconnect_attempts, 60)  # Максимум 60 секунд

        logger.info(f"Scheduling reconnect attempt {self.reconnect_attempts} in {delay} seconds")

        self.reconnect_task = asyncio.create_task(self._reconnect_after_delay(delay))

    async def _reconnect_after_delay(self, delay: int):
        """Переподключение после задержки."""
        try:
            await asyncio.sleep(delay)
            if not self.is_closing:
                await self.connect()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error during reconnect: {e}")


# Удобные функции для создания клиента


def create_ws_client(host: str = "localhost", port: int = 8000, use_ssl: bool = False, **kwargs) -> WSClient:
    """Создание WebSocket клиента с стандартными параметрами."""
    protocol = "wss" if use_ssl else "ws"
    uri = f"{protocol}://{host}:{port}/ws/connect"
    return WSClient(uri, **kwargs)


def create_authenticated_client(
    host: str = "localhost", port: int = 8000, token: str = None, api_key: str = None, use_ssl: bool = False, **kwargs
) -> WSClient:
    """Создание аутентифицированного WebSocket клиента."""
    return create_ws_client(host=host, port=port, use_ssl=use_ssl, token=token, api_key=api_key, **kwargs)
