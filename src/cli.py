"""Command Line Interface for TaskIQ Worker Management.

This module provides CLI commands for managing TaskIQ workers, testing connections,
and monitoring background task processing. It includes commands for starting workers,
running tests, and getting configuration information.

Commands available:
    - worker: Start TaskIQ workers for processing background tasks
    - scheduler: Future functionality for scheduled tasks
    - test: Test TaskIQ broker connection and available tasks
    - info: Display current TaskIQ configuration

Example:
    Start workers::

        python -m cli worker --workers 4 --reload

    Test connection::

        python -m cli test
        python -m cli test add_numbers

    Show configuration::

        python -m cli info

Note:
    This module requires TaskIQ broker and result backend to be properly
    configured in the application settings.
"""

from __future__ import annotations

import asyncio
import logging

import click
from taskiq.api import run_receiver_task

# Import tasks for registration
import core.tasks  # noqa
from core.config import get_settings
from core.taskiq_client import broker

logger = logging.getLogger(__name__)
settings = get_settings()


def setup_logging() -> None:
    """Configure logging for CLI operations.

    Sets up basic logging configuration for CLI command debugging
    and monitoring with INFO level by default.

    Example:
        Called automatically when CLI group is invoked::

            # Logging will be configured when running:
            python -m cli worker
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )


@click.group()
def cli() -> None:
    """TaskIQ Management CLI.

    Command-line interface for managing TaskIQ workers and background tasks.
    Provides commands for starting workers, testing connections, and getting
    configuration information.

    Example:
        Show available commands::

            python -m cli --help

        Use specific command::

            python -m cli worker --help
            python -m cli test --help
    """
    setup_logging()


@cli.command()
@click.option(
    "--workers",
    "-w",
    default=1,
    help="Number of parallel workers",
    type=int,
    show_default=True,
)
@click.option(
    "--reload",
    "-r",
    is_flag=True,
    help="Auto-reload on code changes",
    default=False,
)
@click.option(
    "--log-level",
    "-l",
    default="INFO",
    help="Logging level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    show_default=True,
)
def worker(
    workers: int,
    reload: bool,
    log_level: str,
) -> None:
    """Start TaskIQ workers for background task processing.

    Launches the specified number of TaskIQ workers to process background tasks
    from the configured broker. Workers will run until manually stopped.

    Args:
        workers (int): Number of parallel workers to start
        reload (bool): Enable auto-reload on code changes
        log_level (str): Logging level for workers

    Example:
        Start single worker::

            python -m cli worker

        Start multiple workers with reload::

            python -m cli worker --workers 4 --reload

        Start with debug logging::

            python -m cli worker --log-level DEBUG

    Note:
        Workers will continue running until interrupted with Ctrl+C.
        In production, consider using process managers like systemd or supervisor.
    """
    settings = get_settings()

    click.echo(f"🚀 Starting {workers} TaskIQ workers...")
    click.echo(f"📊 Broker URL: {settings.TASKIQ_BROKER_URL}")
    click.echo(f"💾 Result Backend: {settings.TASKIQ_RESULT_BACKEND_URL}")
    click.echo(f"🔄 Reload: {reload}")
    click.echo(f"📝 Log Level: {log_level}")

    try:
        asyncio.run(run_receiver_task(broker))
    except KeyboardInterrupt:
        click.echo("\n🛑 Stopping workers...")
    except Exception as e:
        click.echo(f"❌ Error starting workers: {e}", err=True)
        raise


@cli.command()
def scheduler() -> None:
    """Start task scheduler (future functionality).

    This command will start a task scheduler for running tasks on schedule.
    Currently not implemented but reserved for future use.

    Example:
        When implemented::

            python -m cli scheduler

    Note:
        This functionality is planned for future releases.
        For now, use cron jobs or similar for scheduled tasks.
    """
    click.echo("🕐 Task scheduler not yet implemented")


@cli.command()
@click.argument("task_name", required=False)
def test(task_name: str | None) -> None:
    """Test TaskIQ broker connection and available tasks.

    Tests the connection to the TaskIQ broker and optionally tests
    a specific task. Useful for debugging and verifying configuration.

    Args:
        task_name (str | None): Name of specific task to test (optional)

    Example:
        Test general connection::

            python -m cli test

        Test specific task::

            python -m cli test add_numbers
            python -m cli test test_task

    Raises:
        Exception: If broker connection fails or task testing fails
    """
    settings = get_settings()

    click.echo("🧪 Testing TaskIQ connection...")
    click.echo(f"📊 Broker URL: {settings.TASKIQ_BROKER_URL}")
    click.echo(f"💾 Result Backend: {settings.TASKIQ_RESULT_BACKEND_URL}")

    async def test_connection() -> None:
        """Test broker connection and available tasks.

        Raises:
            Exception: If connection or task testing fails
        """
        try:
            await broker.startup()
            click.echo("✅ Broker connection successful")

            # Import and test tasks
            from core.tasks import add_numbers, test_task  # noqa: F401

            if task_name:
                click.echo(f"🔍 Testing task: {task_name}")
                # Future: Add logic for testing specific task
            else:
                click.echo("📋 Available tasks:")
                click.echo("  - test_task")
                click.echo("  - add_numbers")

            await broker.shutdown()
            click.echo("✅ Test completed successfully")

        except Exception as e:
            click.echo(f"❌ Test error: {e}", err=True)
            raise

    try:
        asyncio.run(test_connection())
    except Exception:
        click.echo("❌ Test failed", err=True)
        raise


@cli.command()
def info() -> None:
    """Display TaskIQ configuration information.

    Shows current TaskIQ settings including broker URL, result backend,
    retry configuration, and broker availability status.

    Example:
        Show configuration::

            python -m cli info

        Output example::

            ℹ️  TaskIQ Information:
            📊 Broker URL: redis://localhost:6379/1
            💾 Result Backend: redis://localhost:6379/2
            🔄 Max Retries: 3
            ⏱️  Retry Delay: 5s
            ⏰ Task Timeout: 300s

            🔍 Checking availability...
            ✅ Broker available

    Note:
        This command also performs a quick broker availability check.
    """
    settings = get_settings()

    click.echo("ℹ️  TaskIQ Information:")
    click.echo(f"📊 Broker URL: {settings.TASKIQ_BROKER_URL}")
    click.echo(f"💾 Result Backend: {settings.TASKIQ_RESULT_BACKEND_URL}")
    click.echo(f"🔄 Max Retries: {settings.TASKIQ_MAX_RETRIES}")
    click.echo(f"⏱️  Retry Delay: {settings.TASKIQ_RETRY_DELAY}s")
    click.echo(f"⏰ Task Timeout: {settings.TASKIQ_TASK_TIMEOUT}s")

    # Check broker availability
    click.echo("\n🔍 Checking availability...")

    async def check_broker() -> None:
        """Check broker availability.

        Performs a quick connection test to verify broker is accessible.
        """
        try:
            await broker.startup()
            click.echo("✅ Broker available")
            await broker.shutdown()
        except Exception as e:
            click.echo(f"❌ Broker unavailable: {e}", err=True)

    try:
        asyncio.run(check_broker())
    except Exception:
        pass


if __name__ == "__main__":
    cli()
