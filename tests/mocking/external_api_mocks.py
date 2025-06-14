"""
Моки для внешних API и сервисов.
"""

import json
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import respx


class ExternalAPIMocker:
    """Класс для мокирования внешних API."""

    def __init__(self):
        self.mocked_endpoints = {}
        self.call_history = []

    @contextmanager
    def mock_httpx_client(self):
        """Контекстный менеджер для мокирования httpx клиента."""
        with respx.mock:
            yield self

    def add_endpoint(
        self,
        method: str,
        url: str,
        response_data: Dict[str, Any] = None,
        status_code: int = 200,
        headers: Dict[str, str] = None,
        delay: float = 0.0,
    ):
        """Добавляет мокированный endpoint."""
        if response_data is None:
            response_data = {"status": "success"}

        if headers is None:
            headers = {"Content-Type": "application/json"}

        def mock_response(request):
            # Записываем историю вызовов
            self.call_history.append(
                {
                    "method": method,
                    "url": str(request.url),
                    "headers": dict(request.headers),
                    "content": request.content.decode() if request.content else None,
                    "timestamp": time.time(),
                }
            )

            # Эмулируем задержку
            if delay > 0:
                time.sleep(delay)

            return httpx.Response(status_code=status_code, json=response_data, headers=headers)

        route = respx.route(method=method, url=url)
        route.side_effect = mock_response

        self.mocked_endpoints[f"{method}:{url}"] = {
            "response_data": response_data,
            "status_code": status_code,
            "headers": headers,
            "delay": delay,
        }

    def get_call_history(self, method: str = None, url: str = None) -> List[Dict[str, Any]]:
        """Получает историю вызовов API."""
        history = self.call_history

        if method:
            history = [call for call in history if call["method"].upper() == method.upper()]

        if url:
            history = [call for call in history if url in call["url"]]

        return history

    def clear_history(self):
        """Очищает историю вызовов."""
        self.call_history.clear()

    def assert_called(self, method: str, url: str, times: int = None):
        """Проверяет что API был вызван."""
        calls = self.get_call_history(method, url)

        if times is not None:
            assert len(calls) == times, f"Expected {times} calls, but got {len(calls)}"
        else:
            assert len(calls) > 0, f"Expected API call to {method} {url}, but none found"

    def assert_not_called(self, method: str, url: str):
        """Проверяет что API НЕ был вызван."""
        calls = self.get_call_history(method, url)
        assert len(calls) == 0, f"Expected no calls to {method} {url}, but found {len(calls)}"


class DatabaseMocker:
    """Мокер для базы данных."""

    def __init__(self):
        self.data = {}
        self.query_history = []

    def add_table_data(self, table_name: str, data: List[Dict[str, Any]]):
        """Добавляет данные для таблицы."""
        self.data[table_name] = data

    def mock_query_result(self, query: str, result: Any):
        """Мокирует результат SQL запроса."""
        # Простая реализация для демонстрации
        pass

    @contextmanager
    def mock_database_session(self):
        """Мокирует сессию базы данных."""
        mock_session = AsyncMock()

        # Мокируем основные методы
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        with patch("core.database.get_db", return_value=mock_session):
            yield mock_session


class NotificationServiceMocker:
    """Мокер для сервиса уведомлений."""

    def __init__(self):
        self.sent_notifications = []
        self.should_fail = False
        self.failure_reason = "Service unavailable"

    def mock_send_email(self, to: str, subject: str, body: str) -> bool:
        """Мокирует отправку email."""
        if self.should_fail:
            raise Exception(self.failure_reason)

        self.sent_notifications.append(
            {"type": "email", "to": to, "subject": subject, "body": body, "timestamp": time.time()}
        )
        return True

    def mock_send_sms(self, phone: str, message: str) -> bool:
        """Мокирует отправку SMS."""
        if self.should_fail:
            raise Exception(self.failure_reason)

        self.sent_notifications.append({"type": "sms", "phone": phone, "message": message, "timestamp": time.time()})
        return True

    def mock_send_push(self, user_id: str, title: str, body: str) -> bool:
        """Мокирует отправку push уведомления."""
        if self.should_fail:
            raise Exception(self.failure_reason)

        self.sent_notifications.append(
            {"type": "push", "user_id": user_id, "title": title, "body": body, "timestamp": time.time()}
        )
        return True

    def set_failure_mode(self, should_fail: bool, reason: str = "Service unavailable"):
        """Устанавливает режим сбоя."""
        self.should_fail = should_fail
        self.failure_reason = reason

    def get_sent_notifications(self, notification_type: str = None) -> List[Dict[str, Any]]:
        """Получает отправленные уведомления."""
        if notification_type:
            return [n for n in self.sent_notifications if n["type"] == notification_type]
        return self.sent_notifications.copy()

    def clear_notifications(self):
        """Очищает историю уведомлений."""
        self.sent_notifications.clear()


