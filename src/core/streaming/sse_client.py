"""SSE клиент для подключения к серверу."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import httpx
from httpx_sse import aconnect_sse

from .ws_models import SSEConnectionStatus

logger = logging.getLogger(__name__)


class SSEClient:
    """SSE клиент с автоматическим переподключением."""

    def __init__(
        self,
        uri: str,
        token: str | None = None,
        api_key: str | None = None,
        user_id: str | None = None,
        auto_reconnect: bool = True,
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = 10,
        timeout: int = 30,
        headers: dict[str, str] | None = None,
    ):
        """
        Инициализация SSE клиента.

        Args:
            uri: URI для подключения (http://localhost:8000/sse/connect)
            token: JWT токен для авторизации
            api_key: API ключ для авторизации
            user_id: ID пользователя
            auto_reconnect: Автоматическое переподключение
            reconnect_interval: Интервал между попытками переподключения (сек)
            max_reconnect_attempts: Максимальное количество попыток переподключения
            timeout: Таймаут соединения (сек)
            headers: Дополнительные заголовки
        """
        self.uri = uri
        self.token = token
        self.api_key = api_key
        self.user_id = user_id
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.timeout = timeout
        self.custom_headers = headers or {}

        # Состояние соединения
        self.status = SSEConnectionStatus.DISCONNECTED
        self.connection_id: str | None = None
        self.last_event_id: str | None = None
        self.reconnect_attempts = 0
        self.is_closing = False

        # Подписки и обработчики
        self.subscribed_channels: set[str] = set()
        self.event_handlers: dict[str, list[Callable]] = {}

        # HTTP клиент и задачи
        self.http_client: httpx.AsyncClient | None = None
        self.listen_task: asyncio.Task | None = None
        self.reconnect_task: asyncio.Task | None = None

    def _build_params(self) -> dict[str, str]:
        """Построение параметров запроса."""
        params = {}

        if self.token:
            params["token"] = self.token
        if self.api_key:
            params["api_key"] = self.api_key
        if self.user_id:
            params["user_id"] = self.user_id
        if self.subscribed_channels:
            params["channels"] = ",".join(self.subscribed_channels)
        if self.last_event_id:
            params["last_event_id"] = self.last_event_id

        return params

    def _build_headers(self) -> dict[str, str]:
        """Построение заголовков запроса."""
        headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache", **self.custom_headers}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.last_event_id:
            headers["Last-Event-ID"] = self.last_event_id

        return headers

    async def connect(self) -> bool:
        """Подключение к SSE серверу."""
        if self.status == SSEConnectionStatus.CONNECTED:
            return True

        try:
            self.status = SSEConnectionStatus.CONNECTING
            self.is_closing = False

            # Создаем HTTP клиент
            self.http_client = httpx.AsyncClient(timeout=self.timeout)

            # Запускаем задачу прослушивания
            self.listen_task = asyncio.create_task(self._listen_loop())

            logger.info(f"Connecting to SSE: {self.uri}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to SSE: {e}")
            self.status = SSEConnectionStatus.ERROR
            await self._call_handlers("error", {"error": str(e), "type": "connection"})

            if self.auto_reconnect and not self.is_closing:
                await self._schedule_reconnect()

            return False

    async def disconnect(self):
        """Отключение от SSE сервера."""
        self.is_closing = True
        self.auto_reconnect = False

        # Отменяем задачи
        if self.listen_task:
            self.listen_task.cancel()
        if self.reconnect_task:
            self.reconnect_task.cancel()

        # Закрываем HTTP клиент
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

        self.status = SSEConnectionStatus.DISCONNECTED
        self.connection_id = None

        await self._call_handlers("disconnected", {"status": "disconnected"})
        logger.info("SSE disconnected")

    async def send_to_channel(self, channel: str, event: str, data: dict[str, Any]) -> bool:
        """Отправка события в канал через HTTP API."""
        if not self.http_client:
            return False

        try:
            # Отправляем POST запрос к API
            base_url = self.uri.replace("/sse/connect", "")
            url = f"{base_url}/sse/send-to-channel"

            response = await self.http_client.post(
                url, params={"channel": channel, "event": event}, json=data, headers=self._build_headers()
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to send to channel {channel}: {e}")
            return False

    async def send_to_user(self, user_id: str, event: str, data: dict[str, Any]) -> bool:
        """Отправка события пользователю через HTTP API."""
        if not self.http_client:
            return False

        try:
            base_url = self.uri.replace("/sse/connect", "")
            url = f"{base_url}/sse/send-to-user/{user_id}"

            response = await self.http_client.post(
                url, params={"event": event}, json=data, headers=self._build_headers()
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to send to user {user_id}: {e}")
            return False

    async def broadcast(self, event: str, data: dict[str, Any]) -> bool:
        """Рассылка события всем подключенным клиентам."""
        if not self.http_client:
            return False

        try:
            base_url = self.uri.replace("/sse/connect", "")
            url = f"{base_url}/sse/broadcast"

            response = await self.http_client.post(
                url, params={"event": event}, json=data, headers=self._build_headers()
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to broadcast: {e}")
            return False

    async def send_notification(
        self,
        title: str,
        content: str,
        notification_type: str = "info",
        channel: str | None = None,
        user_id: str | None = None,
    ) -> bool:
        """Отправка уведомления."""
        if not self.http_client:
            return False

        try:
            base_url = self.uri.replace("/sse/connect", "")
            url = f"{base_url}/sse/notification"

            params = {}
            if channel:
                params["channel"] = channel
            if user_id:
                params["user_id"] = user_id

            notification_data = {"title": title, "content": content, "type": notification_type}

            response = await self.http_client.post(
                url, params=params, json=notification_data, headers=self._build_headers()
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def on_event(self, event_type: str = "message"):
        """Декоратор для регистрации обработчика событий."""

        def decorator(func: Callable):
            self.add_event_handler(event_type, func)
            return func

        return decorator

    def add_event_handler(self, event_type: str, handler: Callable):
        """Добавление обработчика событий."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def remove_event_handler(self, event_type: str, handler: Callable):
        """Удаление обработчика событий."""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass

    def is_connected(self) -> bool:
        """Проверка состояния соединения."""
        return self.status == SSEConnectionStatus.CONNECTED

    def get_status(self) -> dict[str, Any]:
        """Получение статуса соединения."""
        return {
            "status": self.status.value,
            "connection_id": self.connection_id,
            "reconnect_attempts": self.reconnect_attempts,
            "subscribed_channels": list(self.subscribed_channels),
            "last_event_id": self.last_event_id,
            "is_closing": self.is_closing,
        }

    async def _listen_loop(self):
        """Основной цикл прослушивания SSE событий."""
        try:
            params = self._build_params()
            headers = self._build_headers()

            async with aconnect_sse(self.http_client, "GET", self.uri, params=params, headers=headers) as event_source:
                self.status = SSEConnectionStatus.CONNECTED
                self.reconnect_attempts = 0

                logger.info("SSE connected successfully")
                await self._call_handlers("connected", {"status": "connected"})

                async for sse_event in event_source.aiter_sse():
                    try:
                        await self._handle_sse_event(sse_event)
                    except Exception as e:
                        logger.error(f"Error handling SSE event: {e}")

        except httpx.TimeoutException:
            logger.warning("SSE connection timeout")
            self.status = SSEConnectionStatus.ERROR

        except httpx.ConnectError as e:
            logger.error(f"SSE connection error: {e}")
            self.status = SSEConnectionStatus.ERROR

        except Exception as e:
            logger.error(f"Unexpected error in SSE listen loop: {e}")
            self.status = SSEConnectionStatus.ERROR

        finally:
            if self.status == SSEConnectionStatus.CONNECTED:
                self.status = SSEConnectionStatus.DISCONNECTED

            if not self.is_closing and self.auto_reconnect:
                await self._schedule_reconnect()

    async def _handle_sse_event(self, sse_event):
        """Обработка SSE события."""
        try:
            # Обновляем last_event_id
            if sse_event.id:
                self.last_event_id = sse_event.id

            # Парсим данные
            try:
                data = json.loads(sse_event.data)
            except json.JSONDecodeError:
                data = {"text": sse_event.data}

            # Извлекаем connection_id из события connected
            if sse_event.event == "connected" and isinstance(data, dict):
                if "connection_id" in data:
                    self.connection_id = data["connection_id"]

            # Подготавливаем событие для обработчиков
            event_data = {"id": sse_event.id, "event": sse_event.event, "data": data, "retry": sse_event.retry}

            # Вызываем обработчики
            await self._call_handlers(sse_event.event or "message", event_data)

        except Exception as e:
            logger.error(f"Error processing SSE event: {e}")

    async def _call_handlers(self, event_type: str, data: dict[str, Any]):
        """Вызов обработчиков событий."""
        handlers = self.event_handlers.get(event_type, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    async def _schedule_reconnect(self):
        """Планирование переподключения."""
        if self.is_closing or self.reconnect_attempts >= self.max_reconnect_attempts:
            return

        self.reconnect_attempts += 1
        delay = min(self.reconnect_interval * self.reconnect_attempts, 60)  # Максимум 60 секунд

        logger.info(f"Scheduling SSE reconnect attempt {self.reconnect_attempts} in {delay} seconds")

        self.reconnect_task = asyncio.create_task(self._reconnect_after_delay(delay))

    async def _reconnect_after_delay(self, delay: int):
        """Переподключение после задержки."""
        try:
            await asyncio.sleep(delay)
            if not self.is_closing:
                # Создаем новый HTTP клиент для переподключения
                if self.http_client:
                    await self.http_client.aclose()

                self.http_client = httpx.AsyncClient(timeout=self.timeout)
                self.listen_task = asyncio.create_task(self._listen_loop())

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error during SSE reconnect: {e}")


# Синхронный SSE клиент для простого использования


class SimpleSyncSSEClient:
    """Упрощенный синхронный SSE клиент."""

    def __init__(self, uri: str, token: str | None = None, api_key: str | None = None, timeout: int = 30):
        self.uri = uri
        self.token = token
        self.api_key = api_key
        self.timeout = timeout

    def _build_headers(self) -> dict[str, str]:
        """Построение заголовков запроса."""
        headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    def listen(self, on_event: Callable[[dict[str, Any]], None]):
        """Синхронное прослушивание SSE событий."""
        import httpx
        from httpx_sse import connect_sse

        headers = self._build_headers()

        with httpx.Client(timeout=self.timeout) as client:
            with connect_sse(client, "GET", self.uri, headers=headers) as event_source:
                for sse_event in event_source.iter_sse():
                    try:
                        # Парсим данные
                        try:
                            data = json.loads(sse_event.data)
                        except json.JSONDecodeError:
                            data = {"text": sse_event.data}

                        # Подготавливаем событие
                        event_data = {
                            "id": sse_event.id,
                            "event": sse_event.event,
                            "data": data,
                            "retry": sse_event.retry,
                        }

                        # Вызываем обработчик
                        on_event(event_data)

                    except Exception as e:
                        logger.error(f"Error handling sync SSE event: {e}")


# Удобные функции для создания клиентов


def create_sse_client(host: str = "localhost", port: int = 8000, use_ssl: bool = False, **kwargs) -> SSEClient:
    """Создание SSE клиента с стандартными параметрами."""
    protocol = "https" if use_ssl else "http"
    uri = f"{protocol}://{host}:{port}/sse/connect"
    return SSEClient(uri, **kwargs)


def create_authenticated_sse_client(
    host: str = "localhost", port: int = 8000, token: str = None, api_key: str = None, use_ssl: bool = False, **kwargs
) -> SSEClient:
    """Создание аутентифицированного SSE клиента."""
    return create_sse_client(host=host, port=port, use_ssl=use_ssl, token=token, api_key=api_key, **kwargs)


def create_simple_sse_client(
    host: str = "localhost", port: int = 8000, use_ssl: bool = False, **kwargs
) -> SimpleSyncSSEClient:
    """Создание простого синхронного SSE клиента."""
    protocol = "https" if use_ssl else "http"
    uri = f"{protocol}://{host}:{port}/sse/connect"
    return SimpleSyncSSEClient(uri, **kwargs)
