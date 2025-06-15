"""TaskIQ tasks definitions."""

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
    """Простая задача для сложения двух чисел.

    Args:
        a: Первое число.
        b: Второе число.

    Returns:
        dict: Результат сложения.
    """
    logger.info(f"Adding {a} + {b}")

    result = a + b

    return {"a": a, "b": b, "result": result, "operation": "addition", "calculated_at": datetime.now().isoformat()}