class PaymentServiceMocker:
    """Мокер для платежного сервиса."""

    def __init__(self):
        self.transactions = []
        self.should_fail = False
        self.failure_reason = "Payment declined"

    def mock_charge(self, amount: float, currency: str = "USD", **kwargs) -> Dict[str, Any]:
        """Мокирует платеж."""
        transaction_id = f"txn_{int(time.time())}"

        if self.should_fail:
            result = {
                "id": transaction_id,
                "status": "failed",
                "amount": amount,
                "currency": currency,
                "error": self.failure_reason,
                "timestamp": time.time(),
            }
        else:
            result = {
                "id": transaction_id,
                "status": "succeeded",
                "amount": amount,
                "currency": currency,
                "timestamp": time.time(),
            }

        self.transactions.append(result)
        return result

    def mock_refund(self, transaction_id: str, amount: float = None) -> Dict[str, Any]:
        """Мокирует возврат."""
        # Находим оригинальную транзакцию
        original = next((t for t in self.transactions if t["id"] == transaction_id), None)

        if not original:
            raise ValueError(f"Transaction {transaction_id} not found")

        refund_amount = amount or original["amount"]
        refund_id = f"ref_{int(time.time())}"

        result = {
            "id": refund_id,
            "original_transaction": transaction_id,
            "status": "succeeded",
            "amount": refund_amount,
            "currency": original["currency"],
            "timestamp": time.time(),
        }

        self.transactions.append(result)
        return result

    def set_failure_mode(self, should_fail: bool, reason: str = "Payment declined"):
        """Устанавливает режим сбоя."""
        self.should_fail = should_fail
        self.failure_reason = reason

    def get_transactions(self) -> List[Dict[str, Any]]:
        """Получает все транзакции."""
        return self.transactions.copy()

    def clear_transactions(self):
        """Очищает историю транзакций."""
        self.transactions.clear()


# Удобные функции для использования в тестах
@contextmanager
def mock_external_service(base_url: str, endpoints: List[Dict[str, Any]]):
    """
    Мокирует внешний сервис.

    endpoints: список словарей с ключами method, path, response, status_code
    """
    mocker = ExternalAPIMocker()

    with mocker.mock_httpx_client():
        for endpoint in endpoints:
            url = f"{base_url.rstrip('/')}/{endpoint['path'].lstrip('/')}"
            mocker.add_endpoint(
                method=endpoint.get("method", "GET"),
                url=url,
                response_data=endpoint.get("response", {}),
                status_code=endpoint.get("status_code", 200),
                headers=endpoint.get("headers"),
                delay=endpoint.get("delay", 0.0),
            )

        yield mocker


@contextmanager
def mock_notification_service():
    """Мокирует сервис уведомлений."""
    mocker = NotificationServiceMocker()

    with (
        patch("core.notifications.send_email", side_effect=mocker.mock_send_email),
        patch("core.notifications.send_sms", side_effect=mocker.mock_send_sms),
        patch("core.notifications.send_push", side_effect=mocker.mock_send_push),
    ):
        yield mocker


@contextmanager
def mock_payment_service():
    """Мокирует платежный сервис."""
    mocker = PaymentServiceMocker()

    with (
        patch("core.payments.charge", side_effect=mocker.mock_charge),
        patch("core.payments.refund", side_effect=mocker.mock_refund),
    ):
        yield mocker


# Предустановленные сценарии
COMMON_API_RESPONSES = {
    "success": {"status": "success", "data": {}},
    "error": {"status": "error", "message": "Something went wrong"},
    "not_found": {"status": "error", "message": "Resource not found"},
    "validation_error": {
        "status": "error",
        "message": "Validation failed",
        "errors": [{"field": "email", "message": "Invalid email format"}],
    },
    "rate_limit": {"status": "error", "message": "Rate limit exceeded"},
    "server_error": {"status": "error", "message": "Internal server error"},
}


def get_api_response(response_type: str) -> Dict[str, Any]:
    """Получает предустановленный ответ API."""
    if response_type not in COMMON_API_RESPONSES:
        raise ValueError(f"Unknown response type: {response_type}")

    return COMMON_API_RESPONSES[response_type].copy()
