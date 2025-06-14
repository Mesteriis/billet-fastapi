"""
Фабрика для создания тестовых пользователей.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

import factory.fuzzy
from factory import LazyFunction, Sequence, SubFactory, post_generation
from factory.faker import Faker

from apps.auth.models import RefreshToken
from apps.users.models import User


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Фабрика для создания пользователей."""

    class Meta:
        model = User
        sqlalchemy_session = None  # Будет установлена в conftest.py
        sqlalchemy_session_persistence = "commit"

    @classmethod
    async def create(cls, **kwargs):
        """Async обертка для создания пользователя."""
        return await asyncio.get_event_loop().run_in_executor(None, lambda: super(UserFactory, cls).create(**kwargs))

    # Основные поля
    email = Faker("email")
    username = Faker("user_name")
    full_name = Faker("name")

    # Аутентификация (захардкодированный хеш для тестов)
    hashed_password = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1yZDFgw8Hm"  # "testpassword"

    # Профильные данные
    avatar_url = LazyFunction(lambda: f"https://example.com/avatars/{str(uuid.uuid4())}.jpg")
    bio = Faker("text", max_nb_chars=200)

    # Статусы
    is_active = True
    is_verified = False
    is_superuser = False

    # Даты (используем callable)
    created_at = LazyFunction(datetime.utcnow)
    updated_at = LazyFunction(datetime.utcnow)


class SimpleUserFactory(factory.Factory):
    """Простая фабрика для создания пользователей без SQLAlchemy."""

    class Meta:
        model = User

    # Основные поля
    email = Faker("email")
    username = Faker("user_name")
    full_name = Faker("name")

    # Аутентификация (захардкодированный хеш для тестов)
    hashed_password = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1yZDFgw8Hm"  # "testpassword"

    # Профильные данные
    avatar_url = LazyFunction(lambda: f"https://example.com/avatars/{str(uuid.uuid4())}.jpg")
    bio = Faker("text", max_nb_chars=200)

    # Статусы
    is_active = True
    is_verified = False
    is_superuser = False

    # Даты
    created_at = LazyFunction(datetime.utcnow)
    updated_at = LazyFunction(datetime.utcnow)


class VerifiedUserFactory(SimpleUserFactory):
    """Фабрика для верифицированных пользователей."""

    is_verified = True
    verified_at = LazyFunction(datetime.utcnow)


class AdminUserFactory(SimpleUserFactory):
    """Фабрика для администраторов."""

    is_superuser = True
    is_verified = True
    email = Sequence(lambda n: f"admin{n}@example.com")
    username = Sequence(lambda n: f"admin{n}")
    full_name = Sequence(lambda n: f"Admin User {n}")


class InactiveUserFactory(SimpleUserFactory):
    """Фабрика для неактивных пользователей."""

    is_active = False


class RefreshTokenFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Фабрика для refresh токенов."""

    class Meta:
        model = RefreshToken
        sqlalchemy_session = None  # Будет установлена в conftest.py
        sqlalchemy_session_persistence = "commit"

    token = Faker("uuid4")
    expires_at = LazyFunction(lambda: datetime.utcnow() + timedelta(days=30))
    is_revoked = False
    user = SubFactory(SimpleUserFactory)

    # Даты
    created_at = LazyFunction(datetime.utcnow)
    updated_at = LazyFunction(datetime.utcnow)


class ExpiredRefreshTokenFactory(RefreshTokenFactory):
    """Фабрика для просроченных токенов."""

    expires_at = LazyFunction(lambda: datetime.utcnow() - timedelta(days=1))


class RevokedRefreshTokenFactory(RefreshTokenFactory):
    """Фабрика для отозванных токенов."""

    is_revoked = True


# Удобные функции для создания пользователей
def create_user(**kwargs) -> User:
    """Создает обычного пользователя."""
    return SimpleUserFactory(**kwargs)


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


# Простые функции для создания тестовых данных без factory-boy
def make_user_data(**kwargs) -> dict[str, Any]:
    """Создает данные пользователя как словарь."""
    defaults = {
        "email": f"user{uuid.uuid4().hex[:8]}@example.com",
        "username": f"user{uuid.uuid4().hex[:8]}",
        "full_name": "Test User",
        "avatar_url": None,
        "bio": None,
        "is_active": True,
        "is_verified": False,
        "is_superuser": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return defaults


def make_admin_data(**kwargs) -> dict[str, Any]:
    """Создает данные администратора как словарь."""
    defaults = make_user_data()
    defaults.update(
        {
            "is_superuser": True,
            "is_verified": True,
            "email": f"admin{uuid.uuid4().hex[:8]}@example.com",
            "username": f"admin{uuid.uuid4().hex[:8]}",
            "full_name": "Admin User",
        }
    )
    defaults.update(kwargs)
    return defaults
