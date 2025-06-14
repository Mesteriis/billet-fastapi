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


@broker.task(task_name="send_email_notification")
async def send_email_notification(to: str, subject: str, body: str, priority: str = "normal") -> dict[str, str]:
    """Отправка email уведомления (заглушка).

    Args:
        to: Email получателя.
        subject: Тема письма.
        body: Тело письма.
        priority: Приоритет отправки (low, normal, high).

    Returns:
        dict: Результат отправки с информацией о статусе.
    """
    logger.info(f"Sending email to {to} with subject: {subject}")

    # Имитация отправки email
    await asyncio.sleep(2)  # Симуляция времени отправки

    return {
        "status": "sent",
        "recipient": to,
        "subject": subject,
        "sent_at": datetime.now().isoformat(),
        "priority": priority,
        "message_id": f"msg_{datetime.now().timestamp()}",
    }


@broker.task(task_name="process_file")
async def process_file(
    file_path: str, operation: str = "analyze", options: dict[str, str | int] | None = None
) -> dict[str, str]:
    """Обработка файла.

    Args:
        file_path: Путь к файлу для обработки.
        operation: Тип операции (analyze, compress, convert).
        options: Дополнительные опции обработки.

    Returns:
        dict: Результат обработки файла.
    """
    logger.info(f"Processing file {file_path} with operation: {operation}")

    if options is None:
        options = {}

    # Имитация обработки файла
    processing_time = options.get("processing_time", 3)
    if isinstance(processing_time, str):
        processing_time = int(processing_time)
    await asyncio.sleep(processing_time)

    return {
        "status": "completed",
        "file_path": file_path,
        "operation": operation,
        "processed_at": datetime.now().isoformat(),
        "file_size": str(options.get("file_size", "unknown")),
        "output_path": f"{file_path}.processed",
    }


@broker.task(task_name="fetch_external_data")
async def fetch_external_data(
    url: str, method: str = "GET", headers: dict[str, str] | None = None, timeout: int = 30
) -> dict[str, str | int | dict | list]:
    """Получение данных из внешнего API.

    Args:
        url: URL для запроса.
        method: HTTP метод для запроса.
        headers: HTTP заголовки.
        timeout: Таймаут запроса в секундах.

    Returns:
        dict: Данные от внешнего API или информация об ошибке.
    """
    logger.info(f"Fetching data from {url}")

    if headers is None:
        headers = {}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(method=method, url=url, headers=headers, timeout=timeout)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            data = response.json() if content_type.startswith("application/json") else response.text

            return {
                "status": "success",
                "url": url,
                "method": method,
                "status_code": response.status_code,
                "data": data,
                "fetched_at": datetime.now().isoformat(),
            }

    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        return {
            "status": "error",
            "error_type": "request_error",
            "error_message": str(e),
            "url": url,
            "fetched_at": datetime.now().isoformat(),
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e}")
        return {
            "status": "error",
            "error_type": "http_error",
            "status_code": e.response.status_code,
            "error_message": str(e),
            "url": url,
            "fetched_at": datetime.now().isoformat(),
        }


@broker.task(task_name="database_maintenance")
async def database_maintenance(
    operation: str = "cleanup", table_name: str | None = None, options: dict[str, str | int] | None = None
) -> dict[str, str | int]:
    """Выполнение операций обслуживания базы данных.

    Args:
        operation: Тип операции (cleanup, vacuum, analyze).
        table_name: Имя таблицы (если не указана, то для всей БД).
        options: Дополнительные опции для операции.

    Returns:
        dict: Результат операции обслуживания.
    """
    logger.info(f"Running database maintenance: {operation}")

    if options is None:
        options = {}

    # Имитация операций с БД
    await asyncio.sleep(5)  # Симуляция времени выполнения

    affected_rows = options.get("affected_rows", 100)
    if isinstance(affected_rows, str):
        affected_rows = int(affected_rows)

    return {
        "status": "completed",
        "operation": operation,
        "table_name": table_name or "all_tables",
        "affected_rows": affected_rows,
        "execution_time": "5.2 seconds",
        "completed_at": datetime.now().isoformat(),
    }


@broker.task(task_name="generate_report")
async def generate_report(
    report_type: str, date_from: str, date_to: str, format: str = "pdf", email_to: list[str] | None = None
) -> dict[str, str | int | list[str]]:
    """Генерация отчета.

    Args:
        report_type: Тип отчета для генерации.
        date_from: Начальная дата в формате ISO.
        date_to: Конечная дата в формате ISO.
        format: Формат отчета (pdf, xlsx, csv).
        email_to: Список email адресов для отправки отчета.

    Returns:
        dict: Результат генерации отчета.
    """
    logger.info(f"Generating {report_type} report from {date_from} to {date_to}")

    if email_to is None:
        email_to = []

    # Имитация генерации отчета
    await asyncio.sleep(10)  # Симуляция времени генерации

    report_name = f"{report_type}_{date_from}_{date_to}.{format}"

    result: dict[str, str | int | list[str]] = {
        "status": "completed",
        "report_type": report_type,
        "date_from": date_from,
        "date_to": date_to,
        "format": format,
        "report_name": report_name,
        "file_size": "2.5 MB",
        "generated_at": datetime.now().isoformat(),
    }

    # Если указаны email адреса, имитируем отправку
    if email_to:
        result["emails_sent"] = len(email_to)
        result["recipients"] = email_to

    return result


@broker.task(task_name="scheduled_backup")
async def scheduled_backup(
    backup_type: str = "full", compress: bool = True, retention_days: int = 30
) -> dict[str, str | int | bool]:
    """Создание резервной копии по расписанию.

    Args:
        backup_type: Тип резервной копии (full, incremental).
        compress: Флаг сжатия резервной копии.
        retention_days: Количество дней хранения резервных копий.

    Returns:
        dict: Результат создания резервной копии.
    """
    logger.info(f"Starting {backup_type} backup with compression: {compress}")

    # Имитация создания резервной копии
    await asyncio.sleep(15)  # Симуляция времени создания бэкапа

    backup_name = f"backup_{backup_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if compress:
        backup_name += ".gz"

    return {
        "status": "completed",
        "backup_type": backup_type,
        "backup_name": backup_name,
        "compressed": compress,
        "retention_days": retention_days,
        "file_size": "150 MB" if backup_type == "full" else "25 MB",
        "created_at": datetime.now().isoformat(),
    }


@broker.task(task_name="test_task")
async def test_task(message: str = "Hello, TaskIQ!") -> dict[str, str]:
    """Простая тестовая задача для проверки работы TaskIQ.

    Args:
        message: Сообщение для обработки.

    Returns:
        dict: Результат выполнения тестовой задачи.
    """
    logger.info(f"Running test task with message: {message}")

    await asyncio.sleep(1)  # Небольшая задержка

    return {"status": "success", "message": message, "processed_at": datetime.now().isoformat()}


@broker.task(task_name="add_numbers")
async def add_numbers(a: int, b: int) -> dict[str, int | str]:
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
