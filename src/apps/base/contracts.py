"""
Контракты и интерфейсы для изоляции слоев архитектуры.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from tools.pydantic import BaseModel

# Type variables для generic типов
T = TypeVar("T")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
EntityType = TypeVar("EntityType")


class IRepository(ABC, Generic[EntityType, CreateSchemaType, UpdateSchemaType]):
    """Интерфейс репозитория для работы с данными."""

    @abstractmethod
    async def get(self, db_session: Any, *, id: uuid.UUID) -> EntityType | None:
        """Получить объект по ID."""
        ...

    @abstractmethod
    async def get_multi(
        self, 
        db_session: Any, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: dict[str, Any] | None = None
    ) -> list[EntityType]:
        """Получить несколько объектов с фильтрацией."""
        ...

    @abstractmethod
    async def create(self, db_session: Any, *, obj_in: CreateSchemaType) -> EntityType:
        """Создать новый объект."""
        ...

    @abstractmethod
    async def update(
        self, 
        db_session: Any, 
        *, 
        db_obj: EntityType, 
        obj_in: UpdateSchemaType | dict[str, Any]
    ) -> EntityType:
        """Обновить существующий объект."""
        ...

    @abstractmethod
    async def delete(self, db_session: Any, *, id: uuid.UUID) -> EntityType | None:
        """Удалить объект."""
        ...


class IUserRepository(IRepository[Any, Any, Any]):
    """Интерфейс репозитория пользователей."""

    @abstractmethod
    async def get_by_email(self, db_session: Any, *, email: str) -> Any | None:
        """Получить пользователя по email."""
        ...

    @abstractmethod
    async def get_by_username(self, db_session: Any, *, username: str) -> Any | None:
        """Получить пользователя по username."""
        ...

    @abstractmethod
    async def is_active(self, user: Any) -> bool:
        """Проверить активность пользователя."""
        ...

    @abstractmethod
    async def is_superuser(self, user: Any) -> bool:
        """Проверить права суперпользователя."""
        ...

    @abstractmethod
    async def count(self, db_session: Any, *, filters: dict[str, Any] | None = None) -> int:
        """Подсчитать количество пользователей с фильтрами."""
        ...


class IPasswordService(ABC):
    """Интерфейс сервиса работы с паролями."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Хешировать пароль."""
        ...

    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверить пароль."""
        ...

    @abstractmethod
    def generate_password(self, length: int = 12) -> str:
        """Сгенерировать случайный пароль."""
        ...


class IJWTService(ABC):
    """Интерфейс сервиса работы с JWT токенами."""

    @abstractmethod
    async def create_access_token(self, data: dict[str, Any]) -> str:
        """Создать access токен."""
        ...

    @abstractmethod
    async def create_refresh_token(self, data: dict[str, Any]) -> str:
        """Создать refresh токен."""
        ...

    @abstractmethod
    async def verify_token(self, token: str) -> dict[str, Any] | None:
        """Проверить токен и получить данные."""
        ...

    @abstractmethod
    async def decode_token(self, token: str) -> dict[str, Any] | None:
        """Декодировать токен без проверки подписи."""
        ...


class IAuthService(ABC):
    """Интерфейс сервиса аутентификации."""

    @abstractmethod
    async def authenticate_user(self, db_session: Any, *, email: str, password: str) -> Any | None:
        """Аутентифицировать пользователя."""
        ...

    @abstractmethod
    async def register_user(self, db_session: Any, *, user_data: Any) -> Any:
        """Зарегистрировать нового пользователя."""
        ...

    @abstractmethod
    async def login(self, db_session: Any, *, email: str, password: str) -> Any:
        """Вход пользователя в систему."""
        ...

    @abstractmethod
    async def refresh_tokens(self, db_session: Any, *, refresh_token: str) -> Any:
        """Обновить токены."""
        ...

    @abstractmethod
    async def logout(self, db_session: Any, *, refresh_token: str) -> bool:
        """Выход из системы."""
        ...


class IUserService(ABC):
    """Интерфейс сервиса работы с пользователями."""

    @abstractmethod
    async def get_user(self, db_session: Any, *, user_id: uuid.UUID) -> Any | None:
        """Получить пользователя по ID."""
        ...

    @abstractmethod
    async def get_users(
        self, 
        db_session: Any, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> list[Any]:
        """Получить список пользователей."""
        ...

    @abstractmethod
    async def create_user(self, db_session: Any, *, user_data: Any) -> Any:
        """Создать пользователя."""
        ...

    @abstractmethod
    async def update_user(
        self, 
        db_session: Any, 
        *, 
        user_id: uuid.UUID, 
        user_data: Any
    ) -> Any | None:
        """Обновить пользователя."""
        ...

    @abstractmethod
    async def delete_user(self, db_session: Any, *, user_id: uuid.UUID) -> bool:
        """Удалить пользователя."""
        ...


class IEventPublisher(ABC):
    """Интерфейс для публикации событий."""

    @abstractmethod
    async def publish_event(self, event_name: str, event_data: dict[str, Any]) -> None:
        """Опубликовать событие."""
        ...


class INotificationService(ABC):
    """Интерфейс сервиса уведомлений."""

    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Отправить email."""
        ...

    @abstractmethod
    async def send_sms(self, to: str, message: str) -> bool:
        """Отправить SMS."""
        ...

    @abstractmethod
    async def send_push_notification(self, user_id: uuid.UUID, message: str) -> bool:
        """Отправить push-уведомление."""
        ...


# Базовые исключения
class DomainException(Exception):
    """Базовое исключение доменного слоя."""
    
    def __init__(self, message: str = "", code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ValidationException(DomainException):
    """Исключение валидации."""
    
    def __init__(self, message: str = "Validation error", field: str | None = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")


class NotFoundError(DomainException):
    """Исключение - ресурс не найден."""
    
    def __init__(self, resource: str = "Resource", resource_id: str | uuid.UUID | None = None):
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message, "NOT_FOUND")


class AlreadyExistsError(DomainException):
    """Исключение - ресурс уже существует."""
    
    def __init__(self, resource: str = "Resource", field: str | None = None, value: str | None = None):
        message = f"{resource} already exists"
        if field and value:
            message += f" ({field}: {value})"
        super().__init__(message, "ALREADY_EXISTS")


class UnauthorizedError(DomainException):
    """Исключение - неавторизованный доступ."""
    
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message, "UNAUTHORIZED")


class ForbiddenError(DomainException):
    """Исключение - запрещенный доступ."""
    
    def __init__(self, message: str = "Forbidden access"):
        super().__init__(message, "FORBIDDEN") 