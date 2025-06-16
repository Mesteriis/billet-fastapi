"""
Синхронные фабрики для генерации тестовых данных (не моделей БД).
Используются для создания словарей с данными для тестов.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

from faker import Faker


class BaseDataFactory:
    """Базовая фабрика для генерации тестовых данных."""

    def __init__(self, faker_instance: Faker | None = None):
        self.faker = faker_instance or Faker()

    def _generate_unique_email(self, prefix: str = "user") -> str:
        """Генерирует уникальный email."""
        unique_id = str(uuid.uuid4())[:8]
        domain = self.faker.domain_name()
        return f"{prefix}_{unique_id}@{domain}"

    def _generate_unique_username(self, prefix: str = "user") -> str:
        """Генерирует уникальное имя пользователя."""
        unique_id = str(uuid.uuid4())[:4]
        return f"{prefix}_{unique_id}"


class UserDataFactory(BaseDataFactory):
    """Фабрика для генерации данных пользователя."""

    def create(self, **kwargs) -> Dict[str, Any]:
        """Создает данные пользователя."""
        defaults = {
            "email": self._generate_unique_email(),
            "username": self._generate_unique_username(),
            "full_name": self.faker.name(),
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1yZDFgw8Hm",
            "is_active": self.faker.boolean(chance_of_getting_true=85),  # 85% активных
            "is_verified": self.faker.boolean(chance_of_getting_true=60),  # 60% верифицированных
            "is_superuser": self.faker.boolean(chance_of_getting_true=5),  # 5% суперпользователей
            "bio": self.faker.text(max_nb_chars=200),
        }
        defaults.update(kwargs)
        return defaults

    def create_batch(self, count: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Создает список данных пользователей."""
        return [self.create(**kwargs) for _ in range(count)]


class AdminUserDataFactory(BaseDataFactory):
    """Фабрика для генерации данных администратора."""

    def create(self, **kwargs) -> Dict[str, Any]:
        """Создает данные администратора."""
        defaults = {
            "email": self._generate_unique_email("admin"),
            "username": self._generate_unique_username("admin"),
            "full_name": self.faker.name(),
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1yZDFgw8Hm",
            "is_active": True,
            "is_verified": True,
            "is_superuser": True,
            "bio": self.faker.text(max_nb_chars=100),
        }
        defaults.update(kwargs)
        return defaults


