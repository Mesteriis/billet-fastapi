"""
Тесты для DatabaseManager.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.migrations import DatabaseManager, MigrationError


class TestDatabaseManager:
    """Тесты для DatabaseManager."""

    @pytest.fixture
    def db_manager(self):
        """Фикстура DatabaseManager."""
        return DatabaseManager()

    def test_parse_database_url_postgresql(self, db_manager):
        """Тест парсинга PostgreSQL URL."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        base_url, db_name, db_type = db_manager.parse_database_url(url)

        assert db_type == "postgresql"
        assert db_name == "testdb"
        assert base_url == "postgresql://user:pass@localhost:5432/postgres"

    def test_parse_database_url_sqlite(self, db_manager):
        """Тест парсинга SQLite URL."""
        url = "sqlite+aiosqlite:///path/to/test.db"
        base_url, db_name, db_type = db_manager.parse_database_url(url)

        assert db_type == "sqlite"
        assert db_name == "path/to/test.db"
        assert base_url == url

    def test_parse_database_url_unsupported(self, db_manager):
        """Тест парсинга неподдерживаемого URL."""
        url = "mysql://user:pass@localhost/testdb"

        with pytest.raises(MigrationError, match="Неподдерживаемый тип БД"):
            db_manager.parse_database_url(url)

    @pytest.mark.asyncio
    async def test_sqlite_database_exists_memory(self, db_manager):
        """Тест проверки существования in-memory SQLite БД."""
        result = await db_manager._sqlite_database_exists(":memory:")
        assert result is True

    @pytest.mark.asyncio
    async def test_sqlite_database_exists_file(self, db_manager, tmp_path):
        """Тест проверки существования файла SQLite БД."""
        # Несуществующий файл
        db_path = str(tmp_path / "nonexistent.db")
        result = await db_manager._sqlite_database_exists(db_path)
        assert result is False

        # Создаем файл
        Path(db_path).touch()
        result = await db_manager._sqlite_database_exists(db_path)
        assert result is True

    @pytest.mark.asyncio
    async def test_create_sqlite_database_memory(self, db_manager):
        """Тест создания in-memory SQLite БД."""
        result = await db_manager._create_sqlite_database(":memory:")
        assert result is True

    @pytest.mark.asyncio
    async def test_create_sqlite_database_file(self, db_manager, tmp_path):
        """Тест создания файла SQLite БД."""
        db_path = str(tmp_path / "test.db")
        result = await db_manager._create_sqlite_database(db_path)

        assert result is True
        assert Path(db_path).exists()

    @pytest.mark.asyncio
    async def test_drop_sqlite_database_memory(self, db_manager):
        """Тест удаления in-memory SQLite БД."""
        result = await db_manager._drop_sqlite_database(":memory:")
        assert result is True

    @pytest.mark.asyncio
    async def test_drop_sqlite_database_file(self, db_manager, tmp_path):
        """Тест удаления файла SQLite БД."""
        db_path = str(tmp_path / "test.db")
        Path(db_path).touch()  # Создаем файл

        result = await db_manager._drop_sqlite_database(db_path)

        assert result is True
        assert not Path(db_path).exists()

    @pytest.mark.asyncio
    async def test_drop_sqlite_database_nonexistent(self, db_manager, tmp_path):
        """Тест удаления несуществующего файла SQLite БД."""
        db_path = str(tmp_path / "nonexistent.db")
        result = await db_manager._drop_sqlite_database(db_path)
        assert result is True  # Должно успешно завершиться

    @pytest.mark.asyncio
    @patch("core.migrations.database.create_async_engine")
    async def test_test_connection_success(self, mock_create_engine, db_manager):
        """Тест успешного подключения к БД."""
        # Мокаем engine и connection
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        result = await db_manager.test_connection("sqlite+aiosqlite:///test.db")

        assert result is True
        mock_conn.execute.assert_called_once()
        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    @patch("core.migrations.database.create_async_engine")
    async def test_test_connection_failure(self, mock_create_engine, db_manager):
        """Тест неудачного подключения к БД."""
        mock_create_engine.side_effect = Exception("Connection failed")

        result = await db_manager.test_connection("sqlite+aiosqlite:///test.db")

        assert result is False

    @pytest.mark.asyncio
    async def test_database_exists_calls_correct_method(self, db_manager):
        """Тест что database_exists вызывает правильный метод."""
        with (
            patch.object(db_manager, "_postgresql_database_exists") as mock_pg,
            patch.object(db_manager, "_sqlite_database_exists") as mock_sqlite,
        ):
            mock_pg.return_value = True
            await db_manager.database_exists("postgresql://user@localhost/test")
            mock_pg.assert_called_once()

            mock_sqlite.return_value = True
            await db_manager.database_exists("sqlite:///test.db")
            mock_sqlite.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_database_calls_correct_method(self, db_manager):
        """Тест что create_database вызывает правильный метод."""
        with (
            patch.object(db_manager, "database_exists", return_value=False),
            patch.object(db_manager, "_create_postgresql_database") as mock_pg,
            patch.object(db_manager, "_create_sqlite_database") as mock_sqlite,
        ):
            mock_pg.return_value = True
            await db_manager.create_database("postgresql://user@localhost/test")
            mock_pg.assert_called_once()

            mock_sqlite.return_value = True
            await db_manager.create_database("sqlite:///test.db")
            mock_sqlite.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_database_already_exists(self, db_manager):
        """Тест создания БД которая уже существует."""
        with patch.object(db_manager, "database_exists", return_value=True):
            result = await db_manager.create_database("sqlite:///test.db")
            assert result is True

    @pytest.mark.asyncio
    async def test_drop_database_calls_correct_method(self, db_manager):
        """Тест что drop_database вызывает правильный метод."""
        with (
            patch.object(db_manager, "_drop_postgresql_database") as mock_pg,
            patch.object(db_manager, "_drop_sqlite_database") as mock_sqlite,
        ):
            mock_pg.return_value = True
            await db_manager.drop_database("postgresql://user@localhost/test")
            mock_pg.assert_called_once()

            mock_sqlite.return_value = True
            await db_manager.drop_database("sqlite:///test.db")
            mock_sqlite.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_database_info_nonexistent(self, db_manager):
        """Тест получения информации о несуществующей БД."""
        with patch.object(db_manager, "database_exists", return_value=False):
            info = await db_manager.get_database_info("sqlite:///test.db")

            assert info["exists"] is False
            assert info["connection_test"] is False
            assert info["database_name"] == "test.db"
            assert info["database_type"] == "sqlite"

    @pytest.mark.asyncio
    async def test_get_database_info_existing(self, db_manager):
        """Тест получения информации о существующей БД."""
        with (
            patch.object(db_manager, "database_exists", return_value=True),
            patch.object(db_manager, "test_connection", return_value=True),
            patch.object(db_manager, "_get_sqlite_info", return_value={"size": "1.5 MB", "tables_count": 5}),
        ):
            info = await db_manager.get_database_info("sqlite:///test.db")

            assert info["exists"] is True
            assert info["connection_test"] is True
            assert info["size"] == "1.5 MB"
            assert info["tables_count"] == 5

    @pytest.mark.asyncio
    async def test_ensure_database_exists_creates_new(self, db_manager):
        """Тест ensure_database_exists создает новую БД."""
        with (
            patch.object(db_manager, "database_exists", return_value=False),
            patch.object(db_manager, "create_database", return_value=True),
            patch.object(db_manager, "test_connection", return_value=True),
        ):
            result = await db_manager.ensure_database_exists("sqlite:///test.db")
            assert result is True

    @pytest.mark.asyncio
    async def test_ensure_database_exists_already_exists(self, db_manager):
        """Тест ensure_database_exists с существующей БД."""
        with (
            patch.object(db_manager, "database_exists", return_value=True),
            patch.object(db_manager, "test_connection", return_value=True),
        ):
            result = await db_manager.ensure_database_exists("sqlite:///test.db")
            assert result is True

    @pytest.mark.asyncio
    async def test_ensure_database_exists_creation_fails(self, db_manager):
        """Тест ensure_database_exists когда создание не удается."""
        with (
            patch.object(db_manager, "database_exists", return_value=False),
            patch.object(db_manager, "create_database", return_value=False),
        ):
            result = await db_manager.ensure_database_exists("sqlite:///test.db")
            assert result is False

    @pytest.mark.asyncio
    async def test_ensure_database_exists_connection_fails(self, db_manager):
        """Тест ensure_database_exists когда подключение не работает."""
        with (
            patch.object(db_manager, "database_exists", return_value=True),
            patch.object(db_manager, "test_connection", return_value=False),
        ):
            result = await db_manager.ensure_database_exists("sqlite:///test.db")
            assert result is False

    @pytest.mark.asyncio
    async def test_create_database_error_handling(self, db_manager):
        """Тест обработки ошибок при создании БД."""
        with (
            patch.object(db_manager, "database_exists", return_value=False),
            patch.object(db_manager, "_create_sqlite_database", side_effect=Exception("Creation failed")),
        ):
            with pytest.raises(MigrationError, match="Не удалось создать базу данных"):
                await db_manager.create_database("sqlite:///test.db")

    @pytest.mark.asyncio
    async def test_drop_database_error_handling(self, db_manager):
        """Тест обработки ошибок при удалении БД."""
        with patch.object(db_manager, "_drop_sqlite_database", side_effect=Exception("Drop failed")):
            with pytest.raises(MigrationError, match="Не удалось удалить базу данных"):
                await db_manager.drop_database("sqlite:///test.db")


