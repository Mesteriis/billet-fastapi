"""
EnterpriseMixin - корпоративные функции для репозиториев.
"""

from __future__ import annotations

import logging
from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.base.models import BaseModel as SQLAlchemyBaseModel
from core.exceptions import CoreRepositoryValueError
from tools.pydantic import BaseModel as PydanticBaseModel

from ..cache import CacheManager, cache_result
from ..query_builder import QueryBuilder

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=SQLAlchemyBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)


class EnterpriseMixin(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Корпоративный миксин для масштабируемых приложений.

    Предоставляет функциональность:
    - Кэширование с Redis/Memory
    - Bulk операции с батчингом
    - Статистика производительности
    - Мониторинг и метрики
    - Enterprise Security

    Включает методы:
    - bulk_create() - массовое создание с батчингом
    - bulk_update() - массовое обновление
    - bulk_delete() - массовое удаление
    - get_cache_stats() - статистика кэша
    - warm_cache() - прогрев кэша
    - invalidate_cache() - инвалидация кэша

    Требует наличие BaseCrudMixin для базовых операций.
    """

    # Эти атрибуты должны быть определены в BaseCrudMixin
    _model: type[ModelType]
    _db: AsyncSession
    _qb: QueryBuilder
    _cache_manager: CacheManager | None = None

    def __init__(self, model: type[ModelType], db: AsyncSession, cache_manager: CacheManager | None = None):
        """
        Initialize EnterpriseMixin.

        :param model: SQLAlchemy model class
        :param db: async SQLAlchemy session
        :param cache_manager: Cache manager for caching functionality
        """
        # Предполагаем что BaseCrudMixin уже инициализировал _model, _db, _qb
        if not hasattr(self, "_model"):
            self._model = model
        if not hasattr(self, "_db"):
            self._db = db
        if not hasattr(self, "_qb"):
            self._qb = QueryBuilder(model)

        self._cache_manager = cache_manager

    async def invalidate_cache(self, pattern: str = "*") -> None:
        """
        Инвалидировать кэш по паттерну.

        :param pattern: Паттерн для инвалидации кэша

        Example:
            ```python
            # Очистить весь кэш для модели
            await repository.invalidate_cache("*")

            # Очистить кэш для конкретного пользователя
            await repository.invalidate_cache(f"user_{user_id}_*")
            ```
        """
        if self._cache_manager:
            try:
                await self._cache_manager.clear_pattern(pattern)
                logger.debug(f"Cache invalidated for pattern: {pattern}")
            except Exception as e:
                logger.error(f"Error invalidating cache: {e}")

    @cache_result(ttl=300)
    async def get_cache_stats(self) -> dict[str, Any]:
        """
        Получить статистику кэша.

        :return: Статистика кэширования

        Example:
            ```python
            stats = await repository.get_cache_stats()
            print(f"Cache enabled: {stats['cache_enabled']}")
            print(f"Memory entries: {stats['memory']['active_entries']}")
            ```
        """
        if not self._cache_manager:
            return {"cache_enabled": False, "model": self._model.__name__, "message": "Cache manager not configured"}

        try:
            cache_stats = await self._cache_manager.get_stats()
            return {"cache_enabled": True, "model": self._model.__name__, **cache_stats}
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"cache_enabled": False, "model": self._model.__name__, "error": str(e)}

    async def warm_cache(self, popular_queries: list[dict[str, Any]] | None = None) -> None:
        """
        Прогреть кэш популярными запросами.

        :param popular_queries: Список популярных запросов для прогрева

        Example:
            ```python
            # Прогрев кэша популярными запросами
            popular_queries = [
                {"status": "active", "limit": 10},
                {"role": "admin"},
                {"created_at__gte": datetime(2023, 1, 1)}
            ]
            await repository.warm_cache(popular_queries)
            ```
        """
        if not self._cache_manager:
            logger.warning("Cache manager not configured, skipping cache warming")
            return

        if not popular_queries:
            # Дефолтные запросы для прогрева
            popular_queries = [
                {"limit": 10},  # Первые 10 записей
                {"limit": 20, "offset": 0},  # Первая страница
            ]

        try:
            for query_params in popular_queries:
                # Выполняем запрос для прогрева кэша
                try:
                    # Используем метод list который может быть кэширован
                    if hasattr(self, "list"):
                        await self.list(**query_params)  # type: ignore
                    logger.debug(f"Cache warmed for query: {query_params}")
                except Exception as e:
                    logger.warning(f"Failed to warm cache for query {query_params}: {e}")

        except Exception as e:
            logger.error(f"Error warming cache: {e}")

    async def bulk_create(
        self,
        data_list: list[CreateSchemaType | dict[str, Any]],
        *,
        batch_size: int = 1000,
    ) -> list[ModelType]:
        """
        Массовое создание объектов с батчингом.

        :param data_list: Список данных для создания
        :param batch_size: Размер батча для обработки
        :return: Список созданных объектов
        :raises CoreRepositoryValueError: При ошибке создания

        Example:
            ```python
            users_data = [
                {"name": "User1", "email": "user1@example.com"},
                {"name": "User2", "email": "user2@example.com"},
                # ... еще 1000 пользователей
            ]

            created_users = await repository.bulk_create(
                users_data,
                batch_size=500
            )
            print(f"Created {len(created_users)} users")
            ```
        """
        if not data_list:
            return []

        try:
            created_objects = []

            # Обрабатываем данные батчами
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i : i + batch_size]
                batch_objects = []

                for data in batch:
                    # Преобразуем данные в словарь
                    if isinstance(data, dict):
                        obj_in_data = data
                    else:
                        obj_in_data = data.model_dump(exclude_unset=True)

                    # Создаем объект
                    db_obj = self._model(**obj_in_data)
                    batch_objects.append(db_obj)

                # Добавляем весь батч в сессию
                self._db.add_all(batch_objects)
                await self._db.commit()

                # Обновляем объекты для получения ID
                for obj in batch_objects:
                    await self._db.refresh(obj)

                created_objects.extend(batch_objects)
                logger.debug(f"Created batch of {len(batch_objects)} {self._model.__name__} objects")

            # Инвалидируем кэш после массового создания
            if self._cache_manager:
                await self.invalidate_cache("*")

            logger.info(f"Bulk created {len(created_objects)} {self._model.__name__} objects")
            return created_objects

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error in bulk create for {self._model.__name__}: {e}")
            raise CoreRepositoryValueError(f"Failed to bulk create {self._model.__name__}") from e

    async def bulk_update(
        self,
        filters: dict[str, Any],
        update_data: dict[str, Any],
    ) -> int:
        """
        Массовое обновление объектов по фильтрам.

        :param filters: Фильтры для выбора объектов
        :param update_data: Данные для обновления
        :return: Количество обновленных записей
        :raises CoreRepositoryValueError: При ошибке обновления

        Example:
            ```python
            # Обновить статус всех неактивных пользователей
            updated_count = await repository.bulk_update(
                filters={"is_active": False},
                update_data={"status": "inactive", "updated_at": datetime.utcnow()}
            )
            print(f"Updated {updated_count} users")
            ```
        """
        try:
            # Строим запрос обновления
            query = update(self._model)

            # Применяем фильтры
            if filters:
                temp_query = self._qb.get_list_query()
                temp_query = self._qb.apply_filters(temp_query, filters, use_advanced_operators=True)
                if temp_query.whereclause is not None:
                    query = query.where(temp_query.whereclause)

            # Применяем данные для обновления
            query = query.values(**update_data)

            # Выполняем обновление
            result = await self._db.execute(query)
            await self._db.commit()

            affected_count = result.rowcount or 0

            # Инвалидируем кэш после массового обновления
            if self._cache_manager:
                await self.invalidate_cache("*")

            logger.info(f"Bulk updated {affected_count} {self._model.__name__} objects")
            return affected_count

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error in bulk update for {self._model.__name__}: {e}")
            raise CoreRepositoryValueError(f"Failed to bulk update {self._model.__name__}") from e

    async def bulk_delete(
        self,
        filters: dict[str, Any],
        *,
        soft_delete: bool = True,
    ) -> int:
        """
        Массовое удаление объектов по фильтрам.

        :param filters: Фильтры для выбора объектов
        :param soft_delete: Использовать soft delete (если поддерживается)
        :return: Количество удаленных записей
        :raises CoreRepositoryValueError: При ошибке удаления

        Example:
            ```python
            # Soft delete всех пользователей старше 90 дней
            deleted_count = await repository.bulk_delete(
                filters={"created_at__lt": cutoff_date},
                soft_delete=True
            )
            print(f"Deleted {deleted_count} old users")
            ```
        """
        try:
            if soft_delete and hasattr(self._model, "deleted_at"):
                # Soft delete через обновление
                from datetime import datetime

                return await self.bulk_update(filters=filters, update_data={"deleted_at": datetime.utcnow()})
            else:
                # Hard delete
                query = delete(self._model)

                # Применяем фильтры
                if filters:
                    temp_query = self._qb.get_list_query()
                    temp_query = self._qb.apply_filters(temp_query, filters, use_advanced_operators=True)
                    if temp_query.whereclause is not None:
                        query = query.where(temp_query.whereclause)

                # Выполняем удаление
                result = await self._db.execute(query)
                await self._db.commit()

                affected_count = result.rowcount or 0

                # Инвалидируем кэш после массового удаления
                if self._cache_manager:
                    await self.invalidate_cache("*")

                logger.info(f"Bulk deleted {affected_count} {self._model.__name__} objects")
                return affected_count

        except Exception as e:
            await self._db.rollback()
            logger.error(f"Error in bulk delete for {self._model.__name__}: {e}")
            raise CoreRepositoryValueError(f"Failed to bulk delete {self._model.__name__}") from e
