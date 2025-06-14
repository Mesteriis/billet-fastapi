"""
Базовые модели для всех приложений.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from sqlalchemy import UUID, DateTime
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from tools.pydantic import BaseModel as SafeBaseModel


class BaseModel(DeclarativeBase):
    """Базовая модель SQLAlchemy для всех таблиц."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Автоматическое создание имени таблицы из имени класса."""
        return cls.__name__.lower() + "s"


class TimestampMixin:
    """Миксин для добавления временных меток."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Мягкое удаление
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    @property
    def is_deleted(self) -> bool:
        """Проверка на мягкое удаление."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Мягкое удаление записи."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Восстановление мягко удаленной записи."""
        self.deleted_at = None


class BaseEntity(BaseModel, TimestampMixin):
    """Базовая сущность с временными метками."""

    __abstract__ = True

    def to_dict(self) -> dict[str, Any]:
        """Преобразование модели в словарь."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def update(self, **kwargs) -> None:
        """Обновление полей модели."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


# Базовые Pydantic схемы для API с использованием SafeModel
class BaseSchema(SafeBaseModel):
    """Базовая Pydantic схема."""

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class TimestampSchema(BaseSchema):
    """Схема с временными метками."""

    id: Annotated[uuid.UUID, "Уникальный идентификатор"]
    created_at: Annotated[datetime, "Дата и время создания"]
    updated_at: Annotated[datetime, "Дата и время последнего обновления"]
    deleted_at: Annotated[datetime | None, "Дата и время мягкого удаления"] = None


class CreateSchema(BaseSchema):
    """Базовая схема для создания."""

    pass


class UpdateSchema(BaseSchema):
    """Базовая схема для обновления."""

    pass


# Вспомогательные типы для аннотаций
EmailStr = Annotated[str, "Email адрес"]
PasswordStr = Annotated[str, "Пароль"]
UsernameStr = Annotated[str, "Имя пользователя"]
PhoneStr = Annotated[str, "Номер телефона"]
TokenStr = Annotated[str, "JWT токен"]
