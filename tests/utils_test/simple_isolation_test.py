"""
Простой тест для проверки работы декораторов изоляции.
"""

import pytest

from tests.utils_test.isolation_decorators import transaction_isolated_test


class TestSimpleIsolation:
    """Простые тесты изоляции."""

    @transaction_isolated_test(verbose=True)
    async def test_simple_isolation(self, setup_test_models):
        """Простой тест изоляции с автоматической настройкой фабрик."""
        # Фабрики автоматически настроены декоратором

        # Создаем тестовые данные
        from tests.core.base.test_repo.factories import UserFactory

        user = await UserFactory.create(username="isolated_user_1")

        # Проверяем что данные созданы
        assert user.id is not None
        assert user.username == "isolated_user_1"

        # Все данные будут автоматически откачены после завершения теста

    async def test_without_isolation(self, setup_test_models):
        """Тест без изоляции для сравнения."""
        # Используем стандартную настройку фабрик через conftest.py

        from tests.core.base.test_repo.factories import UserFactory

        # Настраиваем фабрику для этого теста
        UserFactory._meta.sqlalchemy_session = setup_test_models

        # Создаем тестовые данные
        user = await UserFactory.create(username="normal_user")

        # Проверяем что данные созданы
        assert user.id is not None
        assert user.username == "normal_user"
