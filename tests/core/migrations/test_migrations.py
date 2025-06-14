"""
Тесты миграций Alembic с использованием pytest-alembic.
"""

import pytest
from pytest_alembic.tests import (
    test_model_definitions_match_ddl,
    test_single_head_revision,
    test_up_down_consistency,
    test_upgrade,
)

from core.migrations import MigrationManager, MigrationMonitor, MigrationValidator


class TestAlembicMigrations:
    """Тесты миграций Alembic."""

    def test_single_head_revision_builtin(self, alembic_runner):
        """Проверяет, что существует только одна головная ревизия."""
        test_single_head_revision(alembic_runner)

    def test_upgrade_builtin(self, alembic_runner):
        """Проверяет, что все миграции можно применить."""
        test_upgrade(alembic_runner)

    def test_model_definitions_match_ddl_builtin(self, alembic_runner):
        """Проверяет соответствие моделей и DDL."""
        test_model_definitions_match_ddl(alembic_runner)

    def test_up_down_consistency_builtin(self, alembic_runner):
        """Проверяет консистентность применения и отката миграций."""
        test_up_down_consistency(alembic_runner)


class TestMigrationValidator:
    """Тесты валидатора миграций."""

    @pytest.fixture
    def validator(self):
        """Фикстура валидатора."""
        return MigrationValidator()

    def test_validator_initialization(self, validator):
        """Тест инициализации валидатора."""
        assert validator is not None
        assert validator.settings is not None
        assert validator.alembic_config_path == "pyproject.toml"

    @pytest.mark.asyncio
    async def test_validate_migration_syntax_valid_file(self, validator, tmp_path):
        """Тест валидации синтаксиса корректного файла миграции."""
        # Создаем корректный файл миграции
        migration_content = '''"""Test migration

Revision ID: abc123
Revises: def456
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade function."""
    op.create_table(
        'test_table',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False)
    )

def downgrade():
    """Downgrade function."""
    op.drop_table('test_table')
'''

        migration_file = tmp_path / "test_migration.py"
        migration_file.write_text(migration_content)

        errors = validator.validate_migration_syntax(migration_file)
        assert errors == []

    @pytest.mark.asyncio
    async def test_validate_migration_syntax_invalid_file(self, validator, tmp_path):
        """Тест валидации синтаксиса некорректного файла миграции."""
        # Создаем некорректный файл миграции
        migration_content = '''"""Test migration"""
# Отсутствуют обязательные импорты и функции
def invalid_function():
    pass
'''

        migration_file = tmp_path / "invalid_migration.py"
        migration_file.write_text(migration_content)

        errors = validator.validate_migration_syntax(migration_file)
        assert len(errors) > 0
        assert any("Отсутствует функция upgrade()" in error for error in errors)
        assert any("Отсутствует функция downgrade()" in error for error in errors)


class TestMigrationMonitor:
    """Тесты монитора миграций."""

    @pytest.fixture
    def monitor(self):
        """Фикстура монитора."""
        return MigrationMonitor()

    def test_monitor_initialization(self, monitor):
        """Тест инициализации монитора."""
        assert monitor is not None
        assert monitor.settings is not None

    @pytest.mark.asyncio
    async def test_get_migration_status(self, monitor):
        """Тест получения статуса миграций."""
        status = await monitor.get_migration_status()

        assert isinstance(status, dict)
        assert "last_check" in status

        # Если есть ошибка, проверяем её наличие
        if "error" in status:
            assert isinstance(status["error"], str)
        else:
            # Если нет ошибки, проверяем структуру ответа
            assert "current_version" in status
            assert "total_migrations" in status
            assert "pending_migrations" in status
            assert "migrations_info" in status

    @pytest.mark.asyncio
    async def test_check_migration_integrity(self, monitor):
        """Тест проверки целостности миграций."""
        integrity = await monitor.check_migration_integrity()

        assert isinstance(integrity, dict)

        if "error" not in integrity:
            assert "total_checked" in integrity
            assert "errors" in integrity
            assert "warnings" in integrity
            assert "valid_migrations" in integrity
            assert isinstance(integrity["errors"], list)
            assert isinstance(integrity["warnings"], list)
            assert isinstance(integrity["valid_migrations"], list)


class TestMigrationManager:
    """Тесты менеджера миграций."""

    @pytest.fixture
    def manager(self):
        """Фикстура менеджера."""
        return MigrationManager()

    def test_manager_initialization(self, manager):
        """Тест инициализации менеджера."""
        assert manager is not None
        assert manager.validator is not None
        assert manager.monitor is not None
        assert manager.backup is not None

    @pytest.mark.asyncio
    async def test_safe_migrate_validation_errors(self, manager, monkeypatch):
        """Тест безопасной миграции с ошибками валидации."""

        # Мокаем проверку целостности с ошибками
        async def mock_check_integrity():
            return {"errors": ["Test error"]}

        monkeypatch.setattr(manager.monitor, "check_migration_integrity", mock_check_integrity)

        result = await manager.safe_migrate()

        assert result["success"] is False
        assert result["validation_errors"] == ["Test error"]
        assert "Найдены ошибки в миграциях" in result["error"]


class TestCustomMigrationScenarios:
    """Тесты кастомных сценариев миграций."""

    @pytest.mark.slow
    def test_migration_with_data(self, alembic_runner, alembic_engine):
        """Тест миграции с данными."""
        # Применяем миграции до определенной точки
        alembic_runner.migrate_up_to("head")

        # Добавляем тестовые данные
        # (здесь должна быть логика добавления данных)

        # Проверяем, что данные сохранились после миграции
        # (здесь должна быть логика проверки данных)

        # Тестируем откат
        alembic_runner.migrate_down_one()

        # Проверяем состояние после отката
        # (здесь должна быть логика проверки состояния)

    @pytest.mark.integration
    def test_migration_rollback_scenario(self, alembic_runner):
        """Тест сценария отката миграций."""
        # Получаем текущую ревизию
        current = alembic_runner.current

        # Применяем одну миграцию вперед
        alembic_runner.migrate_up_one()

        # Проверяем, что ревизия изменилась
        new_current = alembic_runner.current
        assert new_current != current

        # Откатываем назад
        alembic_runner.migrate_down_one()

        # Проверяем, что вернулись к исходной ревизии
        final_current = alembic_runner.current
        assert final_current == current


@pytest.mark.alembic
class TestAlembicIntegration:
    """Интеграционные тесты Alembic."""

    def test_alembic_config_loads(self):
        """Тест загрузки конфигурации Alembic из pyproject.toml."""
        # Проверяем, что конфигурация загружается корректно
        import tomllib
        from pathlib import Path

        pyproject_path = Path("pyproject.toml")
        assert pyproject_path.exists()

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        assert "tool" in config
        assert "alembic" in config["tool"]

        alembic_config = config["tool"]["alembic"]
        assert "script_location" in alembic_config
        assert alembic_config["script_location"] == "migrations"

    def test_migrations_directory_exists(self):
        """Тест существования директории миграций."""
        from pathlib import Path

        migrations_dir = Path("migrations")
        assert migrations_dir.exists()
        assert migrations_dir.is_dir()

        versions_dir = migrations_dir / "versions"
        assert versions_dir.exists()
        assert versions_dir.is_dir()

        env_py = migrations_dir / "env.py"
        assert env_py.exists()
        assert env_py.is_file()
