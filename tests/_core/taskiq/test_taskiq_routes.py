"""Тесты для TaskIQ API routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.routes import BackupRequest, EmailTaskRequest, ExternalDataRequest, FileProcessingRequest, router


@pytest.fixture
def app():
    """Создает FastAPI приложение для тестов."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Создает тестовый клиент."""
    return TestClient(app)


class TestEmailTaskEndpoint:
    """Тесты для endpoint отправки email."""

    @patch("core.routes.send_email_notification")
    def test_send_email_task_success(self, mock_task, client):
        """Тест успешной отправки email задачи."""
        # Настройка мока
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "email-task-123"
        mock_task.kiq.return_value = mock_task_result

        payload = {"to": "test@example.com", "subject": "Test Subject", "body": "Test Body", "priority": "high"}

        response = client.post("/tasks/email/send", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "email-task-123"
        assert data["status"] == "queued"
        assert "Email task queued for test@example.com" in data["message"]

        # Проверяем, что задача была вызвана с правильными параметрами
        mock_task.kiq.assert_called_once_with(
            to="test@example.com", subject="Test Subject", body="Test Body", priority="high"
        )

    def test_send_email_task_validation_error(self, client):
        """Тест ошибки валидации для email задачи."""
        payload = {
            "subject": "Test Subject",
            "body": "Test Body",
            # Отсутствует обязательное поле "to"
        }

        response = client.post("/tasks/email/send", json=payload)
        assert response.status_code == 422

    @patch("core.routes.send_email_notification")
    def test_send_email_task_default_priority(self, mock_task, client):
        """Тест email задачи с приоритетом по умолчанию."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "email-task-456"
        mock_task.kiq.return_value = mock_task_result

        payload = {"to": "default@example.com", "subject": "Default Priority", "body": "Default message"}

        response = client.post("/tasks/email/send", json=payload)
        assert response.status_code == 200

        mock_task.kiq.assert_called_once_with(
            to="default@example.com",
            subject="Default Priority",
            body="Default message",
            priority="normal",  # Значение по умолчанию
        )


class TestFileProcessingEndpoint:
    """Тесты для endpoint обработки файлов."""

    @patch("core.routes.process_file")
    def test_process_file_task_success(self, mock_task, client):
        """Тест успешной обработки файла."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "file-task-789"
        mock_task.kiq.return_value = mock_task_result

        payload = {
            "file_path": "/test/document.pdf",
            "operation": "compress",
            "options": {"quality": 85, "format": "jpg"},
        }

        response = client.post("/tasks/files/process", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "file-task-789"
        assert data["status"] == "queued"
        assert "/test/document.pdf" in data["message"]

        mock_task.kiq.assert_called_once_with(
            file_path="/test/document.pdf", operation="compress", options={"quality": 85, "format": "jpg"}
        )

    @patch("core.routes.process_file")
    def test_process_file_task_minimal_payload(self, mock_task, client):
        """Тест обработки файла с минимальными параметрами."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "file-task-minimal"
        mock_task.kiq.return_value = mock_task_result

        payload = {"file_path": "/test/simple.txt"}

        response = client.post("/tasks/files/process", json=payload)
        assert response.status_code == 200

        mock_task.kiq.assert_called_once_with(
            file_path="/test/simple.txt",
            operation="analyze",  # Значение по умолчанию
            options=None,
        )


class TestExternalDataEndpoint:
    """Тесты для endpoint получения внешних данных."""

    @patch("core.routes.fetch_external_data")
    def test_fetch_external_data_success(self, mock_task, client):
        """Тест успешного получения внешних данных."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "fetch-task-abc"
        mock_task.kiq.return_value = mock_task_result

        payload = {
            "url": "https://api.example.com/data",
            "method": "POST",
            "headers": {"Authorization": "Bearer token123", "Content-Type": "application/json"},
            "timeout": 60,
        }

        response = client.post("/tasks/external/fetch", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "fetch-task-abc"
        assert "https://api.example.com/data" in data["message"]

        mock_task.kiq.assert_called_once_with(
            url="https://api.example.com/data",
            method="POST",
            headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
            timeout=60,
        )

    @patch("core.routes.fetch_external_data")
    def test_fetch_external_data_defaults(self, mock_task, client):
        """Тест получения данных с параметрами по умолчанию."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "fetch-task-default"
        mock_task.kiq.return_value = mock_task_result

        payload = {"url": "https://api.example.com/simple"}

        response = client.post("/tasks/external/fetch", json=payload)
        assert response.status_code == 200

        mock_task.kiq.assert_called_once_with(
            url="https://api.example.com/simple", method="GET", headers=None, timeout=30
        )


class TestDatabaseMaintenanceEndpoint:
    """Тесты для endpoint обслуживания базы данных."""

    @patch("core.routes.database_maintenance")
    def test_database_maintenance_success(self, mock_task, client):
        """Тест успешного обслуживания БД."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "db-task-xyz"
        mock_task.kiq.return_value = mock_task_result

        payload = {"operation": "vacuum", "table_name": "users", "options": {"full": True, "analyze": True}}

        response = client.post("/tasks/database/maintenance", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "db-task-xyz"
        assert "vacuum" in data["message"]

        mock_task.kiq.assert_called_once_with(
            operation="vacuum", table_name="users", options={"full": True, "analyze": True}
        )


class TestReportGenerationEndpoint:
    """Тесты для endpoint генерации отчетов."""

    @patch("core.routes.generate_report")
    def test_generate_report_with_email(self, mock_task, client):
        """Тест генерации отчета с отправкой email."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "report-task-123"
        mock_task.kiq.return_value = mock_task_result

        payload = {
            "report_type": "sales",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "format": "xlsx",
            "email_to": ["manager@example.com", "director@example.com"],
        }

        response = client.post("/tasks/reports/generate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "report-task-123"
        assert "sales" in data["message"]

        mock_task.kiq.assert_called_once_with(
            report_type="sales",
            date_from="2024-01-01",
            date_to="2024-01-31",
            format="xlsx",
            email_to=["manager@example.com", "director@example.com"],
        )

    @patch("core.routes.generate_report")
    def test_generate_report_without_email(self, mock_task, client):
        """Тест генерации отчета без email."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "report-task-456"
        mock_task.kiq.return_value = mock_task_result

        payload = {"report_type": "analytics", "date_from": "2024-02-01", "date_to": "2024-02-29"}

        response = client.post("/tasks/reports/generate", json=payload)
        assert response.status_code == 200

        mock_task.kiq.assert_called_once_with(
            report_type="analytics",
            date_from="2024-02-01",
            date_to="2024-02-29",
            format="pdf",  # Значение по умолчанию
            email_to=None,
        )


class TestBackupEndpoint:
    """Тесты для endpoint создания резервных копий."""

    @patch("core.routes.scheduled_backup")
    def test_create_backup_success(self, mock_task, client):
        """Тест успешного создания бэкапа."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "backup-task-def"
        mock_task.kiq.return_value = mock_task_result

        payload = {"backup_type": "incremental", "compress": False, "retention_days": 7}

        response = client.post("/tasks/backup/create", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "backup-task-def"
        assert "incremental" in data["message"]

        mock_task.kiq.assert_called_once_with(backup_type="incremental", compress=False, retention_days=7)


class TestTaskManagementEndpoints:
    """Тесты для endpoints управления задачами."""

    @patch("core.routes.get_task_status")
    def test_get_task_status_success(self, mock_get_status, client):
        """Тест получения статуса задачи."""
        mock_get_status.return_value = {
            "status": "completed",
            "result": {"data": "success"},
            "error": None,
            "logs": "Task completed",
        }

        response = client.get("/tasks/status/task123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"]["data"] == "success"

        mock_get_status.assert_called_once_with("task123")

    @patch("core.routes.get_task_status")
    def test_get_task_status_error(self, mock_get_status, client):
        """Тест ошибки получения статуса задачи."""
        mock_get_status.side_effect = Exception("Task not found")

        response = client.get("/tasks/status/invalid_task")

        assert response.status_code == 500
        assert "Task not found" in response.json()["detail"]

    @patch("core.routes.get_task_result")
    def test_get_task_result_success(self, mock_get_result, client):
        """Тест получения результата задачи."""
        mock_result_obj = MagicMock()
        mock_result_obj.return_value = {"status": "completed"}
        mock_result_obj.error = None
        mock_result_obj.log = "Task logs"
        mock_get_result.return_value = mock_result_obj

        response = client.get("/tasks/result/task456")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task456"
        assert data["result"] == {"status": "completed"}
        assert data["error"] is None
        assert data["logs"] == "Task logs"

        mock_get_result.assert_called_once_with("task456", None)

    @patch("core.routes.get_task_result")
    def test_get_task_result_with_timeout(self, mock_get_result, client):
        """Тест получения результата с таймаутом."""
        mock_result_obj = MagicMock()
        mock_result_obj.return_value = {"data": "test"}
        mock_result_obj.error = None
        mock_result_obj.log = None
        mock_get_result.return_value = mock_result_obj

        response = client.get("/tasks/result/task789?timeout=120")

        assert response.status_code == 200
        mock_get_result.assert_called_once_with("task789", 120.0)

    @patch("core.routes.get_task_result")
    def test_get_task_result_error(self, mock_get_result, client):
        """Тест ошибки получения результата задачи."""
        mock_get_result.side_effect = RuntimeError("Result backend not configured")

        response = client.get("/tasks/result/task999")

        assert response.status_code == 500
        assert "Result backend not configured" in response.json()["detail"]


class TestHealthAndInfoEndpoints:
    """Тесты для endpoints здоровья и информации."""

    @patch("core.routes.send_email_notification")
    def test_health_check_success(self, mock_task, client):
        """Тест успешной проверки здоровья."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "health-check-task"
        mock_task.kiq.return_value = mock_task_result

        response = client.get("/tasks/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["broker"] == "connected"
        assert data["test_task_id"] == "health-check-task"
        assert "operational" in data["message"]

        mock_task.kiq.assert_called_once_with(
            to="test@example.com", subject="Health Check", body="System health check", priority="low"
        )

    @patch("core.routes.send_email_notification")
    def test_health_check_failure(self, mock_task, client):
        """Тест неудачной проверки здоровья."""
        mock_task.kiq = AsyncMock()
        mock_task.kiq.side_effect = Exception("Broker connection failed")

        response = client.get("/tasks/health")

        assert response.status_code == 200  # Endpoint не падает, а возвращает статус
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["broker"] == "disconnected"
        assert "Broker connection failed" in data["error"]
        assert "issues" in data["message"]

    def test_list_available_tasks(self, client):
        """Тест получения списка доступных задач."""
        response = client.get("/tasks/")

        assert response.status_code == 200
        data = response.json()

        # Проверяем структуру ответа
        assert "available_tasks" in data
        assert "management_endpoints" in data

        # Проверяем, что есть ожидаемые задачи
        task_names = [task["name"] for task in data["available_tasks"]]
        expected_tasks = [
            "send_email_notification",
            "process_file",
            "fetch_external_data",
            "database_maintenance",
            "generate_report",
            "scheduled_backup",
        ]

        for expected_task in expected_tasks:
            assert expected_task in task_names

        # Проверяем endpoints управления
        management_endpoints = [ep["endpoint"] for ep in data["management_endpoints"]]
        assert "/tasks/status/{task_id}" in management_endpoints
        assert "/tasks/result/{task_id}" in management_endpoints
        assert "/tasks/health" in management_endpoints


class TestPydanticModels:
    """Тесты для Pydantic моделей."""

    def test_email_task_request_model(self):
        """Тест модели EmailTaskRequest."""
        data = {"to": "test@example.com", "subject": "Test", "body": "Test body", "priority": "high"}
        model = EmailTaskRequest(**data)
        assert model.to == "test@example.com"
        assert model.priority == "high"

    def test_email_task_request_default_priority(self):
        """Тест значения по умолчанию для приоритета."""
        data = {"to": "test@example.com", "subject": "Test", "body": "Test body"}
        model = EmailTaskRequest(**data)
        assert model.priority == "normal"

    def test_file_processing_request_model(self):
        """Тест модели FileProcessingRequest."""
        data = {"file_path": "/test/file.txt", "operation": "compress", "options": {"quality": 85}}
        model = FileProcessingRequest(**data)
        assert model.file_path == "/test/file.txt"
        assert model.operation == "compress"
        assert model.options == {"quality": 85}

    def test_external_data_request_model(self):
        """Тест модели ExternalDataRequest."""
        data = {"url": "https://api.example.com", "method": "POST", "headers": {"Auth": "Bearer token"}, "timeout": 60}
        model = ExternalDataRequest(**data)
        assert model.url == "https://api.example.com"
        assert model.method == "POST"
        assert model.timeout == 60

    def test_backup_request_model(self):
        """Тест модели BackupRequest."""
        data = {"backup_type": "incremental", "compress": False, "retention_days": 14}
        model = BackupRequest(**data)
        assert model.backup_type == "incremental"
        assert model.compress is False
        assert model.retention_days == 14

    def test_backup_request_defaults(self):
        """Тест значений по умолчанию для BackupRequest."""
        model = BackupRequest()
        assert model.backup_type == "full"
        assert model.compress is True
        assert model.retention_days == 30
