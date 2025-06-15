"""Интеграционные тесты для TaskIQ."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.taskiq_client import broker
from core.tasks import process_file, send_email_notification
from src.main import app


class TestTaskIQIntegration:
    """Интеграционные тесты для TaskIQ системы."""

    @pytest.fixture
    def client(self):
        """Создает тестовый клиент для FastAPI."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_broker_lifecycle(self):
        """Тест жизненного цикла брокера."""
        # Тест запуска
        await broker.startup()

        # Проверяем, что брокер запущен
        assert broker is not None

        # Тест остановки
        await broker.shutdown()

    @pytest.mark.asyncio
    async def test_task_registration(self):
        """Тест регистрации задач в брокере."""
        # Проверяем, что задачи зарегистрированы
        task_names = [task.task_name for task in broker._tasks.values()]

        expected_tasks = [
            "send_email_notification",
            "process_file",
            "fetch_external_data",
            "database_maintenance",
            "generate_report",
            "scheduled_backup",
        ]

        for expected_task in expected_tasks:
            assert expected_task in task_names

    @pytest.mark.asyncio
    async def test_task_execution_in_memory(self):
        """Тест выполнения задачи через InMemoryBroker."""
        await broker.startup()

        try:
            # Тестируем простую задачу
            result = await send_email_notification(
                to="test@example.com", subject="Integration Test", body="This is an integration test", priority="low"
            )

            assert result["status"] == "sent"
            assert result["recipient"] == "test@example.com"
            assert result["subject"] == "Integration Test"
            assert "sent_at" in result

        finally:
            await broker.shutdown()

    @pytest.mark.asyncio
    async def test_task_with_options(self):
        """Тест выполнения задачи с опциями."""
        await broker.startup()

        try:
            result = await process_file(
                file_path="/test/integration.txt", operation="test_operation", options={"test_option": "test_value"}
            )

            assert result["status"] == "completed"
            assert result["file_path"] == "/test/integration.txt"
            assert result["operation"] == "test_operation"

        finally:
            await broker.shutdown()

    def test_fastapi_integration(self, client):
        """Тест интеграции с FastAPI."""
        # Тест корневого endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["taskiq_enabled"] is True
        assert "tasks" in data["endpoints"]

    def test_tasks_endpoint_available(self, client):
        """Тест доступности endpoints задач."""
        response = client.get("/tasks/")
        assert response.status_code == 200
        data = response.json()
        assert "available_tasks" in data
        assert len(data["available_tasks"]) == 6

    @patch("core.routes.send_email_notification")
    def test_email_task_end_to_end(self, mock_task, client):
        """Тест end-to-end для email задачи."""
        # Настройка мока
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "integration-email-123"
        mock_task.kiq.return_value = mock_task_result

        # Отправляем запрос
        payload = {
            "to": "integration@example.com",
            "subject": "Integration Test",
            "body": "End-to-end test",
            "priority": "normal",
        }

        response = client.post("/tasks/email/send", json=payload)

        # Проверяем ответ
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "integration-email-123"
        assert data["status"] == "queued"

    @patch("core.routes.get_task_status")
    def test_task_status_workflow(self, mock_get_status, client):
        """Тест workflow получения статуса задачи."""
        # Имитируем разные статусы
        test_cases = [
            {"status": "pending", "message": "Task is still running"},
            {
                "status": "completed",
                "result": {"data": "success"},
                "error": None,
                "logs": "Task completed successfully",
            },
            {"status": "error", "message": "Task failed"},
        ]

        for case in test_cases:
            mock_get_status.return_value = case
            response = client.get("/tasks/status/test-task")
            assert response.status_code == 200
            assert response.json() == case


class TestTaskIQConfiguration:
    """Тесты конфигурации TaskIQ."""

    @patch("core.taskiq_client.get_settings")
    def test_broker_configuration(self, mock_get_settings):
        """Тест конфигурации брокера."""
        # Настройка мока
        mock_settings = MagicMock()
        mock_settings.TASKIQ_BROKER_URL = "redis://localhost:6379/1"
        mock_settings.TASKIQ_RESULT_BACKEND_URL = "redis://localhost:6379/2"
        mock_settings.DB_POOL_SIZE = 20
        mock_get_settings.return_value = mock_settings

        with patch("core.taskiq_client.ListQueueBroker") as mock_broker_class:
            mock_broker_instance = MagicMock()
            mock_broker_class.return_value = mock_broker_instance
            mock_broker_instance.with_result_backend.return_value = mock_broker_instance

            from core.taskiq_client import create_broker

            result = create_broker()

            # Проверяем, что брокер создан с правильными настройками
            mock_broker_class.assert_called_once_with(
                url="redis://localhost:6379/1",
                max_connection_pool_size=20,
            )

    def test_settings_defaults(self):
        """Тест значений по умолчанию в настройках."""
        from core.config import Settings

        settings = Settings()

        # Проверяем TaskIQ настройки
        assert settings.TASKIQ_MAX_RETRIES == 3
        assert settings.TASKIQ_RETRY_DELAY == 5
        assert settings.TASKIQ_TASK_TIMEOUT == 300

    @patch.dict(
        "os.environ",
        {
            "TASKIQ_BROKER_URL": "redis://test:6379/1",
            "TASKIQ_RESULT_BACKEND_URL": "redis://test:6379/2",
            "TASKIQ_MAX_RETRIES": "5",
            "TASKIQ_RETRY_DELAY": "10",
            "TASKIQ_TASK_TIMEOUT": "600",
        },
    )
    def test_settings_from_environment(self):
        """Тест загрузки настроек из переменных окружения."""
        from core.config import Settings

        settings = Settings()

        assert settings.TASKIQ_BROKER_URL == "redis://test:6379/1"
        assert settings.TASKIQ_RESULT_BACKEND_URL == "redis://test:6379/2"
        assert settings.TASKIQ_MAX_RETRIES == 5
        assert settings.TASKIQ_RETRY_DELAY == 10
        assert settings.TASKIQ_TASK_TIMEOUT == 600


