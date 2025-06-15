"""
Главный менеджер миграций с полным функционалом.
"""

import logging
import subprocess
from typing import Any, Dict

from .backup import MigrationBackup
from .database import DatabaseManager
from .monitor import MigrationMonitor
from .validator import MigrationValidator

logger = logging.getLogger(__name__)


class MigrationManager:
    """Главный менеджер миграций с полным функционалом."""
    
    def __init__(self):
        self.validator = MigrationValidator()
        self.monitor = MigrationMonitor()
        self.backup = MigrationBackup()
        self.database = DatabaseManager()
        
    async def safe_migrate(self, target: str = "head", create_backup: bool = True) -> Dict[str, Any]:
        """Безопасное применение миграций с валидацией и бэкапом."""
        result: Dict[str, Any] = {
            "success": False,
            "backup_name": None,
            "validation_errors": [],
            "migration_status": None,
            "error": None
        }
        
        try:
            # 0. Проверяем/создаем базу данных
            if not await self.database.ensure_database_exists():
                result["error"] = "Не удалось создать или подключиться к базе данных"
                return result
            
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
            import os
            import sys
            env = os.environ.copy()
            env["DATABASE_URL"] = self.validator.settings.SQLALCHEMY_DATABASE_URI
            migrate_result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", target],
                env=env,
                capture_output=True,
                text=True
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
            
            return {
                "success": True,
                "restored_backup": backup_name,
                "current_status": status
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            } 