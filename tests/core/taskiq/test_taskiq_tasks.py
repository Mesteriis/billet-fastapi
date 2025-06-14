"""Тесты для TaskIQ задач."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.tasks import (
    database_maintenance,
    fetch_external_data,
    generate_report,
    process_file,
    scheduled_backup,
    send_email_notification,
)


class TestEmailNotificationTask:
    """Тесты для задачи отправки email."""

    @pytest.mark.asyncio
    async def test_send_email_notification_success(self):
        """Тест успешной отправки email."""
        result = await send_email_notification(
            to="test@example.com", subject="Test Subject", body="Test Body", priority="normal"
        )

        assert result["status"] == "sent"
        assert result["recipient"] == "test@example.com"
        assert result["subject"] == "Test Subject"
        assert result["priority"] == "normal"
        assert "sent_at" in result
        assert "message_id" in result

    @pytest.mark.asyncio
    async def test_send_email_notification_high_priority(self):
        """Тест отправки email с высоким приоритетом."""
        result = await send_email_notification(
            to="urgent@example.com", subject="Urgent", body="Urgent message", priority="high"
        )

        assert result["status"] == "sent"
        assert result["priority"] == "high"
        assert result["recipient"] == "urgent@example.com"

    @pytest.mark.asyncio
    async def test_send_email_notification_default_priority(self):
        """Тест отправки email с приоритетом по умолчанию."""
        result = await send_email_notification(to="default@example.com", subject="Default", body="Default message")

        assert result["priority"] == "normal"


class TestProcessFileTask:
    """Тесты для задачи обработки файлов."""

    @pytest.mark.asyncio
    async def test_process_file_analyze(self):
        """Тест анализа файла."""
        result = await process_file(file_path="/test/file.txt", operation="analyze")

        assert result["status"] == "completed"
        assert result["file_path"] == "/test/file.txt"
        assert result["operation"] == "analyze"
        assert result["output_path"] == "/test/file.txt.processed"
        assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_process_file_with_options(self):
        """Тест обработки файла с опциями."""
        options = {"processing_time": 1, "file_size": "5MB"}

        result = await process_file(file_path="/test/large_file.txt", operation="compress", options=options)

        assert result["status"] == "completed"
        assert result["operation"] == "compress"
        assert result["file_size"] == "5MB"

    @pytest.mark.asyncio
    async def test_process_file_no_options(self):
        """Тест обработки файла без опций."""
        result = await process_file(file_path="/test/simple.txt")

        assert result["status"] == "completed"
        assert result["operation"] == "analyze"
        assert result["file_size"] == "unknown"


class TestFetchExternalDataTask:
    """Тесты для задачи получения внешних данных."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_fetch_external_data_success_json(self, mock_client):
        """Тест успешного получения JSON данных."""
        # Настройка мока
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status.return_value = None

        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await fetch_external_data(url="https://api.example.com/data", method="GET")

        assert result["status"] == "success"
        assert result["url"] == "https://api.example.com/data"
        assert result["method"] == "GET"
        assert result["status_code"] == 200
        assert result["data"] == {"key": "value"}
        assert "fetched_at" in result

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_fetch_external_data_success_text(self, mock_client):
        """Тест успешного получения текстовых данных."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "Plain text response"
        mock_response.raise_for_status.return_value = None

        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await fetch_external_data(url="https://example.com/text", method="GET")

        assert result["status"] == "success"
        assert result["data"] == "Plain text response"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_fetch_external_data_request_error(self, mock_client):
        """Тест ошибки запроса."""
        from httpx import RequestError

        mock_client_instance = AsyncMock()
        mock_client_instance.request.side_effect = RequestError("Connection failed")
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await fetch_external_data(url="https://invalid.example.com", method="GET")

        assert result["status"] == "error"
        assert result["error_type"] == "request_error"
        assert "Connection failed" in result["error_message"]

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_fetch_external_data_http_error(self, mock_client):
        """Тест HTTP ошибки."""
        from httpx import HTTPStatusError

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client_instance = AsyncMock()
        http_error = HTTPStatusError("404 Not Found", request=None, response=mock_response)
        mock_client_instance.request.side_effect = http_error
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await fetch_external_data(url="https://example.com/notfound", method="GET")

        assert result["status"] == "error"
        assert result["error_type"] == "http_error"
        assert result["status_code"] == 404

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_fetch_external_data_with_headers(self, mock_client):
        """Тест запроса с заголовками."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"authenticated": True}
        mock_response.raise_for_status.return_value = None

        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        headers = {"Authorization": "Bearer token123"}

        result = await fetch_external_data(
            url="https://api.example.com/secure", method="GET", headers=headers, timeout=60
        )

        assert result["status"] == "success"
        assert result["data"] == {"authenticated": True}

        # Проверяем, что request был вызван с правильными параметрами
        mock_client_instance.request.assert_called_once_with(
            method="GET", url="https://api.example.com/secure", headers=headers, timeout=60
        )


