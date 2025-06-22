"""
EventMixin - система событий для репозиториев.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from core.base.models import BaseModel as SQLAlchemyBaseModel
from core.exceptions import CoreRepositoryValueError
from tools.pydantic import BaseModel as PydanticBaseModel

from ..events import CreateEvent, DeleteEvent, UpdateEvent
from ..query_builder import QueryBuilder

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=SQLAlchemyBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)


class EventMixin(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Миксин для интеграции системы событий в репозитории.

    Предоставляет функциональность:
    - Автоматические события для CRUD операций
    - Настраиваемые хуки событий
    - Контроль эмиссии событий через параметры
    - Интеграция с системой трейсинга

    Включает методы с поддержкой событий:
    - create_with_event() - создание с событием
    - update_with_event() - обновление с событием
    - remove_with_event() - удаление с событием
    - restore_with_event() - восстановление с событием
    - bulk_*_with_events() - массовые операции с событиями

    Требует наличие BaseCrudMixin для базовых операций.
    """

    # Эти атрибуты должны быть определены в BaseCrudMixin
    _model: type[ModelType]
    _db: AsyncSession
    _qb: QueryBuilder

    # Настройки событий
    _event_source: str = "repository"
    _event_version: str = "1.0"

    def _get_event_metadata(self) -> dict[str, Any]:
        """
        Получить метаданные для событий.

        :return: Словарь метаданных
        """
        return {
            "model": self._model.__name__,
            "repository": self.__class__.__name__,
            "source": self._event_source,
            "version": self._event_version,
        }

    def _should_emit_event(self, emit_event: bool) -> bool:
        """
        Определить, нужно ли эмитить событие.

        :param emit_event: Параметр из вызова метода
        :return: True если нужно эмитить событие
        """
        return emit_event

    async def _before_create_event(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Хук перед созданием объекта (для переопределения в наследниках).

        :param data: Данные для создания
        :return: Модифицированные данные
        """
        return data

    async def _after_create_event(self, db_obj: ModelType, data: dict[str, Any]) -> None:
        """
        Хук после создания объекта (для переопределения в наследниках).

        :param db_obj: Созданный объект
        :param data: Данные использованные для создания
        """
        pass

    async def _before_update_event(self, db_obj: ModelType, data: dict[str, Any]) -> dict[str, Any]:
        """
        Хук перед обновлением объекта.

        :param db_obj: Объект для обновления
        :param data: Данные для обновления
        :return: Модифицированные данные
        """
        return data

    async def _after_update_event(self, db_obj: ModelType, old_data: dict[str, Any], new_data: dict[str, Any]) -> None:
        """
        Хук после обновления объекта.

        :param db_obj: Обновленный объект
        :param old_data: Старые данные
        :param new_data: Новые данные
        """
        pass

    async def _before_delete_event(self, db_obj: ModelType) -> None:
        """
        Хук перед удалением объекта.

        :param db_obj: Объект для удаления
        """
        pass

    async def _after_delete_event(self, db_obj: ModelType, soft_delete: bool) -> None:
        """
        Хук после удаления объекта.

        :param db_obj: Удаленный объект
        :param soft_delete: Был ли использован soft delete
        """
        pass

    async def create_with_event(self, data: CreateSchemaType | dict[str, Any], *, emit_event: bool = True) -> ModelType:
        """
        Создать объект с событием.

        :param data: Данные для создания
        :param emit_event: Эмитить ли событие
        :return: Созданный объект
        :raises CoreRepositoryValueError: При ошибке создания

        Example:
            ```python
            # Создание с событием
            user = await repository.create_with_event({
                "name": "John",
                "email": "john@example.com"
            })

            # Создание без события
            user = await repository.create_with_event(
                user_data,
                emit_event=False
            )
            ```
        """
        try:
            # Преобразуем данные в словарь
            if isinstance(data, dict):
                obj_in_data = data
            else:
                obj_in_data = data.model_dump(exclude_unset=True)

            # Хук перед созданием
            obj_in_data = await self._before_create_event(obj_in_data)

            # Создаем объект (используем базовый метод)
            if hasattr(self, "create"):
                db_obj = await self.create(data)  # type: ignore
            else:
                # Fallback если BaseCrudMixin не используется
                db_obj = self._model(**obj_in_data)
                self._db.add(db_obj)
                await self._db.commit()
                await self._db.refresh(db_obj)

            # Хук после создания
            await self._after_create_event(db_obj, obj_in_data)

            # Эмитим событие
            if self._should_emit_event(emit_event):
                event = CreateEvent(
                    entity_data=db_obj,
                    source=self._event_source,
                    version=self._event_version,
                    metadata=self._get_event_metadata(),
                )
                event.emit()
                logger.debug(f"Emitted CreateEvent for {self._model.__name__} with ID: {db_obj.id}")

            return db_obj

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error creating {self._model.__name__} with event: {e}")
            raise CoreRepositoryValueError(f"Failed to create {self._model.__name__} with event") from e

    async def update_with_event(
        self, db_obj: ModelType, data: UpdateSchemaType | dict[str, Any], *, emit_event: bool = True
    ) -> ModelType:
        """
        Обновить объект с событием.

        :param db_obj: Объект для обновления
        :param data: Новые данные
        :param emit_event: Эмитить ли событие
        :return: Обновленный объект
        :raises CoreRepositoryValueError: При ошибке обновления

        Example:
            ```python
            user = await repository.get(user_id)
            if user:
                updated_user = await repository.update_with_event(
                    user,
                    {"name": "Jane", "status": "active"}
                )
            ```
        """
        try:
            # Сохраняем старые данные для события
            from .base_crud import model_to_dict

            old_data = model_to_dict(db_obj)

            # Преобразуем данные в словарь
            if isinstance(data, dict):
                update_data = data
            else:
                update_data = data.model_dump(exclude_unset=True)

            # Хук перед обновлением
            update_data = await self._before_update_event(db_obj, update_data)

            # Обновляем объект (используем базовый метод)
            if hasattr(self, "update"):
                db_obj = await self.update(db_obj, update_data)  # type: ignore
            else:
                # Fallback если BaseCrudMixin не используется
                for field, value in update_data.items():
                    if hasattr(db_obj, field):
                        setattr(db_obj, field, value)
                await self._db.commit()
                await self._db.refresh(db_obj)

            # Получаем новые данные
            new_data = model_to_dict(db_obj)

            # Хук после обновления
            await self._after_update_event(db_obj, old_data, new_data)

            # Определяем измененные поля
            changed_fields = [field for field in update_data.keys() if old_data.get(field) != new_data.get(field)]

            # Эмитим событие
            if self._should_emit_event(emit_event) and changed_fields:
                event = UpdateEvent(
                    entity_id=str(db_obj.id),
                    old_data=old_data,
                    new_data=new_data,
                    changed_fields=changed_fields,
                    source=self._event_source,
                    version=self._event_version,
                    metadata=self._get_event_metadata(),
                )
                event.emit()
                logger.debug(f"Emitted UpdateEvent for {self._model.__name__} with ID: {db_obj.id}")

            return db_obj

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error updating {self._model.__name__} with event: {e}")
            raise CoreRepositoryValueError(f"Failed to update {self._model.__name__} with event") from e

    async def remove_with_event(
        self, id: uuid.UUID, *, soft_delete: bool = True, emit_event: bool = True
    ) -> ModelType | None:
        """
        Удалить объект с событием.

        :param id: UUID объекта для удаления
        :param soft_delete: Использовать soft delete
        :param emit_event: Эмитить ли событие
        :return: Удаленный объект или None если не найден
        :raises CoreRepositoryValueError: При ошибке удаления

        Example:
            ```python
            deleted_user = await repository.remove_with_event(
                user_id,
                soft_delete=True,
                emit_event=True
            )
            ```
        """
        try:
            # Получаем объект перед удалением
            if hasattr(self, "get"):
                db_obj = await self.get(id)  # type: ignore
            else:
                query = self._qb.get_object_query(id)
                result = await self._db.execute(query)
                db_obj = result.scalar_one_or_none()

            if not db_obj:
                return None

            # Сохраняем данные для события
            from .base_crud import model_to_dict

            entity_data = model_to_dict(db_obj)

            # Хук перед удалением
            await self._before_delete_event(db_obj)

            # Удаляем объект (используем базовый метод)
            if hasattr(self, "remove"):
                db_obj = await self.remove(id, soft_delete=soft_delete)  # type: ignore
            else:
                # Fallback если BaseCrudMixin не используется
                if soft_delete and hasattr(db_obj, "deleted_at"):
                    from datetime import datetime

                    db_obj.deleted_at = datetime.utcnow()
                    await self._db.commit()
                    await self._db.refresh(db_obj)
                else:
                    await self._db.delete(db_obj)
                    await self._db.commit()

            # Хук после удаления
            await self._after_delete_event(db_obj, soft_delete)

            # Эмитим событие
            if self._should_emit_event(emit_event):
                event = DeleteEvent(
                    entity_id=str(id),
                    entity_data=entity_data,
                    soft_delete=soft_delete,
                    source=self._event_source,
                    version=self._event_version,
                    metadata=self._get_event_metadata(),
                )
                event.emit()
                logger.debug(f"Emitted DeleteEvent for {self._model.__name__} with ID: {id}")

            return db_obj

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error removing {self._model.__name__} with event: {e}")
            raise CoreRepositoryValueError(f"Failed to remove {self._model.__name__} with event") from e

    async def restore_with_event(self, id: uuid.UUID, *, emit_event: bool = True) -> ModelType | None:
        """
        Восстановить soft-deleted объект с событием.

        :param id: UUID объекта для восстановления
        :param emit_event: Эмитить ли событие
        :return: Восстановленный объект или None если не найден
        :raises CoreRepositoryValueError: При ошибке восстановления

        Example:
            ```python
            restored_user = await repository.restore_with_event(user_id)
            ```
        """
        try:
            # Восстанавливаем объект (используем базовый метод)
            if hasattr(self, "restore"):
                db_obj = await self.restore(id)  # type: ignore
            else:
                # Fallback если BaseCrudMixin не используется
                db_obj = await self.get(id, include_deleted=True)  # type: ignore
                if db_obj and hasattr(db_obj, "deleted_at"):
                    db_obj.deleted_at = None
                    await self._db.commit()
                    await self._db.refresh(db_obj)

            if not db_obj:
                return None

            # Эмитим событие восстановления (как создание)
            if self._should_emit_event(emit_event):
                event = CreateEvent(
                    entity_data=db_obj,
                    source=self._event_source,
                    version=self._event_version,
                    metadata={**self._get_event_metadata(), "restored": True, "original_event_type": "restore"},
                )
                event.emit()
                logger.debug(f"Emitted RestoreEvent for {self._model.__name__} with ID: {id}")

            return db_obj

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error restoring {self._model.__name__} with event: {e}")
            raise CoreRepositoryValueError(f"Failed to restore {self._model.__name__} with event") from e

    async def bulk_create_with_events(
        self,
        data_list: list[CreateSchemaType | dict[str, Any]],
        *,
        emit_events: bool = True,
    ) -> list[ModelType]:
        """
        Массовое создание с событиями.

        :param data_list: Список данных для создания
        :param emit_events: Эмитить ли события
        :return: Список созданных объектов

        Example:
            ```python
            users_data = [
                {"name": "User1", "email": "user1@example.com"},
                {"name": "User2", "email": "user2@example.com"},
            ]

            created_users = await repository.bulk_create_with_events(
                users_data,
                emit_events=True
            )
            ```
        """
        if not data_list:
            return []

        # Используем базовый метод bulk_create если доступен
        if hasattr(self, "bulk_create"):
            created_objects = await self.bulk_create(data_list)  # type: ignore
        else:
            # Fallback - создаем по одному
            created_objects = []
            for data in data_list:
                obj = await self.create_with_event(data, emit_event=emit_events)
                created_objects.append(obj)
            return created_objects

        # Эмитим события для всех созданных объектов
        if self._should_emit_event(emit_events):
            for db_obj in created_objects:
                event = CreateEvent(
                    entity_data=db_obj,
                    source=self._event_source,
                    version=self._event_version,
                    metadata={**self._get_event_metadata(), "bulk_operation": True, "batch_size": len(created_objects)},
                )
                event.emit()

            logger.info(f"Emitted {len(created_objects)} CreateEvents for bulk operation")

        return created_objects
