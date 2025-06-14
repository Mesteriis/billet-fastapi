"""
Настройка подключения к базе данных.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .config import get_settings

tracer = trace.get_tracer(__name__)
settings = get_settings()

# Создание асинхронного движка
if settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    # Для SQLite используем упрощенную конфигурацию
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=settings.DB_ECHO,
        poolclass=NullPool,
    )
else:
    # Для PostgreSQL используем полную конфигурацию пула
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Получить сессию базы данных.

    Yields:
        AsyncSession: Сессия базы данных
    """
    with tracer.start_as_current_span("database.get_db") as span:
        async with AsyncSessionLocal() as session:
            try:
                span.set_attribute("db.connection_string", settings.SQLALCHEMY_DATABASE_URI.split("@")[0] + "@[hidden]")
                yield session
            except Exception as e:
                span.set_attribute("error", str(e))
                await session.rollback()
                raise
            finally:
                await session.close()


async def close_db() -> None:
    """Закрыть подключение к базе данных."""
    with tracer.start_as_current_span("database.close_db"):
        await engine.dispose()