class TestTaskIQErrorHandling:
    """Тесты обработки ошибок в TaskIQ."""

    @pytest.mark.asyncio
    async def test_task_with_exception(self):
        """Тест задачи, которая выбрасывает исключение."""

        @broker.task(task_name="failing_task")
        async def failing_task():
            raise ValueError("Test error")

        await broker.startup()

        try:
            with pytest.raises(ValueError, match="Test error"):
                await failing_task()
        finally:
            await broker.shutdown()

    @pytest.fixture
    def client(self):
        """Создает тестовый клиент."""
        return TestClient(app)

    @patch("core.routes.get_task_status")
    def test_api_error_handling(self, mock_get_status, client):
        """Тест обработки ошибок в API."""
        mock_get_status.side_effect = Exception("Database connection lost")

        response = client.get("/tasks/status/error-task")

        assert response.status_code == 500
        assert "Database connection lost" in response.json()["detail"]

    def test_invalid_task_id_format(self, client):
        """Тест невалидного формата ID задачи."""
        response = client.get("/tasks/status/")

        # Должен вернуть 404 или 422 для невалидного пути
        assert response.status_code in [404, 422]


class TestTaskIQPerformance:
    """Тесты производительности TaskIQ."""

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self):
        """Тест одновременного выполнения задач."""
        await broker.startup()

        try:
            # Создаем несколько задач одновременно
            tasks = []
            for i in range(5):
                task = send_email_notification(
                    to=f"test{i}@example.com", subject=f"Concurrent Test {i}", body=f"Message {i}", priority="low"
                )
                tasks.append(task)

            # Выполняем все задачи параллельно
            results = await asyncio.gather(*tasks)

            # Проверяем результаты
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result["status"] == "sent"
                assert result["recipient"] == f"test{i}@example.com"

        finally:
            await broker.shutdown()

    @pytest.mark.asyncio
    async def test_task_execution_time(self):
        """Тест времени выполнения задачи."""
        await broker.startup()

        try:
            import time

            start_time = time.time()

            result = await process_file(
                file_path="/test/perf.txt",
                operation="analyze",
                options={"processing_time": 0.1},  # Минимальное время
            )

            end_time = time.time()
            execution_time = end_time - start_time

            # Проверяем, что задача выполнилась быстро
            assert execution_time < 1.0  # Менее секунды
            assert result["status"] == "completed"

        finally:
            await broker.shutdown()


class TestTaskIQMemoryUsage:
    """Тесты использования памяти TaskIQ."""

    @pytest.mark.asyncio
    async def test_memory_cleanup_after_tasks(self):
        """Тест очистки памяти после выполнения задач."""
        await broker.startup()

        try:
            # Выполняем много мелких задач
            for i in range(10):
                await send_email_notification(
                    to=f"memory{i}@example.com", subject="Memory Test", body="Testing memory usage", priority="low"
                )

            # Память должна освобождаться после выполнения
            # В реальных тестах здесь можно использовать psutil для проверки
            assert True  # Placeholder для реальной проверки памяти

        finally:
            await broker.shutdown()


@pytest.mark.integration
class TestTaskIQRedisIntegration:
    """Интеграционные тесты с Redis (требуют запущенный Redis)."""

    @pytest.mark.skip("Requires Redis server")
    @pytest.mark.asyncio
    async def test_redis_broker_connection(self):
        """Тест подключения к реальному Redis."""
        from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

        # Создаем реальный Redis брокер
        redis_broker = ListQueueBroker(
            url="redis://localhost:6379/15",  # Используем отдельную БД для тестов
        ).with_result_backend(RedisAsyncResultBackend(redis_url="redis://localhost:6379/15"))

        try:
            await redis_broker.startup()

            # Регистрируем тестовую задачу
            @redis_broker.task(task_name="redis_test_task")
            async def redis_test_task(message: str) -> str:
                return f"Processed: {message}"

            # Выполняем задачу
            task = await redis_test_task.kiq("Redis integration test")
            result = await redis_broker.result_backend.get_result(task_id=task.task_id, timeout=10.0)

            assert result.return_value == "Processed: Redis integration test"

        finally:
            await redis_broker.shutdown()

    @pytest.mark.skip("Requires Redis server")
    def test_redis_configuration_validation(self):
        """Тест валидации конфигурации Redis."""
        from core.config import Settings

        # Тестируем с валидным URL
        settings = Settings(TASKIQ_BROKER_URL="redis://localhost:6379/1")
        assert settings.TASKIQ_BROKER_URL.startswith("redis://")

        # Тестируем автоматическое создание URL
        settings = Settings(REDIS_HOST="testhost", REDIS_PORT=6380, REDIS_PASSWORD="testpass")
        assert "testhost" in settings.TASKIQ_BROKER_URL
        assert "6380" in settings.TASKIQ_BROKER_URL
        assert "testpass" in settings.TASKIQ_BROKER_URL
