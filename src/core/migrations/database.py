"""
Модуль для управления базой данных.
Включает автоматическое создание БД, если она не существует.
"""

import asyncio
import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

import asyncpg  # type: ignore[import-untyped]
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import get_settings

from .exceptions import MigrationError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер для управления базой данных."""
    
    def __init__(self):
        self.settings = get_settings()
        
    def parse_database_url(self, db_url: str) -> Tuple[str, str, str]:
        """
        Парсит URL базы данных и возвращает компоненты.
        
        Returns:
            Tuple[base_url, db_name, db_type]
        """
        parsed = urlparse(db_url)
        
        # Определяем тип БД
        if parsed.scheme.startswith('postgresql'):
            db_type = 'postgresql'
            # Убираем +asyncpg из схемы для подключения к postgres
            base_scheme = 'postgresql'
        elif parsed.scheme.startswith('sqlite'):
            db_type = 'sqlite'
            base_scheme = parsed.scheme
        else:
            raise MigrationError(f"Неподдерживаемый тип БД: {parsed.scheme}")
        
        # Извлекаем имя БД
        db_name = parsed.path.lstrip('/')
        
        # Формируем базовый URL (без имени БД для PostgreSQL)
        if db_type == 'postgresql':
            # Подключаемся к postgres БД для создания новой
            base_url = f"{base_scheme}://{parsed.netloc}/postgres"
        else:
            # Для SQLite возвращаем полный путь
            base_url = db_url
            
        return base_url, db_name, db_type
    
    async def database_exists(self, db_url: str) -> bool:
        """Проверяет существование базы данных."""
        base_url, db_name, db_type = self.parse_database_url(db_url)
        
        try:
            if db_type == 'postgresql':
                return await self._postgresql_database_exists(base_url, db_name)
            elif db_type == 'sqlite':
                return await self._sqlite_database_exists(db_name)
        except Exception as e:
            logger.warning(f"Ошибка проверки существования БД: {e}")
            return False
            
        return False
    
    async def _postgresql_database_exists(self, base_url: str, db_name: str) -> bool:
        """Проверяет существование PostgreSQL базы данных."""
        try:
            # Подключаемся к postgres БД
            conn = await asyncpg.connect(base_url)
            try:
                # Проверяем существование БД
                result = await conn.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = $1",
                    db_name
                )
                return result is not None
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Ошибка проверки PostgreSQL БД: {e}")
            return False
    
    async def _sqlite_database_exists(self, db_path: str) -> bool:
        """Проверяет существование SQLite базы данных."""
        from pathlib import Path

        # Для SQLite просто проверяем существование файла
        if db_path == ":memory:":
            return True  # In-memory БД всегда "существует"
            
        return Path(db_path).exists()
    
    async def create_database(self, db_url: str) -> bool:
        """
        Создает базу данных, если она не существует.
        
        Returns:
            bool: True если БД была создана или уже существует
        """
        # Сначала проверяем существование
        if await self.database_exists(db_url):
            logger.info("База данных уже существует")
            return True
            
        base_url, db_name, db_type = self.parse_database_url(db_url)
        
        try:
            if db_type == 'postgresql':
                return await self._create_postgresql_database(base_url, db_name)
            elif db_type == 'sqlite':
                return await self._create_sqlite_database(db_name)
        except Exception as e:
            logger.error(f"Ошибка создания БД: {e}")
            raise MigrationError(f"Не удалось создать базу данных: {e}")
            
        return False
    
    async def _create_postgresql_database(self, base_url: str, db_name: str) -> bool:
        """Создает PostgreSQL базу данных."""
        try:
            logger.info(f"Создание PostgreSQL базы данных: {db_name}")
            
            # Подключаемся к postgres БД
            conn = await asyncpg.connect(base_url)
            try:
                # Создаем БД (нужно использовать execute, а не fetchval)
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                logger.info(f"✅ База данных {db_name} успешно создана")
                return True
            finally:
                await conn.close()
                
        except asyncpg.DuplicateDatabaseError:
            logger.info(f"База данных {db_name} уже существует")
            return True
        except Exception as e:
            logger.error(f"Ошибка создания PostgreSQL БД: {e}")
            raise
    
    async def _create_sqlite_database(self, db_path: str) -> bool:
        """Создает SQLite базу данных."""
        try:
            if db_path == ":memory:":
                logger.info("Используется in-memory SQLite БД")
                return True
                
            from pathlib import Path
            
            logger.info(f"Создание SQLite базы данных: {db_path}")
            
            # Создаем директорию если нужно
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Создаем пустую БД (SQLite создает файл при первом подключении)
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.close()
            
            logger.info(f"✅ SQLite база данных {db_path} успешно создана")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания SQLite БД: {e}")
            raise
    
    async def drop_database(self, db_url: str) -> bool:
        """
        Удаляет базу данных.
        ОСТОРОЖНО: Это удалит все данные!
        """
        base_url, db_name, db_type = self.parse_database_url(db_url)
        
        try:
            if db_type == 'postgresql':
                return await self._drop_postgresql_database(base_url, db_name)
            elif db_type == 'sqlite':
                return await self._drop_sqlite_database(db_name)
        except Exception as e:
            logger.error(f"Ошибка удаления БД: {e}")
            raise MigrationError(f"Не удалось удалить базу данных: {e}")
            
        return False
    
    async def _drop_postgresql_database(self, base_url: str, db_name: str) -> bool:
        """Удаляет PostgreSQL базу данных."""
        try:
            logger.warning(f"🗑️ Удаление PostgreSQL базы данных: {db_name}")
            
            conn = await asyncpg.connect(base_url)
            try:
                # Закрываем все активные соединения к БД
                await conn.execute(f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = '{db_name}' AND pid <> pg_backend_pid()
                """)
                
                # Удаляем БД
                await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
                logger.info(f"✅ База данных {db_name} успешно удалена")
                return True
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Ошибка удаления PostgreSQL БД: {e}")
            raise
    
    async def _drop_sqlite_database(self, db_path: str) -> bool:
        """Удаляет SQLite базу данных."""
        try:
            if db_path == ":memory:":
                logger.info("In-memory SQLite БД не требует удаления")
                return True
                
            from pathlib import Path
            
            logger.warning(f"🗑️ Удаление SQLite базы данных: {db_path}")
            
            db_file = Path(db_path)
            if db_file.exists():
                db_file.unlink()
                logger.info(f"✅ SQLite база данных {db_path} успешно удалена")
            else:
                logger.info(f"SQLite база данных {db_path} не существует")
                
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления SQLite БД: {e}")
            raise
    
    async def test_connection(self, db_url: str) -> bool:
        """Тестирует подключение к базе данных."""
        try:
            engine = create_async_engine(db_url)
            
            async with engine.connect() as conn:
                # Простой запрос для проверки соединения
                await conn.execute(text("SELECT 1"))
                
            await engine.dispose()
            logger.info("✅ Подключение к БД успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            return False
    
    async def get_database_info(self, db_url: str) -> dict:
        """Получает информацию о базе данных."""
        base_url, db_name, db_type = self.parse_database_url(db_url)
        
        info = {
            "database_name": db_name,
            "database_type": db_type,
            "exists": await self.database_exists(db_url),
            "connection_test": False,
            "size": None,
            "tables_count": None
        }
        
        if info["exists"]:
            info["connection_test"] = await self.test_connection(db_url)
            
            if info["connection_test"]:
                try:
                    # Получаем дополнительную информацию
                    if db_type == 'postgresql':
                        info.update(await self._get_postgresql_info(db_url, db_name))
                    elif db_type == 'sqlite':
                        info.update(await self._get_sqlite_info(db_url))
                except Exception as e:
                    logger.warning(f"Не удалось получить дополнительную информацию о БД: {e}")
        
        return info
    
    async def _get_postgresql_info(self, db_url: str, db_name: str) -> dict:
        """Получает информацию о PostgreSQL базе данных."""
        try:
            engine = create_async_engine(db_url)
            
            async with engine.connect() as conn:
                # Размер БД
                size_result = await conn.execute(text(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                ))
                size = size_result.scalar()
                
                # Количество таблиц
                tables_result = await conn.execute(text("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """))
                tables_count = tables_result.scalar()
                
            await engine.dispose()
            
            return {
                "size": size,
                "tables_count": tables_count
            }
            
        except Exception as e:
            logger.warning(f"Ошибка получения информации о PostgreSQL: {e}")
            return {}
    
    async def _get_sqlite_info(self, db_url: str) -> dict:
        """Получает информацию о SQLite базе данных."""
        try:
            from pathlib import Path

            # Извлекаем путь к файлу
            db_path = db_url.replace("sqlite+aiosqlite:///", "")
            
            if db_path == ":memory:":
                return {"size": "In-memory", "tables_count": 0}
            
            # Размер файла
            db_file = Path(db_path)
            if db_file.exists():
                size_bytes = db_file.stat().st_size
                size = f"{size_bytes / 1024 / 1024:.2f} MB"
            else:
                size = "0 MB"
            
            # Количество таблиц
            engine = create_async_engine(db_url)
            async with engine.connect() as conn:
                tables_result = await conn.execute(text(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                ))
                tables_count = tables_result.scalar()
                
            await engine.dispose()
            
            return {
                "size": size,
                "tables_count": tables_count
            }
            
        except Exception as e:
            logger.warning(f"Ошибка получения информации о SQLite: {e}")
            return {}
    
    async def ensure_database_exists(self, db_url: Optional[str] = None) -> bool:
        """
        Гарантирует существование базы данных.
        Создает БД если она не существует.
        """
        if db_url is None:
            db_url = self.settings.SQLALCHEMY_DATABASE_URI
            
        logger.info(f"🔍 Проверка существования базы данных...")
        
        if await self.database_exists(db_url):
            logger.info("✅ База данных уже существует")
            
            # Тестируем подключение
            if await self.test_connection(db_url):
                logger.info("✅ Подключение к БД работает")
                return True
            else:
                logger.error("❌ Не удается подключиться к существующей БД")
                return False
        else:
            logger.info("📝 База данных не существует, создаем...")
            
            if await self.create_database(db_url):
                logger.info("✅ База данных успешно создана")
                
                # Тестируем подключение к новой БД
                if await self.test_connection(db_url):
                    logger.info("✅ Подключение к новой БД работает")
                    return True
                else:
                    logger.error("❌ Не удается подключиться к созданной БД")
                    return False
            else:
                logger.error("❌ Не удалось создать базу данных")
                return False