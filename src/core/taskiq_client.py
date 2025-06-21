"""TaskIQ Client Configuration and Broker Setup.

This module provides TaskIQ broker configuration with Redis backend support
and fallback to in-memory broker for development. It handles broker creation,
event handlers, and task result management.

Features:
    - Redis-based task queue with async result backend
    - Automatic fallback to in-memory broker for development
    - Event handlers for worker and client lifecycle
    - Task result and status retrieval utilities
    - Connection pool management

Example:
    Basic usage with tasks::

        from core.taskiq_client import broker
        from core.tasks import example_task

        # Send task to queue
        task_result = await example_task.kiq(10, 5)

        # Get result when ready
        result = await task_result.wait_result()

    Checking task status::

        from core.taskiq_client import get_task_status

        status = await get_task_status(task_id)
        if status["status"] == "completed":
            print(f"Result: {status['result']}")

    Manual result retrieval::

        from core.taskiq_client import get_task_result

        try:
            result = await get_task_result(task_id, timeout=30)
            print(f"Task completed: {result}")
        except TimeoutError:
            print("Task still running")

Note:
    The broker is automatically configured based on settings and
    falls back to InMemoryBroker if Redis is not available.
"""

import logging
from typing import Any

from taskiq import InMemoryBroker, TaskiqEvents
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from core.config import get_settings
from core.exceptions import CoreTaskiqBrokerError, CoreTaskiqValidationError

logger = logging.getLogger(__name__)
settings = get_settings()


def create_broker() -> ListQueueBroker | InMemoryBroker:
    """Create and configure TaskIQ broker with Redis backend.

    Creates a Redis-based TaskIQ broker with result backend support.
    Falls back to InMemoryBroker if Redis configuration is missing
    or connection fails.

    Returns:
        ListQueueBroker | InMemoryBroker: Configured TaskIQ broker

    Example:
        Manual broker creation::

            broker = create_broker()

            # Register task
            @broker.task
            async def my_task():
                return "Hello from task"

        Checking broker type::

            broker = create_broker()
            if isinstance(broker, ListQueueBroker):
                print("Using Redis broker")
            else:
                print("Using in-memory broker")

    Raises:
        ValueError: If TaskIQ URLs are not properly configured

    Note:
        Redis broker is preferred for production, while InMemoryBroker
        is suitable for development and testing.
    """
    try:
        if not settings.TASKIQ_BROKER_URL or not settings.TASKIQ_RESULT_BACKEND_URL:
            raise CoreTaskiqValidationError(task_name="broker_creation", validation_error="TaskIQ URLs not configured")

        # Create Redis broker
        broker = ListQueueBroker(
            url=settings.TASKIQ_BROKER_URL,
            max_connection_pool_size=settings.DB_POOL_SIZE,
        )

        # Add result backend
        result_backend: RedisAsyncResultBackend = RedisAsyncResultBackend(
            redis_url=settings.TASKIQ_RESULT_BACKEND_URL,
        )
        broker = broker.with_result_backend(result_backend)

        logger.info(f"TaskIQ Redis broker initialized: {settings.TASKIQ_BROKER_URL}")
        return broker

    except Exception as e:
        logger.warning(f"Failed to initialize Redis broker: {e}. Using InMemoryBroker.")
        # Fallback to InMemoryBroker for development
        return InMemoryBroker()


# Create global broker instance
broker = create_broker()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def worker_startup() -> None:
    """Handle worker startup event.

    Called when a TaskIQ worker process starts up.
    Useful for initializing worker-specific resources.

    Example:
        Adding custom worker startup logic::

            @broker.on_event(TaskiqEvents.WORKER_STARTUP)
            async def my_worker_startup():
                logger.info("Custom worker initialization")
                await initialize_worker_database_pool()
    """
    logger.info("TaskIQ worker started")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def worker_shutdown() -> None:
    """Handle worker shutdown event.

    Called when a TaskIQ worker process shuts down.
    Useful for cleanup and resource deallocation.

    Example:
        Adding custom worker shutdown logic::

            @broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
            async def my_worker_shutdown():
                logger.info("Custom worker cleanup")
                await cleanup_worker_resources()
    """
    logger.info("TaskIQ worker stopped")


