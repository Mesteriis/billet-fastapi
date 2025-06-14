"""
Конфигурация логирования для pytest.

Этот файл должен быть импортирован в conftest.py для автоматической
настройки логирования при запуске тестов.
"""

import logging
import os
from typing import Generator

import pytest

from tests.utils_test.logging_config import TestLoggingConfig, setup_quiet_testing, setup_verbose_testing


def configure_test_logging() -> None:
    """Настройка логирования для pytest сессии."""
    # Проверяем переменные окружения
    test_log_level = os.getenv("TEST_LOG_LEVEL", "normal").lower()
    pytest_verbosity = os.getenv("PYTEST_VERBOSITY", "0")

    if test_log_level in ["quiet", "silent"] or pytest_verbosity == "0":
        setup_quiet_testing()
    elif test_log_level in ["verbose", "debug"] or int(pytest_verbosity) >= 2:
        setup_verbose_testing()
    else:
        # Стандартная настройка
        TestLoggingConfig.setup_test_logging(level=logging.INFO, quiet_mode=False, disable_external=True)


@pytest.fixture(scope="session", autouse=True)
def setup_logging_for_tests() -> Generator[None, None, None]:
    """Автоматическая настройка логирования для всех тестов."""
    configure_test_logging()
    yield
    # Cleanup при завершении сессии
    logging.shutdown()


@pytest.fixture
def quiet_logger() -> Generator[None, None, None]:
    """Фикстура для временного отключения логирования в конкретном тесте."""
    original_levels = {}

    # Сохраняем текущие уровни
    for logger_name in TestLoggingConfig.NOISY_LOGGERS.keys():
        logger = logging.getLogger(logger_name)
        original_levels[logger_name] = logger.level
        logger.setLevel(logging.CRITICAL)

    yield

    # Восстанавливаем уровни
    for logger_name, level in original_levels.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


@pytest.fixture
def verbose_logger() -> Generator[None, None, None]:
    """Фикстура для временного включения подробного логирования."""
    original_levels = {}

    # Сохраняем текущие уровни
    for logger_name in ["tests", "apps", "core", "tools"]:
        logger = logging.getLogger(logger_name)
        original_levels[logger_name] = logger.level
        logger.setLevel(logging.DEBUG)

    yield

    # Восстанавливаем уровни
    for logger_name, level in original_levels.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


@pytest.fixture
def capture_logs():
    """Фикстура для захвата логов в тесте."""
    import io
    import sys

    # Создаем StringIO для захвата логов
    log_capture = io.StringIO()

    # Создаем handler
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # Добавляем handler к root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    yield log_capture

    # Удаляем handler
    root_logger.removeHandler(handler)


def pytest_configure(config):
    """Хук pytest для настройки логирования."""
    # Отключаем логирование pytest по умолчанию если не в verbose режиме
    if config.getoption("verbose", 0) < 2:
        logging.getLogger("pytest").setLevel(logging.WARNING)
        logging.getLogger("_pytest").setLevel(logging.WARNING)

    # Настраиваем логирование
    configure_test_logging()


def pytest_runtest_setup(item):
    """Хук для настройки перед каждым тестом."""
    # Проверяем маркеры теста
    if item.get_closest_marker("quiet_logs"):
        TestLoggingConfig.silence_all_external()
    elif item.get_closest_marker("verbose_logs"):
        TestLoggingConfig.enable_debug_for(["tests", "apps", "core"])


# Дополнительные маркеры для pytest
def pytest_configure_markers(config):
    """Регистрация кастомных маркеров."""
    config.addinivalue_line("markers", "quiet_logs: отключить все внешние логеры для теста")
    config.addinivalue_line("markers", "verbose_logs: включить подробное логирование для теста")


# Функции для использования в тестах
def silence_noisy_loggers():
    """Быстрое отключение шумных логеров."""
    TestLoggingConfig.silence_all_external()


def enable_debug_logging():
    """Включение debug логирования для проектных модулей."""
    TestLoggingConfig.enable_debug_for(["tests", "apps", "core", "tools"])


def get_test_logger(name: str) -> logging.Logger:
    """Получить логер для тестов."""
    return TestLoggingConfig.create_test_logger(name)
