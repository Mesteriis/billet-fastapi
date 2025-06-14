"""
Пример использования системы логирования в тестах.
"""

import logging

import pytest
from tests.conftest_logging import enable_debug_logging, get_test_logger, silence_noisy_loggers
from tests.utils_test.api_test_client import AsyncApiTestClient
from tests.utils_test.logging_config import TestLoggingConfig, setup_quiet_testing, setup_verbose_testing


class TestLoggingSystem:
    """Тесты системы логирования."""

    def test_quiet_logging_setup(self):
        """Тест тихого режима логирования."""
        setup_quiet_testing()

        # Проверяем что внешние логеры отключены
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level >= logging.WARNING

        # Проверяем что проектные логеры работают
        test_logger = logging.getLogger("tests")
        assert test_logger.level <= logging.ERROR

    def test_verbose_logging_setup(self):
        """Тест подробного режима логирования."""
        setup_verbose_testing()

        # Проверяем что логеры включены
        test_logger = logging.getLogger("tests")
        assert test_logger.level <= logging.DEBUG

    def test_custom_logger_creation(self):
        """Тест создания кастомного логера."""
        logger = get_test_logger("custom_test")
        assert logger.name == "tests.custom_test"
        assert isinstance(logger, logging.Logger)

    def test_silence_noisy_loggers(self):
        """Тест отключения шумных логеров."""
        silence_noisy_loggers()

        # Проверяем что шумные логеры отключены
        for logger_name in ["httpx", "urllib3", "sqlalchemy"]:
            logger = logging.getLogger(logger_name)
            assert logger.disabled or logger.level >= logging.WARNING

    def test_enable_debug_logging(self):
        """Тест включения debug логирования."""
        enable_debug_logging()

        # Проверяем что проектные логеры в debug режиме
        for logger_name in ["tests", "apps", "core"]:
            logger = logging.getLogger(logger_name)
            assert logger.level <= logging.DEBUG

    @pytest.mark.quiet_logs
    def test_with_quiet_marker(self):
        """Тест с маркером тихого логирования."""
        # Этот тест должен работать с отключенными внешними логерами
        logger = get_test_logger("quiet_test")
        logger.info("Это сообщение должно быть видно")

        # Внешние логеры должны быть отключены
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.info("Это сообщение НЕ должно быть видно")

    @pytest.mark.verbose_logs
    def test_with_verbose_marker(self):
        """Тест с маркером подробного логирования."""
        # Этот тест должен работать с включенным debug логированием
        logger = get_test_logger("verbose_test")
        logger.debug("Это debug сообщение должно быть видно")

    def test_capture_logs_fixture(self, capture_logs):
        """Тест фикстуры захвата логов."""
        logger = get_test_logger("capture_test")
        test_message = "Тестовое сообщение для захвата"

        logger.info(test_message)

        # Проверяем что сообщение захвачено
        log_contents = capture_logs.getvalue()
        assert test_message in log_contents

    @pytest.mark.asyncio
    async def test_api_client_logging(self):
        """Тест логирования в AsyncApiTestClient."""
        # Настраиваем тихий режим для этого теста
        TestLoggingConfig.setup_test_logging(quiet_mode=True)

        # Создаем клиент (он должен использовать настроенное логирование)
        client = AsyncApiTestClient()

        # Проверяем что логер клиента настроен правильно
        assert hasattr(client, "logger")

        # Внешние логеры должны быть отключены
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level >= logging.WARNING or httpx_logger.disabled


class TestLoggingIntegration:
    """Интеграционные тесты логирования."""

    def test_environment_variable_configuration(self, monkeypatch):
        """Тест конфигурации через переменные окружения."""
        # Устанавливаем переменную окружения
        monkeypatch.setenv("TEST_LOG_LEVEL", "quiet")

        # Импортируем модуль заново чтобы применить настройки
        import importlib

        from tests.utils_test import logging_config

        importlib.reload(logging_config)

        # Проверяем что настройки применились
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level >= logging.WARNING

    def test_pytest_verbosity_integration(self, monkeypatch):
        """Тест интеграции с pytest verbosity."""
        monkeypatch.setenv("PYTEST_VERBOSITY", "2")

        # Импортируем модуль заново
        import importlib

        from tests.utils_test import logging_config

        importlib.reload(logging_config)

        # В verbose режиме проектные логеры должны быть в DEBUG
        test_logger = logging.getLogger("tests")
        assert test_logger.level <= logging.DEBUG

    def test_logging_with_different_levels(self):
        """Тест различных уровней логирования."""
        logger = get_test_logger("level_test")

        # Тестируем разные уровни
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # Все должно работать без ошибок
        assert True

    def test_logger_hierarchy(self):
        """Тест иерархии логеров."""
        # Создаем логеры на разных уровнях
        parent_logger = get_test_logger("parent")
        child_logger = get_test_logger("parent.child")
        grandchild_logger = get_test_logger("parent.child.grandchild")

        # Проверяем иерархию
        assert child_logger.parent == parent_logger
        assert grandchild_logger.parent == child_logger

    def test_concurrent_logging(self):
        """Тест логирования в многопоточной среде."""
        import threading
        import time

        results = []

        def log_messages(thread_id):
            logger = get_test_logger(f"thread_{thread_id}")
            for i in range(5):
                logger.info(f"Thread {thread_id}, message {i}")
                time.sleep(0.01)
            results.append(thread_id)

        # Создаем несколько потоков
        threads = []
        for i in range(3):
            thread = threading.Thread(target=log_messages, args=(i,))
            threads.append(thread)
            thread.start()

        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()

        # Проверяем что все потоки завершились
        assert len(results) == 3
        assert set(results) == {0, 1, 2}


# Пример использования в реальном тесте
class TestRealWorldExample:
    """Реальный пример использования логирования в тестах."""

    @pytest.mark.asyncio
    async def test_api_endpoint_with_logging(self):
        """Пример теста API endpoint с логированием."""
        # Настраиваем логирование для этого теста
        TestLoggingConfig.setup_test_logging(level=logging.INFO, quiet_mode=False, disable_external=True)

        logger = get_test_logger("api_test")
        logger.info("Начинаем тест API endpoint")

        try:
            # Создаем клиент
            client = AsyncApiTestClient()
            logger.info("Клиент создан успешно")

            # Здесь был бы реальный тест API
            # response = await client.get("/api/test")
            # logger.info(f"Получен ответ: {response.status_code}")

            logger.info("Тест завершен успешно")

        except Exception as e:
            logger.error(f"Ошибка в тесте: {e}")
            raise

    def test_performance_with_logging(self):
        """Пример теста производительности с логированием."""
        import time

        logger = get_test_logger("performance")

        start_time = time.time()
        logger.info("Начинаем тест производительности")

        # Имитируем работу
        time.sleep(0.1)

        end_time = time.time()
        duration = end_time - start_time

        logger.info(f"Тест завершен за {duration:.3f} секунд")

        # Проверяем производительность
        assert duration < 1.0, f"Тест слишком медленный: {duration:.3f}s"
