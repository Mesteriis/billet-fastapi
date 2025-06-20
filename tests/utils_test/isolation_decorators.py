"""
Декораторы для полной изоляции тестов от данных других тестов.

Предоставляет различные стратегии изоляции:
1. TransactionRollback - откат транзакций
2. DatabaseReset - полная очистка БД
3. SchemaIsolation - отдельная схема для каждого теста
4. CompleteIsolation - комбинированный подход

Usage:
    @isolated_test()  # По умолчанию - transaction rollback
    async def test_my_function():
        pass

    @database_reset_test()  # Полная очистка БД
    async def test_with_fresh_db():
        pass

    @schema_isolated_test()  # Отдельная схема
    async def test_with_own_schema():
        pass
"""

import asyncio
import functools
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional, TypeVar, Union

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from tests.core.base.test_repo.modesl_for_test import TestBaseModel

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger("test_session")


class IsolationError(Exception):
    """Исключение для ошибок изоляции тестов."""

    pass


class TestIsolationManager:
    """Менеджер для управления различными стратегиями изоляции тестов."""

    def __init__(self):
        self._active_schemas: Dict[str, str] = {}
        self._rollback_points: Dict[str, Any] = {}

    async def create_isolated_schema(self, session: AsyncSession, test_name: str) -> str:
        """Создает изолированную схему для теста."""
        schema_name = f"test_{test_name}_{uuid.uuid4().hex[:8]}"

        try:
            # Создаем схему
            await session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

            # Устанавливаем search_path для этой схемы
            await session.execute(text(f'SET search_path TO "{schema_name}", public'))

            # Создаем таблицы в новой схеме
            async with session.bind.begin() as conn:
                # Temporarily set schema in metadata
                old_schema = TestBaseModel.metadata.schema
                TestBaseModel.metadata.schema = schema_name

                try:
                    await conn.run_sync(TestBaseModel.metadata.create_all)
                finally:
                    TestBaseModel.metadata.schema = old_schema

            self._active_schemas[test_name] = schema_name
            logger.debug(f"✅ Создана изолированная схема: {schema_name}")

            return schema_name

        except Exception as e:
            logger.error(f"❌ Ошибка создания схемы {schema_name}: {e}")
            raise IsolationError(f"Не удалось создать изолированную схему: {e}")

    async def cleanup_isolated_schema(self, session: AsyncSession, test_name: str) -> None:
        """Удаляет изолированную схему после теста."""
        schema_name = self._active_schemas.get(test_name)
        if not schema_name:
            return

        try:
            # Сбрасываем search_path
            await session.execute(text("SET search_path TO public"))

            # Удаляем схему
            await session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
            await session.commit()

            del self._active_schemas[test_name]
            logger.debug(f"✅ Удалена изолированная схема: {schema_name}")

        except Exception as e:
            # Критическая ошибка - не скрываем через логгер!
            raise IsolationError(f"Не удалось удалить изолированную схему {schema_name}: {e}") from e

    async def create_savepoint(self, session: AsyncSession, test_name: str) -> str:
        """Создает точку сохранения (savepoint) для отката."""
        savepoint_name = f"sp_{test_name}_{uuid.uuid4().hex[:8]}"

        try:
            await session.execute(text(f'SAVEPOINT "{savepoint_name}"'))
            self._rollback_points[test_name] = savepoint_name
            logger.debug(f"✅ Создана точка сохранения: {savepoint_name}")

            return savepoint_name

        except Exception as e:
            logger.error(f"❌ Ошибка создания savepoint {savepoint_name}: {e}")
            raise IsolationError(f"Не удалось создать savepoint: {e}")

    async def rollback_to_savepoint(self, session: AsyncSession, test_name: str) -> None:
        """Откатывается к точке сохранения."""
        savepoint_name = self._rollback_points.get(test_name)
        if not savepoint_name:
            return

        try:
            await session.execute(text(f'ROLLBACK TO SAVEPOINT "{savepoint_name}"'))
            await session.execute(text(f'RELEASE SAVEPOINT "{savepoint_name}"'))

            del self._rollback_points[test_name]
            logger.debug(f"✅ Откат к точке сохранения: {savepoint_name}")

        except Exception as e:
            # Если savepoint не существует, просто удаляем его из списка
            if "does not exist" in str(e):
                if test_name in self._rollback_points:
                    del self._rollback_points[test_name]
                logger.debug(f"⚠️ Savepoint {savepoint_name} уже не существует, пропускаем откат")
                return
            # Для других ошибок - пробрасываем исключение
            raise IsolationError(f"Не удалось откатить к savepoint {savepoint_name}: {e}") from e

    async def full_database_reset(self, session: AsyncSession) -> None:
        """Полная очистка и пересоздание всех таблиц."""
        try:
            # Отключаем foreign key constraints для быстрой очистки
            if "postgresql" in str(session.bind.url):
                await session.execute(text("SET session_replication_role = replica"))

            # Удаляем все таблицы
            async with session.bind.begin() as conn:
                await conn.run_sync(TestBaseModel.metadata.drop_all)

            # Пересоздаем все таблицы
            async with session.bind.begin() as conn:
                await conn.run_sync(TestBaseModel.metadata.create_all)

            # Включаем обратно constraints
            if "postgresql" in str(session.bind.url):
                await session.execute(text("SET session_replication_role = DEFAULT"))

            await session.commit()
            logger.debug("✅ Полная очистка БД завершена")

        except Exception as e:
            logger.error(f"❌ Ошибка полной очистки БД: {e}")
            try:
                await session.rollback()
            except:
                pass
            raise IsolationError(f"Не удалось выполнить полную очистку БД: {e}")


