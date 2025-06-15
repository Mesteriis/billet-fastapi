"""Тесты для TaskIQ CLI команд."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli import cli, setup_logging


class TestCLICommands:
    """Тесты для CLI команд."""

    @pytest.fixture
    def runner(self):
        """Создает CLI runner для тестов."""
        return CliRunner()

    def test_cli_help(self, runner):
        """Тест справочной информации CLI."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "TaskIQ Management CLI" in result.output

    @patch("src.cli.run_worker_async")
    @patch("src.cli.asyncio.run")
    def test_worker_command_default(self, mock_asyncio_run, mock_run_worker, runner):
        """Тест команды worker с параметрами по умолчанию."""
        result = runner.invoke(cli, ["worker"])

        assert result.exit_code == 0
        assert "🚀 Запуск" in result.output
        mock_asyncio_run.assert_called_once()

    @patch("src.cli.run_worker_async")
    @patch("src.cli.asyncio.run")
    def test_worker_command_with_options(self, mock_asyncio_run, mock_run_worker, runner):
        """Тест команды worker с опциями."""
        result = runner.invoke(
            cli, ["worker", "--workers", "8", "--max-tasks", "100", "--max-memory", "512", "--reload"]
        )

        assert result.exit_code == 0
        assert "🚀 Запуск 8 TaskIQ воркеров" in result.output
        mock_asyncio_run.assert_called_once()

    @patch("src.cli.run_worker_async")
    @patch("src.cli.asyncio.run")
    def test_worker_command_keyboard_interrupt(self, mock_asyncio_run, mock_run_worker, runner):
        """Тест прерывания команды worker."""
        mock_asyncio_run.side_effect = KeyboardInterrupt()

        result = runner.invoke(cli, ["worker"])

        assert result.exit_code == 0
        assert "👋 TaskIQ воркеры остановлены" in result.output

    @patch("src.cli.run_worker_async")
    @patch("src.cli.asyncio.run")
    def test_worker_command_exception(self, mock_asyncio_run, mock_run_worker, runner):
        """Тест ошибки в команде worker."""
        mock_asyncio_run.side_effect = Exception("Worker failed to start")

        result = runner.invoke(cli, ["worker"])

        assert result.exit_code == 1
        assert "❌ Ошибка при запуске воркеров" in result.output

    def test_scheduler_command(self, runner):
        """Тест команды scheduler."""
        result = runner.invoke(cli, ["scheduler"])

        assert result.exit_code == 0
        assert "📅 Планировщик задач пока не реализован" in result.output
        assert "💡 Для периодических задач используйте cron" in result.output

    @patch("src.cli.send_email_notification")
    @patch("src.cli.broker")
    @patch("src.cli.asyncio.run")
    def test_test_command_default(self, mock_asyncio_run, mock_broker, mock_task, runner):
        """Тест команды test с параметрами по умолчанию."""
        # Настройка моков
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "test-task-123"
        mock_task.kiq.return_value = mock_task_result

        mock_broker.startup = AsyncMock()
        mock_broker.shutdown = AsyncMock()

        # Настройка async run для выполнения переданной функции
        def run_async_func(func):
            import asyncio

            return asyncio.run(func())

        mock_asyncio_run.side_effect = run_async_func

        result = runner.invoke(cli, ["test"])

        assert result.exit_code == 0
        assert "🧪 Тестирование TaskIQ" in result.output
        assert "✅ Тест завершен успешно" in result.output

    @patch("src.cli.send_email_notification")
    @patch("src.cli.broker")
    @patch("src.cli.asyncio.run")
    def test_test_command_with_task_name(self, mock_asyncio_run, mock_broker, mock_task, runner):
        """Тест команды test с указанием задачи."""
        mock_task.kiq = AsyncMock()
        mock_task_result = MagicMock()
        mock_task_result.task_id = "email-test-456"
        mock_task.kiq.return_value = mock_task_result

        mock_broker.startup = AsyncMock()
        mock_broker.shutdown = AsyncMock()

        def run_async_func(func):
            import asyncio

            return asyncio.run(func())

        mock_asyncio_run.side_effect = run_async_func

        result = runner.invoke(cli, ["test", "--task-name", "email"])

        assert result.exit_code == 0
        assert "📧 Тестируем отправку email" in result.output

    @patch("src.cli.broker")
    @patch("src.cli.asyncio.run")
    def test_test_command_exception(self, mock_asyncio_run, mock_broker, runner):
        """Тест ошибки в команде test."""
        mock_broker.startup = AsyncMock(side_effect=Exception("Connection failed"))

        def run_async_func(func):
            import asyncio

            return asyncio.run(func())

        mock_asyncio_run.side_effect = run_async_func

        result = runner.invoke(cli, ["test"])

        assert result.exit_code == 1
        assert "❌ Ошибка тестирования" in result.output

    @patch("src.cli.settings")
    def test_info_command(self, mock_settings, runner):
        """Тест команды info."""
        # Настройка мока настроек
        mock_settings.TASKIQ_BROKER_URL = "redis://localhost:6379/1"
        mock_settings.TASKIQ_RESULT_BACKEND_URL = "redis://localhost:6379/2"
        mock_settings.MAX_BACKGROUND_WORKERS = 4
        mock_settings.TASKIQ_MAX_RETRIES = 3
        mock_settings.TASKIQ_RETRY_DELAY = 5
        mock_settings.TASKIQ_TASK_TIMEOUT = 300

        result = runner.invoke(cli, ["info"])

        assert result.exit_code == 0
        assert "ℹ️  Информация о TaskIQ" in result.output
        assert "redis://localhost:6379/1" in result.output
        assert "redis://localhost:6379/2" in result.output
        assert "📋 Доступные задачи" in result.output
        assert "send_email_notification" in result.output
        assert "process_file" in result.output