@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def client_startup() -> None:
    """Handle client startup event.

    Called when TaskIQ client (web application) starts up.
    Useful for initializing client-specific resources.

    Example:
        Adding custom client startup logic::

            @broker.on_event(TaskiqEvents.CLIENT_STARTUP)
            async def my_client_startup():
                logger.info("Custom client initialization")
                await initialize_task_monitoring()
    """
    logger.info("TaskIQ client started")


@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def client_shutdown() -> None:
    """Handle client shutdown event.

    Called when TaskIQ client (web application) shuts down.
    Useful for cleanup and graceful shutdown.

    Example:
        Adding custom client shutdown logic::

            @broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
            async def my_client_shutdown():
                logger.info("Custom client cleanup")
                await cleanup_client_resources()
    """
    logger.info("TaskIQ client stopped")


async def get_task_result(task_id: str, timeout: float | None = None) -> Any:
    """Get task result by task ID.

    Retrieves the result of a completed task from the result backend.
    Can optionally wait for task completion with a timeout.

    Args:
        task_id (str): Unique task identifier
        timeout (float | None): Maximum time to wait for result

    Returns:
        Any: Task execution result

    Raises:
        RuntimeError: If result backend is not configured
        TimeoutError: If task doesn't complete within timeout
        Exception: If task failed or result retrieval failed

    Example:
        Get completed task result::

            result = await get_task_result("task-123")
            print(f"Task result: {result}")

        Get result with timeout::

            try:
                result = await get_task_result("task-123", timeout=30.0)
                print(f"Task completed: {result}")
            except TimeoutError:
                print("Task timed out")
            except Exception as e:
                print(f"Task failed: {e}")

        Used with task queue::

            from core.tasks import example_task

            # Send task
            task_result = await example_task.kiq(10, 5)

            # Get result later
            result = await get_task_result(task_result.task_id)

    Note:
        This function requires a configured result backend.
        Use get_task_status() for status checking without exceptions.
    """
    if not broker.result_backend:
        raise CoreTaskiqBrokerError(broker_url="result_backend")

    return await broker.result_backend.get_result(
        task_id=task_id,
        with_logs=True,
    )


async def get_task_status(task_id: str) -> dict[str, Any]:
    """Get task status information by task ID.

    Safely retrieves task status without raising exceptions.
    Returns status information including completion state, result, and errors.

    Args:
        task_id (str): Unique task identifier

    Returns:
        dict[str, Any]: Task status information
            - status (str): Task status ("completed", "pending", "error", "unknown")
            - result (Any): Task result if completed
            - error (Any): Error information if failed
            - logs (Any): Task execution logs if available
            - message (str): Status message for pending/error states

    Example:
        Check task status::

            status = await get_task_status("task-123")

            if status["status"] == "completed":
                print(f"Result: {status['result']}")
            elif status["status"] == "pending":
                print("Task still running")
            elif status["status"] == "error":
                print(f"Task failed: {status['message']}")

        Status monitoring loop::

            import asyncio

            async def monitor_task(task_id: str):
                while True:
                    status = await get_task_status(task_id)
                    print(f"Status: {status['status']}")

                    if status["status"] in ["completed", "error"]:
                        break

                    await asyncio.sleep(1)

        Task result processing::

            status = await get_task_status(task_id)

            match status["status"]:
                case "completed":
                    process_result(status["result"])
                case "error":
                    handle_error(status["error"])
                case "pending":
                    schedule_retry_check(task_id)

    Note:
        This function never raises exceptions and always returns a status dict.
        Use this for safe status checking in web endpoints.
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