# Глобальный экземпляр менеджера изоляции
isolation_manager = TestIsolationManager()


def _setup_factories_session(session: AsyncSession) -> None:
    """Настраивает сессию для всех доступных фабрик."""
    try:
        # Импортируем все фабрики
        from tests.core.base.test_repo.factories import (
            CategoryFactory,
            CommentFactory,
            PostFactory,
            ProfileFactory,
            TagFactory,
            TestCategoryFactory,
            TestCommentFactory,
            TestPostFactory,
            TestProfileFactory,
            TestTagFactory,
            TestUserFactory,
            UserFactory,
        )

        # Устанавливаем сессию для всех фабрик
        factories = [
            UserFactory,
            PostFactory,
            CategoryFactory,
            TagFactory,
            CommentFactory,
            ProfileFactory,
            TestUserFactory,
            TestPostFactory,
            TestCategoryFactory,
            TestTagFactory,
            TestCommentFactory,
            TestProfileFactory,
        ]

        for factory in factories:
            if hasattr(factory, "_meta") and hasattr(factory._meta, "sqlalchemy_session"):
                factory._meta.sqlalchemy_session = session

    except ImportError:
        # Если фабрики не найдены, игнорируем ошибку
        pass


def _cleanup_factories_session() -> None:
    """Очищает сессии в фабриках."""
    try:
        from tests.core.base.test_repo.factories import (
            CategoryFactory,
            CommentFactory,
            PostFactory,
            ProfileFactory,
            TagFactory,
            TestCategoryFactory,
            TestCommentFactory,
            TestPostFactory,
            TestProfileFactory,
            TestTagFactory,
            TestUserFactory,
            UserFactory,
        )

        factories = [
            UserFactory,
            PostFactory,
            CategoryFactory,
            TagFactory,
            CommentFactory,
            ProfileFactory,
            TestUserFactory,
            TestPostFactory,
            TestCategoryFactory,
            TestTagFactory,
            TestCommentFactory,
            TestProfileFactory,
        ]

        for factory in factories:
            if hasattr(factory, "_meta") and hasattr(factory._meta, "sqlalchemy_session"):
                factory._meta.sqlalchemy_session = None

    except ImportError:
        pass


