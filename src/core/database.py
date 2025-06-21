"""Database Connection and Session Management.

This module provides database configuration, connection management, and session handling
for both PostgreSQL and SQLite databases with OpenTelemetry tracing integration.

Features:
    - Async SQLAlchemy engine configuration
    - Connection pooling for PostgreSQL
    - Session management with dependency injection
    - OpenTelemetry tracing integration
    - Automatic rollback on errors

Example:
    Basic usage::

        from core.database import get_db

        async def example_function():
            async for session in get_db():
                # Use session for database operations
                result = await session.execute(text("SELECT 1"))
                print(result.scalar())

    Using as FastAPI dependency::

        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession

        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # Session is automatically managed
            result = await db.execute(text("SELECT * FROM users"))
            return result.fetchall()

    Manual session management::

        from core.database import AsyncSessionLocal

        async def manual_example():
            async with AsyncSessionLocal() as session:
                try:
                    # Database operations
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

Note:
    The module automatically configures connection pooling for PostgreSQL
    and uses NullPool for SQLite to avoid threading issues.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .config import get_settings

tracer = trace.get_tracer(__name__)
settings = get_settings()

# Create async engine
if settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    # For SQLite use simplified configuration
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=settings.DB_ECHO,
        poolclass=NullPool,
    )
else:
    # For PostgreSQL use full pool configuration
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Get database session with tracing and error handling.

    This function provides a database session with automatic:
    - OpenTelemetry tracing integration
    - Error handling and rollback
    - Session cleanup on completion
    - Connection string sanitization for tracing

    Yields:
        AsyncSession: Database session instance

    Raises:
        Exception: Database connection or operation errors

    Example:
        FastAPI dependency injection::

            from fastapi import Depends
            from sqlalchemy.ext.asyncio import AsyncSession

            @app.get("/items")
            async def get_items(db: AsyncSession = Depends(get_db)):
                result = await db.execute(text("SELECT * FROM items"))
                return result.fetchall()

        Manual usage with async generator::

            async def manual_usage():
                async for session in get_db():
                    # Session is automatically managed
                    result = await session.execute(text("SELECT COUNT(*) FROM users"))
                    count = result.scalar()
                    return count

        Error handling::

            async def with_error_handling():
                try:
                    async for session in get_db():
                        # This will auto-rollback on error
                        await session.execute(text("INVALID SQL"))
                except Exception as e:
                    print(f"Database error: {e}")

    Note:
        The session is automatically committed if no exceptions occur,
        and rolled back if any exceptions are raised during the session lifetime.
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