class TestCLIUtilities:
    """Тесты для утилит CLI."""

    @patch("src.cli.logging.basicConfig")
    @patch("src.cli.settings")
    def test_setup_logging(self, mock_settings, mock_logging_config):
        """Тест настройки логирования."""
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_FORMAT = "%(asctime)s - %(message)s"
        mock_settings.LOG_FILE = "test.log"

        setup_logging()

        mock_logging_config.assert_called_once()
        args, kwargs = mock_logging_config.call_args
        assert "level" in kwargs
        assert "format" in kwargs
        assert "handlers" in kwargs

    @pytest.fixture
    def runner(self):
        """Создает CLI runner для тестов."""
        return CliRunner()

    def test_cli_group_exists(self, runner):
        """Тест существования CLI группы."""
        result = runner.invoke(cli)
        assert result.exit_code == 0

    def test_all_commands_exist(self, runner):
        """Тест существования всех команд."""
        result = runner.invoke(cli, ["--help"])

        expected_commands = ["worker", "scheduler", "test", "info"]
        for command in expected_commands:
            assert command in result.output


class TestCLISignalHandling:
    """Тесты для обработки сигналов в CLI."""

    @pytest.fixture
    def runner(self):
        """Создает CLI runner для тестов."""
        return CliRunner()

    @patch("src.cli.signal.signal")
    @patch("src.cli.run_worker_async")
    @patch("src.cli.asyncio.run")
    def test_signal_handler_setup(self, mock_asyncio_run, mock_run_worker, mock_signal, runner):
        """Тест настройки обработчиков сигналов."""
        result = runner.invoke(cli, ["worker"])

        # Проверяем, что обработчики сигналов были установлены
        assert mock_signal.call_count >= 2  # SIGINT и SIGTERM

    @patch("src.cli.sys.exit")
    @patch("src.cli.signal.signal")
    @patch("src.cli.run_worker_async")
    @patch("src.cli.asyncio.run")
    def test_signal_handler_execution(self, mock_asyncio_run, mock_run_worker, mock_signal, mock_exit, runner):
        """Тест выполнения обработчика сигналов."""
        # Получаем обработчик сигнала из вызовов signal.signal
        signal_handler = None

        def capture_signal_handler(sig, handler):
            nonlocal signal_handler
            signal_handler = handler

        mock_signal.side_effect = capture_signal_handler

        result = runner.invoke(cli, ["worker"])

        # Проверяем, что обработчик был установлен
        assert signal_handler is not None

        # Симулируем получение сигнала
        if signal_handler:
            signal_handler(None, None)
            mock_exit.assert_called_once_with(0)


