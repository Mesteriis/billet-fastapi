"""
Тесты для фабрик пользователей.
"""

from datetime import datetime

import pytest

from apps.auth.models import RefreshToken
from apps.users.models import User
from tests.factories.user_factory import (
    AdminUserFactory,
    InactiveUserFactory,
    RefreshTokenFactory,
    SimpleUserFactory,
    VerifiedUserFactory,
    create_admin_user,
    create_inactive_user,
    create_user,
    create_verified_user,
    make_admin_data,
    make_user_data,
)


@pytest.mark.factories
@pytest.mark.unit
class TestUserFactories:
    """Тесты фабрик пользователей."""

    def test_simple_user_factory_creates_user(self, user_factory):
        """Тест создания простого пользователя через фабрику."""
        user = user_factory()

        assert isinstance(user, User)
        assert user.email is not None
        assert user.username is not None
        assert user.full_name is not None
        assert user.is_active is True
        assert user.is_verified is False
        assert user.is_superuser is False
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_verified_user_factory_creates_verified_user(self, verified_user_factory):
        """Тест создания верифицированного пользователя."""
        user = verified_user_factory()

        assert isinstance(user, User)
        assert user.is_verified is True
        assert user.is_active is True
        assert user.is_superuser is False

    def test_admin_user_factory_creates_admin(self, admin_user_factory):
        """Тест создания администратора."""
        admin = admin_user_factory()

        assert isinstance(admin, User)
        assert admin.is_superuser is True
        assert admin.is_verified is True
        assert admin.is_active is True
        assert "admin" in admin.email
        assert "admin" in admin.username

    def test_inactive_user_factory_creates_inactive_user(self, inactive_user_factory):
        """Тест создания неактивного пользователя."""
        user = inactive_user_factory()

        assert isinstance(user, User)
        assert user.is_active is False
        assert user.is_verified is False
        assert user.is_superuser is False

    def test_refresh_token_factory_creates_token(self, refresh_token_factory):
        """Тест создания refresh токена."""
        token = refresh_token_factory()

        assert isinstance(token, RefreshToken)
        assert token.token is not None
        assert token.expires_at is not None
        assert token.is_revoked is False
        assert token.user is not None
        assert isinstance(token.user, User)

    def test_user_factory_with_custom_params(self, user_factory):
        """Тест создания пользователя с кастомными параметрами."""
        custom_email = "custom@example.com"
        user = user_factory(email=custom_email, is_active=False)

        assert user.email == custom_email
        assert user.is_active is False

    def test_multiple_users_are_unique(self, user_factory):
        """Тест что множественные пользователи уникальны."""
        users = [user_factory() for _ in range(5)]

        emails = [user.email for user in users]
        usernames = [user.username for user in users]

        # Проверяем уникальность email и username
        assert len(set(emails)) == 5
        assert len(set(usernames)) == 5

    def test_admin_sequence_generation(self, admin_user_factory):
        """Тест генерации последовательности для админов."""
        admins = [admin_user_factory() for _ in range(3)]

        # Проверяем что email и username содержат последовательные номера
        for i, admin in enumerate(admins):
            assert f"admin{i}" in admin.email
            assert f"admin{i}" in admin.username


@pytest.mark.factories
@pytest.mark.unit
class TestUserFactoryFunctions:
    """Тесты функций-обёрток для фабрик."""

    def test_create_user_function(self):
        """Тест функции create_user."""
        user = create_user(email="test@example.com")

        assert isinstance(user, User)
        assert user.email == "test@example.com"
        assert user.is_verified is False

    def test_create_verified_user_function(self):
        """Тест функции create_verified_user."""
        user = create_verified_user(email="verified@example.com")

        assert isinstance(user, User)
        assert user.email == "verified@example.com"
        assert user.is_verified is True

    def test_create_admin_user_function(self):
        """Тест функции create_admin_user."""
        admin = create_admin_user()

        assert isinstance(admin, User)
        assert admin.is_superuser is True
        assert admin.is_verified is True

    def test_create_inactive_user_function(self):
        """Тест функции create_inactive_user."""
        user = create_inactive_user()

        assert isinstance(user, User)
        assert user.is_active is False


