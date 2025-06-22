"""
User factories для тестов.

Используется структура: фабрика -> фикстура -> тест с create(args)
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

import bcrypt
import faker
from async_factory_boy.factory.sqlalchemy import AsyncSQLAlchemyFactory
from factory.declarations import LazyAttribute, LazyFunction, SubFactory
from factory.faker import Faker
from pytz import utc

# Импортируем нужные enum'ы
from apps.users.models.enums import UserRole, UserStatus

# Глобальный faker для избежания дублирования
fake = faker.Faker()

# Импорты моделей будут в фикстурах


class UserFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания пользователей."""

    class Meta:
        model = "apps.users.models.user_models.User"
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    # Базовые поля с уникальными значениями
    username = LazyFunction(lambda: f"user_{fake.uuid4()[:8]}")
    email = LazyFunction(lambda: fake.unique.email())
    first_name = Faker("first_name")
    last_name = Faker("last_name")

    # ИСПРАВЛЕНО: Используем настоящий bcrypt хеш вместо фейкового
    password_hash = LazyFunction(
        lambda: bcrypt.hashpw("test_password".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    )

    # Статусные поля
    is_active = True
    is_superuser = False
    is_verified = Faker("boolean", chance_of_getting_true=60)

    # Роль пользователя - используем правильные enum объекты
    role = LazyFunction(lambda: fake.random_element([UserRole.USER, UserRole.MODERATOR, UserRole.ADMIN]))

    # Статус пользователя - по умолчанию активный для прохождения can_login проверки
    status = UserStatus.ACTIVE

    # Дополнительные поля модели User
    avatar_url = LazyFunction(lambda: fake.image_url(width=200, height=200) if fake.boolean() else None)

    # Временные поля
    last_login_at = LazyFunction(lambda: fake.date_time_this_month(tzinfo=utc) if fake.boolean() else None)
    email_verified_at = LazyAttribute(lambda obj: datetime.now(tz=utc) if obj.is_verified else None)


class UserProfileFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания профилей пользователей."""

    class Meta:
        model = "apps.users.models.user_models.UserProfile"
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    # Контактная информация
    phone = LazyFunction(lambda: fake.phone_number()[:15])  # Ограничиваем длину
    website = Faker("url")

    # Адресная информация
    address = Faker("address")
    city = LazyFunction(lambda: fake.city()[:95])  # Ограничиваем длину
    country = LazyFunction(lambda: fake.country()[:95])
    postal_code = LazyFunction(lambda: fake.postcode()[:15])

    # Настройки
    timezone = Faker("timezone")
    language = LazyFunction(lambda: fake.language_code()[:8])

    # JSON настройки
    preferences = LazyFunction(
        lambda: {
            "theme": fake.random_element(["light", "dark", "auto"]),
            "notifications": fake.boolean(),
            "language": fake.language_code(),
            "email_frequency": fake.random_element(["daily", "weekly", "monthly", "never"]),
        }
    )

    # Связь с пользователем - будет установлена в тесте
    user = None


# Вспомогательные классы для тестовых данных
class TestDataBundle:
    """Связка тестовых данных для комплексных тестов."""

    def __init__(self, user: Any, profile: Any = None):
        self.user = user
        self.profile = profile

    @classmethod
    async def create_full_user(cls, user_factory, profile_factory, **user_kwargs) -> "TestDataBundle":
        """Создает пользователя с профилем."""
        user = await user_factory.create(**user_kwargs)
        profile = await profile_factory.create(user=user)
        return cls(user=user, profile=profile)

    @classmethod
    async def create_batch_users(cls, user_factory, count: int = 5, **user_kwargs) -> list[Any]:
        """Создает батч пользователей."""
        return await user_factory.create_batch(count, **user_kwargs)