class PredictableUserDataFactory(BaseDataFactory):
    """Фабрика для генерации предсказуемых данных пользователя."""

    def __init__(self, faker_instance: Faker | None = None):
        super().__init__(faker_instance)
        self._counter = 0

    def create(self, **kwargs) -> Dict[str, Any]:
        """Создает предсказуемые данные пользователя."""
        self._counter += 1
        defaults = {
            "email": f"predictable_user_{self._counter}@testdomain.com",
            "username": f"predictable_user_{self._counter}",
            "full_name": f"Predictable User {self._counter}",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1yZDFgw8Hm",
            "is_active": True,
            "is_verified": self._counter % 2 == 0,  # Четные верифицированы
            "is_superuser": False,
            "bio": f"Bio for Predictable User {self._counter}" if self._counter % 3 != 0 else None,
        }
        defaults.update(kwargs)
        return defaults

    def create_batch(self, count: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Создает список предсказуемых данных пользователей."""
        return [self.create(**kwargs) for _ in range(count)]


class ComplexFilterDataFactory(BaseDataFactory):
    """Фабрика для генерации данных для тестирования сложных фильтров."""

    def create_company_admin(self, **kwargs) -> Dict[str, Any]:
        """Создает данные администратора компании."""
        defaults = {
            "email": f"{self.faker.user_name()}_admin@company.com",
            "username": self._generate_unique_username("admin"),
            "full_name": self.faker.name(),
            "hashed_password": "hash",
            "is_active": True,
            "is_verified": True,
            "is_superuser": True,
            "bio": self.faker.text(max_nb_chars=100),
        }
        defaults.update(kwargs)
        return defaults

    def create_company_manager(self, **kwargs) -> Dict[str, Any]:
        """Создает данные менеджера компании."""
        defaults = {
            "email": f"{self.faker.user_name()}_manager@company.com",
            "username": self._generate_unique_username("manager"),
            "full_name": self.faker.name(),
            "hashed_password": "hash",
            "is_active": True,
            "is_verified": True,
            "is_superuser": False,
            "bio": self.faker.text(max_nb_chars=100),
        }
        defaults.update(kwargs)
        return defaults

    def create_external_user(self, **kwargs) -> Dict[str, Any]:
        """Создает данные внешнего пользователя."""
        defaults = {
            "email": f"{self.faker.user_name()}_external@{self.faker.domain_name()}",
            "username": self._generate_unique_username("external"),
            "full_name": self.faker.name(),
            "hashed_password": "hash",
            "is_active": True,
            "is_verified": False,
            "is_superuser": False,
            "bio": None,
        }
        defaults.update(kwargs)
        return defaults

    def create_inactive_company_user(self, **kwargs) -> Dict[str, Any]:
        """Создает данные неактивного пользователя компании."""
        defaults = {
            "email": f"{self.faker.user_name()}_inactive@company.com",
            "username": self._generate_unique_username("inactive"),
            "full_name": self.faker.name(),
            "hashed_password": "hash",
            "is_active": False,
            "is_verified": True,
            "is_superuser": False,
            "bio": self.faker.text(max_nb_chars=100),
        }
        defaults.update(kwargs)
        return defaults

    def create_set(self, **kwargs) -> List[Dict[str, Any]]:
        """Создает полный набор данных для сложных фильтров."""
        return [
            self.create_company_admin(**kwargs),
            self.create_company_manager(**kwargs),
            self.create_external_user(**kwargs),
            self.create_inactive_company_user(**kwargs),
        ]


class PaginationDataFactory(BaseDataFactory):
    """Фабрика для генерации данных для тестирования пагинации."""

    def __init__(self, faker_instance: Faker | None = None):
        super().__init__(faker_instance)
        self._counter = 0

    def create(self, **kwargs) -> Dict[str, Any]:
        """Создает данные для пагинации."""
        self._counter += 1
        domain = self.faker.domain_name()
        defaults = {
            "email": f"{self.faker.user_name()}_page_{self._counter}@{domain}",
            "username": f"{self.faker.user_name()}_page_{self._counter:02d}_{str(uuid.uuid4())[:4]}",
            "full_name": self.faker.name(),
            "hashed_password": "hash",
            "is_active": self.faker.boolean(chance_of_getting_true=95),  # 95% активных
            "is_verified": self._counter % 3 == 0,  # Каждый третий верифицирован
            "is_superuser": False,
            "bio": self.faker.text(max_nb_chars=120),
        }
        defaults.update(kwargs)
        return defaults

    def create_batch(self, count: int = 25, **kwargs) -> List[Dict[str, Any]]:
        """Создает список данных для пагинации."""
        return [self.create(**kwargs) for _ in range(count)]


class SpecializedDataFactory(BaseDataFactory):
    """Фабрика для специализированных тестовых сценариев."""

    def create_user_with_bio(self, **kwargs) -> Dict[str, Any]:
        """Создает пользователя с обязательной биографией."""
        defaults = {
            "email": self._generate_unique_email("with_bio"),
            "username": self._generate_unique_username("with_bio"),
            "full_name": self.faker.name(),
            "hashed_password": "hash",
            "is_active": True,
            "is_verified": False,
            "is_superuser": False,
            "bio": self.faker.text(max_nb_chars=100),
        }
        defaults.update(kwargs)
        return defaults

    def create_user_without_bio(self, **kwargs) -> Dict[str, Any]:
        """Создает пользователя без биографии."""
        defaults = {
            "email": self._generate_unique_email("without_bio"),
            "username": self._generate_unique_username("without_bio"),
            "full_name": self.faker.name(),
            "hashed_password": "hash",
            "is_active": True,
            "is_verified": False,
            "is_superuser": False,
            "bio": None,
        }
        defaults.update(kwargs)
        return defaults

    def create_comparison_test_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Создает данные для тестирования фильтров сравнения."""
        domain = self.faker.domain_name()
        return [
            {
                "email": f"{self.faker.user_name()}_1@{domain}",
                "username": f"{self.faker.user_name()}_1_{str(uuid.uuid4())[:4]}",
                "full_name": self.faker.name(),
                "hashed_password": "hash",
                "is_active": True,
                "is_verified": False,
                "is_superuser": False,
                **kwargs,
            },
            {
                "email": f"{self.faker.user_name()}_2@{domain}",
                "username": f"{self.faker.user_name()}_2_{str(uuid.uuid4())[:4]}",
                "full_name": self.faker.name(),
                "hashed_password": "hash",
                "is_active": True,
                "is_verified": False,
                "is_superuser": False,
                **kwargs,
            },
        ]

    def create_stress_test_data(self, count: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Создает данные для stress тестов."""
        domain = self.faker.domain_name()
        return [
            {
                "email": f"{self.faker.user_name()}_stress_{i}@{domain}",
                "username": f"{self.faker.user_name()}_stress_{i}_{str(uuid.uuid4())[:4]}",
                "full_name": self.faker.name(),
                "hashed_password": "hash",
                "is_active": True,
                "is_verified": i % 10 == 0,  # Каждый 10-й верифицирован
                "is_superuser": False,
                "bio": self.faker.text(max_nb_chars=80),
                **kwargs,
            }
            for i in range(1, count + 1)
        ]

    def create_concurrent_test_data(self, count: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Создает данные для тестирования конкурентных операций."""
        domain = self.faker.domain_name()
        return [
            {
                "email": f"{self.faker.user_name()}_concurrent_{i}@{domain}",
                "username": f"{self.faker.user_name()}_concurrent_{i}_{str(uuid.uuid4())[:4]}",
                "full_name": self.faker.name(),
                "hashed_password": "hash",
                "is_active": True,
                "is_verified": False,
                "is_superuser": False,
                **kwargs,
            }
            for i in range(count)
        ]

    def create_batch_test_data(self, count: int = 20, **kwargs) -> List[Dict[str, Any]]:
        """Создает данные для тестирования batch операций."""
        domain = self.faker.domain_name()
        return [
            {
                "email": f"{self.faker.user_name()}_batch_{i}@{domain}",
                "username": f"{self.faker.user_name()}_batch_{i}_{str(uuid.uuid4())[:4]}",
                "full_name": self.faker.name(),
                "hashed_password": "hash",
                "is_active": True,
                "is_verified": False,
                "is_superuser": False,
                **kwargs,
            }
            for i in range(1, count + 1)
        ]


class DataFactoryManager:
    """Менеджер для управления всеми фабриками данных."""

    def __init__(self, faker_instance: Faker | None = None):
        self.faker = faker_instance or Faker()

        # Инициализируем все фабрики
        self.user = UserDataFactory(self.faker)
        self.admin = AdminUserDataFactory(self.faker)
        self.predictable = PredictableUserDataFactory(self.faker)
        self.complex_filter = ComplexFilterDataFactory(self.faker)
        self.pagination = PaginationDataFactory(self.faker)
        self.specialized = SpecializedDataFactory(self.faker)
