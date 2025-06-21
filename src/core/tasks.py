"""Background Task Definitions for TaskIQ.

This module contains all TaskIQ task definitions for background processing.
Tasks are registered with the broker and can be executed asynchronously
by worker processes.

Available tasks:
    - example_task: Simple arithmetic task for demonstration

Example:
    Calling a task directly::

        from core.tasks import example_task

        # Direct execution (synchronous)
        result = await example_task(5, 3)
        print(result)  # {"result": 8, "operation": "addition", ...}

    Sending task to broker::

        from core.tasks import example_task

        # Send to TaskIQ broker (asynchronous execution)
        task_result = await example_task.kiq(5, 3)

        # Get result when task completes
        result = await task_result.wait_result()

    Using in web endpoints::

        from fastapi import APIRouter
        from core.tasks import example_task

        router = APIRouter()

        @router.post("/calculate")
        async def calculate(a: int, b: int):
            # Queue task for background processing
            task_result = await example_task.kiq(a, b)
            return {"task_id": task_result.task_id}

Note:
    Tasks are automatically registered with the broker when this module is imported.
    Workers must import this module to process the tasks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import httpx

from core.config import get_settings
from core.taskiq_client import broker

logger = logging.getLogger(__name__)
settings = get_settings()


@broker.task(task_name="example_task")
async def example_task(a: int, b: int) -> dict[str, int | str]:
    """Simple arithmetic task for demonstration purposes.

    Performs addition of two numbers and returns a detailed result.
    This task demonstrates basic TaskIQ functionality and can be used
    for testing worker connectivity.

    Args:
        a (int): First number to add
        b (int): Second number to add

    Returns:
        dict[str, int | str]: Calculation result with metadata
            - a (int): First input number
            - b (int): Second input number
            - result (int): Sum of a and b
            - operation (str): Operation performed ("addition")
            - calculated_at (str): ISO timestamp of calculation

    Example:
        Direct execution::

            result = await example_task(10, 5)
            print(result)
            # {
            #     "a": 10,
            #     "b": 5,
            #     "result": 15,
            #     "operation": "addition",
            #     "calculated_at": "2024-01-15T10:30:00"
            # }

        Background execution::

            # Send to worker
            task_result = await example_task.kiq(10, 5)

            # Wait for completion
            result = await task_result.wait_result()

        Error handling::

            try:
                result = await example_task.kiq(a, b)
                data = await result.wait_result(timeout=30)
            except asyncio.TimeoutError:
                print("Task timed out")
            except Exception as e:
                print(f"Task failed: {e}")

    Note:
        This task includes logging for monitoring and debugging purposes.
        The calculated_at timestamp uses the worker's local time.
    """
    logger.info(f"Adding {a} + {b}")

    result = a + b

    return {"a": a, "b": b, "result": result, "operation": "addition", "calculated_at": datetime.now().isoformat()}
