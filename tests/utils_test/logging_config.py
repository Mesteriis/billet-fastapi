"""
Конфигурация логирования для тестов.

Отключает шумные логеры из внешних пакетов и настраивает
оптимальное логирование для тестовой среды.
"""

import logging
import sys
from typing import Dict, List, Optional


class TestLoggingConfig:
    """Конфигурация логирования для тестовой среды."""

    # Логеры которые нужно отключить или понизить уровень
    NOISY_LOGGERS = {
        # HTTP клиенты
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        "urllib3": logging.WARNING,
        "requests": logging.WARNING,
        # WebSocket
        "websockets": logging.WARNING,
        "websockets.client": logging.WARNING,
        "websockets.server": logging.WARNING,
        "websockets.protocol": logging.WARNING,
        # Async/await
        "asyncio": logging.WARNING,
        "concurrent.futures": logging.WARNING,
        # FastAPI и связанные
        "fastapi": logging.WARNING,
        "uvicorn": logging.WARNING,
        "uvicorn.access": logging.WARNING,
        "uvicorn.error": logging.WARNING,
        "starlette": logging.WARNING,
        "starlette.routing": logging.WARNING,
        "starlette.middleware": logging.WARNING,
        # SQLAlchemy
        "sqlalchemy": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "sqlalchemy.pool": logging.WARNING,
        "sqlalchemy.dialects": logging.WARNING,
        "alembic": logging.WARNING,
        # Pydantic
        "pydantic": logging.WARNING,
        "pydantic.main": logging.WARNING,
        "pydantic.fields": logging.WARNING,
        # Тестирование
        "pytest": logging.WARNING,
        "pytest_asyncio": logging.WARNING,
        "_pytest": logging.WARNING,
        # Другие библиотеки
        "faker": logging.WARNING,
        "factory": logging.WARNING,
        "factory_boy": logging.WARNING,
        "multipart": logging.WARNING,
        "email_validator": logging.WARNING,
        "passlib": logging.WARNING,
        "jose": logging.WARNING,
        "cryptography": logging.WARNING,
        # Системные
        "root": logging.WARNING,
        "urllib3.connectionpool": logging.WARNING,
        "charset_normalizer": logging.WARNING,
    }

    # Логеры проекта которые должны работать
    PROJECT_LOGGERS = {
        "tests": logging.INFO,
        "apps": logging.INFO,
        "core": logging.INFO,
        "tools": logging.INFO,
    }

    @classmethod
    def setup_test_logging(
        cls,
        level: int = logging.INFO,
        format_string: Optional[str] = None,
        disable_external: bool = True,
        quiet_mode: bool = False,
    ) -> None:
        """
        Настройка логирования для тестов.

        Args:
            level: Уровень логирования для проектных логеров
            format_string: Формат сообщений (если None, используется простой)
            disable_external: Отключить внешние логеры
            quiet_mode: Тихий режим (только ERROR и выше)
        """
        if quiet_mode:
            level = logging.ERROR

        # Базовый формат для тестов
        if format_string is None:
            if quiet_mode:
                format_string = "%(levelname)s: %(message)s"
            else:
                format_string = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

        # Настраиваем root logger
        logging.basicConfig(level=level, format=format_string, datefmt="%H:%M:%S", force=True, stream=sys.stdout)

        if disable_external:
            cls._disable_noisy_loggers()

        cls._setup_project_loggers(level)

        # Специальная настройка для AsyncApiTestClient
        test_client_logger = logging.getLogger("tests.utils_test.api_test_client")
        test_client_logger.setLevel(logging.INFO if not quiet_mode else logging.ERROR)

    @classmethod
    def _disable_noisy_loggers(cls) -> None:
        """Отключение шумных логеров."""
        for logger_name, log_level in cls.NOISY_LOGGERS.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(log_level)

            # Полностью отключаем некоторые особо шумные
            if logger_name in ["httpcore", "urllib3.connectionpool", "charset_normalizer"]:
                logger.disabled = True

    @classmethod
    def _setup_project_loggers(cls, level: int) -> None:
        """Настройка логеров проекта."""
        for logger_name, log_level in cls.PROJECT_LOGGERS.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(min(level, log_level))

    @classmethod
    def silence_all_external(cls) -> None:
        """Полностью отключить все внешние логеры."""
        for logger_name in cls.NOISY_LOGGERS.keys():
            logger = logging.getLogger(logger_name)
            logger.disabled = True

    @classmethod
    def enable_debug_for(cls, logger_names: List[str]) -> None:
        """Включить DEBUG уровень для конкретных логеров."""
        for logger_name in logger_names:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            logger.disabled = False

    @classmethod
    def create_test_logger(cls, name: str, level: int = logging.INFO) -> logging.Logger:
        """Создать логер для тестов."""
        logger = logging.getLogger(f"tests.{name}")
        logger.setLevel(level)
        return logger


def setup_quiet_testing() -> None:
    """Быстрая настройка тихого режима для тестов."""
    TestLoggingConfig.setup_test_logging(level=logging.ERROR, quiet_mode=True, disable_external=True)


def setup_verbose_testing() -> None:
    """Настройка подробного логирования для отладки."""
    TestLoggingConfig.setup_test_logging(level=logging.DEBUG, quiet_mode=False, disable_external=False)


def setup_normal_testing() -> None:
    """Стандартная настройка для тестов."""
    TestLoggingConfig.setup_test_logging(level=logging.INFO, quiet_mode=False, disable_external=True)


# Автоматическая настройка при импорте
import os

# Проверяем переменные окружения для настройки
test_log_level = os.getenv("TEST_LOG_LEVEL", "normal").lower()

if test_log_level == "quiet":
    setup_quiet_testing()
elif test_log_level == "verbose":
    setup_verbose_testing()
elif test_log_level == "debug":
    setup_verbose_testing()
else:
    setup_normal_testing()


# Создаем основной логер для тестов
test_logger = TestLoggingConfig.create_test_logger("main")