def isolated_test(
    strategy: str = "transaction", cleanup_on_error: bool = True, verbose: bool = False
) -> Callable[[F], F]:
    """
    Декоратор для полной изоляции теста от данных других тестов.

    Args:
        strategy: Стратегия изоляции ("transaction", "database_reset", "schema")
        cleanup_on_error: Очищать ли данные при ошибке теста
        verbose: Подробное логирование

    Usage:
        @isolated_test(strategy="transaction")
        async def test_my_function(async_session):
            # Тест будет полностью изолирован
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Извлекаем session из аргументов
            session = None
            for arg in args:
                if isinstance(arg, AsyncSession):
                    session = arg
                    break

            for key, value in kwargs.items():
                if isinstance(value, AsyncSession):
                    session = value
                    break

            if session is None:
                # Пытаемся найти session в setup_test_models фикстуре
                if "setup_test_models" in kwargs:
                    session = kwargs["setup_test_models"]
                else:
                    raise IsolationError("Не найдена AsyncSession в аргументах теста")

            test_name = f"{func.__module__}.{func.__name__}".replace(".", "_")

            # Настраиваем все доступные фабрики для работы с сессией
            _setup_factories_session(session)

            if verbose:
                logger.info(f"🔒 Начало изолированного теста: {test_name} (strategy: {strategy})")

            try:
                if strategy == "transaction":
                    await isolation_manager.create_savepoint(session, test_name)
                elif strategy == "schema":
                    await isolation_manager.create_isolated_schema(session, test_name)
                elif strategy == "database_reset":
                    await isolation_manager.full_database_reset(session)
                else:
                    raise IsolationError(f"Неизвестная стратегия изоляции: {strategy}")

                # Выполняем тест
                result = await func(*args, **kwargs)

                if verbose:
                    logger.info(f"✅ Тест {test_name} завершен успешно")

                return result

            except Exception as e:
                if verbose:
                    logger.error(f"❌ Ошибка в тесте {test_name}: {e}")

                if not cleanup_on_error:
                    raise

                # Принудительная очистка при ошибке
                try:
                    if strategy == "transaction":
                        await isolation_manager.rollback_to_savepoint(session, test_name)
                    elif strategy == "schema":
                        await isolation_manager.cleanup_isolated_schema(session, test_name)
                    elif strategy == "database_reset":
                        await isolation_manager.full_database_reset(session)
                except Exception as cleanup_error:
                    # Ошибка очистки критична - не скрываем!
                    raise IsolationError(
                        f"Критическая ошибка очистки после теста {test_name}: {cleanup_error}"
                    ) from cleanup_error

                raise

            finally:
                # Финальная очистка
                try:
                    if strategy == "transaction":
                        await isolation_manager.rollback_to_savepoint(session, test_name)
                    elif strategy == "schema":
                        await isolation_manager.cleanup_isolated_schema(session, test_name)
                    # database_reset стратегия не требует финальной очистки

                    if verbose:
                        logger.info(f"🧹 Очистка после теста {test_name} завершена")

                except Exception as cleanup_error:
                    # Ошибка финальной очистки критична - не скрываем!
                    raise IsolationError(
                        f"Критическая ошибка финальной очистки теста {test_name}: {cleanup_error}"
                    ) from cleanup_error

        return wrapper

    return decorator


def transaction_isolated_test(cleanup_on_error: bool = True, verbose: bool = False) -> Callable[[F], F]:
    """
    Декоратор для изоляции теста через откат транзакций (самый быстрый).

    Использует savepoints для создания вложенных транзакций.
    Все изменения автоматически откатываются после теста.

    Usage:
        @transaction_isolated_test()
        async def test_my_function(async_session):
            # Все изменения будут откачены
            pass
    """
    return isolated_test(strategy="transaction", cleanup_on_error=cleanup_on_error, verbose=verbose)


def database_reset_test(cleanup_on_error: bool = True, verbose: bool = False) -> Callable[[F], F]:
    """
    Декоратор для полной очистки БД перед тестом (самый надежный).

    Полностью удаляет и пересоздает все таблицы перед каждым тестом.
    Гарантирует 100% чистоту данных, но работает медленнее.

    Usage:
        @database_reset_test()
        async def test_with_fresh_db(async_session):
            # Полностью чистая БД
            pass
    """
    return isolated_test(strategy="database_reset", cleanup_on_error=cleanup_on_error, verbose=verbose)


def schema_isolated_test(cleanup_on_error: bool = True, verbose: bool = False) -> Callable[[F], F]:
    """
    Декоратор для изоляции теста через отдельную схему (баланс скорости и изоляции).

    Создает отдельную схему PostgreSQL для каждого теста.
    Обеспечивает полную изоляцию при умеренных затратах производительности.

    Usage:
        @schema_isolated_test()
        async def test_with_own_schema(async_session):
            # Отдельная схема только для этого теста
            pass
    """
    return isolated_test(strategy="schema", cleanup_on_error=cleanup_on_error, verbose=verbose)


def complete_isolation_test(verbose: bool = False) -> Callable[[F], F]:
    """
    Декоратор для максимальной изоляции теста (комбинированный подход).

    Комбинирует несколько стратегий:
    1. Создает отдельную схему
    2. Использует savepoints для дополнительного контроля
    3. Полная очистка при любых ошибках

    Usage:
        @complete_isolation_test()
        async def test_maximum_isolation(async_session):
            # Максимальная изоляция данных
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Извлекаем session
            session = None
            for arg in args:
                if isinstance(arg, AsyncSession):
                    session = arg
                    break

            for key, value in kwargs.items():
                if isinstance(value, AsyncSession):
                    session = value
                    break

            if "setup_test_models" in kwargs:
                session = kwargs["setup_test_models"]

            if session is None:
                raise IsolationError("Не найдена AsyncSession в аргументах теста")

            test_name = f"{func.__module__}.{func.__name__}".replace(".", "_")

            # Настраиваем все доступные фабрики для работы с сессией
            _setup_factories_session(session)

            if verbose:
                logger.info(f"🔒🔒 Начало теста с максимальной изоляцией: {test_name}")

            schema_created = False
            savepoint_created = False

            try:
                # 1. Создаем отдельную схему
                await isolation_manager.create_isolated_schema(session, test_name)
                schema_created = True

                # 2. Создаем savepoint для дополнительного контроля
                await isolation_manager.create_savepoint(session, test_name)
                savepoint_created = True

                # 3. Выполняем тест
                result = await func(*args, **kwargs)

                if verbose:
                    logger.info(f"✅✅ Тест с максимальной изоляцией {test_name} завершен успешно")

                return result

            except Exception as e:
                if verbose:
                    logger.error(f"❌❌ Ошибка в тесте с максимальной изоляцией {test_name}: {e}")

                # Экстренная полная очистка при любой ошибке
                try:
                    await isolation_manager.full_database_reset(session)
                    if verbose:
                        logger.info(f"🧹🧹 Выполнена экстренная полная очистка для {test_name}")
                except Exception as cleanup_error:
                    # Критическая ошибка экстренной очистки - не скрываем!
                    raise IsolationError(
                        f"Критическая ошибка экстренной очистки для {test_name}: {cleanup_error}"
                    ) from cleanup_error

                raise

            finally:
                # Финальная очистка в правильном порядке
                try:
                    if savepoint_created:
                        await isolation_manager.rollback_to_savepoint(session, test_name)

                    if schema_created:
                        await isolation_manager.cleanup_isolated_schema(session, test_name)

                    if verbose:
                        logger.info(f"🧹🧹 Финальная очистка максимальной изоляции для {test_name} завершена")

                except Exception as cleanup_error:
                    # Ошибка финальной очистки критична - не скрываем!
                    raise IsolationError(
                        f"Критическая ошибка финальной очистки максимальной изоляции для {test_name}: {cleanup_error}"
                    ) from cleanup_error

        return wrapper

    return decorator


