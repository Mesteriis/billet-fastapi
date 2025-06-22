"""
BaseCrudMixin - базовые CRUD операции для репозиториев.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base.models import BaseModel as SQLAlchemyBaseModel
from core.exceptions import CoreRepositoryValueError
from tools.pydantic import BaseModel as PydanticBaseModel

from ..query_builder import QueryBuilder

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=SQLAlchemyBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)


def model_to_dict(obj: Any) -> dict[str, Any]:
    """
    Convert SQLAlchemy model instance into a dictionary.
    Only includes direct column attributes.

    :param obj: SQLAlchemy model instance
    :return: Dictionary representation of the model
    """
    from sqlalchemy.inspection import inspect

    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


class BaseCrudMixin(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Базовый миксин для CRUD операций с SQLAlchemy моделями.

    Предоставляет основные операции:
    - Создание, чтение, обновление, удаление объектов
    - Простые фильтры (только базовые операторы)
    - Простая пагинация с offset/limit
    - Подсчет записей
    - Проверка существования

    Поддерживает только базовые операторы фильтрации:
    - eq, ne, lt, lte, gt, gte (сравнение)
    - isnull, isnotnull (проверка NULL)

    :param model: SQLAlchemy модель класса (например, User)
    :param db: async SQLAlchemy сессия
    """

    _model: type[ModelType]
    _db: AsyncSession
    _qb: QueryBuilder

    def __init__(self, model: type[ModelType], db: AsyncSession):
        """
        Initialize BaseCrudMixin.

        :param model: SQLAlchemy model class
        :param db: async SQLAlchemy session
        """
        self._model = model
        self._db = db
        self._qb = QueryBuilder(model)

    async def create(self, data: CreateSchemaType | dict[str, Any]) -> ModelType:
        """
        Создать новый объект в базе данных.

        :param data: Данные для создания (Pydantic схема или словарь)
        :return: Созданный объект
        :raises CoreRepositoryValueError: При ошибке создания

        Example:
            ```python
            user = await repository.create({"name": "John", "email": "john@example.com"})
            ```
        """
        try:
            # Преобразуем данные в словарь
            if isinstance(data, dict):
                obj_in_data = data
            else:
                obj_in_data = data.model_dump(exclude_unset=True)

            # Создаем объект
            db_obj = self._model(**obj_in_data)
            self._db.add(db_obj)
            await self._db.commit()
            await self._db.refresh(db_obj)

            logger.debug(f"Created {self._model.__name__} with ID: {db_obj.id}")
            return db_obj

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error creating {self._model.__name__}: {e}")
            raise CoreRepositoryValueError(f"Failed to create {self._model.__name__}") from e

    async def get(self, id: uuid.UUID, include_deleted: bool = False) -> ModelType | None:
        """
        Получить объект по ID.

        :param id: UUID объекта
        :param include_deleted: Включать ли soft-deleted объекты
        :return: Найденный объект или None

        Example:
            ```python
            user = await repository.get(user_id)
            if user:
                print(f"Found user: {user.name}")
            ```
        """
        try:
            query = self._qb.get_object_query(id, include_deleted)
            result = await self._db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting {self._model.__name__} with ID {id}: {e}")
            return None

    async def get_by(self, **filters) -> ModelType | None:
        """
        Получить объект по фильтрам (возвращает первый найденный).

        Поддерживает только базовые операторы фильтрации:
        - eq (по умолчанию): field="value"
        - ne: field__ne="value"
        - lt, lte, gt, gte: field__gt=10
        - isnull, isnotnull: field__isnull=True

        :param filters: Фильтры для поиска
        :return: Найденный объект или None

        Example:
            ```python
            user = await repository.get_by(email="john@example.com")
            active_user = await repository.get_by(status="active", deleted_at__isnull=True)
            ```
        """
        try:
            query = self._qb.get_list_query(filters.get("include_deleted", False))
            query = self._qb.apply_filters(query, filters, use_advanced_operators=False)

            result = await self._db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting {self._model.__name__} with filters {filters}: {e}")
            return None

    async def list(
        self,
        *,
        offset: int | None = None,
        limit: int | None = None,
        include_deleted: bool = False,
        order_by: str = "created_at",
        **filters,
    ) -> Sequence[ModelType]:
        """
        Получить список объектов с фильтрацией и пагинацией.

        Поддерживает только базовые операторы фильтрации.

        :param offset: Смещение для пагинации
        :param limit: Лимит записей
        :param include_deleted: Включать ли soft-deleted объекты
        :param order_by: Поле для сортировки (по умолчанию "created_at")
        :param filters: Фильтры для поиска
        :return: Список объектов

        Example:
            ```python
            # Получить активных пользователей
            users = await repository.list(
                status="active",
                deleted_at__isnull=True,
                limit=10,
                offset=0
            )
            ```
        """
        try:
            query = self._qb.get_list_query(include_deleted)
            query = self._qb.apply_filters(query, filters, use_advanced_operators=False)

            # Применяем сортировку
            if hasattr(self._model, order_by):
                order_field = getattr(self._model, order_by)
                query = query.order_by(desc(order_field))

            # Применяем пагинацию
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            result = await self._db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error listing {self._model.__name__}: {e}")
            return []

    async def count(self, *, include_deleted: bool = False, **filters) -> int:
        """
        Подсчитать количество записей с фильтрами.

        :param include_deleted: Включать ли soft-deleted объекты
        :param filters: Фильтры для подсчета
        :return: Количество записей

        Example:
            ```python
            total_users = await repository.count()
            active_users = await repository.count(status="active")
            ```
        """
        try:
            query = select(func.count(self._model.id))

            # Применяем фильтр deleted_at если модель поддерживает soft delete
            if not include_deleted and hasattr(self._model, "deleted_at"):
                query = query.where(self._model.deleted_at.is_(None))

            # Применяем остальные фильтры
            if filters:
                temp_query = self._qb.get_list_query(include_deleted)
                temp_query = self._qb.apply_filters(temp_query, filters, use_advanced_operators=False)
                if temp_query.whereclause is not None:
                    query = query.where(temp_query.whereclause)

            result = await self._db.execute(query)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting {self._model.__name__}: {e}")
            return 0

    async def exists(self, **filters) -> bool:
        """
        Проверить существование объекта с заданными фильтрами.

        :param filters: Фильтры для проверки
        :return: True если объект существует, False иначе

        Example:
            ```python
            if await repository.exists(email="john@example.com"):
                print("User with this email already exists")
            ```
        """
        return await self.count(**filters) > 0

    async def update(self, db_obj: ModelType, data: UpdateSchemaType | dict[str, Any]) -> ModelType:
        """
        Обновить существующий объект.

        :param db_obj: Объект для обновления
        :param data: Новые данные (Pydantic схема или словарь)
        :return: Обновленный объект
        :raises CoreRepositoryValueError: При ошибке обновления

        Example:
            ```python
            user = await repository.get(user_id)
            if user:
                updated_user = await repository.update(user, {"name": "Jane"})
            ```
        """
        try:
            # Преобразуем данные в словарь
            if isinstance(data, dict):
                update_data = data
            else:
                update_data = data.model_dump(exclude_unset=True)

            # Обновляем поля объекта
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Сохраняем изменения
            await self._db.commit()
            await self._db.refresh(db_obj)

            logger.debug(f"Updated {self._model.__name__} with ID: {db_obj.id}")
            return db_obj

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error updating {self._model.__name__}: {e}")
            raise CoreRepositoryValueError(f"Failed to update {self._model.__name__}") from e

    async def remove(self, id: uuid.UUID, *, soft_delete: bool = True) -> ModelType | None:
        """
        Удалить объект по ID.

        :param id: UUID объекта для удаления
        :param soft_delete: Использовать soft delete (если поддерживается моделью)
        :return: Удаленный объект или None если не найден
        :raises CoreRepositoryValueError: При ошибке удаления

        Example:
            ```python
            deleted_user = await repository.remove(user_id, soft_delete=True)
            if deleted_user:
                print(f"User {deleted_user.name} was deleted")
            ```
        """
        try:
            db_obj = await self.get(id)
            if not db_obj:
                return None

            if soft_delete and hasattr(db_obj, "deleted_at"):
                # Soft delete - устанавливаем deleted_at
                from datetime import datetime

                db_obj.deleted_at = datetime.utcnow()
                await self._db.commit()
                await self._db.refresh(db_obj)
                logger.debug(f"Soft deleted {self._model.__name__} with ID: {id}")
            else:
                # Hard delete - физическое удаление
                await self._db.delete(db_obj)
                await self._db.commit()
                logger.debug(f"Hard deleted {self._model.__name__} with ID: {id}")

            return db_obj

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error removing {self._model.__name__} with ID {id}: {e}")
            raise CoreRepositoryValueError(f"Failed to remove {self._model.__name__}") from e

    async def restore(self, id: uuid.UUID) -> ModelType | None:
        """
        Восстановить soft-deleted объект.

        :param id: UUID объекта для восстановления
        :return: Восстановленный объект или None если не найден
        :raises CoreRepositoryValueError: При ошибке восстановления

        Example:
            ```python
            restored_user = await repository.restore(user_id)
            if restored_user:
                print(f"User {restored_user.name} was restored")
            ```
        """
        try:
            # Ищем включая удаленные
            db_obj = await self.get(id, include_deleted=True)
            if not db_obj:
                return None

            if hasattr(db_obj, "deleted_at"):
                db_obj.deleted_at = None
                await self._db.commit()
                await self._db.refresh(db_obj)
                logger.debug(f"Restored {self._model.__name__} with ID: {id}")
                return db_obj
            else:
                logger.warning(f"Model {self._model.__name__} does not support soft delete")
                return db_obj

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error restoring {self._model.__name__} with ID {id}: {e}")
            raise CoreRepositoryValueError(f"Failed to restore {self._model.__name__}") from e
