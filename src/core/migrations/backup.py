"""
Система бэкапов для миграций Alembic.
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.config import get_settings

from .exceptions import BackupError

logger = logging.getLogger(__name__)


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
                "database_url": self.settings.SQLALCHEMY_DATABASE_URI.split('@')[-1],
                "backup_file": str(backup_file),
                "file_size": backup_file.stat().st_size if backup_file.exists() else 0
            }
            
            metadata_file = self.backup_dir / f"{backup_name}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
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
        
        cmd = [
            "pg_dump",
            "--no-password",
            "--verbose",
            "--clean",
            "--no-acl",
            "--no-owner",
            pg_url
        ]
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
        if result.returncode != 0:
            raise BackupError(f"Ошибка pg_dump: {result.stderr}")
    
    async def _create_sqlite_dump(self, backup_file: Path, db_url: str):
        """Создает дамп SQLite."""
        # Извлекаем путь к файлу БД
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        
        cmd = ["sqlite3", db_path, ".dump"]
        
        with open(backup_file, 'w') as f:
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
            with open(metadata_file, 'r', encoding='utf-8') as f:
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
        
        with open(backup_file, 'r') as f:
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
        
        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
            
        if result.returncode != 0:
            raise BackupError(f"Ошибка sqlite3: {result.stderr}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Возвращает список всех бэкапов."""
        backups = []
        
        for metadata_file in self.backup_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
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