@asynccontextmanager
async def isolated_data_context(session: AsyncSession, strategy: str = "transaction", verbose: bool = False):
    """
    Контекстный менеджер для изоляции блока кода с данными.

    Используется когда нужно изолировать не весь тест, а только его часть.

    Usage:
        async def test_partial_isolation(async_session):
            # Обычная часть теста
            user = await create_user()

            async with isolated_data_context(async_session, strategy="transaction"):
                # Изолированная часть теста
                isolated_user = await create_isolated_user()
                # Все изменения будут откачены при выходе из блока
    """
    context_id = f"context_{uuid.uuid4().hex[:8]}"

    # Настраиваем все доступные фабрики для работы с сессией
    _setup_factories_session(session)

    if verbose:
        logger.info(f"🔒 Начало изолированного контекста: {context_id} (strategy: {strategy})")

    try:
        if strategy == "transaction":
            await isolation_manager.create_savepoint(session, context_id)
        elif strategy == "schema":
            await isolation_manager.create_isolated_schema(session, context_id)
        elif strategy == "database_reset":
            await isolation_manager.full_database_reset(session)
        else:
            raise IsolationError(f"Неизвестная стратегия изоляции: {strategy}")

        yield session

        if verbose:
            logger.info(f"✅ Изолированный контекст {context_id} завершен успешно")

    except Exception as e:
        if verbose:
            logger.error(f"❌ Ошибка в изолированном контексте {context_id}: {e}")
        raise

    finally:
        try:
            if strategy == "transaction":
                await isolation_manager.rollback_to_savepoint(session, context_id)
            elif strategy == "schema":
                await isolation_manager.cleanup_isolated_schema(session, context_id)

            if verbose:
                logger.info(f"🧹 Очистка изолированного контекста {context_id} завершена")

        except Exception as cleanup_error:
            # Ошибка очистки контекста критична - не скрываем!
            raise IsolationError(
                f"Критическая ошибка очистки изолированного контекста {context_id}: {cleanup_error}"
            ) from cleanup_error


# Синонимы и алиасы для удобства использования
transaction_isolated = transaction_isolated_test
database_reset = database_reset_test
schema_isolated = schema_isolated_test
complete_isolation = complete_isolation_test
isolated = isolated_test

# Экспорт всех декораторов
__all__ = [
    "isolated_test",
    "transaction_isolated_test",
    "database_reset_test",
    "schema_isolated_test",
    "complete_isolation_test",
    "isolated_data_context",
    "IsolationError",
    "TestIsolationManager",
    # Синонимы
    "transaction_isolated",
    "database_reset",
    "schema_isolated",
    "complete_isolation",
    "isolated",
]
# Экспорт всех декораторов
__all__ = [
    "isolated_test",
    "transaction_isolated_test",
    "database_reset_test",
    "schema_isolated_test",
    "complete_isolation_test",
    "isolated_data_context",
    "IsolationError",
    "TestIsolationManager",
    # Синонимы
    "transaction_isolated",
    "database_reset",
    "schema_isolated",
    "complete_isolation",
    "isolated",
]
