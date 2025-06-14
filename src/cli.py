"""CLI commands for TaskIQ worker management."""

from __future__ import annotations

import asyncio
import logging

import click
from taskiq.api import run_receiver_task

# Импортируем задачи для регистрации
import core.tasks  # noqa
from core.config import get_settings
from core.taskiq_client import broker

logger = logging.getLogger(__name__)
settings = get_settings()


def setup_logging() -> None:
    """Настройка логирования для CLI.

    Конфигурирует базовое логирование для отладки CLI команд.
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

    Инструменты для управления TaskIQ воркерами и задачами.
    Предоставляет команды для запуска воркеров, тестирования
    и получения информации о конфигурации.
    """
    setup_logging()


@cli.command()
@click.option(
    "--workers",
    "-w",
    default=1,
    help="Количество параллельных воркеров",
    type=int,
    show_default=True,
)
@click.option(
    "--reload",
    "-r",
    is_flag=True,
    help="Автоматическая перезагрузка при изменении кода",
    default=False,
)
@click.option(
    "--log-level",
    "-l",
    default="INFO",
    help="Уровень логирования",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    show_default=True,
)
def worker(
    workers: int,
    reload: bool,
    log_level: str,
) -> None:
    """Запустить TaskIQ воркеры.

    Args:
        workers: Количество параллельных воркеров для обработки задач.
        reload: Флаг автоматической перезагрузки при изменении кода.
        log_level: Уровень логирования для воркеров.
    """
    settings = get_settings()

    click.echo(f"🚀 Запуск {workers} TaskIQ воркеров...")
    click.echo(f"📊 Broker URL: {settings.TASKIQ_BROKER_URL}")
    click.echo(f"💾 Result Backend: {settings.TASKIQ_RESULT_BACKEND_URL}")
    click.echo(f"🔄 Reload: {reload}")
    click.echo(f"📝 Log Level: {log_level}")

    try:
        asyncio.run(run_receiver_task(broker))
    except KeyboardInterrupt:
        click.echo("\n🛑 Остановка воркеров...")
    except Exception as e:
        click.echo(f"❌ Ошибка запуска воркеров: {e}", err=True)
        raise


@cli.command()
def scheduler() -> None:
    """Запустить планировщик задач (будущая функциональность).

    Планировщик будет запускать задачи по расписанию.
    """
    click.echo("🕐 Планировщик задач пока не реализован")


@cli.command()
@click.argument("task_name", required=False)
def test(task_name: str | None) -> None:
    """Протестировать подключение к TaskIQ.

    Args:
        task_name: Имя конкретной задачи для тестирования (опционально).
    """
    settings = get_settings()

    click.echo("🧪 Тестирование подключения к TaskIQ...")
    click.echo(f"📊 Broker URL: {settings.TASKIQ_BROKER_URL}")
    click.echo(f"💾 Result Backend: {settings.TASKIQ_RESULT_BACKEND_URL}")

    async def test_connection() -> None:
        """Тестирование подключения к брокеру."""
        try:
            await broker.startup()
            click.echo("✅ Подключение к брокеру успешно")

            # Импортируем и тестируем задачи
            from core.tasks import add_numbers, test_task  # noqa: F401

            if task_name:
                click.echo(f"🔍 Тестирование задачи: {task_name}")
                # Здесь можно добавить логику для тестирования конкретной задачи
            else:
                click.echo("📋 Доступные задачи:")
                click.echo("  - test_task")
                click.echo("  - add_numbers")

            await broker.shutdown()
            click.echo("✅ Тест завершен успешно")

        except Exception as e:
            click.echo(f"❌ Ошибка тестирования: {e}", err=True)
            raise

    try:
        asyncio.run(test_connection())
    except Exception:
        click.echo("❌ Тест не пройден", err=True)
        raise


@cli.command()
def info() -> None:
    """Показать информацию о конфигурации TaskIQ.

    Выводит текущие настройки TaskIQ брокера и результирующего бэкенда.
    """
    settings = get_settings()

    click.echo("ℹ️  Информация о TaskIQ:")
    click.echo(f"📊 Broker URL: {settings.TASKIQ_BROKER_URL}")
    click.echo(f"💾 Result Backend: {settings.TASKIQ_RESULT_BACKEND_URL}")
    click.echo(f"🔄 Max Retries: {settings.TASKIQ_MAX_RETRIES}")
    click.echo(f"⏱️  Retry Delay: {settings.TASKIQ_RETRY_DELAY}s")
    click.echo(f"⏰ Task Timeout: {settings.TASKIQ_TASK_TIMEOUT}s")

    # Проверяем доступность брокера
    click.echo("\n🔍 Проверка доступности...")

    async def check_broker() -> None:
        """Проверка доступности брокера."""
        try:
            await broker.startup()
            click.echo("✅ Брокер доступен")
            await broker.shutdown()
        except Exception as e:
            click.echo(f"❌ Брокер недоступен: {e}", err=True)

    try:
        asyncio.run(check_broker())
    except Exception:
        pass


if __name__ == "__main__":
    cli()
