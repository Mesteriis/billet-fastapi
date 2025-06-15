"""
Валидатор миграций Alembic.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any, List

import asyncpg  # type: ignore[import-untyped]
from alembic import command

from core.config import get_settings

from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class MigrationValidator:
    """Валидатор миграций."""
    
    def __init__(self, alembic_config_path: str = "pyproject.toml"):
        self.settings = get_settings()
        self.alembic_config_path = alembic_config_path
        
    def validate_migration_syntax(self, migration_file: Path) -> List[str]:
        """Проверяет синтаксис файла миграции."""
        errors = []
        
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Компилируем Python код для проверки синтаксиса
            compile(content, str(migration_file), 'exec')
            
            # Проверяем наличие обязательных функций
            if 'def upgrade():' not in content:
                errors.append("Отсутствует функция upgrade()")
                
            if 'def downgrade():' not in content:
                errors.append("Отсутствует функция downgrade()")
                
            # Проверяем импорты
            required_imports = ['from alembic import op', 'import sqlalchemy as sa']
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
            with open(migration_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Извлекаем revision и down_revision
            revision = None
            down_revision = None
            
            for line in content.split('\n'):
                if line.strip().startswith('revision ='):
                    revision = line.split('=')[1].strip().strip('\'"')
                elif line.strip().startswith('down_revision ='):
                    down_revision = line.split('=')[1].strip().strip('\'"')
                    
            if not revision:
                errors.append("Не найден revision ID")
                
            if down_revision == 'None':
                down_revision = None
                
            # Проверяем существование родительской миграции
            if down_revision:
                migrations_dir = Path("migrations/versions")
                parent_exists = False
                
                for migration in migrations_dir.glob("*.py"):
                    with open(migration, 'r', encoding='utf-8') as f:
                        parent_content = f.read()
                        if f'revision = \'{down_revision}\'' in parent_content:
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
        db_name = test_db_url.split('/')[-1]
        base_url = test_db_url.rsplit('/', 1)[0]
        
        conn = await asyncpg.connect(base_url.replace('postgresql+asyncpg://', 'postgresql://'))
        try:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
        finally:
            await conn.close()
    
    async def _drop_test_database(self, test_db_url: str):
        """Удаляет тестовую базу данных."""
        db_name = test_db_url.split('/')[-1]
        base_url = test_db_url.rsplit('/', 1)[0]
        
        conn = await asyncpg.connect(base_url.replace('postgresql+asyncpg://', 'postgresql://'))
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        finally:
            await conn.close()
    
    async def _apply_migration_to_test_db(self, test_db_url: str, migration_file: Path):
        """Применяет миграцию к тестовой БД."""
        # Здесь должна быть логика применения конкретной миграции
        # Для упрощения используем subprocess
        env = {"DATABASE_URL": test_db_url}
        result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise ValidationError(f"Ошибка применения миграции: {result.stderr}")
    
    async def _test_migration_rollback(self, test_db_url: str, migration_file: Path):
        """Тестирует откат миграции."""
        env = {"DATABASE_URL": test_db_url}
        result = subprocess.run(
            ["uv", "run", "alembic", "downgrade", "-1"],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise ValidationError(f"Ошибка отката миграции: {result.stderr}") 