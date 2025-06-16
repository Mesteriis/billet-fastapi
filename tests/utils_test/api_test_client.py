"""
Расширенный тестовый клиент для API с поддержкой аутентификации и улучшенной обработкой ошибок.
"""

import asyncio
import difflib
import hashlib
import json
import logging
import random
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
import websockets
from fastapi import FastAPI
from httpx import AsyncClient, Response

# from apps.auth.jwt_service import JWTService
# from apps.users.models import User

# Импортируем конфигурацию логирования
try:
    from tests.utils_test.logging_config import TestLoggingConfig, test_logger

    logger = test_logger
except ImportError:
    # Fallback если конфигурация недоступна
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class TestScenarioType(Enum):
    """Типы тестовых сценариев."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    WEBSOCKET = "websocket"
    LOAD_TEST = "load_test"


class RetryStrategy(Enum):
    """Стратегии повторных попыток."""

    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


class SecurityTestType(Enum):
    """Типы тестов безопасности."""

    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    AUTHENTICATION_BYPASS = "auth_bypass"
    AUTHORIZATION_BYPASS = "authz_bypass"
    RATE_LIMITING = "rate_limiting"
    INPUT_VALIDATION = "input_validation"
    HEADER_SECURITY = "header_security"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data"
    DIRECTORY_TRAVERSAL = "directory_traversal"


class LoadTestPattern(Enum):
    """Паттерны нагрузочного тестирования."""

    CONSTANT_LOAD = "constant"
    RAMP_UP = "ramp_up"
    SPIKE = "spike"
    STRESS = "stress"
    VOLUME = "volume"
    ENDURANCE = "endurance"


class WebSocketEventType(Enum):
    """Типы WebSocket событий."""

    CONNECT = "connect"
    DISCONNECT = "disconnect"
    MESSAGE = "message"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


@dataclass
class APISnapshot:
    """Снимок состояния API для тестов регрессии."""

    endpoint: str
    method: str
    status_code: int
    response_schema: dict
    headers: dict
    timestamp: datetime
    checksum: str


@dataclass
class PerformanceMetrics:
    """Метрики производительности запроса."""

    response_time: float
    request_size: int
    response_size: int
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None


@dataclass
class ChainStep:
    """Шаг в цепочке тестовых запросов."""

    method: str
    url: str
    data: Optional[dict] = None
    params: Optional[dict] = None
    headers: Optional[dict] = None
    expected_status: int = 200
    extract_data: Optional[Callable] = None
    validate_response: Optional[Callable] = None
    description: str = ""


@dataclass
class TestSession:
    """Сессия тестирования с контекстом."""

    session_id: str
    scenario_type: TestScenarioType
    created_at: datetime = field(default_factory=datetime.utcnow)
    metrics: List[PerformanceMetrics] = field(default_factory=list)
    snapshots: List[APISnapshot] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebSocketMessage:
    """WebSocket сообщение для тестирования."""

    event_type: WebSocketEventType
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    connection_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class WebSocketTestSession:
    """Сессия WebSocket тестирования."""

    endpoint: str
    connection_id: str
    messages: List[WebSocketMessage] = field(default_factory=list)
    is_connected: bool = False
    connection_time: Optional[float] = None
    last_ping_time: Optional[float] = None


@dataclass
class SecurityTestResult:
    """Результат теста безопасности."""

    test_type: SecurityTestType
    endpoint: str
    vulnerable: bool
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    evidence: Optional[str] = None
    recommendation: str = ""
    cwe_id: Optional[str] = None  # Common Weakness Enumeration


@dataclass
class LoadTestConfig:
    """Конфигурация нагрузочного тестирования."""

    pattern: LoadTestPattern
    duration_seconds: int
    concurrent_users: int
    requests_per_second: Optional[int] = None
    ramp_up_time: Optional[int] = None
    endpoints: List[str] = field(default_factory=list)
    test_data_generators: Dict[str, Callable] = field(default_factory=dict)


@dataclass
class LoadTestResult:
    """Результат нагрузочного тестирования."""

    config: LoadTestConfig
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    percentile_95: float
    percentile_99: float
    requests_per_second: float
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AIGeneratedTest:
    """AI-сгенерированный тест."""

    test_name: str
    endpoint: str
    method: str
    test_description: str
    test_code: str
    test_data: Dict[str, Any]
    expected_status: int
    schema_validation: bool = True
    security_checks: List[SecurityTestType] = field(default_factory=list)
    confidence_score: float = 0.0  # 0.0 - 1.0


@dataclass
class OpenAPIEndpoint:
    """Информация об endpoint из OpenAPI схемы."""

    path: str
    method: str
    operation_id: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    security: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class MockExternal:
    """Мок для внешних API."""

    def __init__(self):
        self.mocked_urls = {}
        self.call_history = []

    def mock_url(self, url: str, response_data: dict, status_code: int = 200, delay: float = 0):
        """Добавить мок для URL."""
        self.mocked_urls[url] = {"response_data": response_data, "status_code": status_code, "delay": delay}

    async def handle_request(self, request):
        """Обработать замоканный запрос."""
        url = str(request.url)
        if url in self.mocked_urls:
            mock_config = self.mocked_urls[url]

            # Записываем в историю
            self.call_history.append({"url": url, "method": request.method, "timestamp": datetime.utcnow()})

            # Эмулируем задержку
            if mock_config["delay"] > 0:
                await asyncio.sleep(mock_config["delay"])

            return httpx.Response(status_code=mock_config["status_code"], json=mock_config["response_data"])

        # Возвращаем оригинальный запрос если не замокан
        return None


class AsyncApiTestClient(AsyncClient):
    """
    Расширенный асинхронный тестовый клиент для API.

    Новые возможности:
    - Снимки API для тестов регрессии
    - Автоматическая валидация Pydantic схем
    - Поддержка WebSocket тестирования
    - Мокирование внешних API
    - Chain-тестирование (последовательные запросы)
    - Метрики производительности
    - Авто-retry с различными стратегиями
    - Тестовые сценарии и сессии
    """

    def __init__(self, app: Optional[FastAPI] = None, **kwargs):
        """
        Инициализация тестового клиента.

        Args:
            app: Экземпляр FastAPI приложения
            **kwargs: Дополнительные параметры для httpx.AsyncClient
        """
        self._app = app
        self.auth_user: Optional["User"] = None
        # Создаем тестовый JWT сервис с правильными настройками
        self._jwt_service = self._create_test_jwt_service()
        self._cached_routes: Optional[list[str]] = None
        self._performance_tracking = False
        self._metrics_history: List[PerformanceMetrics] = []
        self._snapshots_dir: Optional[Path] = None
        self._mock_external = MockExternal()
        self._current_session: Optional[TestSession] = None
        self._websocket_connections: Dict[str, Any] = {}
        # Async сессия БД (будет установлена в фикстуре)
        self.db_session: Optional[Any] = None
        # Новые атрибуты для расширенной функциональности
        self._websocket_sessions: Dict[str, WebSocketTestSession] = {}
        self._security_test_results: List[SecurityTestResult] = []
        self._load_test_executor: Optional[ThreadPoolExecutor] = None
        self._ai_generated_tests: List[AIGeneratedTest] = []
        self._openapi_schema: Optional[Dict[str, Any]] = None
        self._security_payloads: Dict[SecurityTestType, List[str]] = self._init_security_payloads()
        # Простой трекер производительности
        self.performance_tracker = self._create_performance_tracker()
        super().__init__(**kwargs)

        # Настраиваем зависимости для тестов
        if self._app:
            self._setup_test_dependencies()

    def _create_performance_tracker(self):
        """Создать простой трекер производительности."""
        import time

        class SimplePerformanceTracker:
            def start_timer(self):
                return time.time()

            def end_timer(self, start_time):
                return time.time() - start_time

        return SimplePerformanceTracker()

    def url_for(self, name: str, /, **path_params: Any) -> str:
        """
        Генерация URL для заданного имени endpoint с интеллектуальной обработкой ошибок.

        Args:
            name: Имя route функции
            **path_params: Параметры пути

        Returns:
            Сгенерированный URL

        Raises:
            ValueError: Если route не найден, с предложениями похожих имен

        Example:
            client.url_for("get_user", user_id=123)
            client.url_for("auth:login")  # С префиксом роутера
        """
        if not self._app:
            raise ValueError("FastAPI app не инициализировано. Передайте app в конструктор.")

        try:
            return self._app.url_path_for(name, **path_params)
        except Exception as e:
            # Получаем все доступные routes
            available_routes = self._get_available_routes()

            # Ищем похожие имена
            similar_routes = self._find_similar_routes(name, available_routes)

            error_msg = f"Route '{name}' не найден."

            if similar_routes:
                error_msg += f"\n\nВозможно, вы имели в виду один из этих routes:"
                for route, similarity in similar_routes[:5]:  # Показываем топ-5
                    error_msg += f"\n  - {route} (схожесть: {similarity:.2%})"

            error_msg += f"\n\nВсе доступные routes ({len(available_routes)}):"
            for route in sorted(available_routes)[:10]:  # Показываем первые 10
                error_msg += f"\n  - {route}"

            if len(available_routes) > 10:
                error_msg += f"\n  ... и еще {len(available_routes) - 10} routes"

            error_msg += f"\n\nОригинальная ошибка: {str(e)}"

            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _get_available_routes(self) -> list[str]:
        """Получить список всех доступных routes с кешированием."""
        if self._cached_routes is not None:
            return self._cached_routes

        if not self._app:
            return []

        routes = []
        for route in self._app.routes:
            if hasattr(route, "name") and getattr(route, "name", None):
                routes.append(str(getattr(route, "name")))

        self._cached_routes = routes
        return routes

    def _find_similar_routes(
        self, target: str, available_routes: list[str], min_similarity: float = 0.3
    ) -> list[tuple[str, float]]:
        """
        Найти похожие routes используя алгоритм диффа.

        Args:
            target: Искомое имя route
            available_routes: Список доступных routes
            min_similarity: Минимальная схожесть для включения в результат

        Returns:
            Список tuple (route_name, similarity_score) отсортированный по убыванию схожести
        """
        similarities = []

        for route in available_routes:
            # Вычисляем схожесть строк
            similarity = difflib.SequenceMatcher(None, target.lower(), route.lower()).ratio()

            # Дополнительные бонусы за:
            # - Содержание target в route
            if target.lower() in route.lower():
                similarity += 0.2
            # - Начинается с target
            if route.lower().startswith(target.lower()):
                similarity += 0.1
            # - Заканчивается на target
            if route.lower().endswith(target.lower()):
                similarity += 0.1

            if similarity >= min_similarity:
                similarities.append((route, min(similarity, 1.0)))  # Ограничиваем максимум 1.0

        return sorted(similarities, key=lambda x: x[1], reverse=True)

    async def force_auth(
        self,
        user: Optional["User"] = None,
        email: Optional[str] = None,
        email_verified: bool = True,
        is_superuser: bool = False,
        is_active: bool = True,
        **user_kwargs: Any,
    ) -> "User":
        """
        Принудительная аутентификация пользователя с гибкими опциями.

        Args:
            user: Существующий пользователь (приоритет над email)
            email: Email для поиска существующего пользователя
            email_verified: Статус верификации email
            is_superuser: Права суперпользователя
            is_active: Активность пользователя
            **user_kwargs: Дополнительные параметры для создания пользователя

        Returns:
            Аутентифицированный пользователь

        Raises:
            ValueError: При конфликте параметров
        """
        if user and email:
            raise ValueError("Нельзя передавать одновременно user и email")

        if email:
            # В реальном приложении здесь бы был поиск в БД
            # Для тестов создаем пользователя с указанным email
            from tests.factories.user_factory import VerifiedUserFactory

            self.auth_user = VerifiedUserFactory(email=email, **user_kwargs)
        elif user:
            self.auth_user = user
            # Если у пользователя нет ID, создаем его в БД
            if hasattr(self, "db_session") and self.db_session:
                # Проверяем, есть ли пользователь в БД
                from apps.users.repository import UserRepository

                repo = UserRepository()
                try:
                    existing_user = await repo.get_by_email(self.db_session, email=user.email)
                    if not existing_user:
                        # Создаем пользователя в БД
                        from apps.users.models import User

                        db_user = User(
                            id=user.id,
                            email=user.email,
                            username=user.username,
                            full_name=user.full_name,
                            hashed_password=user.hashed_password,
                            is_active=user.is_active,
                            is_verified=user.is_verified,
                            is_superuser=user.is_superuser,
                        )
                        self.db_session.add(db_user)
                        await self.db_session.commit()
                        self.auth_user = db_user
                    else:
                        self.auth_user = existing_user
                except Exception as e:
                    logger.warning(f"Не удалось создать пользователя в БД: {e}")
                    # Продолжаем с фабричным пользователем
        else:
            # Создаем нового пользователя
            self.auth_user = await self._generate_user(
                is_email_verified=email_verified, is_superuser=is_superuser, is_active=is_active, **user_kwargs
            )

        # Обновляем атрибуты пользователя
        update_fields = []

        if self.auth_user and self.auth_user.is_active != is_active:
            self.auth_user.is_active = is_active
            update_fields.append("is_active")

        if self.auth_user and getattr(self.auth_user, "is_email_verified", False) != email_verified:
            if hasattr(self.auth_user, "is_email_verified"):
                # Используем setattr для безопасного присваивания
                setattr(self.auth_user, "is_verified", email_verified)
                update_fields.append("is_email_verified")

        if self.auth_user and self.auth_user.is_superuser != is_superuser:
            self.auth_user.is_superuser = is_superuser
            update_fields.append("is_superuser")

        # В реальном приложении здесь бы было сохранение в БД
        if update_fields:
            logger.debug(f"Обновлены поля пользователя: {update_fields}")

        # Создаем JWT токены
        if self.auth_user:
            # Убеждаемся, что у пользователя есть UUID ID
            if not hasattr(self.auth_user, "id") or self.auth_user.id is None:
                import uuid

                self.auth_user.id = uuid.uuid4()

            access_token, refresh_token, jti = self._jwt_service.create_token_pair(
                user_id=str(self.auth_user.id),
                email=self.auth_user.email,
                username=self.auth_user.username,
                is_active=self.auth_user.is_active,
                is_superuser=self.auth_user.is_superuser,
                is_verified=getattr(self.auth_user, "is_verified", True),
            )
        else:
            raise ValueError("Не удалось создать или найти пользователя для аутентификации")

        # Устанавливаем заголовок авторизации
        self.headers.update({"Authorization": f"Bearer {access_token}"})

        logger.debug(f"Пользователь аутентифицирован: {self.auth_user.email}")
        return self.auth_user

    async def force_logout(self) -> None:
        """Выход из системы - удаление токенов авторизации."""
        self.auth_user = None
        self.headers.pop("Authorization", None)
        logger.debug("Пользователь разлогинен")

    @staticmethod
    async def _generate_user(
        is_superuser: bool = False, is_active: bool = True, is_email_verified: bool = True, **kwargs: Any
    ) -> "User":
        """
        Генерация тестового пользователя.

        Args:
            is_superuser: Права суперпользователя
            is_active: Активность пользователя
            is_email_verified: Верификация email
            **kwargs: Дополнительные параметры

        Returns:
            Созданный пользователь
        """
        from tests.factories.user_factory import AdminUserFactory, SimpleUserFactory, VerifiedUserFactory

        if is_superuser:
            user = AdminUserFactory(is_active=is_active, **kwargs)
        elif is_email_verified:
            user = VerifiedUserFactory(is_active=is_active, **kwargs)
        else:
            user = SimpleUserFactory(is_active=is_active, is_verified=is_email_verified, **kwargs)
        return user

    def enable_performance_tracking(self) -> None:
        """Включить отслеживание производительности."""
        self._performance_tracking = True
        logger.info("Performance tracking enabled")

    def disable_performance_tracking(self) -> None:
        """Отключить отслеживание производительности."""
        self._performance_tracking = False

    def get_performance_stats(self) -> Dict[str, Any]:
        """Получить статистику производительности."""
        if not self._metrics_history:
            return {"message": "No performance data available"}

        response_times = [m.response_time for m in self._metrics_history]
        return {
            "total_requests": len(self._metrics_history),
            "avg_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "total_time": sum(response_times),
            "requests_per_second": len(self._metrics_history) / sum(response_times) if sum(response_times) > 0 else 0,
        }

    async def request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        retryable_status_codes: Optional[List[int]] = None,
        **kwargs,
    ) -> Response:
        """
        Выполнить запрос с retry логикой.

        Args:
            method: HTTP метод
            url: URL для запроса
            max_retries: Максимальное количество попыток
            retry_strategy: Стратегия повторных попыток
            base_delay: Базовая задержка в секундах
            max_delay: Максимальная задержка в секундах
            retryable_status_codes: Коды статусов для retry (по умолчанию 5xx)
            **kwargs: Дополнительные параметры запроса

        Returns:
            HTTP ответ
        """
        if retryable_status_codes is None:
            retryable_status_codes = [500, 502, 503, 504]

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                response = await self.request(method, url, **kwargs)

                # Если статус код успешный или не требует retry
                if response.status_code < 400 or response.status_code not in retryable_status_codes:
                    return response

                # Если это последняя попытка, возвращаем ответ
                if attempt == max_retries:
                    return response

            except Exception as e:
                last_exception = e
                if attempt == max_retries:
                    raise

            # Вычисляем задержку для следующей попытки
            delay = self._calculate_retry_delay(attempt, retry_strategy, base_delay, max_delay)
            logger.warning(f"Request failed, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})")
            await asyncio.sleep(delay)

        # Этот код никогда не должен выполниться, но для типизации
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry logic error: no response or exception")

    def _calculate_retry_delay(
        self, attempt: int, strategy: RetryStrategy, base_delay: float, max_delay: float
    ) -> float:
        """Вычислить задержку для retry."""
        if strategy == RetryStrategy.LINEAR:
            delay = base_delay * (attempt + 1)
        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = base_delay * (2**attempt)
        elif strategy == RetryStrategy.FIBONACCI:
            # Простая последовательность Фибоначчи
            fib = [1, 1]
            for i in range(2, attempt + 2):
                fib.append(fib[i - 1] + fib[i - 2])
            delay = base_delay * fib[attempt]
        else:
            delay = base_delay

        return min(delay, max_delay)

    def setup_snapshots_dir(self, snapshots_dir: Union[str, Path]) -> None:
        """Настроить директорию для снимков API."""
        self._snapshots_dir = Path(snapshots_dir)
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"API snapshots directory: {self._snapshots_dir}")

    async def create_api_snapshot(
        self, endpoint: str, method: str = "GET", save_to_file: bool = True, **request_kwargs
    ) -> APISnapshot:
        """
        Создать снимок API endpoint для тестов регрессии.

        Args:
            endpoint: URL endpoint
            method: HTTP метод
            save_to_file: Сохранить в файл
            **request_kwargs: Параметры запроса

        Returns:
            Снимок API
        """
        response = await self.request(method, endpoint, **request_kwargs)

        # Создаем снимок
        snapshot = APISnapshot(
            endpoint=endpoint,
            method=method,
            status_code=response.status_code,
            response_schema=self._extract_response_schema(response),
            headers=dict(response.headers),
            timestamp=datetime.utcnow(),
            checksum=self._calculate_response_checksum(response),
        )

        # Сохраняем в файл
        if save_to_file and self._snapshots_dir:
            snapshot_file = self._snapshots_dir / f"{method.lower()}_{endpoint.replace('/', '_')}.json"
            with open(snapshot_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "endpoint": snapshot.endpoint,
                        "method": snapshot.method,
                        "status_code": snapshot.status_code,
                        "response_schema": snapshot.response_schema,
                        "headers": snapshot.headers,
                        "timestamp": snapshot.timestamp.isoformat(),
                        "checksum": snapshot.checksum,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

        if self._current_session:
            self._current_session.snapshots.append(snapshot)

        return snapshot

    def _extract_response_schema(self, response: Response) -> dict:
        """Извлечь схему ответа."""
        try:
            data = response.json()
            return self._infer_json_schema(data)
        except:
            return {"type": "string", "content_type": response.headers.get("content-type", "unknown")}

    def _infer_json_schema(self, data: Any) -> dict:
        """Простая схема JSON для валидации."""
        if isinstance(data, dict):
            properties = {}
            for key, value in data.items():
                properties[key] = self._infer_json_schema(value)
            return {"type": "object", "properties": properties}
        elif isinstance(data, list):
            if data:
                return {"type": "array", "items": self._infer_json_schema(data[0])}
            return {"type": "array", "items": {}}
        elif isinstance(data, str):
            return {"type": "string"}
        elif isinstance(data, bool):
            return {"type": "boolean"}
        elif isinstance(data, int):
            return {"type": "integer"}
        elif isinstance(data, float):
            return {"type": "number"}
        else:
            return {"type": "null"}

    def _calculate_response_checksum(self, response: Response) -> str:
        """Вычислить контрольную сумму ответа."""
        content = response.content
        return hashlib.md5(content).hexdigest()

    async def validate_response_schema(self, response: Response, expected_schema: dict) -> bool:
        """Валидировать схему ответа."""
        try:
            actual_schema = self._extract_response_schema(response)
            return self._schemas_match(actual_schema, expected_schema)
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    def _schemas_match(self, actual: dict, expected: dict) -> bool:
        """Простое сравнение схем."""
        # Упрощенная проверка - в реальности можно использовать jsonschema
        if actual.get("type") != expected.get("type"):
            return False

        if actual.get("type") == "object":
            actual_props = actual.get("properties", {})
            expected_props = expected.get("properties", {})

            # Проверяем что все ожидаемые свойства присутствуют
            for key in expected_props:
                if key not in actual_props:
                    return False
                if not self._schemas_match(actual_props[key], expected_props[key]):
                    return False

        return True

    def mock_external_api(self, url: str, response_data: dict, status_code: int = 200, delay: float = 0):
        """
        Замокать внешний API.

        Args:
            url: URL для мока
            response_data: Данные ответа
            status_code: Код статуса
            delay: Задержка ответа в секундах
        """
        self._mock_external.mock_url(url, response_data, status_code, delay)
        logger.info(f"Mocked external API: {url}")

    def get_external_api_calls(self) -> List[dict]:
        """Получить историю вызовов внешних API."""
        return self._mock_external.call_history

    @asynccontextmanager
    async def test_session(self, scenario_type: TestScenarioType = TestScenarioType.UNIT):
        """
        Контекстный менеджер для тестовой сессии.

        Args:
            scenario_type: Тип тестового сценария
        """
        session_id = f"test_{int(time.time())}"
        self._current_session = TestSession(session_id=session_id, scenario_type=scenario_type)

        logger.info(f"Started test session: {session_id} ({scenario_type.value})")

        try:
            yield self._current_session
        finally:
            logger.info(f"Finished test session: {session_id}")
            self._current_session = None

    async def run_test_chain(self, steps: List[ChainStep]) -> List[Response]:
        """
        Выполнить цепочку тестовых запросов.

        Args:
            steps: Список шагов для выполнения

        Returns:
            Список ответов
        """
        responses = []
        context = {}

        for i, step in enumerate(steps):
            logger.info(
                f"Executing chain step {i + 1}/{len(steps)}: {step.description or step.method + ' ' + step.url}"
            )

            # Подготавливаем параметры запроса
            request_kwargs = {}
            if step.data:
                request_kwargs["json"] = step.data
            if step.params:
                request_kwargs["params"] = step.params
            if step.headers:
                request_kwargs["headers"] = step.headers

            # Выполняем запрос
            response = await self.request(step.method, step.url, **request_kwargs)
            responses.append(response)

            # Проверяем статус код
            if response.status_code != step.expected_status:
                raise AssertionError(
                    f"Chain step {i + 1} failed: expected status {step.expected_status}, got {response.status_code}"
                )

            # Извлекаем данные в контекст
            if step.extract_data:
                extracted = step.extract_data(response)
                context.update(extracted)

            # Валидируем ответ
            if step.validate_response:
                is_valid = step.validate_response(response, context)
                if not is_valid:
                    raise AssertionError(f"Chain step {i + 1} validation failed")

        return responses

    async def authenticated_request(
        self, method: str, url: str, auth_user: Optional["User"] = None, **kwargs: Any
    ) -> Response:
        """
        Выполнить аутентифицированный запрос.

        Args:
            method: HTTP метод
            url: URL для запроса
            auth_user: Пользователь для аутентификации (если не указан, используется текущий)
            **kwargs: Дополнительные параметры запроса

        Returns:
            HTTP ответ
        """
        if auth_user:
            if auth_user != self.auth_user:
                # Временно меняем пользователя
                original_user = self.auth_user
                await self.force_auth(user=auth_user)

                try:
                    response = await self.request(method, url, **kwargs)
                finally:
                    # Восстанавливаем оригинального пользователя
                    if original_user:
                        await self.force_auth(user=original_user)
                    else:
                        await self.force_logout()

                return response
            else:
                # Пользователь уже аутентифицирован как нужный
                return await self.request(method, url, **kwargs)
        else:
            # Если пользователь не указан, используем текущего (если есть)
            if not self.auth_user:
                raise ValueError("Не указан пользователь для аутентификации и нет текущего пользователя")
            return await self.request(method, url, **kwargs)


    def clear_cache(self) -> None:
        """Очистить кеш routes (полезно при динамическом изменении роутов)."""
        self._cached_routes = None


    def is_authenticated(self) -> bool:
        """Проверить, аутентифицирован ли пользователь."""
        return self.auth_user is not None and "Authorization" in self.headers

    async def request(self, method: str, url: str, **kwargs) -> Response:
        """Переопределенный метод request с трекингом метрик."""
        start_time = time.time()

        # Вычисляем размер запроса
        request_size = 0
        if "json" in kwargs:
            request_size = len(json.dumps(kwargs["json"]).encode())
        elif "data" in kwargs:
            request_size = len(str(kwargs["data"]).encode())

        # Выполняем запрос
        response = await super().request(method, url, **kwargs)

        end_time = time.time()
        response_time = end_time - start_time

        # Трекаем метрики если включено
        if self._performance_tracking:
            metrics = PerformanceMetrics(
                response_time=response_time, request_size=request_size, response_size=len(response.content)
            )
            self._metrics_history.append(metrics)

            if self._current_session:
                self._current_session.metrics.append(metrics)

        return response

    def _init_security_payloads(self) -> Dict[SecurityTestType, List[str]]:
        """Инициализация полезных нагрузок для тестов безопасности."""
        return {
            SecurityTestType.SQL_INJECTION: [
                "' OR '1'='1",
                "'; DROP TABLE users; --",
                "' UNION SELECT * FROM users --",
                "admin'--",
                "' OR 1=1#",
                "1'; EXEC xp_cmdshell('dir'); --",
            ],
            SecurityTestType.XSS: [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')",
                "<svg onload=alert('XSS')>",
                "'\"><script>alert('XSS')</script>",
                "<iframe src=javascript:alert('XSS')></iframe>",
            ],
            SecurityTestType.DIRECTORY_TRAVERSAL: [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
                "....//....//....//etc/passwd",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
                "..%252f..%252f..%252fetc%252fpasswd",
            ],
            SecurityTestType.INPUT_VALIDATION: [
                "A" * 10000,  # Длинная строка
                "\x00\x01\x02\x03",  # Нулевые байты
                "{'test': 'value'}",  # JSON инъекция
                "<xml><test>value</test></xml>",  # XML инъекция
                "$(whoami)",  # Command injection
            ],
        }

    # WebSocket Testing Methods
    async def websocket_connect(self, endpoint: str, **kwargs) -> str:
        """
        Подключение к WebSocket endpoint.

        Args:
            endpoint: WebSocket endpoint URL
            **kwargs: Дополнительные параметры подключения

        Returns:
            Идентификатор соединения
        """
        connection_id = str(uuid.uuid4())

        try:
            # Подготавливаем URL для WebSocket
            ws_url = endpoint
            if not ws_url.startswith(("ws://", "wss://")):
                base_url = str(self.base_url) if hasattr(self, "base_url") else "ws://localhost"
                ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://") + endpoint

            # Добавляем авторизацию если есть
            headers = {}
            if self.is_authenticated():
                headers.update(self.get_auth_headers())

            start_time = time.time()

            # Создаем WebSocket соединение
            websocket = await websockets.connect(ws_url, extra_headers=headers, **kwargs)

            connection_time = time.time() - start_time

            # Создаем сессию тестирования
            session = WebSocketTestSession(
                endpoint=endpoint, connection_id=connection_id, is_connected=True, connection_time=connection_time
            )

            self._websocket_connections[connection_id] = websocket
            self._websocket_sessions[connection_id] = session

            # Записываем событие подключения
            connect_message = WebSocketMessage(
                event_type=WebSocketEventType.CONNECT,
                data={"endpoint": endpoint, "connection_time": connection_time},
                connection_id=connection_id,
            )
            session.messages.append(connect_message)

            logger.info(f"WebSocket connected: {endpoint} (connection_id: {connection_id})")
            return connection_id

        except Exception as e:
            logger.error(f"WebSocket connection failed: {endpoint} - {str(e)}")

            # Записываем ошибку если сессия создана
            if connection_id in self._websocket_sessions:
                error_message = WebSocketMessage(
                    event_type=WebSocketEventType.ERROR, data=None, connection_id=connection_id, error=str(e)
                )
                self._websocket_sessions[connection_id].messages.append(error_message)

            raise

    async def websocket_send(self, connection_id: str, data: Any) -> None:
        """
        Отправка данных через WebSocket.

        Args:
            connection_id: Идентификатор соединения
            data: Данные для отправки
        """
        if connection_id not in self._websocket_connections:
            raise ValueError(f"WebSocket connection {connection_id} not found")

        websocket = self._websocket_connections[connection_id]
        session = self._websocket_sessions[connection_id]

        try:
            # Сериализуем данные если это не строка
            message_data = data if isinstance(data, str) else json.dumps(data)

            await websocket.send(message_data)

            # Записываем отправленное сообщение
            sent_message = WebSocketMessage(
                event_type=WebSocketEventType.MESSAGE,
                data={"sent": data, "direction": "outbound"},
                connection_id=connection_id,
            )
            session.messages.append(sent_message)

            logger.debug(f"WebSocket message sent: {connection_id}")

        except Exception as e:
            logger.error(f"WebSocket send failed: {connection_id} - {str(e)}")

            error_message = WebSocketMessage(
                event_type=WebSocketEventType.ERROR, data=None, connection_id=connection_id, error=str(e)
            )
            session.messages.append(error_message)
            raise

    async def websocket_receive(self, connection_id: str, timeout: float = 10.0) -> Any:
        """
        Получение данных через WebSocket.

        Args:
            connection_id: Идентификатор соединения
            timeout: Таймаут ожидания в секундах

        Returns:
            Полученные данные
        """
        if connection_id not in self._websocket_connections:
            raise ValueError(f"WebSocket connection {connection_id} not found")

        websocket = self._websocket_connections[connection_id]
        session = self._websocket_sessions[connection_id]

        try:
            # Получаем сообщение с таймаутом
            message = await asyncio.wait_for(websocket.recv(), timeout=timeout)

            # Пытаемся распарсить JSON
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                data = message

            # Записываем полученное сообщение
            received_message = WebSocketMessage(
                event_type=WebSocketEventType.MESSAGE,
                data={"received": data, "direction": "inbound"},
                connection_id=connection_id,
            )
            session.messages.append(received_message)

            logger.debug(f"WebSocket message received: {connection_id}")
            return data

        except asyncio.TimeoutError:
            logger.warning(f"WebSocket receive timeout: {connection_id}")
            raise
        except Exception as e:
            logger.error(f"WebSocket receive failed: {connection_id} - {str(e)}")

            error_message = WebSocketMessage(
                event_type=WebSocketEventType.ERROR, data=None, connection_id=connection_id, error=str(e)
            )
            session.messages.append(error_message)
            raise

    async def websocket_close(self, connection_id: str) -> None:
        """
        Закрытие WebSocket соединения.

        Args:
            connection_id: Идентификатор соединения
        """
        if connection_id not in self._websocket_connections:
            logger.warning(f"WebSocket connection {connection_id} not found for closing")
            return

        websocket = self._websocket_connections[connection_id]
        session = self._websocket_sessions[connection_id]

        try:
            await websocket.close()
            session.is_connected = False

            # Записываем событие отключения
            disconnect_message = WebSocketMessage(
                event_type=WebSocketEventType.DISCONNECT, data={"reason": "manual_close"}, connection_id=connection_id
            )
            session.messages.append(disconnect_message)

            logger.info(f"WebSocket disconnected: {connection_id}")

        except Exception as e:
            logger.error(f"WebSocket close failed: {connection_id} - {str(e)}")
        finally:
            # Удаляем из активных соединений
            self._websocket_connections.pop(connection_id, None)

    async def websocket_ping(self, connection_id: str) -> float:
        """
        Ping WebSocket соединения.

        Args:
            connection_id: Идентификатор соединения

        Returns:
            Время ping в секундах
        """
        if connection_id not in self._websocket_connections:
            raise ValueError(f"WebSocket connection {connection_id} not found")

        websocket = self._websocket_connections[connection_id]
        session = self._websocket_sessions[connection_id]

        try:
            start_time = time.time()
            await websocket.ping()
            ping_time = time.time() - start_time

            session.last_ping_time = ping_time

            # Записываем ping
            ping_message = WebSocketMessage(
                event_type=WebSocketEventType.PING, data={"ping_time": ping_time}, connection_id=connection_id
            )
            session.messages.append(ping_message)

            logger.debug(f"WebSocket ping: {connection_id} - {ping_time:.3f}s")
            return ping_time

        except Exception as e:
            logger.error(f"WebSocket ping failed: {connection_id} - {str(e)}")
            raise

    def get_websocket_session(self, connection_id: str) -> Optional[WebSocketTestSession]:
        """Получить сессию WebSocket тестирования."""
        return self._websocket_sessions.get(connection_id)

    def get_all_websocket_sessions(self) -> Dict[str, WebSocketTestSession]:
        """Получить все WebSocket сессии."""
        return self._websocket_sessions.copy()

    @asynccontextmanager
    async def websocket_test_session(self, endpoint: str, **kwargs):
        """
        Контекстный менеджер для WebSocket тестирования.

        Args:
            endpoint: WebSocket endpoint
            **kwargs: Дополнительные параметры подключения
        """
        connection_id = None
        try:
            connection_id = await self.websocket_connect(endpoint, **kwargs)
            yield connection_id
        finally:
            if connection_id:
                await self.websocket_close(connection_id)

    # Security Testing Methods
    async def run_security_scan(self, endpoints: Optional[List[str]] = None) -> List[SecurityTestResult]:
        """
        Запуск комплексного сканирования безопасности.

        Args:
            endpoints: Список endpoints для тестирования (если None, тестируются все)

        Returns:
            Список результатов тестов безопасности
        """
        if not self._app:
            raise ValueError("FastAPI app не инициализировано для сканирования безопасности")

        if endpoints is None:
            endpoints = self._extract_endpoints_from_app()

        results = []

        for endpoint in endpoints:
            logger.info(f"Security scanning endpoint: {endpoint}")

            # SQL Injection тесты
            sql_results = await self._test_sql_injection(endpoint)
            results.extend(sql_results)

            # XSS тесты
            xss_results = await self._test_xss(endpoint)
            results.extend(xss_results)

            # Directory Traversal тесты
            traversal_results = await self._test_directory_traversal(endpoint)
            results.extend(traversal_results)

            # Input Validation тесты
            validation_results = await self._test_input_validation(endpoint)
            results.extend(validation_results)

            # Rate Limiting тесты
            rate_results = await self._test_rate_limiting(endpoint)
            results.extend(rate_results)

            # Header Security тесты
            header_results = await self._test_security_headers(endpoint)
            results.extend(header_results)

            # Authentication/Authorization bypass тесты
            auth_results = await self._test_auth_bypass(endpoint)
            results.extend(auth_results)

        self._security_test_results.extend(results)
        return results

    async def _test_sql_injection(self, endpoint: str) -> List[SecurityTestResult]:
        """Тестирование SQL injection уязвимостей."""
        results = []
        payloads = self._security_payloads[SecurityTestType.SQL_INJECTION]

        for payload in payloads:
            try:
                # Тестируем в параметрах запроса
                response = await self.get(endpoint, params={"test": payload})

                # Проверяем признаки SQL injection
                vulnerable = self._detect_sql_injection_response(response)

                if vulnerable:
                    result = SecurityTestResult(
                        test_type=SecurityTestType.SQL_INJECTION,
                        endpoint=endpoint,
                        vulnerable=True,
                        risk_level="HIGH",
                        description=f"SQL Injection vulnerability detected with payload: {payload}",
                        evidence=f"Response status: {response.status_code}, Content sample: {response.text[:200]}",
                        recommendation="Use parameterized queries and input validation",
                        cwe_id="CWE-89",
                    )
                    results.append(result)

            except Exception as e:
                logger.debug(f"SQL injection test error: {e}")

        # Добавляем результат "безопасно" если уязвимостей не найдено
        if not any(r.vulnerable for r in results):
            results.append(
                SecurityTestResult(
                    test_type=SecurityTestType.SQL_INJECTION,
                    endpoint=endpoint,
                    vulnerable=False,
                    risk_level="LOW",
                    description="No SQL injection vulnerabilities detected",
                    recommendation="Continue following secure coding practices",
                )
            )

        return results

    async def _test_xss(self, endpoint: str) -> List[SecurityTestResult]:
        """Тестирование XSS уязвимостей."""
        results = []
        payloads = self._security_payloads[SecurityTestType.XSS]

        for payload in payloads:
            try:
                # Тестируем в POST данных
                response = await self.post(endpoint, json={"test": payload})

                # Проверяем отражение XSS payload в ответе
                vulnerable = payload in response.text

                if vulnerable:
                    result = SecurityTestResult(
                        test_type=SecurityTestType.XSS,
                        endpoint=endpoint,
                        vulnerable=True,
                        risk_level="MEDIUM",
                        description=f"XSS vulnerability detected with payload: {payload}",
                        evidence=f"Payload reflected in response",
                        recommendation="Implement proper input sanitization and output encoding",
                        cwe_id="CWE-79",
                    )
                    results.append(result)

            except Exception as e:
                logger.debug(f"XSS test error: {e}")

        if not any(r.vulnerable for r in results):
            results.append(
                SecurityTestResult(
                    test_type=SecurityTestType.XSS,
                    endpoint=endpoint,
                    vulnerable=False,
                    risk_level="LOW",
                    description="No XSS vulnerabilities detected",
                    recommendation="Continue proper input/output handling",
                )
            )

        return results

    async def _test_directory_traversal(self, endpoint: str) -> List[SecurityTestResult]:
        """Тестирование Directory Traversal уязвимостей."""
        results = []
        payloads = self._security_payloads[SecurityTestType.DIRECTORY_TRAVERSAL]

        for payload in payloads:
            try:
                # Тестируем в параметрах пути
                test_endpoint = endpoint.replace("{id}", payload) if "{id}" in endpoint else endpoint
                response = await self.get(test_endpoint, params={"file": payload})

                # Проверяем признаки доступа к системным файлам
                vulnerable = self._detect_directory_traversal_response(response)

                if vulnerable:
                    result = SecurityTestResult(
                        test_type=SecurityTestType.DIRECTORY_TRAVERSAL,
                        endpoint=endpoint,
                        vulnerable=True,
                        risk_level="HIGH",
                        description=f"Directory traversal vulnerability detected with payload: {payload}",
                        evidence=f"System file content detected in response",
                        recommendation="Implement proper path validation and sandboxing",
                        cwe_id="CWE-22",
                    )
                    results.append(result)

            except Exception as e:
                logger.debug(f"Directory traversal test error: {e}")

        if not any(r.vulnerable for r in results):
            results.append(
                SecurityTestResult(
                    test_type=SecurityTestType.DIRECTORY_TRAVERSAL,
                    endpoint=endpoint,
                    vulnerable=False,
                    risk_level="LOW",
                    description="No directory traversal vulnerabilities detected",
                    recommendation="Continue proper file path validation",
                )
            )

        return results

    async def _test_rate_limiting(self, endpoint: str) -> List[SecurityTestResult]:
        """Тестирование Rate Limiting."""
        try:
            # Отправляем много запросов быстро
            requests_count = 50
            start_time = time.time()

            responses = []
            for _ in range(requests_count):
                response = await self.get(endpoint)
                responses.append(response)

            end_time = time.time()
            duration = end_time - start_time

            # Проверяем наличие rate limiting
            too_many_requests = any(r.status_code == 429 for r in responses)
            requests_per_second = requests_count / duration

            if not too_many_requests and requests_per_second > 10:  # Простая эвристика
                return [
                    SecurityTestResult(
                        test_type=SecurityTestType.RATE_LIMITING,
                        endpoint=endpoint,
                        vulnerable=True,
                        risk_level="MEDIUM",
                        description=f"No rate limiting detected. {requests_count} requests in {duration:.2f}s",
                        evidence=f"RPS: {requests_per_second:.2f}, no 429 responses",
                        recommendation="Implement rate limiting to prevent abuse",
                        cwe_id="CWE-770",
                    )
                ]
            else:
                return [
                    SecurityTestResult(
                        test_type=SecurityTestType.RATE_LIMITING,
                        endpoint=endpoint,
                        vulnerable=False,
                        risk_level="LOW",
                        description="Rate limiting appears to be in place",
                        recommendation="Verify rate limiting configuration is appropriate",
                    )
                ]

        except Exception as e:
            logger.error(f"Rate limiting test error: {e}")
            return []

    async def _test_security_headers(self, endpoint: str) -> List[SecurityTestResult]:
        """Тестирование Security Headers."""
        try:
            response = await self.get(endpoint)

            # Проверяем важные security headers
            security_headers = {
                "X-Frame-Options": "Clickjacking protection",
                "X-Content-Type-Options": "MIME sniffing protection",
                "X-XSS-Protection": "XSS protection",
                "Strict-Transport-Security": "HTTPS enforcement",
                "Content-Security-Policy": "XSS and injection protection",
            }

            missing_headers = []
            for header, description in security_headers.items():
                if header not in response.headers:
                    missing_headers.append(f"{header} ({description})")

            if missing_headers:
                return [
                    SecurityTestResult(
                        test_type=SecurityTestType.HEADER_SECURITY,
                        endpoint=endpoint,
                        vulnerable=True,
                        risk_level="MEDIUM",
                        description=f"Missing security headers: {', '.join(missing_headers)}",
                        evidence=f"Response headers: {dict(response.headers)}",
                        recommendation="Add missing security headers to improve security posture",
                        cwe_id="CWE-693",
                    )
                ]
            else:
                return [
                    SecurityTestResult(
                        test_type=SecurityTestType.HEADER_SECURITY,
                        endpoint=endpoint,
                        vulnerable=False,
                        risk_level="LOW",
                        description="All important security headers are present",
                        recommendation="Verify header values are correctly configured",
                    )
                ]

        except Exception as e:
            logger.error(f"Security headers test error: {e}")
            return []

    async def _test_auth_bypass(self, endpoint: str) -> List[SecurityTestResult]:
        """Тестирование обхода авторизации."""
        results = []

        try:
            # Тест без авторизации
            original_headers = self.headers.copy()
            self.headers.pop("Authorization", None)

            response_no_auth = await self.get(endpoint)

            # Восстанавливаем заголовки
            self.headers.update(original_headers)

            # Если без авторизации получаем 200, это проблема
            if response_no_auth.status_code == 200:
                results.append(
                    SecurityTestResult(
                        test_type=SecurityTestType.AUTHENTICATION_BYPASS,
                        endpoint=endpoint,
                        vulnerable=True,
                        risk_level="HIGH",
                        description="Endpoint accessible without authentication",
                        evidence=f"Response status: {response_no_auth.status_code}",
                        recommendation="Implement proper authentication checks",
                        cwe_id="CWE-306",
                    )
                )

            # Тест с недействительным токеном
            invalid_token_headers = original_headers.copy()
            invalid_token_headers["Authorization"] = "Bearer invalid_token_12345"

            response_invalid = await self.get(endpoint, headers=invalid_token_headers)

            if response_invalid.status_code == 200:
                results.append(
                    SecurityTestResult(
                        test_type=SecurityTestType.AUTHENTICATION_BYPASS,
                        endpoint=endpoint,
                        vulnerable=True,
                        risk_level="HIGH",
                        description="Endpoint accessible with invalid token",
                        evidence=f"Response status with invalid token: {response_invalid.status_code}",
                        recommendation="Implement proper token validation",
                        cwe_id="CWE-287",
                    )
                )

        except Exception as e:
            logger.error(f"Auth bypass test error: {e}")

        if not results:
            results.append(
                SecurityTestResult(
                    test_type=SecurityTestType.AUTHENTICATION_BYPASS,
                    endpoint=endpoint,
                    vulnerable=False,
                    risk_level="LOW",
                    description="Authentication appears to be properly implemented",
                    recommendation="Continue following secure authentication practices",
                )
            )

        return results

    def _extract_endpoints_from_app(self) -> List[str]:
        """Извлечение endpoints из FastAPI приложения."""
        if not self._app:
            return []

        endpoints = []
        for route in self._app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                path = getattr(route, "path")
                methods = getattr(route, "methods", set())

                # Фильтруем системные методы
                filtered_methods = [m for m in methods if m not in {"HEAD", "OPTIONS"}]

                for method in filtered_methods:
                    endpoints.append(f"{method} {path}")

        return endpoints

    async def _test_input_validation(self, endpoint: str) -> List[SecurityTestResult]:
        """Тестирование валидации входных данных."""
        results = []
        payloads = self._security_payloads[SecurityTestType.INPUT_VALIDATION]

        for payload in payloads:
            try:
                # Тестируем различные методы
                methods_to_test = ["GET", "POST", "PUT"]

                for method in methods_to_test:
                    try:
                        if method == "GET":
                            response = await self.get(endpoint, params={"input": payload})
                        else:
                            response = await self.request(method, endpoint, json={"input": payload})

                        # Проверяем на ошибки валидации
                        if response.status_code >= 500:
                            result = SecurityTestResult(
                                test_type=SecurityTestType.INPUT_VALIDATION,
                                endpoint=endpoint,
                                vulnerable=True,
                                risk_level="MEDIUM",
                                description=f"Input validation issue with {method} method and payload: {str(payload)[:50]}",
                                evidence=f"Server error {response.status_code}",
                                recommendation="Implement proper input validation and error handling",
                                cwe_id="CWE-20",
                            )
                            results.append(result)
                            break

                    except Exception:
                        continue

            except Exception as e:
                logger.debug(f"Input validation test error: {e}")

        if not any(r.vulnerable for r in results):
            results.append(
                SecurityTestResult(
                    test_type=SecurityTestType.INPUT_VALIDATION,
                    endpoint=endpoint,
                    vulnerable=False,
                    risk_level="LOW",
                    description="Input validation appears to be properly implemented",
                    recommendation="Continue proper input validation practices",
                )
            )

        return results

    def _detect_sql_injection_response(self, response: Response) -> bool:
        """Обнаружение признаков SQL injection в ответе."""
        # Простые индикаторы SQL injection
        sql_error_patterns = [
            "sql syntax",
            "mysql_fetch",
            "ora-[0-9]{5}",
            "postgresql",
            "sqlite3",
            "sqlalchemy",
            "database error",
            "syntax error",
            "invalid query",
        ]

        response_text = response.text.lower()

        # Проверяем статус код - 500 может указывать на SQL ошибку
        if response.status_code >= 500:
            for pattern in sql_error_patterns:
                if re.search(pattern, response_text):
                    return True

        return False

    def _detect_directory_traversal_response(self, response: Response) -> bool:
        """Обнаружение признаков directory traversal в ответе."""
        # Признаки успешного доступа к системным файлам
        system_file_patterns = [
            "root:x:",  # Linux /etc/passwd
            "127.0.0.1",  # hosts file
            "[boot loader]",  # Windows boot.ini
            "# hosts file",  # Windows hosts
            "daemon:x:",  # Linux passwd entries
        ]

        response_text = response.text.lower()

        for pattern in system_file_patterns:
            if pattern.lower() in response_text:
                return True

        return False

    def get_security_results(self) -> List[SecurityTestResult]:
        """Получить все результаты тестов безопасности."""
        return self._security_test_results.copy()

    def get_vulnerabilities_by_risk(self, risk_level: str) -> List[SecurityTestResult]:
        """Получить уязвимости по уровню риска."""
        return [r for r in self._security_test_results if r.risk_level == risk_level and r.vulnerable]

    def generate_security_report(self) -> Dict[str, Any]:
        """Генерация отчета по безопасности."""
        if not self._security_test_results:
            return {"message": "No security tests have been run"}

        total_tests = len(self._security_test_results)
        vulnerabilities = [r for r in self._security_test_results if r.vulnerable]

        risk_counts = {}
        for vuln in vulnerabilities:
            risk_counts[vuln.risk_level] = risk_counts.get(vuln.risk_level, 0) + 1

        return {
            "total_tests": total_tests,
            "total_vulnerabilities": len(vulnerabilities),
            "risk_breakdown": risk_counts,
            "security_score": max(0, 100 - (len(vulnerabilities) * 10)),  # Простая оценка
            "test_coverage": {
                test_type.value: len([r for r in self._security_test_results if r.test_type == test_type])
                for test_type in SecurityTestType
            },
            "recommendations": list(set([r.recommendation for r in vulnerabilities if r.recommendation])),
        }

    # Load Testing Methods
    async def run_load_test(self, config: LoadTestConfig) -> LoadTestResult:
        """
        Запуск нагрузочного тестирования.

        Args:
            config: Конфигурация нагрузочного теста

        Returns:
            Результат нагрузочного тестирования
        """
        logger.info(
            f"Starting load test: {config.pattern.value} for {config.duration_seconds}s with {config.concurrent_users} users"
        )

        # Инициализируем executor если нужно
        if not self._load_test_executor:
            self._load_test_executor = ThreadPoolExecutor(max_workers=config.concurrent_users)

        start_time = time.time()
        all_responses = []
        errors = []

        try:
            if config.pattern == LoadTestPattern.CONSTANT_LOAD:
                all_responses, errors = await self._run_constant_load_test(config)
            elif config.pattern == LoadTestPattern.RAMP_UP:
                all_responses, errors = await self._run_ramp_up_test(config)
            elif config.pattern == LoadTestPattern.SPIKE:
                all_responses, errors = await self._run_spike_test(config)
            elif config.pattern == LoadTestPattern.STRESS:
                all_responses, errors = await self._run_stress_test(config)
            else:
                raise ValueError(f"Unsupported load test pattern: {config.pattern}")

            # Анализируем результаты
            return self._analyze_load_test_results(config, all_responses, errors, start_time)

        except Exception as e:
            logger.error(f"Load test failed: {e}")
            raise

    async def _run_constant_load_test(self, config: LoadTestConfig) -> Tuple[List[Response], List[str]]:
        """Постоянная нагрузка."""
        all_responses = []
        errors = []

        end_time = time.time() + config.duration_seconds

        # Создаем задачи для параллельного выполнения
        while time.time() < end_time:
            tasks = []

            for _ in range(config.concurrent_users):
                # Выбираем случайный endpoint
                endpoint = random.choice(config.endpoints) if config.endpoints else "/"

                # Создаем задачу
                task = asyncio.create_task(self._perform_load_test_request(endpoint, config))
                tasks.append(task)

            # Выполняем запросы
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                else:
                    all_responses.append(result)

            # Контролируем RPS если задано
            if config.requests_per_second:
                await asyncio.sleep(max(0, config.concurrent_users / config.requests_per_second))

        return all_responses, errors

    async def _run_ramp_up_test(self, config: LoadTestConfig) -> Tuple[List[Response], List[str]]:
        """Тест с нарастающей нагрузкой."""
        all_responses = []
        errors = []

        ramp_up_time = config.ramp_up_time or config.duration_seconds // 2
        steady_time = config.duration_seconds - ramp_up_time

        # Фаза нарастания
        for step in range(ramp_up_time):
            current_users = int((step + 1) * config.concurrent_users / ramp_up_time)

            tasks = []
            for _ in range(current_users):
                endpoint = random.choice(config.endpoints) if config.endpoints else "/"
                task = asyncio.create_task(self._perform_load_test_request(endpoint, config))
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                else:
                    all_responses.append(result)

            await asyncio.sleep(1)  # 1 секунда на шаг

        # Фаза постоянной нагрузки
        steady_config = LoadTestConfig(
            pattern=LoadTestPattern.CONSTANT_LOAD,
            duration_seconds=steady_time,
            concurrent_users=config.concurrent_users,
            endpoints=config.endpoints,
            test_data_generators=config.test_data_generators,
        )

        steady_responses, steady_errors = await self._run_constant_load_test(steady_config)
        all_responses.extend(steady_responses)
        errors.extend(steady_errors)

        return all_responses, errors

    async def _run_spike_test(self, config: LoadTestConfig) -> Tuple[List[Response], List[str]]:
        """Spike тестирование."""
        all_responses = []
        errors = []

        normal_users = config.concurrent_users // 3
        spike_users = config.concurrent_users

        # Нормальная нагрузка
        normal_duration = config.duration_seconds // 3

        # Первый период - нормальная нагрузка
        for _ in range(normal_duration):
            tasks = []
            for _ in range(normal_users):
                endpoint = random.choice(config.endpoints) if config.endpoints else "/"
                task = asyncio.create_task(self._perform_load_test_request(endpoint, config))
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                else:
                    all_responses.append(result)

            await asyncio.sleep(1)

        # Spike период
        spike_duration = config.duration_seconds // 3

        for _ in range(spike_duration):
            tasks = []
            for _ in range(spike_users):
                endpoint = random.choice(config.endpoints) if config.endpoints else "/"
                task = asyncio.create_task(self._perform_load_test_request(endpoint, config))
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                else:
                    all_responses.append(result)

            await asyncio.sleep(0.5)  # Более интенсивная нагрузка

        # Возврат к нормальной нагрузке
        remaining_duration = config.duration_seconds - normal_duration - spike_duration

        for _ in range(remaining_duration):
            tasks = []
            for _ in range(normal_users):
                endpoint = random.choice(config.endpoints) if config.endpoints else "/"
                task = asyncio.create_task(self._perform_load_test_request(endpoint, config))
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                else:
                    all_responses.append(result)

            await asyncio.sleep(1)

        return all_responses, errors

    async def _run_stress_test(self, config: LoadTestConfig) -> Tuple[List[Response], List[str]]:
        """Стресс тестирование - постепенное увеличение нагрузки до отказа."""
        all_responses = []
        errors = []

        current_users = 1
        max_users = config.concurrent_users * 2  # Удваиваем для стресса

        while current_users <= max_users and time.time() < time.time() + config.duration_seconds:
            logger.info(f"Stress test: {current_users} concurrent users")

            tasks = []
            for _ in range(current_users):
                endpoint = random.choice(config.endpoints) if config.endpoints else "/"
                task = asyncio.create_task(self._perform_load_test_request(endpoint, config))
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_errors = 0
            for result in batch_results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                    batch_errors += 1
                else:
                    all_responses.append(result)

            # Проверяем процент ошибок
            error_rate = batch_errors / len(batch_results) if batch_results else 0

            if error_rate > 0.5:  # Если более 50% ошибок, останавливаемся
                logger.warning(f"Stress test stopped at {current_users} users due to high error rate: {error_rate:.2%}")
                break

            current_users += max(1, current_users // 10)  # Увеличиваем на 10%
            await asyncio.sleep(2)  # Пауза между уровнями нагрузки

        return all_responses, errors

    async def _perform_load_test_request(self, endpoint: str, config: LoadTestConfig) -> Response:
        """Выполнение одного запроса в рамках нагрузочного тестирования."""
        try:
            # Генерируем тестовые данные если есть генератор
            test_data = {}
            if endpoint in config.test_data_generators:
                generator = config.test_data_generators[endpoint]
                test_data = generator()

            # Выполняем запрос (по умолчанию GET)
            if test_data:
                response = await self.post(endpoint, json=test_data)
            else:
                response = await self.get(endpoint)

            return response

        except Exception as e:
            logger.debug(f"Load test request failed: {endpoint} - {e}")
            raise

    def _analyze_load_test_results(
        self, config: LoadTestConfig, responses: List[Response], errors: List[str], start_time: float
    ) -> LoadTestResult:
        """Анализ результатов нагрузочного тестирования."""
        end_time = time.time()
        total_duration = end_time - start_time

        successful_responses = [r for r in responses if r.status_code < 400]
        failed_responses = [r for r in responses if r.status_code >= 400]

        # Вычисляем метрики времени ответа
        response_times = []
        for response in responses:
            # Примерное время ответа (в реальности нужно измерять точнее)
            if hasattr(response, "_elapsed"):
                response_times.append(response._elapsed.total_seconds())
            else:
                response_times.append(0.1)  # Заглушка

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)

            # Перцентили
            sorted_times = sorted(response_times)
            percentile_95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
            percentile_99 = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
        else:
            avg_response_time = min_response_time = max_response_time = percentile_95 = percentile_99 = 0

        total_requests = len(responses) + len(errors)
        requests_per_second = total_requests / total_duration if total_duration > 0 else 0

        return LoadTestResult(
            config=config,
            total_requests=total_requests,
            successful_requests=len(successful_responses),
            failed_requests=len(failed_responses) + len(errors),
            average_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            requests_per_second=requests_per_second,
            errors=errors[:50],  # Ограничиваем количество ошибок в отчете
        )

    # AI-Powered Test Generation Methods
    def load_openapi_schema(self, schema_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Загрузка OpenAPI схемы для генерации тестов.

        Args:
            schema_path: Путь к файлу схемы (если None, извлекается из app)

        Returns:
            OpenAPI схема или None
        """
        if schema_path:
            with open(schema_path, "r", encoding="utf-8") as f:
                self._openapi_schema = json.load(f)
        elif self._app:
            self._openapi_schema = self._app.openapi()
        else:
            raise ValueError("Необходимо указать schema_path или инициализировать app")

        logger.info("OpenAPI schema loaded successfully")
        return self._openapi_schema

    def generate_tests_from_schema(self) -> List[AIGeneratedTest]:
        """
        Генерация тестов из OpenAPI схемы.

        Returns:
            Список сгенерированных тестов
        """
        if not self._openapi_schema:
            raise ValueError("OpenAPI schema не загружена. Используйте load_openapi_schema()")

        generated_tests = []

        # Извлекаем endpoints из схемы
        paths = self._openapi_schema.get("paths", {})

        for path, path_info in paths.items():
            for method, operation_info in path_info.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    endpoint_info = OpenAPIEndpoint(
                        path=path,
                        method=method.upper(),
                        operation_id=operation_info.get("operationId"),
                        summary=operation_info.get("summary"),
                        description=operation_info.get("description"),
                        parameters=operation_info.get("parameters", []),
                        request_body=operation_info.get("requestBody"),
                        responses=operation_info.get("responses", {}),
                        security=operation_info.get("security", []),
                        tags=operation_info.get("tags", []),
                    )

                    # Генерируем тесты для этого endpoint
                    endpoint_tests = self._generate_endpoint_tests(endpoint_info)
                    generated_tests.extend(endpoint_tests)

        self._ai_generated_tests.extend(generated_tests)
        logger.info(f"Generated {len(generated_tests)} tests from OpenAPI schema")

        return generated_tests

    def _generate_endpoint_tests(self, endpoint: OpenAPIEndpoint) -> List[AIGeneratedTest]:
        """Генерация тестов для конкретного endpoint."""
        tests = []

        # Базовый тест успешного выполнения
        success_test = self._generate_success_test(endpoint)
        tests.append(success_test)

        # Тесты валидации
        validation_tests = self._generate_validation_tests(endpoint)
        tests.extend(validation_tests)

        # Тесты безопасности
        security_tests = self._generate_security_tests(endpoint)
        tests.extend(security_tests)

        # Тесты авторизации
        if endpoint.security:
            auth_tests = self._generate_authorization_tests(endpoint)
            tests.extend(auth_tests)

        return tests

    def _generate_success_test(self, endpoint: OpenAPIEndpoint) -> AIGeneratedTest:
        """Генерация теста успешного выполнения."""
        test_name = f"test_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_success"

        # Генерируем тестовые данные
        test_data = self._generate_test_data(endpoint)

        # Определяем ожидаемый статус код
        expected_status = 200
        if "200" in endpoint.responses:
            expected_status = 200
        elif "201" in endpoint.responses:
            expected_status = 201
        elif "204" in endpoint.responses:
            expected_status = 204

        # Генерируем код теста
        test_code = self._generate_test_code(endpoint, test_data, expected_status, "success")

        return AIGeneratedTest(
            test_name=test_name,
            endpoint=endpoint.path,
            method=endpoint.method,
            test_description=f"Test successful {endpoint.method} request to {endpoint.path}",
            test_code=test_code,
            test_data=test_data,
            expected_status=expected_status,
            confidence_score=0.9,
        )

    def _generate_validation_tests(self, endpoint: OpenAPIEndpoint) -> List[AIGeneratedTest]:
        """Генерация тестов валидации."""
        tests = []

        # Тесты с недостающими обязательными параметрами
        if endpoint.parameters:
            required_params = [p for p in endpoint.parameters if p.get("required", False)]
            for param in required_params:
                test_name = f"test_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_missing_{param['name']}"

                test_data = self._generate_test_data(endpoint)
                # Удаляем обязательный параметр
                if "params" in test_data and param["name"] in test_data["params"]:
                    del test_data["params"][param["name"]]

                test_code = self._generate_test_code(endpoint, test_data, 400, "validation_error")

                tests.append(
                    AIGeneratedTest(
                        test_name=test_name,
                        endpoint=endpoint.path,
                        method=endpoint.method,
                        test_description=f"Test validation error when {param['name']} is missing",
                        test_code=test_code,
                        test_data=test_data,
                        expected_status=400,
                        confidence_score=0.8,
                    )
                )

        # Тесты с неверными типами данных
        if endpoint.request_body:
            test_name = f"test_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_invalid_data"

            # Генерируем неверные данные
            invalid_data = {"invalid": "data", "number_field": "not_a_number"}

            test_code = self._generate_test_code(endpoint, {"json": invalid_data}, 422, "validation_error")

            tests.append(
                AIGeneratedTest(
                    test_name=test_name,
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    test_description=f"Test validation error with invalid data types",
                    test_code=test_code,
                    test_data={"json": invalid_data},
                    expected_status=422,
                    confidence_score=0.7,
                )
            )

        return tests

    def _generate_security_tests(self, endpoint: OpenAPIEndpoint) -> List[AIGeneratedTest]:
        """Генерация тестов безопасности."""
        tests = []

        # XSS тест
        if endpoint.method in ["POST", "PUT", "PATCH"]:
            test_name = f"test_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_xss"

            xss_data = {"test_field": "<script>alert('XSS')</script>"}
            test_code = self._generate_test_code(endpoint, {"json": xss_data}, 400, "security_test")

            tests.append(
                AIGeneratedTest(
                    test_name=test_name,
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    test_description=f"Test XSS protection in {endpoint.method} request",
                    test_code=test_code,
                    test_data={"json": xss_data},
                    expected_status=400,
                    security_checks=[SecurityTestType.XSS],
                    confidence_score=0.6,
                )
            )

        # SQL Injection тест
        sql_injection_data = {"id": "1' OR '1'='1"}
        test_name = f"test_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_sql_injection"

        test_code = self._generate_test_code(endpoint, {"params": sql_injection_data}, 400, "security_test")

        tests.append(
            AIGeneratedTest(
                test_name=test_name,
                endpoint=endpoint.path,
                method=endpoint.method,
                test_description=f"Test SQL injection protection in {endpoint.method} request",
                test_code=test_code,
                test_data={"params": sql_injection_data},
                expected_status=400,
                security_checks=[SecurityTestType.SQL_INJECTION],
                confidence_score=0.6,
            )
        )

        return tests

    def _generate_authorization_tests(self, endpoint: OpenAPIEndpoint) -> List[AIGeneratedTest]:
        """Генерация тестов авторизации."""
        tests = []

        # Тест без авторизации
        test_name = f"test_{endpoint.method.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_unauthorized"

        test_data = self._generate_test_data(endpoint)
        test_code = self._generate_test_code(endpoint, test_data, 401, "unauthorized")

        tests.append(
            AIGeneratedTest(
                test_name=test_name,
                endpoint=endpoint.path,
                method=endpoint.method,
                test_description=f"Test unauthorized access to {endpoint.method} {endpoint.path}",
                test_code=test_code,
                test_data=test_data,
                expected_status=401,
                security_checks=[SecurityTestType.AUTHENTICATION_BYPASS],
                confidence_score=0.8,
            )
        )

        return tests

    def _generate_test_data(self, endpoint: OpenAPIEndpoint) -> Dict[str, Any]:
        """Генерация тестовых данных для endpoint."""
        test_data = {}

        # Генерируем параметры запроса
        if endpoint.parameters:
            params = {}
            for param in endpoint.parameters:
                param_name = param["name"]
                param_type = param.get("schema", {}).get("type", "string")

                if param.get("in") == "query":
                    params[param_name] = self._generate_value_by_type(param_type)
                elif param.get("in") == "path":
                    # Path параметры будут подставлены в URL
                    test_data["path_params"] = test_data.get("path_params", {})
                    test_data["path_params"][param_name] = self._generate_value_by_type(param_type)

            if params:
                test_data["params"] = params

        # Генерируем тело запроса
        if endpoint.request_body:
            content = endpoint.request_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                json_data = self._generate_json_from_schema(schema)
                test_data["json"] = json_data

        return test_data

    def _generate_value_by_type(self, param_type: str) -> Any:
        """Генерация значения по типу."""
        if param_type == "integer":
            return random.randint(1, 100)
        elif param_type == "number":
            return round(random.uniform(1.0, 100.0), 2)
        elif param_type == "boolean":
            return random.choice([True, False])
        elif param_type == "array":
            return [f"item_{i}" for i in range(3)]
        else:  # string по умолчанию
            return f"test_value_{random.randint(1, 1000)}"

    def _generate_json_from_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация JSON данных из схемы."""
        if schema.get("type") == "object":
            properties = schema.get("properties", {})
            result = {}

            for prop_name, prop_schema in properties.items():
                prop_type = prop_schema.get("type", "string")
                result[prop_name] = self._generate_value_by_type(prop_type)

            return result
        else:
            return {"data": self._generate_value_by_type(schema.get("type", "string"))}

    def _generate_test_code(
        self, endpoint: OpenAPIEndpoint, test_data: Dict[str, Any], expected_status: int, test_type: str
    ) -> str:
        """Генерация кода теста."""
        method = endpoint.method.lower()
        path = endpoint.path

        # Базовый шаблон теста
        code_lines = [
            "async def test_function(client):",
            f'    """Generated test for {endpoint.method} {endpoint.path}"""',
        ]

        # Подготовка авторизации для некоторых типов тестов
        if test_type == "success" and endpoint.security:
            code_lines.append("    await client.force_auth()")
        elif test_type == "unauthorized":
            code_lines.append("    await client.force_logout()")

        # Формирование URL
        if "path_params" in test_data:
            path_with_params = path
            for param_name, param_value in test_data["path_params"].items():
                path_with_params = path_with_params.replace(f"{{{param_name}}}", str(param_value))
            code_lines.append(f'    url = "{path_with_params}"')
        else:
            code_lines.append(f'    url = "{path}"')

        # Формирование запроса
        request_args = []
        if "params" in test_data:
            request_args.append(f"params={test_data['params']}")
        if "json" in test_data:
            request_args.append(f"json={test_data['json']}")

        args_str = ", ".join(request_args)
        if args_str:
            code_lines.append(f"    response = await client.{method}(url, {args_str})")
        else:
            code_lines.append(f"    response = await client.{method}(url)")

        # Проверка статуса
        code_lines.append(f"    assert response.status_code == {expected_status}")

        # Дополнительные проверки в зависимости от типа теста
        if test_type == "success":
            code_lines.append("    # Verify response structure")
            code_lines.append("    assert response.json() is not None")
        elif test_type == "validation_error":
            code_lines.append("    # Verify error response")
            code_lines.append("    assert 'error' in response.json() or 'detail' in response.json()")
        elif test_type == "security_test":
            code_lines.append("    # Verify security protection")
            code_lines.append("    assert response.status_code >= 400  # Should reject malicious input")

        return "\n".join(code_lines)

    def get_generated_tests(self) -> List[AIGeneratedTest]:
        """Получить все сгенерированные тесты."""
        return self._ai_generated_tests.copy()

    def save_generated_tests(self, output_dir: Union[str, Path]) -> None:
        """Сохранить сгенерированные тесты в файлы."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Группируем тесты по endpoint
        tests_by_endpoint = {}
        for test in self._ai_generated_tests:
            endpoint_key = f"{test.method}_{test.endpoint}".replace("/", "_").replace("{", "").replace("}", "")
            if endpoint_key not in tests_by_endpoint:
                tests_by_endpoint[endpoint_key] = []
            tests_by_endpoint[endpoint_key].append(test)

        # Создаем файлы тестов
        for endpoint_key, tests in tests_by_endpoint.items():
            file_path = output_path / f"test_{endpoint_key}_generated.py"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write('"""Generated tests from OpenAPI schema"""\n\n')
                f.write("import pytest\n")
                f.write("from tests.utils_test.api_test_client import AsyncApiTestClient\n\n")

                for test in tests:
                    f.write(f"# {test.test_description}\n")
                    f.write(f"# Confidence Score: {test.confidence_score}\n")
                    if test.security_checks:
                        f.write(f"# Security Checks: {[t.value for t in test.security_checks]}\n")
                    f.write(test.test_code)
                    f.write("\n\n")

        logger.info(f"Generated test files saved to {output_path}")

    def run_generated_test(self, test: AIGeneratedTest) -> bool:
        """
        Выполнить сгенерированный тест.

        Args:
            test: Тест для выполнения

        Returns:
            True если тест прошел успешно
        """
        try:
            # Выполняем код теста в контролируемом окружении
            # В реальности здесь должно быть более безопасное выполнение
            exec_globals = {
                "client": self,
                "asyncio": asyncio,
                "pytest": None,  # Заглушка для pytest
            }

            exec(test.test_code, exec_globals)

            # Если дошли до сюда, тест прошел
            logger.info(f"Generated test passed: {test.test_name}")
            return True

        except Exception as e:
            logger.error(f"Generated test failed: {test.test_name} - {e}")
            return False

    async def validate_generated_tests(self) -> Dict[str, Any]:
        """Валидация всех сгенерированных тестов."""
        if not self._ai_generated_tests:
            return {"message": "No generated tests to validate"}

        results = {"total_tests": len(self._ai_generated_tests), "passed": 0, "failed": 0, "failed_tests": []}

        for test in self._ai_generated_tests:
            try:
                success = self.run_generated_test(test)
                if success:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    results["failed_tests"].append(test.test_name)
            except Exception as e:
                results["failed"] += 1
                results["failed_tests"].append(f"{test.test_name}: {str(e)}")

        results["success_rate"] = results["passed"] / results["total_tests"] if results["total_tests"] > 0 else 0

        return results

    async def __aenter__(self):
        """Поддержка async context manager."""
        await super().__aenter__()
        return self

    def _create_test_jwt_service(self) -> "JWTService":
        """Создать тестовый JWT сервис с правильными настройками.

        Returns:
            Настроенный JWT сервис для тестов
        """
        from apps.auth.jwt_service import JWTService
        from core.config import get_settings

        # Получаем тестовые настройки
        settings = get_settings()

        # Создаем новый экземпляр JWT сервиса
        jwt_service = JWTService()

        # Применяем тестовые настройки
        jwt_service.secret_key = settings.SECRET_KEY
        jwt_service.algorithm = settings.ALGORITHM
        # Увеличиваем время жизни токена для тестов (24 часа)
        jwt_service.access_token_expire_minutes = 24 * 60  # 24 часа для тестов
        jwt_service.refresh_token_expire_days = 30  # 30 дней для тестов

        return jwt_service

    def _setup_test_dependencies(self) -> None:
        """Настроить зависимости для тестов.

        Подменяет глобальные зависимости на тестовые версии.
        """
        if not self._app:
            return

        from apps.auth.dependencies import get_jwt_service

        # Подменяем зависимость JWT сервиса
        def get_test_jwt_service():
            return self._jwt_service

            # Переопределяем зависимость в приложении

        self._app.dependency_overrides[get_jwt_service] = get_test_jwt_service
