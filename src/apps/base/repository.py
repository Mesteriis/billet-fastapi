"""
Базовый репозиторий для всех приложений.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from opentelemetry import trace
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .events import CreateEvent, DeleteEvent, UpdateEvent
from .models import BaseEntity

tracer = trace.get_tracer(__name__)

ModelType = TypeVar("ModelType", bound=BaseEntity)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Базовый репозиторий с CRUD операциями."""

    def __init__(self, model: type[ModelType]):
        """Инициализация репозитория.

        Args:
            model: SQLAlchemy модель
        """
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID, include_deleted: bool = False) -> ModelType | None:
        """Получить объект по ID.

        Args:
            db: Сессия базы данных
            id: Идентификатор объекта
            include_deleted: Включать мягко удаленные записи

        Returns:
            Объект модели или None
        """
        with tracer.start_as_current_span("repository.get") as span:
            span.set_attribute("model.name", self.model.__name__)
            span.set_attribute("entity.id", str(id))
            span.set_attribute("include_deleted", include_deleted)

            query = select(self.model).where(self.model.id == id)

            if not include_deleted:
                query = query.where(self.model.deleted_at.is_(None))

            result = await db.execute(query)
            entity = result.scalar_one_or_none()

            span.set_attribute("entity.found", entity is not None)
            return entity

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        order_by: str = "created_at",
        **filters,
    ) -> Sequence[ModelType]:
        """Получить множество объектов.

        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            include_deleted: Включать мягко удаленные записи
            order_by: Поле для сортировки
            **filters: Дополнительные фильтры

        Returns:
            Список объектов модели
        """
        with tracer.start_as_current_span("repository.get_multi") as span:
            span.set_attribute("model.name", self.model.__name__)
            span.set_attribute("skip", skip)
            span.set_attribute("limit", limit)
            span.set_attribute("include_deleted", include_deleted)

            query = select(self.model)

            if not include_deleted:
                query = query.where(self.model.deleted_at.is_(None))

            # Применяем фильтры
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

            # Сортировка
            if hasattr(self.model, order_by):
                query = query.order_by(getattr(self.model, order_by))

            query = query.offset(skip).limit(limit)

            result = await db.execute(query)
            entities = result.scalars().all()

            span.set_attribute("entities.count", len(entities))
            return entities

    async def count(self, db: AsyncSession, include_deleted: bool = False, **filters) -> int:
        """Подсчитать количество записей.

        Args:
            db: Сессия базы данных
            include_deleted: Включать мягко удаленные записи
            **filters: Дополнительные фильтры

        Returns:
            Количество записей
        """
        with tracer.start_as_current_span("repository.count") as span:
            span.set_attribute("model.name", self.model.__name__)
            span.set_attribute("include_deleted", include_deleted)

            query = select(func.count(self.model.id))

            if not include_deleted:
                query = query.where(self.model.deleted_at.is_(None))

            # Применяем фильтры
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

            result = await db.execute(query)
            count = result.scalar() or 0

            span.set_attribute("entities.count", count)
            return count

    async def create(
        self, db: AsyncSession, *, obj_in: CreateSchemaType | dict[str, Any], emit_event: bool = True
    ) -> ModelType:
        """Создать новый объект.

        Args:
            db: Сессия базы данных
            obj_in: Данные для создания объекта
            emit_event: Отправлять событие создания

        Returns:
            Созданный объект
        """
        with tracer.start_as_current_span("repository.create") as span:
            span.set_attribute("model.name", self.model.__name__)

            if isinstance(obj_in, dict):
                obj_data = obj_in
            else:
                # Поддержка и Pydantic v1 и v2
                if hasattr(obj_in, "model_dump"):
                    obj_data = getattr(obj_in, "model_dump")()
                elif hasattr(obj_in, "dict"):
                    obj_data = getattr(obj_in, "dict")()
                else:
                    obj_data = dict(obj_in)

            db_obj = self.model(**obj_data)
            db.add(db_obj)
            await db.flush()
            await db.refresh(db_obj)

            span.set_attribute("entity.id", str(db_obj.id))

            # Отправляем событие создания
            if emit_event:
                event = CreateEvent(entity_data=db_obj)
                event.emit()

            return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any], emit_event: bool = True
    ) -> ModelType:
        """Обновить объект.

        Args:
            db: Сессия базы данных
            db_obj: Существующий объект
            obj_in: Новые данные
            emit_event: Отправлять событие обновления

        Returns:
            Обновленный объект
        """
        with tracer.start_as_current_span("repository.update") as span:
            span.set_attribute("model.name", self.model.__name__)
            span.set_attribute("entity.id", str(db_obj.id))

            # Сохраняем старые данные для события
            old_data = db_obj.to_dict() if emit_event else None

            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True)

            # Отслеживаем измененные поля
            changed_fields = []
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    old_value = getattr(db_obj, field)
                    if old_value != value:
                        changed_fields.append(field)
                        setattr(db_obj, field, value)

            await db.flush()
            await db.refresh(db_obj)

            span.set_attribute("changed_fields.count", len(changed_fields))

            # Отправляем событие обновления
            if emit_event and changed_fields:
                event = UpdateEvent(
                    entity_id=str(db_obj.id),
                    old_data=old_data,
                    new_data=db_obj.to_dict(),
                    changed_fields=changed_fields,
                )
                event.emit()

            return db_obj

    async def remove(
        self, db: AsyncSession, *, id: uuid.UUID, soft_delete: bool = True, emit_event: bool = True
    ) -> ModelType | None:
        """Удалить объект.

        Args:
            db: Сессия базы данных
            id: Идентификатор объекта
            soft_delete: Использовать мягкое удаление
            emit_event: Отправлять событие удаления

        Returns:
            Удаленный объект или None
        """
        with tracer.start_as_current_span("repository.remove") as span:
            span.set_attribute("model.name", self.model.__name__)
            span.set_attribute("entity.id", str(id))
            span.set_attribute("soft_delete", soft_delete)

            db_obj = await self.get(db, id=id)
            if not db_obj:
                return None

            # Сохраняем данные объекта для события
            entity_data = db_obj.to_dict() if emit_event else None

            if soft_delete:
                db_obj.soft_delete()
                await db.flush()
                await db.refresh(db_obj)
            else:
                await db.delete(db_obj)

            # Отправляем событие удаления
            if emit_event:
                event = DeleteEvent(entity_id=str(id), entity_data=entity_data, soft_delete=soft_delete)
                event.emit()

            return db_obj

    async def restore(self, db: AsyncSession, *, id: uuid.UUID, emit_event: bool = True) -> ModelType | None:
        """Восстановить мягко удаленный объект.

        Args:
            db: Сессия базы данных
            id: Идентификатор объекта
            emit_event: Отправлять событие восстановления

        Returns:
            Восстановленный объект или None
        """
        with tracer.start_as_current_span("repository.restore") as span:
            span.set_attribute("model.name", self.model.__name__)
            span.set_attribute("entity.id", str(id))

            db_obj = await self.get(db, id=id, include_deleted=True)
            if not db_obj or not db_obj.is_deleted:
                return None

            db_obj.restore()
            await db.flush()
            await db.refresh(db_obj)

            # Отправляем событие создания (как восстановление)
            if emit_event:
                event = CreateEvent(entity_data=db_obj)
                event.metadata["restored"] = True
                event.emit()

            return db_obj
