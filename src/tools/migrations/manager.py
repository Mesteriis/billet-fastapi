"""Database Migration Manager with Comprehensive Safety Features.

This module provides a complete database migration management system with:
- Safe migration execution with backup and validation
- Database integrity checking and monitoring  
- Automatic backup creation before migrations
- Migration status tracking and reporting
- Error handling and rollback capabilities

The MigrationManager combines multiple specialized components:
- MigrationValidator: Pre-migration validation and integrity checks
- MigrationMonitor: Status tracking and health monitoring
- MigrationBackup: Automated backup and restore functionality
- DatabaseManager: Database creation and connection management

Features:
    - Safe migration execution with automatic backups
    - Pre-migration validation to catch issues early
    - Post-migration integrity verification
    - Backup/restore functionality for quick rollbacks
    - Comprehensive error reporting and logging
    - Integration with Alembic for migration execution

Example:
    Basic safe migration::

        from tools.migrations.manager import MigrationManager

        async def migrate_database():
            manager = MigrationManager()
            
            result = await manager.safe_migrate(
                target="head",
                create_backup=True
            )
            
            if result["success"]:
                print("Migration completed successfully")
                if result["backup_name"]:
                    print(f"Backup created: {result['backup_name']}")
            else:
                print(f"Migration failed: {result['error']}")

    Rollback with backup::

        async def rollback_database():
            manager = MigrationManager()
            
            result = await manager.rollback_with_backup(
                backup_name="backup_20240115_123000_before_migrate_to_head"
            )
            
            if result["success"]:
                print("Rollback completed successfully")
            else:
                print(f"Rollback failed: {result['error']}")

    Custom migration target::

        async def migrate_to_specific():
            manager = MigrationManager()
            
            # Migrate to specific revision
            result = await manager.safe_migrate(
                target="abc123def456",  # Specific revision hash
                create_backup=True
            )

Note:
    All migration operations are async and include comprehensive error handling.
    Backups are automatically created before migrations unless explicitly disabled.
    The manager ensures database exists before attempting migrations.
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
    """Comprehensive database migration manager with safety features.

    Orchestrates the complete migration workflow including validation,
    backup creation, migration execution, and status monitoring.
    Provides high-level interface for safe database schema updates.

    Components:
        validator (MigrationValidator): Pre-migration validation and checks
        monitor (MigrationMonitor): Migration status tracking and monitoring
        backup (MigrationBackup): Backup creation and restoration
        database (DatabaseManager): Database management operations

    Example:
        Basic initialization and usage::

            manager = MigrationManager()
            
            # Safe migration with all safety features
            result = await manager.safe_migrate()
            
            if result["success"]:
                print("Migration completed successfully")
            else:
                print(f"Failed: {result['error']}")

        Advanced usage with custom target::

            manager = MigrationManager()
            
            # Migrate to specific revision without backup
            result = await manager.safe_migrate(
                target="revision_hash_here",
                create_backup=False
            )

        Error handling and recovery::

            manager = MigrationManager()
            
            result = await manager.safe_migrate()
            
            if not result["success"]:
                # Check if backup was created
                if result["backup_name"]:
                    # Restore from backup
                    rollback_result = await manager.rollback_with_backup(
                        result["backup_name"]
                    )

    Attributes:
        validator: MigrationValidator instance for pre-migration checks
        monitor: MigrationMonitor instance for status tracking
        backup: MigrationBackup instance for backup operations
        database: DatabaseManager instance for database operations

    Note:
        All operations are designed to be idempotent and safe to retry.
        The manager automatically handles database creation if needed.
    """
    
    def __init__(self):
        """Initialize the migration manager with all required components.

        Creates instances of all specialized managers:
        - MigrationValidator for integrity checks
        - MigrationMonitor for status tracking
        - MigrationBackup for backup operations
        - DatabaseManager for database management

        Example:
            Basic initialization::

                manager = MigrationManager()
                # All components are ready for use

            Checking component status::

                manager = MigrationManager()
                print(f"Validator ready: {manager.validator is not None}")
                print(f"Monitor ready: {manager.monitor is not None}")
        """
        self.validator = MigrationValidator()
        self.monitor = MigrationMonitor()
        self.backup = MigrationBackup()
        self.database = DatabaseManager()
        
    async def safe_migrate(self, target: str = "head", create_backup: bool = True) -> Dict[str, Any]:
        """Execute safe migration with comprehensive validation and backup.

        Performs a complete migration workflow with all safety measures:
        1. Database existence verification/creation
        2. Migration integrity validation
        3. Optional backup creation
        4. Migration execution via Alembic
        5. Post-migration status verification

        Args:
            target (str): Migration target ("head", revision hash, relative like "+1")
            create_backup (bool): Whether to create backup before migration

        Returns:
            Dict[str, Any]: Comprehensive migration result with:
                - success (bool): Whether migration completed successfully
                - backup_name (str | None): Name of created backup if any
                - validation_errors (list): List of validation errors found
                - migration_status (dict | None): Final migration status
                - error (str | None): Error message if migration failed

        Example:
            Migrate to latest::

                result = await manager.safe_migrate()
                
                if result["success"]:
                    print("Migration to head completed")
                    print(f"Status: {result['migration_status']}")
                else:
                    print(f"Migration failed: {result['error']}")
                    if result["validation_errors"]:
                        print("Validation errors:")
                        for error in result["validation_errors"]:
                            print(f"  - {error}")

            Migrate to specific revision::

                result = await manager.safe_migrate(
                    target="abc123def",
                    create_backup=True
                )

            Skip backup (for testing/development)::

                result = await manager.safe_migrate(
                    target="head",
                    create_backup=False
                )

        Note:
            If create_backup is True, a backup is created before migration.
            The backup name includes timestamp and target for easy identification.
            All errors are captured and returned in the result dictionary.
        """
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
        """Rollback database to state from backup.

        Restores the database to the exact state captured in the specified
        backup, including schema structure, data, and migration status.

        Args:
            backup_name (str): Name of the backup to restore from

        Returns:
            Dict[str, Any]: Rollback operation result with:
                - success (bool): Whether rollback completed successfully
                - restored_backup (str): Name of the restored backup
                - current_status (dict): Current migration status after rollback
                - error (str | None): Error message if rollback failed

        Example:
            Rollback after failed migration::

                # After failed migration
                failed_result = await manager.safe_migrate()
                
                if not failed_result["success"] and failed_result["backup_name"]:
                    # Rollback to pre-migration state
                    rollback_result = await manager.rollback_with_backup(
                        failed_result["backup_name"]
                    )
                    
                    if rollback_result["success"]:
                        print("Successfully rolled back to previous state")
                        print(f"Current status: {rollback_result['current_status']}")

            Rollback to specific backup::

                # List available backups first
                backups = await manager.backup.list_backups()
                
                # Choose backup to restore
                selected_backup = "backup_20240115_100000_before_migrate_to_head"
                
                result = await manager.rollback_with_backup(selected_backup)

        Raises:
            Exception: If backup restoration fails or backup doesn't exist

        Note:
            This operation completely replaces the current database state.
            All changes made after the backup was created will be lost.
            The operation includes verification of the restored state.
        """
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