class TestCLIErrorScenarios:
    """Тесты для сценариев ошибок в CLI."""

    @pytest.fixture
    def runner(self):
        """Создает CLI runner для тестов."""
        return CliRunner()

    def test_invalid_command(self, runner):
        """Тест невалидной команды."""
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0

    def test_invalid_worker_options(self, runner):
        """Тест невалидных опций для worker."""
        result = runner.invoke(cli, ["worker", "--workers", "invalid"])
        assert result.exit_code != 0

    def test_invalid_max_tasks_option(self, runner):
        """Тест невалидной опции max-tasks."""
        result = runner.invoke(cli, ["worker", "--max-tasks", "not-a-number"])
        assert result.exit_code != 0

    def test_invalid_max_memory_option(self, runner):
        """Тест невалидной опции max-memory."""
        result = runner.invoke(cli, ["worker", "--max-memory", "invalid-memory"])
        assert result.exit_code != 0


class TestCLIOutputFormatting:
    """Тесты для форматирования вывода CLI."""

    @pytest.fixture
    def runner(self):
        """Создает CLI runner для тестов."""
        return CliRunner()

    @patch("src.cli.settings")
    def test_info_command_formatting(self, mock_settings, runner):
        """Тест форматирования вывода команды info."""
        mock_settings.TASKIQ_BROKER_URL = "redis://test:6379/1"
        mock_settings.TASKIQ_RESULT_BACKEND_URL = "redis://test:6379/2"
        mock_settings.MAX_BACKGROUND_WORKERS = 8
        mock_settings.TASKIQ_MAX_RETRIES = 5
        mock_settings.TASKIQ_RETRY_DELAY = 10
        mock_settings.TASKIQ_TASK_TIMEOUT = 600

        result = runner.invoke(cli, ["info"])

        # Проверяем структуру вывода
        lines = result.output.split("\n")

        # Должны быть emoji в выводе
        emoji_lines = [
            line for line in lines if any(emoji in line for emoji in ["📊", "💾", "👥", "🔄", "⏱️", "⏰", "📋"])
        ]
        assert len(emoji_lines) >= 6

    @patch("src.cli.run_worker_async")
    @patch("src.cli.asyncio.run")
    def test_worker_command_output_formatting(self, mock_asyncio_run, mock_run_worker, runner):
        """Тест форматирования вывода команды worker."""
        result = runner.invoke(cli, ["worker", "--workers", "4"])

        # Проверяем наличие emoji и структурированного вывода
        assert "🚀" in result.output
        assert "📊" in result.output
        assert "💾" in result.output
        assert "TaskIQ воркеров" in result.output

    def test_scheduler_command_output_formatting(self, runner):
        """Тест форматирования вывода команды scheduler."""
        result = runner.invoke(cli, ["scheduler"])

        # Проверяем наличие emoji
        assert "📅" in result.output
        assert "💡" in result.output


class TestCLIPerformance:
    """Тесты производительности CLI."""

    @pytest.fixture
    def runner(self):
        """Создает CLI runner для тестов."""
        return CliRunner()

    def test_cli_startup_time(self, runner):
        """Тест времени запуска CLI."""
        import time

        start_time = time.time()
        result = runner.invoke(cli, ["--help"])
        end_time = time.time()

        startup_time = end_time - start_time

        # CLI должен запускаться быстро
        assert startup_time < 2.0
        assert result.exit_code == 0

    @patch("src.cli.settings")
    def test_info_command_performance(self, mock_settings, runner):
        """Тест производительности команды info."""
        mock_settings.TASKIQ_BROKER_URL = "redis://localhost:6379/1"
        mock_settings.TASKIQ_RESULT_BACKEND_URL = "redis://localhost:6379/2"
        mock_settings.MAX_BACKGROUND_WORKERS = 4
        mock_settings.TASKIQ_MAX_RETRIES = 3
        mock_settings.TASKIQ_RETRY_DELAY = 5
        mock_settings.TASKIQ_TASK_TIMEOUT = 300

        import time

        start_time = time.time()
        result = runner.invoke(cli, ["info"])
        end_time = time.time()

        execution_time = end_time - start_time

        # Команда info должна выполняться быстро
        assert execution_time < 1.0
        assert result.exit_code == 0
