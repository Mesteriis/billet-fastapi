"""
Мониторинг состояния миграций Alembic.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import get_settings

from .exceptions import MonitoringError
from .validator import MigrationValidator

logger = logging.getLogger(__name__)


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
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                current_version = result.scalar()
                
                # Получаем информацию о миграциях
                migrations_info = await self._get_migrations_info()
                
                return {
                    "current_version": current_version,
                    "total_migrations": len(migrations_info),
                    "pending_migrations": self._get_pending_migrations(
                        current_version or "", migrations_info
                    ),
                    "last_check": datetime.now().isoformat(),
                    "database_url": self.settings.SQLALCHEMY_DATABASE_URI.split('@')[-1],  # Без credentials
                    "migrations_info": migrations_info
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения статуса миграций: {e}")
            return {
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    async def _get_migrations_info(self) -> List[Dict[str, Any]]:
        """Получает информацию о всех миграциях."""
        migrations: List[Dict[str, Any]] = []
        migrations_dir = Path("migrations/versions")
        
        if not migrations_dir.exists():
            return migrations
            
        for migration_file in sorted(migrations_dir.glob("*.py")):
            try:
                with open(migration_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Извлекаем метаданные
                revision = None
                down_revision = None
                message = None
                
                for line in content.split('\n'):
                    if line.strip().startswith('revision ='):
                        revision = line.split('=')[1].strip().strip('\'"')
                    elif line.strip().startswith('down_revision ='):
                        down_revision = line.split('=')[1].strip().strip('\'"')
                        if down_revision == 'None':
                            down_revision = None
                    elif line.strip().startswith('"""') and not message:
                        # Извлекаем сообщение из docstring
                        message = line.strip().strip('"""')
                        
                migrations.append({
                    "file": migration_file.name,
                    "revision": revision,
                    "down_revision": down_revision,
                    "message": message,
                    "created": datetime.fromtimestamp(migration_file.stat().st_ctime).isoformat()
                })
                
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
            
        return migrations_info[current_index + 1:]
    
    async def check_migration_integrity(self) -> Dict[str, Any]:
        """Проверяет целостность миграций."""
        try:
            validator = MigrationValidator()
            migrations_dir = Path("migrations/versions")
            
            results = {
                "total_checked": 0,
                "errors": [],
                "warnings": [],
                "valid_migrations": []
            }
            
            for migration_file in migrations_dir.glob("*.py"):
                results["total_checked"] += 1
                
                # Проверяем синтаксис
                syntax_errors = validator.validate_migration_syntax(migration_file)
                if syntax_errors:
                    results["errors"].extend([
                        f"{migration_file.name}: {error}" for error in syntax_errors
                    ])
                    continue
                    
                # Проверяем зависимости
                dep_errors = validator.validate_migration_dependencies(migration_file)
                if dep_errors:
                    results["warnings"].extend([
                        f"{migration_file.name}: {error}" for error in dep_errors
                    ])
                    
                if not syntax_errors and not dep_errors:
                    results["valid_migrations"].append(migration_file.name)
                    
            return results
            
        except Exception as e:
            return {"error": str(e)} 