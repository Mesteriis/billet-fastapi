"""
Auth factories для тестов.

Используется структура: фабрика -> фикстура -> тест с create(args)
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

import faker
from async_factory_boy.factory.sqlalchemy import AsyncSQLAlchemyFactory
from factory.declarations import LazyAttribute, LazyFunction, SubFactory
from factory.faker import Faker
from pytz import utc

# Глобальный faker для избежания дублирования
fake = faker.Faker()

# Импорты моделей будут в фикстурах


class RefreshTokenFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания refresh токенов."""

    class Meta:
        model = "apps.auth.models.auth_models.RefreshToken"
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    # Основные поля токена
    token = LazyFunction(lambda: fake.uuid4())
    user_agent = Faker("user_agent")
    ip_address = Faker("ipv4")

    # Временные поля
    expires_at = LazyFunction(lambda: datetime.now(tz=utc) + timedelta(days=30))
    last_used_at = LazyFunction(lambda: fake.date_time_this_month(tzinfo=utc))

    # Статусные поля
    is_active = True
    is_revoked = False

    # Связь с пользователем - будет установлена в тесте
    user = None


class UserSessionFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания пользовательских сессий."""

    class Meta:
        model = "apps.auth.models.auth_models.UserSession"
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    # Идентификатор сессии
    session_id = LazyFunction(lambda: fake.uuid4())

    # Данные о клиенте
    user_agent = Faker("user_agent")
    ip_address = Faker("ipv4")
    device_type = LazyFunction(lambda: fake.random_element(["desktop", "mobile", "tablet"]))

    # Локация (опционально)
    location = LazyFunction(lambda: fake.city() if fake.boolean() else None)

    # Временные поля
    created_at = LazyFunction(lambda: fake.date_time_this_month(tzinfo=utc))
    last_activity_at = LazyFunction(lambda: fake.date_time_this_week(tzinfo=utc))
    expires_at = LazyFunction(lambda: datetime.now(tz=utc) + timedelta(hours=24))

    # Статусы
    is_active = True

    # Связь с пользователем - будет установлена в тесте
    user = None


class OrbitalTokenFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания orbital токенов."""

    class Meta:
        model = "apps.auth.models.auth_models.OrbitalToken"
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None

    # Токен данные
    token = LazyFunction(lambda: fake.uuid4())
    token_type = LazyFunction(
        lambda: fake.random_element(["email_verification", "password_reset", "two_factor", "login_confirmation"])
    )

    # Дополнительные данные
    payload = LazyFunction(
        lambda: {"action": fake.word(), "client_id": fake.uuid4(), "metadata": {"created_by": "test"}}
    )

    # Временные поля
    created_at = LazyFunction(lambda: fake.date_time_this_week(tzinfo=utc))
    expires_at = LazyFunction(lambda: datetime.now(tz=utc) + timedelta(hours=1))
    used_at = None

    # Статусы
    is_used = False
    is_revoked = False

    # Связь с пользователем - будет установлена в тесте
    user = None


# Вспомогательные классы для тестовых данных
class AuthTestBundle:
    """Связка данных авторизации для комплексных тестов."""

    def __init__(self, user: Any, refresh_token: Any = None, session: Any = None, orbital_token: Any = None):
        self.user = user
        self.refresh_token = refresh_token
        self.session = session
        self.orbital_token = orbital_token

    @classmethod
    async def create_full_auth_data(
        cls, user_factory, refresh_token_factory, session_factory, orbital_token_factory, **user_kwargs
    ) -> "AuthTestBundle":
        """Создает полный набор данных авторизации."""
        # Создаем пользователя
        user = await user_factory.create(**user_kwargs)

        # Создаем связанные объекты
        refresh_token = await refresh_token_factory.create(user=user)
        session = await session_factory.create(user=user)
        orbital_token = await orbital_token_factory.create(user=user, token_type="email_verification")

        return cls(user=user, refresh_token=refresh_token, session=session, orbital_token=orbital_token)

    @classmethod
    async def create_expired_tokens(
        cls, user_factory, refresh_token_factory, orbital_token_factory, **user_kwargs
    ) -> "AuthTestBundle":
        """Создает пользователя с истекшими токенами."""
        user = await user_factory.create(**user_kwargs)

        # Истекшие токены
        expired_refresh = await refresh_token_factory.create(
            user=user, expires_at=datetime.now(tz=utc) - timedelta(days=1), is_active=False
        )

        expired_orbital = await orbital_token_factory.create(
            user=user, expires_at=datetime.now(tz=utc) - timedelta(hours=1), token_type="password_reset"
        )

        return cls(user=user, refresh_token=expired_refresh, orbital_token=expired_orbital)
