#!/usr/bin/env python3
"""
CLI для управления миграциями с расширенными возможностями.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
import rich
from rich.console import Console
from rich.table import Table

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.migrations import DatabaseManager, MigrationBackup, MigrationManager, MigrationMonitor, MigrationValidator

console = Console()


@click.group()
def cli():
    """🚀 Управление миграциями с расширенными возможностями."""
    pass


@cli.command()
@click.option("--target", default="head", help="Целевая ревизия для миграции")
@click.option("--no-backup", is_flag=True, help="Не создавать бэкап")
def safe_migrate(target: str, no_backup: bool):
    """🛡️ Безопасная миграция с валидацией и бэкапом."""

    async def _migrate():
        manager = MigrationManager()

        with console.status("[bold green]Выполняется безопасная миграция..."):
            result = await manager.safe_migrate(target=target, create_backup=not no_backup)

        if result["success"]:
            console.print("✅ [bold green]Миграция успешно выполнена!")

            if result["backup_name"]:
                console.print(f"💾 Создан бэкап: {result['backup_name']}")

            if result["migration_status"]:
                status = result["migration_status"]
                console.print(f"📊 Текущая версия: {status.get('current_version', 'N/A')}")
                console.print(f"📈 Всего миграций: {status.get('total_migrations', 0)}")
        else:
            console.print("❌ [bold red]Ошибка миграции!")
            console.print(f"🔍 Ошибка: {result['error']}")

            if result["validation_errors"]:
                console.print("⚠️ Ошибки валидации:")
                for error in result["validation_errors"]:
                    console.print(f"  • {error}")

    asyncio.run(_migrate())


@cli.command()
def status():
    """📊 Статус миграций."""

    async def _status():
        monitor = MigrationMonitor()

        with console.status("[bold blue]Получение статуса миграций..."):
            status = await monitor.get_migration_status()

        if "error" in status:
            console.print(f"❌ [bold red]Ошибка: {status['error']}")
            return

        # Создаем таблицу статуса
        table = Table(title="📊 Статус миграций")
        table.add_column("Параметр", style="cyan")
        table.add_column("Значение", style="green")

        table.add_row("Текущая версия", status.get("current_version", "N/A"))
        table.add_row("Всего миграций", str(status.get("total_migrations", 0)))
        table.add_row("Ожидающих применения", str(len(status.get("pending_migrations", []))))
        table.add_row("Последняя проверка", status.get("last_check", "N/A"))
        table.add_row("База данных", status.get("database_url", "N/A"))

        console.print(table)

        # Показываем ожидающие миграции
        pending = status.get("pending_migrations", [])
        if pending:
            console.print("\n⏳ [bold yellow]Ожидающие миграции:")
            for migration in pending:
                console.print(f"  • {migration.get('file', 'N/A')} - {migration.get('message', 'Без описания')}")

    asyncio.run(_status())


@cli.command()
def validate():
    """🔍 Валидация миграций."""

    async def _validate():
        monitor = MigrationMonitor()

        with console.status("[bold blue]Проверка целостности миграций..."):
            result = await monitor.check_migration_integrity()

        if "error" in result:
            console.print(f"❌ [bold red]Ошибка: {result['error']}")
            return

        console.print(f"📊 Проверено миграций: {result.get('total_checked', 0)}")

        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        valid = result.get("valid_migrations", [])

        if errors:
            console.print(f"\n❌ [bold red]Ошибки ({len(errors)}):")
            for error in errors:
                console.print(f"  • {error}")

        if warnings:
            console.print(f"\n⚠️ [bold yellow]Предупреждения ({len(warnings)}):")
            for warning in warnings:
                console.print(f"  • {warning}")

        if valid:
            console.print(f"\n✅ [bold green]Корректные миграции ({len(valid)}):")
            for migration in valid[:5]:  # Показываем только первые 5
                console.print(f"  • {migration}")
            if len(valid) > 5:
                console.print(f"  ... и еще {len(valid) - 5}")

        if not errors and not warnings:
            console.print("\n🎉 [bold green]Все миграции корректны!")

    asyncio.run(_validate())


@cli.command()
@click.option("--description", default="", help="Описание бэкапа")
def backup(description: str):
    """💾 Создание бэкапа базы данных."""

    async def _backup():
        backup_service = MigrationBackup()

        with console.status("[bold blue]Создание бэкапа..."):
            backup_name = await backup_service.create_backup(description)

        console.print(f"✅ [bold green]Бэкап создан: {backup_name}")

    asyncio.run(_backup())


@cli.command()
def list_backups():
    """📋 Список бэкапов."""
    backup_service = MigrationBackup()
    backups = backup_service.list_backups()

    if not backups:
        console.print("📭 [yellow]Бэкапы не найдены")
        return

    table = Table(title="📋 Список бэкапов")
    table.add_column("Имя", style="cyan")
    table.add_column("Дата создания", style="green")
    table.add_column("Описание", style="yellow")
    table.add_column("Размер", style="blue")

    for backup in backups:
        size_mb = backup.get("file_size", 0) / (1024 * 1024)
        table.add_row(
            backup.get("backup_name", "N/A"),
            backup.get("created_at", "N/A")[:19],  # Убираем микросекунды
            backup.get("description", "Без описания"),
            f"{size_mb:.2f} MB",
        )

    console.print(table)


@cli.command()
@click.argument("backup_name")
def restore(backup_name: str):
    """🔄 Восстановление из бэкапа."""

    async def _restore():
        backup_service = MigrationBackup()

        # Подтверждение
        if not click.confirm(f"⚠️ Восстановить базу данных из бэкапа '{backup_name}'? Это удалит все текущие данные!"):
            console.print("❌ Операция отменена")
            return

        with console.status("[bold red]Восстановление из бэкапа..."):
            try:
                await backup_service.restore_backup(backup_name)
                console.print(f"✅ [bold green]База данных восстановлена из бэкапа: {backup_name}")
            except Exception as e:
                console.print(f"❌ [bold red]Ошибка восстановления: {e}")

    asyncio.run(_restore())


@cli.command()
@click.option("--keep", default=10, help="Количество бэкапов для сохранения")
def cleanup_backups(keep: int):
    """🧹 Очистка старых бэкапов."""
    backup_service = MigrationBackup()

    removed = backup_service.cleanup_old_backups(keep_count=keep)

    if removed > 0:
        console.print(f"🗑️ [bold green]Удалено старых бэкапов: {removed}")
    else:
        console.print("✨ [green]Нет бэкапов для удаления")


@cli.command()
@click.argument("migration_file", type=click.Path(exists=True))
def validate_file(migration_file: str):
    """🔍 Валидация конкретного файла миграции."""
    validator = MigrationValidator()
    migration_path = Path(migration_file)

    console.print(f"🔍 Валидация файла: {migration_path.name}")

    # Проверка синтаксиса
    syntax_errors = validator.validate_migration_syntax(migration_path)
    if syntax_errors:
        console.print("❌ [bold red]Ошибки синтаксиса:")
        for error in syntax_errors:
            console.print(f"  • {error}")
    else:
        console.print("✅ [green]Синтаксис корректен")

    # Проверка зависимостей
    dep_errors = validator.validate_migration_dependencies(migration_path)
    if dep_errors:
        console.print("⚠️ [bold yellow]Проблемы с зависимостями:")
        for error in dep_errors:
            console.print(f"  • {error}")
    else:
        console.print("✅ [green]Зависимости корректны")

    if not syntax_errors and not dep_errors:
        console.print("🎉 [bold green]Файл миграции полностью корректен!")


@cli.command()
def monitor():
    """📈 Интерактивный мониторинг миграций."""

    async def _monitor():
        monitor = MigrationMonitor()

        console.print("📈 [bold blue]Мониторинг миграций (нажмите Ctrl+C для выхода)")

        try:
            while True:
                console.clear()

                # Получаем статус
                status = await monitor.get_migration_status()

                if "error" in status:
                    console.print(f"❌ [bold red]Ошибка: {status['error']}")
                else:
                    # Показываем статус
                    table = Table(title="📊 Статус миграций (обновляется каждые 10 сек)")
                    table.add_column("Параметр", style="cyan")
                    table.add_column("Значение", style="green")

                    table.add_row("Текущая версия", status.get("current_version", "N/A"))
                    table.add_row("Всего миграций", str(status.get("total_migrations", 0)))
                    table.add_row("Ожидающих", str(len(status.get("pending_migrations", []))))
                    table.add_row("Последнее обновление", status.get("last_check", "N/A")[:19])

                    console.print(table)

                # Ждем 10 секунд
                await asyncio.sleep(10)

        except KeyboardInterrupt:
            console.print("\n👋 [yellow]Мониторинг остановлен")

    asyncio.run(_monitor())


@cli.command()
def db_info():
    """🗄️ Информация о базе данных."""

    async def _db_info():
        db_manager = DatabaseManager()

        with console.status("[bold blue]Получение информации о БД..."):
            info = await db_manager.get_database_info(db_manager.settings.SQLALCHEMY_DATABASE_URI)

        # Создаем таблицу с информацией
        table = Table(title="🗄️ Информация о базе данных")
        table.add_column("Параметр", style="cyan")
        table.add_column("Значение", style="green")

        table.add_row("Имя БД", info.get("database_name", "N/A"))
        table.add_row("Тип БД", info.get("database_type", "N/A"))
        table.add_row("Существует", "✅ Да" if info.get("exists") else "❌ Нет")
        table.add_row("Подключение", "✅ OK" if info.get("connection_test") else "❌ Ошибка")
        table.add_row("Размер", info.get("size", "N/A"))
        table.add_row("Количество таблиц", str(info.get("tables_count", "N/A")))

        console.print(table)

    asyncio.run(_db_info())


@cli.command()
@click.option("--force", is_flag=True, help="Принудительное создание без подтверждения")
def db_create(force: bool):
    """🏗️ Создание базы данных."""

    async def _db_create():
        db_manager = DatabaseManager()

        # Проверяем существование
        if await db_manager.database_exists(db_manager.settings.SQLALCHEMY_DATABASE_URI):
            console.print("ℹ️ [yellow]База данных уже существует")
            return

        # Подтверждение если не force
        if not force:
            if not click.confirm("🏗️ Создать новую базу данных?"):
                console.print("❌ Операция отменена")
                return

        with console.status("[bold blue]Создание базы данных..."):
            success = await db_manager.create_database(db_manager.settings.SQLALCHEMY_DATABASE_URI)

        if success:
            console.print("✅ [bold green]База данных успешно создана!")
        else:
            console.print("❌ [bold red]Не удалось создать базу данных")

    asyncio.run(_db_create())


@cli.command()
@click.option("--force", is_flag=True, help="Принудительное удаление без подтверждения")
def db_drop(force: bool):
    """🗑️ Удаление базы данных."""

    async def _db_drop():
        db_manager = DatabaseManager()

        # Проверяем существование
        if not await db_manager.database_exists(db_manager.settings.SQLALCHEMY_DATABASE_URI):
            console.print("ℹ️ [yellow]База данных не существует")
            return

        # Подтверждение
        if not force:
            console.print("⚠️ [bold red]ВНИМАНИЕ: Это удалит ВСЕ данные в базе данных!")
            if not click.confirm("🗑️ Вы уверены, что хотите удалить базу данных?"):
                console.print("❌ Операция отменена")
                return

            # Двойное подтверждение
            if not click.confirm("🚨 Последнее предупреждение! Удалить базу данных НАВСЕГДА?"):
                console.print("❌ Операция отменена")
                return

        with console.status("[bold red]Удаление базы данных..."):
            success = await db_manager.drop_database(db_manager.settings.SQLALCHEMY_DATABASE_URI)

        if success:
            console.print("✅ [bold green]База данных успешно удалена")
        else:
            console.print("❌ [bold red]Не удалось удалить базу данных")

    asyncio.run(_db_drop())


@cli.command()
def db_test():
    """🔌 Тестирование подключения к БД."""

    async def _db_test():
        db_manager = DatabaseManager()

        with console.status("[bold blue]Тестирование подключения..."):
            success = await db_manager.test_connection(db_manager.settings.SQLALCHEMY_DATABASE_URI)

        if success:
            console.print("✅ [bold green]Подключение к базе данных работает!")
        else:
            console.print("❌ [bold red]Не удается подключиться к базе данных")

    asyncio.run(_db_test())


@cli.command()
def db_ensure():
    """🔍 Проверка/создание БД если не существует."""

    async def _db_ensure():
        db_manager = DatabaseManager()

        with console.status("[bold blue]Проверка существования БД..."):
            success = await db_manager.ensure_database_exists()

        if success:
            console.print("✅ [bold green]База данных готова к использованию!")
        else:
            console.print("❌ [bold red]Проблемы с базой данных")

    asyncio.run(_db_ensure())


if __name__ == "__main__":
    cli()
