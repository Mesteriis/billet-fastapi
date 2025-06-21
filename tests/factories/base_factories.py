"""
Base factories utilities для тестов.

Простые утилиты для работы с фабриками без сложной логики.
"""

import uuid
from typing import Any, Type

import faker
from async_factory_boy.factory.sqlalchemy import AsyncSQLAlchemyFactory

# Глобальный faker для всех фабрик
fake = faker.Faker()


class BaseTestFactory(AsyncSQLAlchemyFactory):
    """Базовая фабрика с общими настройками."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None


class TestDataGenerator:
    """Простой генератор тестовых данных."""

    @staticmethod
    def unique_email() -> str:
        """Генерирует уникальный email."""
        return fake.unique.email()

    @staticmethod
    def unique_username() -> str:
        """Генерирует уникальное имя пользователя."""
        return f"user_{fake.uuid4()[:8]}"

    @staticmethod
    def random_uuid() -> str:
        """Генерирует случайный UUID."""
        return str(uuid.uuid4())

    @staticmethod
    def random_phone() -> str:
        """Генерирует случайный телефон."""
        return fake.phone_number()[:15]  # Ограничиваем длину

    @staticmethod
    def random_text(max_chars: int = 200) -> str:
        """Генерирует случайный текст."""
        return fake.text(max_nb_chars=max_chars)


# Простая функция сброса для очистки между тестами
async def reset_factories():
    """Сбрасывает состояние фабрик между тестами."""
    # Сбрасываем уникальные значения faker
    fake.unique.clear()


# Утилиты для работы с фабриками
def setup_factory_session(factory_class: Type[AsyncSQLAlchemyFactory], session: Any) -> None:
    """Настраивает сессию для фабрики."""
    factory_class._meta.sqlalchemy_session = session  # type: ignore # noqa: SLF001


def setup_factory_model(factory_class: Type[AsyncSQLAlchemyFactory], model: Any) -> None:
    """Настраивает модель для фабрики."""
    factory_class._meta.model = model  # type: ignore # noqa: SLF001
