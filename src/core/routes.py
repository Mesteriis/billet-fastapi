"""FastAPI routes for TaskIQ task management."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import Field

from tools.pydantic import BaseModel

from core.taskiq_client import get_task_result, get_task_status
from core.tasks import (
    database_maintenance,
    fetch_external_data,
    generate_report,
    process_file,
    scheduled_backup,
    send_email_notification,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# Pydantic модели для запросов
class EmailTaskRequest(BaseModel):
    to: str = Field(..., description="Email получателя")
    subject: str = Field(..., description="Тема письма")
    body: str = Field(..., description="Тело письма")
    priority: str = Field(default="normal", description="Приоритет (low, normal, high)")


class FileProcessingRequest(BaseModel):
    file_path: str = Field(..., description="Путь к файлу")
    operation: str = Field(default="analyze", description="Тип операции")
    options: dict[str, Any] | None = Field(default=None, description="Дополнительные опции")


class ExternalDataRequest(BaseModel):
    url: str = Field(..., description="URL для запроса")
    method: str = Field(default="GET", description="HTTP метод")
    headers: dict[str, str] | None = Field(default=None, description="HTTP заголовки")
    timeout: int = Field(default=30, description="Таймаут запроса")


class DatabaseMaintenanceRequest(BaseModel):
    operation: str = Field(default="cleanup", description="Тип операции")
    table_name: str | None = Field(default=None, description="Имя таблицы")
    options: dict[str, Any] | None = Field(default=None, description="Дополнительные опции")


class ReportGenerationRequest(BaseModel):
    report_type: str = Field(..., description="Тип отчета")
    date_from: str = Field(..., description="Дата начала периода")
    date_to: str = Field(..., description="Дата окончания периода")
    format: str = Field(default="pdf", description="Формат отчета")
    email_to: list[str] | None = Field(default=None, description="Список email для отправки")


class BackupRequest(BaseModel):
    backup_type: str = Field(default="full", description="Тип бэкапа")
    compress: bool = Field(default=True, description="Сжимать ли бэкап")
    retention_days: int = Field(default=30, description="Срок хранения бэкапов")


class TaskResponse(BaseModel):
    task_id: str = Field(..., description="ID задачи")
    status: str = Field(..., description="Статус задачи")
    message: str = Field(..., description="Сообщение")


# Роуты для запуска задач
@router.post("/email/send", response_model=TaskResponse)
async def send_email_task(request: EmailTaskRequest) -> TaskResponse:
    """Запустить задачу отправки email."""
    task = await send_email_notification.kiq(
        to=request.to, subject=request.subject, body=request.body, priority=request.priority
    )

    return TaskResponse(task_id=task.task_id, status="queued", message=f"Email task queued for {request.to}")


@router.post("/files/process", response_model=TaskResponse)
async def process_file_task(request: FileProcessingRequest) -> TaskResponse:
    """Запустить задачу обработки файла."""
    task = await process_file.kiq(file_path=request.file_path, operation=request.operation, options=request.options)

    return TaskResponse(
        task_id=task.task_id, status="queued", message=f"File processing task queued for {request.file_path}"
    )


@router.post("/external/fetch", response_model=TaskResponse)
async def fetch_external_data_task(request: ExternalDataRequest) -> TaskResponse:
    """Запустить задачу получения внешних данных."""
    task = await fetch_external_data.kiq(
        url=request.url, method=request.method, headers=request.headers, timeout=request.timeout
    )

    return TaskResponse(
        task_id=task.task_id, status="queued", message=f"External data fetch task queued for {request.url}"
    )


@router.post("/database/maintenance", response_model=TaskResponse)
async def database_maintenance_task(request: DatabaseMaintenanceRequest) -> TaskResponse:
    """Запустить задачу обслуживания базы данных."""
    task = await database_maintenance.kiq(
        operation=request.operation, table_name=request.table_name, options=request.options
    )

    return TaskResponse(
        task_id=task.task_id, status="queued", message=f"Database maintenance task queued: {request.operation}"
    )


@router.post("/reports/generate", response_model=TaskResponse)
async def generate_report_task(request: ReportGenerationRequest) -> TaskResponse:
    """Запустить задачу генерации отчета."""
    task = await generate_report.kiq(
        report_type=request.report_type,
        date_from=request.date_from,
        date_to=request.date_to,
        format=request.format,
        email_to=request.email_to,
    )

    return TaskResponse(
        task_id=task.task_id, status="queued", message=f"Report generation task queued: {request.report_type}"
    )


@router.post("/backup/create", response_model=TaskResponse)
async def create_backup_task(request: BackupRequest) -> TaskResponse:
    """Запустить задачу создания резервной копии."""
    task = await scheduled_backup.kiq(
        backup_type=request.backup_type, compress=request.compress, retention_days=request.retention_days
    )

    return TaskResponse(task_id=task.task_id, status="queued", message=f"Backup task queued: {request.backup_type}")


# Роуты для управления задачами
@router.get("/status/{task_id}")
async def get_task_status_endpoint(task_id: str) -> dict[str, Any]:
    """Получить статус задачи."""
    try:
        status = await get_task_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{task_id}")
async def get_task_result_endpoint(task_id: str, timeout: float | None = None) -> dict[str, Any]:
    """Получить результат задачи."""
    try:
        result = await get_task_result(task_id, timeout)
        return {
            "task_id": task_id,
            "result": result.return_value if result else None,
            "error": result.error if result else None,
            "logs": result.log if result else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Проверка здоровья TaskIQ системы."""
    try:
        # Попробуем запустить простую задачу для проверки
        task = await send_email_notification.kiq(
            to="test@example.com", subject="Health Check", body="System health check", priority="low"
        )

        return {
            "status": "healthy",
            "broker": "connected",
            "test_task_id": task.task_id,
            "message": "TaskIQ system is operational",
        }
    except Exception as e:
        return {"status": "unhealthy", "broker": "disconnected", "error": str(e), "message": "TaskIQ system has issues"}


@router.get("/")
async def list_available_tasks() -> dict[str, Any]:
    """Получить список доступных задач."""
    return {
        "available_tasks": [
            {
                "name": "send_email_notification",
                "description": "Отправка email уведомления",
                "endpoint": "/tasks/email/send",
            },
            {"name": "process_file", "description": "Обработка файла", "endpoint": "/tasks/files/process"},
            {
                "name": "fetch_external_data",
                "description": "Получение данных из внешнего API",
                "endpoint": "/tasks/external/fetch",
            },
            {
                "name": "database_maintenance",
                "description": "Обслуживание базы данных",
                "endpoint": "/tasks/database/maintenance",
            },
            {"name": "generate_report", "description": "Генерация отчета", "endpoint": "/tasks/reports/generate"},
            {"name": "scheduled_backup", "description": "Создание резервной копии", "endpoint": "/tasks/backup/create"},
        ],
        "management_endpoints": [
            {"endpoint": "/tasks/status/{task_id}", "description": "Получить статус задачи"},
            {"endpoint": "/tasks/result/{task_id}", "description": "Получить результат задачи"},
            {"endpoint": "/tasks/health", "description": "Проверка здоровья системы"},
        ],
    }