class TestDatabaseMaintenanceTask:
    """Тесты для задачи обслуживания базы данных."""

    @pytest.mark.asyncio
    async def test_database_maintenance_cleanup(self):
        """Тест очистки базы данных."""
        result = await database_maintenance(operation="cleanup")

        assert result["status"] == "completed"
        assert result["operation"] == "cleanup"
        assert result["table_name"] == "all_tables"
        assert result["affected_rows"] == 100
        assert "completed_at" in result

    @pytest.mark.asyncio
    async def test_database_maintenance_specific_table(self):
        """Тест обслуживания конкретной таблицы."""
        result = await database_maintenance(operation="vacuum", table_name="users", options={"affected_rows": 250})

        assert result["status"] == "completed"
        assert result["operation"] == "vacuum"
        assert result["table_name"] == "users"
        assert result["affected_rows"] == 250

    @pytest.mark.asyncio
    async def test_database_maintenance_analyze(self):
        """Тест анализа базы данных."""
        result = await database_maintenance(operation="analyze", table_name="orders")

        assert result["status"] == "completed"
        assert result["operation"] == "analyze"
        assert result["table_name"] == "orders"


class TestGenerateReportTask:
    """Тесты для задачи генерации отчетов."""

    @pytest.mark.asyncio
    @patch("core.tasks.send_email_notification")
    async def test_generate_report_without_email(self, mock_email_task):
        """Тест генерации отчета без отправки email."""
        result = await generate_report(report_type="sales", date_from="2024-01-01", date_to="2024-01-31", format="pdf")

        assert result["status"] == "completed"
        assert result["report_type"] == "sales"
        assert result["date_from"] == "2024-01-01"
        assert result["date_to"] == "2024-01-31"
        assert result["format"] == "pdf"
        assert result["filename"] == "sales_report_2024-01-01_2024-01-31.pdf"
        assert result["file_size"] == "2.3 MB"
        assert "generated_at" in result
        assert "emails_sent" not in result

        # Email задача не должна вызываться
        mock_email_task.kiq.assert_not_called()

    @pytest.mark.asyncio
    @patch("core.tasks.send_email_notification")
    async def test_generate_report_with_email(self, mock_email_task):
        """Тест генерации отчета с отправкой email."""
        # Настройка мока для email задачи
        mock_email_task.kiq = AsyncMock()

        email_list = ["manager@example.com", "director@example.com"]

        result = await generate_report(
            report_type="analytics", date_from="2024-02-01", date_to="2024-02-29", format="xlsx", email_to=email_list
        )

        assert result["status"] == "completed"
        assert result["report_type"] == "analytics"
        assert result["format"] == "xlsx"
        assert result["filename"] == "analytics_report_2024-02-01_2024-02-29.xlsx"
        assert result["emails_sent"] == 2

        # Проверяем, что email задача вызывалась для каждого адреса
        assert mock_email_task.kiq.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_report_csv_format(self):
        """Тест генерации отчета в CSV формате."""
        result = await generate_report(report_type="users", date_from="2024-03-01", date_to="2024-03-31", format="csv")

        assert result["format"] == "csv"
        assert result["filename"] == "users_report_2024-03-01_2024-03-31.csv"


class TestScheduledBackupTask:
    """Тесты для задачи резервного копирования."""

    @pytest.mark.asyncio
    async def test_scheduled_backup_full(self):
        """Тест полного резервного копирования."""
        result = await scheduled_backup(backup_type="full", compress=True, retention_days=30)

        assert result["status"] == "completed"
        assert result["backup_type"] == "full"
        assert result["compressed"] is True
        assert result["retention_days"] == 30
        assert result["backup_size"] == "150.2 MB"
        assert result["filename"].startswith("backup_full_")
        assert result["filename"].endswith(".gz")
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_scheduled_backup_incremental(self):
        """Тест инкрементального резервного копирования."""
        result = await scheduled_backup(backup_type="incremental", compress=False, retention_days=7)

        assert result["status"] == "completed"
        assert result["backup_type"] == "incremental"
        assert result["compressed"] is False
        assert result["retention_days"] == 7
        assert result["backup_size"] == "23.1 MB"
        assert result["filename"].startswith("backup_incremental_")
        assert not result["filename"].endswith(".gz")

    @pytest.mark.asyncio
    async def test_scheduled_backup_default_params(self):
        """Тест резервного копирования с параметрами по умолчанию."""
        result = await scheduled_backup()

        assert result["status"] == "completed"
        assert result["backup_type"] == "full"
        assert result["compressed"] is True
        assert result["retention_days"] == 30
