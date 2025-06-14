"""Тесты для TaskIQ клиента."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from taskiq import InMemoryBroker
from taskiq_redis import ListQueueBroker

from core.taskiq_client import broker, create_broker, get_task_result, get_task_status


class TestCreateBroker:
    """Тесты для создания брокера."""

    @patch("core.taskiq_client.get_settings")
    def test_create_broker_redis_success(self, mock_get_settings):
        """Тест успешного создания Redis брокера."""
        # Настройка мока для настроек
        mock_settings = MagicMock()
        mock_settings.TASKIQ_BROKER_URL = "redis://localhost:6379/1"
        mock_settings.TASKIQ_RESULT_BACKEND_URL = "redis://localhost:6379/2"
        mock_settings.DB_POOL_SIZE = 10
        mock_get_settings.return_value = mock_settings

        with (
            patch("core.taskiq_client.ListQueueBroker") as mock_broker_class,
            patch("core.taskiq_client.RedisAsyncResultBackend") as mock_backend_class,
        ):
            # Настройка моков
            mock_broker_instance = MagicMock()
            mock_backend_instance = MagicMock()
            mock_broker_class.return_value = mock_broker_instance
            mock_backend_class.return_value = mock_backend_instance
            mock_broker_instance.with_result_backend.return_value = mock_broker_instance

            result = create_broker()

            # Проверки
            mock_broker_class.assert_called_once_with(
                url="redis://localhost:6379/1",
                max_connection_pool_size=10,
            )
            mock_backend_class.assert_called_once_with(
                redis_url="redis://localhost:6379/2",
            )
            mock_broker_instance.with_result_backend.assert_called_once_with(mock_backend_instance)
            assert result == mock_broker_instance

    @patch("core.taskiq_client.get_settings")
    @patch("core.taskiq_client.logger")
    def test_create_broker_redis_failure_fallback_to_memory(self, mock_logger, mock_get_settings):
        """Тест fallback к InMemoryBroker при ошибке Redis."""
        # Настройка мока для настроек
        mock_settings = MagicMock()
        mock_settings.TASKIQ_BROKER_URL = "redis://invalid:6379/1"
        mock_settings.TASKIQ_RESULT_BACKEND_URL = "redis://invalid:6379/2"
        mock_settings.DB_POOL_SIZE = 10
        mock_get_settings.return_value = mock_settings

        with (
            patch("core.taskiq_client.ListQueueBroker") as mock_broker_class,
            patch("core.taskiq_client.InMemoryBroker") as mock_memory_broker_class,
        ):
            # Настройка мока для выброса исключения
            mock_broker_class.side_effect = Exception("Connection failed")
            mock_memory_instance = MagicMock()
            mock_memory_broker_class.return_value = mock_memory_instance

            result = create_broker()

            # Проверки
            mock_logger.warning.assert_called_once()
            mock_memory_broker_class.assert_called_once()
            assert result == mock_memory_instance


class TestTaskResultAndStatus:
    """Тесты для получения результатов и статуса задач."""

    @pytest.fixture
    def mock_broker_with_backend(self):
        """Мок брокера с result backend."""
        mock_broker = MagicMock()
        mock_backend = MagicMock()
        mock_broker.result_backend = mock_backend
        return mock_broker, mock_backend

    @pytest.mark.asyncio
    async def test_get_task_result_success(self, mock_broker_with_backend):
        """Тест успешного получения результата задачи."""
        mock_broker, mock_backend = mock_broker_with_backend

        # Настройка мока
        mock_result = MagicMock()
        mock_result.return_value = {"status": "completed", "data": "test"}
        mock_backend.get_result = AsyncMock(return_value=mock_result)

        with patch("core.taskiq_client.broker", mock_broker):
            result = await get_task_result("task123", timeout=60)

            assert result == mock_result
            mock_backend.get_result.assert_called_once_with(
                task_id="task123",
                with_logs=True,
                timeout=60,
            )

    @pytest.mark.asyncio
    async def test_get_task_result_no_backend(self):
        """Тест ошибки при отсутствии result backend."""
        mock_broker = MagicMock()
        mock_broker.result_backend = None

        with patch("core.taskiq_client.broker", mock_broker):
            with pytest.raises(RuntimeError, match="Result backend not configured"):
                await get_task_result("task123")

    @pytest.mark.asyncio
    async def test_get_task_result_with_default_timeout(self, mock_broker_with_backend):
        """Тест получения результата с таймаутом по умолчанию."""
        mock_broker, mock_backend = mock_broker_with_backend

        mock_result = MagicMock()
        mock_backend.get_result = AsyncMock(return_value=mock_result)

        with patch("core.taskiq_client.broker", mock_broker), patch("core.taskiq_client.settings") as mock_settings:
            mock_settings.TASKIQ_TASK_TIMEOUT = 300

            await get_task_result("task123")

            mock_backend.get_result.assert_called_once_with(
                task_id="task123",
                with_logs=True,
                timeout=300,
            )

    @pytest.mark.asyncio
    async def test_get_task_status_completed(self, mock_broker_with_backend):
        """Тест получения статуса завершенной задачи."""
        mock_broker, mock_backend = mock_broker_with_backend

        # Настройка мока для завершенной задачи
        mock_result = MagicMock()
        mock_result.return_value = {"data": "completed"}
        mock_result.error = None
        mock_result.log = "Task completed successfully"
        mock_backend.get_result = AsyncMock(return_value=mock_result)

        with patch("core.taskiq_client.broker", mock_broker):
            status = await get_task_status("task123")

            expected = {
                "status": "completed",
                "result": {"data": "completed"},
                "error": None,
                "logs": "Task completed successfully",
            }
            assert status == expected

    @pytest.mark.asyncio
    async def test_get_task_status_with_error(self, mock_broker_with_backend):
        """Тест получения статуса задачи с ошибкой."""
        mock_broker, mock_backend = mock_broker_with_backend

        # Настройка мока для задачи с ошибкой
        mock_result = MagicMock()
        mock_result.return_value = None
        mock_result.error = "Division by zero"
        mock_result.log = "Error occurred during execution"
        mock_backend.get_result = AsyncMock(return_value=mock_result)

        with patch("core.taskiq_client.broker", mock_broker):
            status = await get_task_status("task123")

            expected = {
                "status": "completed",
                "result": None,
                "error": "Division by zero",
                "logs": "Error occurred during execution",
            }
            assert status == expected

    @pytest.mark.asyncio
    async def test_get_task_status_pending(self, mock_broker_with_backend):
        """Тест получения статуса выполняющейся задачи."""
        mock_broker, mock_backend = mock_broker_with_backend

        # Настройка мока для timeout (задача еще выполняется)
        mock_backend.get_result = AsyncMock(side_effect=TimeoutError())

        with patch("core.taskiq_client.broker", mock_broker):
            status = await get_task_status("task123")

            expected = {"status": "pending", "message": "Task is still running"}
            assert status == expected

    @pytest.mark.asyncio
    async def test_get_task_status_error(self, mock_broker_with_backend):
        """Тест получения статуса при ошибке."""
        mock_broker, mock_backend = mock_broker_with_backend

        # Настройка мока для общей ошибки
        mock_backend.get_result = AsyncMock(side_effect=Exception("Connection error"))

        with patch("core.taskiq_client.broker", mock_broker):
            status = await get_task_status("task123")

            expected = {"status": "error", "message": "Connection error"}
            assert status == expected

    @pytest.mark.asyncio
    async def test_get_task_status_no_backend(self):
        """Тест получения статуса при отсутствии result backend."""
        mock_broker = MagicMock()
        mock_broker.result_backend = None

        with patch("core.taskiq_client.broker", mock_broker):
            status = await get_task_status("task123")

            expected = {"status": "unknown", "message": "Result backend not configured"}
            assert status == expected


class TestBrokerEvents:
    """Тесты для событий брокера."""

    @pytest.mark.asyncio
    @patch("core.taskiq_client.logger")
    async def test_worker_startup_event(self, mock_logger):
        """Тест события запуска воркера."""
        from core.taskiq_client import worker_startup

        await worker_startup()
        mock_logger.info.assert_called_once_with("TaskIQ worker started")

    @pytest.mark.asyncio
    @patch("core.taskiq_client.logger")
    async def test_worker_shutdown_event(self, mock_logger):
        """Тест события остановки воркера."""
        from core.taskiq_client import worker_shutdown

        await worker_shutdown()
        mock_logger.info.assert_called_once_with("TaskIQ worker stopped")

    @pytest.mark.asyncio
    @patch("core.taskiq_client.logger")
    async def test_client_startup_event(self, mock_logger):
        """Тест события запуска клиента."""
        from core.taskiq_client import client_startup

        await client_startup()
        mock_logger.info.assert_called_once_with("TaskIQ client started")

    @pytest.mark.asyncio
    @patch("core.taskiq_client.logger")
    async def test_client_shutdown_event(self, mock_logger):
        """Тест события остановки клиента."""
        from core.taskiq_client import client_shutdown

        await client_shutdown()
        mock_logger.info.assert_called_once_with("TaskIQ client stopped")


class TestBrokerIntegration:
    """Интеграционные тесты для брокера."""

    def test_broker_is_created(self):
        """Тест, что брокер создается при импорте модуля."""

        assert broker is not None
        # В тестовой среде ожидаем InMemoryBroker
        assert isinstance(broker, (InMemoryBroker, ListQueueBroker))

    def test_broker_has_required_methods(self):
        """Тест, что брокер имеет необходимые методы."""

        assert hasattr(broker, "startup")
        assert hasattr(broker, "shutdown")
        assert hasattr(broker, "task")

    @pytest.mark.asyncio
    async def test_broker_startup_shutdown(self):
        """Тест запуска и остановки брокера."""

        # Тест запуска
        await broker.startup()

        # Тест остановки
        await broker.shutdown()

        # Не должно быть исключений


@pytest.fixture
def mock_settings():
    """Фикстура для мока настроек."""
    mock = MagicMock()
    mock.TASKIQ_BROKER_URL = "redis://localhost:6379/1"
    mock.TASKIQ_RESULT_BACKEND_URL = "redis://localhost:6379/2"
    mock.DB_POOL_SIZE = 10
    mock.TASKIQ_TASK_TIMEOUT = 300
    return mock


class TestConfigurationIntegration:
    """Тесты интеграции с конфигурацией."""

    @patch("core.taskiq_client.get_settings")
    def test_settings_integration(self, mock_get_settings, mock_settings):
        """Тест интеграции с настройками."""
        mock_get_settings.return_value = mock_settings

        # Пересоздаем модуль для тестирования
        with patch("core.taskiq_client.ListQueueBroker") as mock_broker_class:
            mock_broker_instance = MagicMock()
            mock_broker_class.return_value = mock_broker_instance
            mock_broker_instance.with_result_backend.return_value = mock_broker_instance

            from core.taskiq_client import create_broker

            broker = create_broker()

            # Проверяем, что настройки используются правильно
            mock_broker_class.assert_called_with(
                url="redis://localhost:6379/1",
                max_connection_pool_size=10,
            )
