"""
Фабрика для создания тестовых пользователей.
"""

from datetime import datetime, timedelta
from typing import Any

import factory
from factory import Faker, SubFactory

from apps.auth.models import RefreshToken
from apps.users.models import User


class UserFactory(factory.Factory):
    """Фабрика для создания пользователей."""

    class Meta:
        model = User

    # Основные поля
    email = Faker("email")
    username = Faker("user_name")
    full_name = Faker("name")

    # Профильные данные
    avatar_url = factory.LazyFunction(lambda: f"https://example.com/avatars/{factory.Faker('uuid4').generate()}.jpg")
    bio = Faker("text", max_nb_chars=200)

    # Статусы
    is_active = True
    is_verified = False
    is_superuser = False

    # Даты
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)

    @factory.post_generation
    def set_updated_at(obj, create, extracted, **kwargs):
        """Устанавливает updated_at после created_at."""
        if obj.created_at:
            obj.updated_at = obj.created_at + timedelta(seconds=1)


class VerifiedUserFactory(UserFactory):
    """Фабрика для верифицированных пользователей."""

    is_verified = True
    verified_at = factory.LazyFunction(datetime.utcnow)


class AdminUserFactory(UserFactory):
    """Фабрика для администраторов."""

    is_superuser = True
    is_verified = True
    email = factory.Sequence(lambda n: f"admin{n}@example.com")
    username = factory.Sequence(lambda n: f"admin{n}")
    full_name = factory.Sequence(lambda n: f"Admin User {n}")


class InactiveUserFactory(UserFactory):
    """Фабрика для неактивных пользователей."""

    is_active = False


class RefreshTokenFactory(factory.Factory):
    """Фабрика для refresh токенов."""

    class Meta:
        model = RefreshToken

    token = Faker("uuid4")
    expires_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=30))
    is_revoked = False
    user = SubFactory(UserFactory)

    # Даты
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class ExpiredRefreshTokenFactory(RefreshTokenFactory):
    """Фабрика для просроченных токенов."""

    expires_at = factory.LazyFunction(lambda: datetime.utcnow() - timedelta(days=1))


class RevokedRefreshTokenFactory(RefreshTokenFactory):
    """Фабрика для отозванных токенов."""

    is_revoked = True


# Удобные функции для создания пользователей
def create_user(**kwargs) -> User:
    """Создает обычного пользователя."""
    return UserFactory(**kwargs)


def create_verified_user(**kwargs) -> User:
    """Создает верифицированного пользователя."""
    return VerifiedUserFactory(**kwargs)


def create_admin_user(**kwargs) -> User:
    """Создает администратора."""
    return AdminUserFactory(**kwargs)


def create_inactive_user(**kwargs) -> User:
    """Создает неактивного пользователя."""
    return InactiveUserFactory(**kwargs)


def create_user_with_token(**kwargs) -> tuple[User, RefreshToken]:
    """Создает пользователя с refresh токеном."""
    user = create_verified_user(**kwargs)
    token = RefreshTokenFactory(user=user)
    return user, token


def create_test_users(count: int = 5, **kwargs) -> list[User]:
    """Создает список тестовых пользователей."""
    return [create_user(**kwargs) for _ in range(count)]


def create_admin_and_users(admin_count: int = 1, user_count: int = 5) -> tuple[list[User], list[User]]:
    """Создает администраторов и обычных пользователей."""
    admins = [create_admin_user() for _ in range(admin_count)]
    users = [create_verified_user() for _ in range(user_count)]
    return admins, users
