from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import ConfigDict, Field, BaseModel as PydanticBaseModel
from pytz import utc
from sqlalchemy import UUID, DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from sqlalchemy.sql import func

if os.environ.get("DEBUG", "false").lower() == "true":
    from sqlalchemy import event
    from sqlalchemy.engine import Engine


    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        print(f"Executing SQL: {statement} with params: {parameters}")
        return statement, parameters


    from tools.pydantic import SafeModel as BaseModel  # noqa


class BaseModel(DeclarativeBase, AsyncAttrs):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    @hybrid_property
    def is_deleted(self) -> bool:
        """Проверка на мягкое удаление."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Мягкое удаление записи."""
        self.deleted_at = datetime.now(tz=utc)

    def restore(self) -> None:
        """Восстановление мягко удаленной записи."""
        self.deleted_at = None

    def to_dict(self) -> dict[str, Any]:
        """Преобразование модели в словарь."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def update(self, **kwargs) -> None:
        """Обновление полей модели."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class BaseSchema(PydanticBaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    id: Annotated[uuid.UUID, Field(default_factory=uuid.uuid4)]
    created_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(tz=utc))]
    updated_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(tz=utc))]
    deleted_at: Annotated[datetime | None, Field(default=None)]
    is_deleted: Annotated[bool, Field(default=False)]