@pytest.mark.factories
@pytest.mark.unit
class TestUserDataFunctions:
    """Тесты функций создания данных пользователей."""

    def test_make_user_data_returns_dict(self):
        """Тест что make_user_data возвращает словарь."""
        data = make_user_data()

        assert isinstance(data, dict)
        assert "email" in data
        assert "username" in data
        assert "full_name" in data
        assert "is_active" in data
        assert "is_verified" in data
        assert "is_superuser" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_make_user_data_with_custom_params(self):
        """Тест make_user_data с кастомными параметрами."""
        custom_email = "custom@test.com"
        data = make_user_data(email=custom_email, is_active=False)

        assert data["email"] == custom_email
        assert data["is_active"] is False

    def test_make_admin_data_returns_admin_dict(self):
        """Тест что make_admin_data возвращает данные админа."""
        data = make_admin_data()

        assert isinstance(data, dict)
        assert data["is_superuser"] is True
        assert data["is_verified"] is True
        assert "admin" in data["email"]
        assert "admin" in data["username"]
        assert data["full_name"] == "Admin User"

    def test_make_admin_data_with_overrides(self):
        """Тест make_admin_data с переопределением параметров."""
        custom_name = "Custom Admin"
        data = make_admin_data(full_name=custom_name, is_active=False)

        assert data["full_name"] == custom_name
        assert data["is_active"] is False
        assert data["is_superuser"] is True  # Не должно переопределяться

    def test_user_data_timestamps(self):
        """Тест что данные пользователя содержат корректные временные метки."""
        data = make_user_data()

        assert isinstance(data["created_at"], datetime)
        assert isinstance(data["updated_at"], datetime)
        assert data["created_at"] <= data["updated_at"]

    def test_multiple_user_data_unique(self):
        """Тест что множественные данные пользователей уникальны."""
        data_list = [make_user_data() for _ in range(5)]

        emails = [data["email"] for data in data_list]
        usernames = [data["username"] for data in data_list]

        assert len(set(emails)) == 5
        assert len(set(usernames)) == 5


@pytest.mark.factories
@pytest.mark.unit
class TestFactoryIntegration:
    """Интеграционные тесты фабрик."""

    def test_user_with_refresh_token(self, user_factory, refresh_token_factory):
        """Тест создания пользователя с refresh токеном."""
        user = user_factory()
        token = refresh_token_factory(user=user)

        assert token.user == user
        assert token.token is not None
        assert not token.is_revoked

    def test_factory_inheritance_chain(self):
        """Тест цепочки наследования фабрик."""
        # Базовая фабрика
        user = SimpleUserFactory()
        assert not user.is_verified
        assert not user.is_superuser

        # Верифицированный пользователь наследует от базовой
        verified = VerifiedUserFactory()
        assert verified.is_verified
        assert not verified.is_superuser

        # Админ наследует от базовой
        admin = AdminUserFactory()
        assert admin.is_verified
        assert admin.is_superuser

    def test_factory_data_consistency(self):
        """Тест консистентности данных между фабриками."""
        users = [SimpleUserFactory(), VerifiedUserFactory(), AdminUserFactory(), InactiveUserFactory()]

        for user in users:
            # Все пользователи должны иметь базовые поля
            assert user.email is not None
            assert user.username is not None
            assert user.full_name is not None
            assert user.created_at is not None
            assert user.updated_at is not None

            # Email должен быть валидным
            assert "@" in user.email
            assert len(user.username) > 0

    def test_factory_performance(self, user_factory):
        """Тест производительности создания пользователей."""
        import time

        start_time = time.time()
        users = [user_factory() for _ in range(100)]
        end_time = time.time()

        # Создание 100 пользователей должно занимать менее 1 секунды
        assert end_time - start_time < 1.0
        assert len(users) == 100

        # Все пользователи должны быть уникальными
        user_ids = [id(user) for user in users]
        assert len(set(user_ids)) == 100


@pytest.mark.factories
@pytest.mark.unit
class TestFactoryEdgeCases:
    """Тесты граничных случаев для фабрик."""

    def test_factory_with_none_values(self, user_factory):
        """Тест фабрики с None значениями."""
        user = user_factory(bio=None, avatar_url=None)

        assert user.bio is None
        assert user.avatar_url is None
        assert user.email is not None  # Обязательные поля не должны быть None

    def test_factory_with_empty_strings(self, user_factory):
        """Тест фабрики с пустыми строками."""
        # Пустые строки не должны создаваться для обязательных полей
        user = user_factory()

        assert user.email != ""
        assert user.username != ""
        assert user.full_name != ""

    def test_refresh_token_expiry_logic(self, refresh_token_factory):
        """Тест логики истечения refresh токена."""
        from datetime import timedelta

        # Обычный токен
        token = refresh_token_factory()
        assert token.expires_at > datetime.utcnow()

        # Просроченный токен
        from tests.factories.user_factory import ExpiredRefreshTokenFactory

        expired_token = ExpiredRefreshTokenFactory()
        assert expired_token.expires_at < datetime.utcnow()

    def test_factory_unicode_support(self, user_factory):
        """Тест поддержки unicode в фабриках."""
        unicode_name = "Тестовый Пользователь 🚀"
        user = user_factory(full_name=unicode_name)

        assert user.full_name == unicode_name
        assert len(user.full_name) > 0
