"""
Модуль для управления миграциями Alembic с расширенными возможностями.

Включает:
- Валидацию миграций перед применением
- Мониторинг состояния миграций
- Автоматическое создание бэкапов
- Проверку целостности схемы
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
from alembic import command
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import get_settings

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Базовое исключение для ошибок миграций."""

    pass


class ValidationError(MigrationError):
    """Ошибка валидации миграции."""

    pass


class BackupError(MigrationError):
    """Ошибка создания бэкапа."""

    pass


class MigrationValidator:
    """Валидатор миграций."""

    def __init__(self, alembic_config_path: str = "pyproject.toml"):
        self.settings = get_settings()
        self.alembic_config_path = alembic_config_path

    def validate_migration_syntax(self, migration_file: Path) -> List[str]:
        """Проверяет синтаксис файла миграции."""
        errors = []

        try:
            with open(migration_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Компилируем Python код для проверки синтаксиса
            compile(content, str(migration_file), "exec")

            # Проверяем наличие обязательных функций
            if "def upgrade():" not in content:
                errors.append("Отсутствует функция upgrade()")

            if "def downgrade():" not in content:
                errors.append("Отсутствует функция downgrade()")

            # Проверяем импорты
            required_imports = ["from alembic import op", "import sqlalchemy as sa"]
            for imp in required_imports:
                if imp not in content:
                    errors.append(f"Отсутствует импорт: {imp}")

        except SyntaxError as e:
            errors.append(f"Синтаксическая ошибка: {e}")
        except Exception as e:
            errors.append(f"Ошибка чтения файла: {e}")

        return errors

    def validate_migration_dependencies(self, migration_file: Path) -> List[str]:
        """Проверяет зависимости миграции."""
        errors = []

        try:
            with open(migration_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Извлекаем revision и down_revision
            revision = None
            down_revision = None

            for line in content.split("\n"):
                if line.strip().startswith("revision ="):
                    revision = line.split("=")[1].strip().strip("'\"")
                elif line.strip().startswith("down_revision ="):
                    down_revision = line.split("=")[1].strip().strip("'\"")

            if not revision:
                errors.append("Не найден revision ID")

            if down_revision == "None":
                down_revision = None

            # Проверяем существование родительской миграции
            if down_revision:
                migrations_dir = Path("migrations/versions")
                parent_exists = False

                for migration in migrations_dir.glob("*.py"):
                    with open(migration, "r", encoding="utf-8") as f:
                        parent_content = f.read()
                        if f"revision = '{down_revision}'" in parent_content:
                            parent_exists = True
                            break

                if not parent_exists:
                    errors.append(f"Родительская миграция {down_revision} не найдена")

        except Exception as e:
            errors.append(f"Ошибка проверки зависимостей: {e}")

        return errors

    async def validate_migration_on_test_db(self, migration_file: Path) -> List[str]:
        """Проверяет миграцию на тестовой базе данных."""
        errors = []

        try:
            # Создаем временную тестовую БД
            test_db_url = f"{self.settings.SQLALCHEMY_DATABASE_URI}_test_migration"

            # Создаем тестовую БД
            await self._create_test_database(test_db_url)

            try:
                # Применяем миграцию
                await self._apply_migration_to_test_db(test_db_url, migration_file)

                # Проверяем откат
                await self._test_migration_rollback(test_db_url, migration_file)

            finally:
                # Удаляем тестовую БД
                await self._drop_test_database(test_db_url)

        except Exception as e:
            errors.append(f"Ошибка тестирования миграции: {e}")

        return errors

    async def _create_test_database(self, test_db_url: str):
        """Создает тестовую базу данных."""
        # Извлекаем имя БД из URL
        db_name = test_db_url.split("/")[-1]
        base_url = test_db_url.rsplit("/", 1)[0]

        conn = await asyncpg.connect(base_url.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
        finally:
            await conn.close()

    async def _drop_test_database(self, test_db_url: str):
        """Удаляет тестовую базу данных."""
        db_name = test_db_url.split("/")[-1]
        base_url = test_db_url.rsplit("/", 1)[0]

        conn = await asyncpg.connect(base_url.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        finally:
            await conn.close()

    async def _apply_migration_to_test_db(self, test_db_url: str, migration_file: Path):
        """Применяет миграцию к тестовой БД."""
        # Здесь должна быть логика применения конкретной миграции
        # Для упрощения используем subprocess
        env = {"DATABASE_URL": test_db_url}
        result = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], env=env, capture_output=True, text=True)

        if result.returncode != 0:
            raise ValidationError(f"Ошибка применения миграции: {result.stderr}")

    async def _test_migration_rollback(self, test_db_url: str, migration_file: Path):
        """Тестирует откат миграции."""
        env = {"DATABASE_URL": test_db_url}
        result = subprocess.run(["uv", "run", "alembic", "downgrade", "-1"], env=env, capture_output=True, text=True)

        if result.returncode != 0:
            raise ValidationError(f"Ошибка отката миграции: {result.stderr}")


class MigrationMonitor:
    """Мониторинг состояния миграций."""

    def __init__(self):
        self.settings = get_settings()

    async def get_migration_status(self) -> Dict[str, Any]:
        """Получает текущий статус миграций."""
        try:
            engine = create_async_engine(self.settings.SQLALCHEMY_DATABASE_URI)

            async with engine.connect() as conn:
                # Получаем текущую версию
                result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                current_version = result.scalar()

                # Получаем информацию о миграциях
                migrations_info = await self._get_migrations_info()

                return {
                    "current_version": current_version,
                    "total_migrations": len(migrations_info),
                    "pending_migrations": self._get_pending_migrations(current_version, migrations_info),
                    "last_check": datetime.now().isoformat(),
                    "database_url": self.settings.SQLALCHEMY_DATABASE_URI.split("@")[-1],  # Без credentials
                    "migrations_info": migrations_info,
                }

        except Exception as e:
            logger.error(f"Ошибка получения статуса миграций: {e}")
            return {"error": str(e), "last_check": datetime.now().isoformat()}

    async def _get_migrations_info(self) -> List[Dict[str, Any]]:
        """Получает информацию о всех миграциях."""
        migrations = []
        migrations_dir = Path("migrations/versions")

        if not migrations_dir.exists():
            return migrations

        for migration_file in sorted(migrations_dir.glob("*.py")):
            try:
                with open(migration_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Извлекаем метаданные
                revision = None
                down_revision = None
                message = None

                for line in content.split("\n"):
                    if line.strip().startswith("revision ="):
                        revision = line.split("=")[1].strip().strip("'\"")
                    elif line.strip().startswith("down_revision ="):
                        down_revision = line.split("=")[1].strip().strip("'\"")
                        if down_revision == "None":
                            down_revision = None
                    elif line.strip().startswith('"""') and not message:
                        # Извлекаем сообщение из docstring
                        message = line.strip().strip('"""')

                migrations.append(
                    {
                        "file": migration_file.name,
                        "revision": revision,
                        "down_revision": down_revision,
                        "message": message,
                        "created": datetime.fromtimestamp(migration_file.stat().st_ctime).isoformat(),
                    }
                )

            except Exception as e:
                logger.warning(f"Ошибка чтения миграции {migration_file}: {e}")

        return migrations

    def _get_pending_migrations(self, current_version: str, migrations_info: List[Dict]) -> List[Dict]:
        """Получает список неприменённых миграций."""
        if not current_version:
            return migrations_info

        # Находим текущую миграцию и возвращаем все последующие
        current_index = -1
        for i, migration in enumerate(migrations_info):
            if migration["revision"] == current_version:
                current_index = i
                break

        if current_index == -1:
            return migrations_info

        return migrations_info[current_index + 1 :]

    async def check_migration_integrity(self) -> Dict[str, Any]:
        """Проверяет целостность миграций."""
        try:
            validator = MigrationValidator()
            migrations_dir = Path("migrations/versions")

            results = {"total_checked": 0, "errors": [], "warnings": [], "valid_migrations": []}

            for migration_file in migrations_dir.glob("*.py"):
                results["total_checked"] += 1

                # Проверяем синтаксис
                syntax_errors = validator.validate_migration_syntax(migration_file)
                if syntax_errors:
                    results["errors"].extend([f"{migration_file.name}: {error}" for error in syntax_errors])
                    continue

                # Проверяем зависимости
                dep_errors = validator.validate_migration_dependencies(migration_file)
                if dep_errors:
                    results["warnings"].extend([f"{migration_file.name}: {error}" for error in dep_errors])

                if not syntax_errors and not dep_errors:
                    results["valid_migrations"].append(migration_file.name)

            return results

        except Exception as e:
            return {"error": str(e)}


class MigrationBackup:
    """Система бэкапов для миграций."""

    def __init__(self, backup_dir: str = "backups/migrations"):
        self.settings = get_settings()
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_backup(self, description: str = "") -> str:
        """Создает бэкап базы данных перед миграцией."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"

        if description:
            backup_name += f"_{description.replace(' ', '_')}"

        backup_file = self.backup_dir / f"{backup_name}.sql"

        try:
            # Создаем дамп базы данных
            await self._create_database_dump(backup_file)

            # Создаем метаданные бэкапа
            metadata = {
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "description": description,
                "database_url": self.settings.SQLALCHEMY_DATABASE_URI.split("@")[-1],
                "backup_file": str(backup_file),
                "file_size": backup_file.stat().st_size if backup_file.exists() else 0,
            }

            metadata_file = self.backup_dir / f"{backup_name}.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"Создан бэкап: {backup_name}")
            return backup_name

        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {e}")
            raise BackupError(f"Не удалось создать бэкап: {e}")

    async def _create_database_dump(self, backup_file: Path):
        """Создает дамп базы данных."""
        # Парсим URL базы данных
        db_url = self.settings.SQLALCHEMY_DATABASE_URI

        if db_url.startswith("postgresql"):
            await self._create_postgres_dump(backup_file, db_url)
        elif db_url.startswith("sqlite"):
            await self._create_sqlite_dump(backup_file, db_url)
        else:
            raise BackupError(f"Неподдерживаемый тип БД: {db_url}")

    async def _create_postgres_dump(self, backup_file: Path, db_url: str):
        """Создает дамп PostgreSQL."""
        # Конвертируем asyncpg URL в psql URL
        pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        cmd = ["pg_dump", "--no-password", "--verbose", "--clean", "--no-acl", "--no-owner", pg_url]

        with open(backup_file, "w") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            raise BackupError(f"Ошибка pg_dump: {result.stderr}")

    async def _create_sqlite_dump(self, backup_file: Path, db_url: str):
        """Создает дамп SQLite."""
        # Извлекаем путь к файлу БД
        db_path = db_url.replace("sqlite+aiosqlite:///", "")

        cmd = ["sqlite3", db_path, ".dump"]

        with open(backup_file, "w") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            raise BackupError(f"Ошибка sqlite3: {result.stderr}")

    async def restore_backup(self, backup_name: str) -> bool:
        """Восстанавливает базу данных из бэкапа."""
        backup_file = self.backup_dir / f"{backup_name}.sql"
        metadata_file = self.backup_dir / f"{backup_name}.json"

        if not backup_file.exists():
            raise BackupError(f"Файл бэкапа не найден: {backup_file}")

        try:
            # Читаем метаданные
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            logger.info(f"Восстановление бэкапа: {backup_name}")

            # Восстанавливаем БД
            db_url = self.settings.SQLALCHEMY_DATABASE_URI

            if db_url.startswith("postgresql"):
                await self._restore_postgres_dump(backup_file, db_url)
            elif db_url.startswith("sqlite"):
                await self._restore_sqlite_dump(backup_file, db_url)
            else:
                raise BackupError(f"Неподдерживаемый тип БД: {db_url}")

            logger.info(f"Бэкап {backup_name} успешно восстановлен")
            return True

        except Exception as e:
            logger.error(f"Ошибка восстановления бэкапа: {e}")
            raise BackupError(f"Не удалось восстановить бэкап: {e}")

    async def _restore_postgres_dump(self, backup_file: Path, db_url: str):
        """Восстанавливает дамп PostgreSQL."""
        pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        cmd = ["psql", "--no-password", pg_url]

        with open(backup_file, "r") as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            raise BackupError(f"Ошибка psql: {result.stderr}")

    async def _restore_sqlite_dump(self, backup_file: Path, db_url: str):
        """Восстанавливает дамп SQLite."""
        db_path = db_url.replace("sqlite+aiosqlite:///", "")

        # Удаляем старую БД
        if Path(db_path).exists():
            Path(db_path).unlink()

        cmd = ["sqlite3", db_path]

        with open(backup_file, "r") as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            raise BackupError(f"Ошибка sqlite3: {result.stderr}")

    def list_backups(self) -> List[Dict[str, Any]]:
        """Возвращает список всех бэкапов."""
        backups = []

        for metadata_file in self.backup_dir.glob("*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    backups.append(metadata)
            except Exception as e:
                logger.warning(f"Ошибка чтения метаданных {metadata_file}: {e}")

        return sorted(backups, key=lambda x: x["created_at"], reverse=True)

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Удаляет старые бэкапы, оставляя только указанное количество."""
        backups = self.list_backups()

        if len(backups) <= keep_count:
            return 0

        removed_count = 0
        for backup in backups[keep_count:]:
            try:
                backup_name = backup["backup_name"]

                # Удаляем файлы
                backup_file = Path(backup["backup_file"])
                metadata_file = self.backup_dir / f"{backup_name}.json"

                if backup_file.exists():
                    backup_file.unlink()
                if metadata_file.exists():
                    metadata_file.unlink()

                removed_count += 1
                logger.info(f"Удален старый бэкап: {backup_name}")

            except Exception as e:
                logger.warning(f"Ошибка удаления бэкапа {backup['backup_name']}: {e}")

        return removed_count


class MigrationManager:
    """Главный менеджер миграций с полным функционалом."""

    def __init__(self):
        self.validator = MigrationValidator()
        self.monitor = MigrationMonitor()
        self.backup = MigrationBackup()

    async def safe_migrate(self, target: str = "head", create_backup: bool = True) -> Dict[str, Any]:
        """Безопасное применение миграций с валидацией и бэкапом."""
        result = {
            "success": False,
            "backup_name": None,
            "validation_errors": [],
            "migration_status": None,
            "error": None,
        }

        try:
            # 1. Проверяем целостность миграций
            integrity_check = await self.monitor.check_migration_integrity()
            if integrity_check.get("errors"):
                result["validation_errors"] = integrity_check["errors"]
                result["error"] = "Найдены ошибки в миграциях"
                return result

            # 2. Создаем бэкап если нужно
            if create_backup:
                backup_name = await self.backup.create_backup(f"before_migrate_to_{target}")
                result["backup_name"] = backup_name

            # 3. Применяем миграции
            env = {"DATABASE_URL": self.validator.settings.SQLALCHEMY_DATABASE_URI}
            migrate_result = subprocess.run(
                ["uv", "run", "alembic", "upgrade", target], env=env, capture_output=True, text=True
            )

            if migrate_result.returncode != 0:
                result["error"] = f"Ошибка применения миграций: {migrate_result.stderr}"
                return result

            # 4. Проверяем финальный статус
            result["migration_status"] = await self.monitor.get_migration_status()
            result["success"] = True

            logger.info(f"Миграции успешно применены до {target}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Ошибка безопасной миграции: {e}")

        return result

    async def rollback_with_backup(self, backup_name: str) -> Dict[str, Any]:
        """Откат к состоянию из бэкапа."""
        try:
            await self.backup.restore_backup(backup_name)
            status = await self.monitor.get_migration_status()

            return {"success": True, "restored_backup": backup_name, "current_status": status}

        except Exception as e:
            return {"success": False, "error": str(e)}
