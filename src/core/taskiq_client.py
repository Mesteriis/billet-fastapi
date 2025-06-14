"""TaskIQ client configuration and broker setup."""

import logging
from typing import Any

from taskiq import InMemoryBroker, TaskiqEvents
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def create_broker() -> ListQueueBroker | InMemoryBroker:
    """Create and configure TaskIQ broker."""
    try:
        if not settings.TASKIQ_BROKER_URL or not settings.TASKIQ_RESULT_BACKEND_URL:
            raise ValueError("TaskIQ URLs not configured")

        # Создаем Redis брокер
        broker = ListQueueBroker(
            url=settings.TASKIQ_BROKER_URL,
            max_connection_pool_size=settings.DB_POOL_SIZE,
        )

        # Добавляем результат бэкенд
        result_backend: RedisAsyncResultBackend = RedisAsyncResultBackend(
            redis_url=settings.TASKIQ_RESULT_BACKEND_URL,
        )
        broker = broker.with_result_backend(result_backend)

        logger.info(f"TaskIQ Redis broker initialized: {settings.TASKIQ_BROKER_URL}")
        return broker

    except Exception as e:
        logger.warning(f"Failed to initialize Redis broker: {e}. Using InMemoryBroker.")
        # Fallback к InMemoryBroker для разработки
        return InMemoryBroker()


# Создаем глобальный экземпляр брокера
broker = create_broker()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def worker_startup() -> None:
    """Выполняется при запуске воркера."""
    logger.info("TaskIQ worker started")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def worker_shutdown() -> None:
    """Выполняется при остановке воркера."""
    logger.info("TaskIQ worker stopped")


@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def client_startup() -> None:
    """Выполняется при запуске клиента."""
    logger.info("TaskIQ client started")


@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def client_shutdown() -> None:
    """Выполняется при остановке клиента."""
    logger.info("TaskIQ client stopped")


async def get_task_result(task_id: str, timeout: float | None = None) -> Any:
    """
    Получить результат задачи по ID.

    Args:
        task_id: ID задачи
        timeout: Таймаут ожидания результата

    Returns:
        Результат выполнения задачи
    """
    if not broker.result_backend:
        raise RuntimeError("Result backend not configured")

    return await broker.result_backend.get_result(
        task_id=task_id,
        with_logs=True,
    )


async def get_task_status(task_id: str) -> dict[str, Any]:
    """
    Получить статус задачи по ID.

    Args:
        task_id: ID задачи

    Returns:
        Информация о статусе задачи
    """
    if not broker.result_backend:
        return {"status": "unknown", "message": "Result backend not configured"}

    try:
        result = await broker.result_backend.get_result(
            task_id=task_id,
            with_logs=True,
        )
        return {
            "status": "completed",
            "result": result.return_value if result else None,
            "error": result.error if result else None,
            "logs": result.log if result else None,
        }
    except TimeoutError:
        return {"status": "pending", "message": "Task is still running"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