class TestDatabaseManagerIntegration:
    """Интеграционные тесты для DatabaseManager."""

    @pytest.mark.asyncio
    async def test_sqlite_full_lifecycle(self, tmp_path):
        """Тест полного жизненного цикла SQLite БД."""
        db_manager = DatabaseManager()
        db_path = str(tmp_path / "lifecycle_test.db")
        db_url = f"sqlite+aiosqlite:///{db_path}"

        # 1. БД не должна существовать
        assert not await db_manager.database_exists(db_url)

        # 2. Создаем БД
        assert await db_manager.create_database(db_url)

        # 3. БД должна существовать
        assert await db_manager.database_exists(db_url)

        # 4. Тестируем подключение
        assert await db_manager.test_connection(db_url)

        # 5. Получаем информацию
        info = await db_manager.get_database_info(db_url)
        assert info["exists"] is True
        assert info["connection_test"] is True
        assert info["database_type"] == "sqlite"

        # 6. Удаляем БД
        assert await db_manager.drop_database(db_url)

        # 7. БД не должна существовать
        assert not await db_manager.database_exists(db_url)

    @pytest.mark.asyncio
    async def test_ensure_database_exists_integration(self, tmp_path):
        """Интеграционный тест ensure_database_exists."""
        db_manager = DatabaseManager()
        db_path = str(tmp_path / "ensure_test.db")
        db_url = f"sqlite+aiosqlite:///{db_path}"

        # Первый вызов должен создать БД
        assert await db_manager.ensure_database_exists(db_url)
        assert Path(db_path).exists()

        # Второй вызов должен просто подтвердить существование
        assert await db_manager.ensure_database_exists(db_url)
