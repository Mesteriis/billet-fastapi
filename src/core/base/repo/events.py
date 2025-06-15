"""
Базовые события для системы.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar

from opentelemetry import trace
from pydantic import BaseModel, Field
from pytz import utc

# Получаем tracer для отслеживания событий
tracer = trace.get_tracer(__name__)

T = TypeVar("T")


class BaseEvent(BaseModel, ABC, Generic[T]):
    """Базовое событие системы."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda : datetime.now(tz=utc))
    event_type: str = Field(...)
    source: str = Field(default="system")
    version: str = Field(default="1.0")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @abstractmethod
    def get_entity_id(self) -> str:
        """Получить ID сущности, с которой связано событие."""
        pass

    @abstractmethod
    def get_payload(self) -> T:
        """Получить полезную нагрузку события."""
        pass

    def emit(self) -> None:
        """Отправить событие в систему."""
        with tracer.start_as_current_span(f"event.{self.event_type}") as span:
            span.set_attribute("event.id", self.id)
            span.set_attribute("event.type", self.event_type)
            span.set_attribute("event.entity_id", self.get_entity_id())
            span.set_attribute("event.source", self.source)

            # Здесь можно добавить логику отправки события в очередь/брокер
            # Пока просто логируем
            print(f"Event emitted: {self.event_type} for entity {self.get_entity_id()}")


class CreateEvent(BaseEvent[T]):
    """Событие создания сущности."""

    event_type: str = Field(default="entity.created", frozen=True)
    entity_data: T = Field(...)

    def get_entity_id(self) -> str:
        """Получить ID созданной сущности."""
        if hasattr(self.entity_data, "id"):
            return str(getattr(self.entity_data, "id"))
        return "unknown"

    def get_payload(self) -> T:
        """Получить данные созданной сущности."""
        return self.entity_data


class UpdateEvent(BaseEvent[T]):
    """Событие обновления сущности."""

    event_type: str = Field(default="entity.updated", frozen=True)
    entity_id: str = Field(...)
    old_data: T = Field(...)
    new_data: T = Field(...)
    changed_fields: list[str] = Field(default_factory=list)

    def get_entity_id(self) -> str:
        """Получить ID обновленной сущности."""
        return self.entity_id

    def get_payload(self) -> T:
        """Получить данные об обновлении."""
        return {"old_data": self.old_data, "new_data": self.new_data, "changed_fields": self.changed_fields}  # type: ignore[return-value]


class DeleteEvent(BaseEvent[T]):
    """Событие удаления сущности."""

    event_type: str = Field(default="entity.deleted", frozen=True)
    entity_id: str = Field(...)
    entity_data: T = Field(...)
    soft_delete: bool = Field(default=False)

    def get_entity_id(self) -> str:
        """Получить ID удаленной сущности."""
        return self.entity_id

    def get_payload(self) -> T:
        """Получить данные об удалении."""
        return {"entity_data": self.entity_data, "soft_delete": self.soft_delete}  # type: ignore[return-value]
