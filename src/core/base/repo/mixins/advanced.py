"""
AdvancedMixin - продвинутые возможности для репозиториев.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from typing import Any, Generic, Literal, TypeVar

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base.models import BaseModel as SQLAlchemyBaseModel
from core.exceptions import CoreRepositoryValueError
from tools.pydantic import BaseModel as PydanticBaseModel

from ..query_builder import QueryBuilder
from ..types import AggregationResult, CursorPaginationResult

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=SQLAlchemyBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)


class AdvancedMixin(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Продвинутый миксин для расширенных возможностей репозитория.

    Предоставляет функциональность:
    - Расширенная фильтрация (40+ операторов)
    - Полнотекстовый поиск PostgreSQL
    - Курсорная пагинация для больших данных
    - Сложные фильтры (AND/OR/NOT)
    - Агрегации (SUM, AVG, MAX, MIN, COUNT, GROUP BY)
    - JOIN операции через фильтры

    Поддерживает все операторы фильтрации:
    - Базовые: eq, ne, lt, lte, gt, gte
    - Строковые: like, ilike, startswith, endswith, contains, regex
    - Коллекции: in, not_in, between, not_between
    - Даты: date, year, month, day, week, quarter, hour, minute, second
    - JSON: json_contains, json_has_key, json_extract
    - Полнотекстовый поиск: search, search_phrase, search_websearch
    - NULL: isnull, isnotnull

    Требует наличие BaseCrudMixin для базовых операций.
    """

    # Эти атрибуты должны быть определены в BaseCrudMixin
    _model: type[ModelType]
    _db: AsyncSession
    _qb: QueryBuilder

    async def fulltext_search(
        self,
        search_fields: list[str],
        query_text: str,
        *,
        search_type: Literal["simple", "phrase", "websearch", "raw"] = "simple",
        language: str = "russian",
        min_rank: float = 0.0,
        limit: int = 100,
        include_rank: bool = False,
        **filters,
    ) -> list[dict[str, Any]]:
        """
        Выполнить полнотекстовый поиск PostgreSQL.

        :param search_fields: Список полей для поиска
        :param query_text: Поисковый запрос
        :param search_type: Тип поиска (simple, phrase, websearch, raw)
        :param language: Язык для поиска (russian, english, simple)
        :param min_rank: Минимальный ранг результатов
        :param limit: Максимальное количество результатов
        :param include_rank: Включать ли ранг в результаты
        :param filters: Дополнительные фильтры
        :return: Список результатов поиска с рангом

        Example:
            ```python
            # Простой поиск
            results = await repository.fulltext_search(
                search_fields=["title", "content"],
                query_text="python programming",
                search_type="simple",
                limit=20
            )

            # Поиск с фразой
            results = await repository.fulltext_search(
                search_fields=["description"],
                query_text="machine learning algorithms",
                search_type="phrase",
                include_rank=True
            )
            ```
        """
        try:
            if not search_fields or not query_text.strip():
                return []

            # Выбираем функцию для поиска
            search_functions = {
                "simple": func.plainto_tsquery,
                "phrase": func.phraseto_tsquery,
                "websearch": func.websearch_to_tsquery,
                "raw": func.to_tsquery,
            }

            search_func = search_functions.get(search_type, func.plainto_tsquery)

            # Строим поисковый запрос
            rank_expressions = []
            search_conditions = []

            for field in search_fields:
                if hasattr(self._model, field):
                    field_attr = getattr(self._model, field)
                    tsvector = func.to_tsvector(language, field_attr)
                    tsquery = search_func(language, query_text)

                    # Условие поиска
                    search_conditions.append(tsvector.op("@@")(tsquery))

                    # Выражение для ранжирования
                    rank_expressions.append(func.ts_rank(tsvector, tsquery))

            if not search_conditions:
                logger.warning(f"No valid search fields found in model {self._model.__name__}")
                return []

            # Общий ранг как среднее по всем полям
            avg_rank = func.greatest(*rank_expressions) if len(rank_expressions) > 1 else rank_expressions[0]

            # Базовый запрос с условиями поиска
            if include_rank:
                query = select(self._model, avg_rank.label("search_rank"))
            else:
                query = select(self._model)

            # Применяем условия поиска (OR между полями)
            if len(search_conditions) > 1:
                from sqlalchemy import or_

                query = query.where(or_(*search_conditions))
            else:
                query = query.where(search_conditions[0])

            # Фильтруем по минимальному рангу
            if min_rank > 0.0:
                query = query.where(avg_rank >= min_rank)

            # Применяем дополнительные фильтры
            if filters:
                query = self._qb.apply_filters(query, filters, use_advanced_operators=True)

            # Сортируем по рангу (лучшие первыми)
            query = query.order_by(desc(avg_rank))

            # Ограничиваем количество результатов
            query = query.limit(limit)

            result = await self._db.execute(query)

            if include_rank:
                # Возвращаем с рангом
                rows = result.all()
                return [
                    {
                        "object": row[0],
                        "rank": float(row[1]),
                        **{c.key: getattr(row[0], c.key) for c in row[0].__table__.columns},
                    }
                    for row in rows
                ]
            else:
                # Возвращаем только объекты, преобразованные в словари
                objects = result.scalars().all()
                return [{c.key: getattr(obj, c.key) for c in obj.__table__.columns} for obj in objects]

        except Exception as e:
            logger.error(f"Error in fulltext search for {self._model.__name__}: {e}")
            return []

    async def list_with_complex_filters(
        self,
        complex_filters: dict[str, Any],
        *,
        offset: int | None = None,
        limit: int | None = None,
        include_deleted: bool = False,
        order_by: str = "created_at",
    ) -> Sequence[ModelType]:
        """
        Получить список объектов со сложными фильтрами (AND/OR/NOT).

        :param complex_filters: Сложные фильтры с логическими операторами
        :param offset: Смещение для пагинации
        :param limit: Лимит записей
        :param include_deleted: Включать ли soft-deleted объекты
        :param order_by: Поле для сортировки
        :return: Список объектов

        Example:
            ```python
            # Сложные условия
            complex_filters = {
                "and_filters": {"status": "active", "age__gt": 18},
                "or_filters": [
                    {"role": "admin"},
                    {"permissions__contains": "write"}
                ],
                "not_filters": {"deleted_at__isnotnull": True}
            }

            users = await repository.list_with_complex_filters(
                complex_filters,
                limit=20,
                order_by="created_at"
            )
            ```
        """
        try:
            query = self._qb.get_list_query(include_deleted)

            # Применяем сложные фильтры
            query = self._qb.apply_complex_filters(
                query,
                and_filters=complex_filters.get("and_filters"),
                or_filters=complex_filters.get("or_filters"),
                not_filters=complex_filters.get("not_filters"),
            )

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
            logger.error(f"Error in complex filters for {self._model.__name__}: {e}")
            return []

    async def aggregate(
        self,
        field: str,
        *,
        operations: list[Literal["count", "sum", "avg", "min", "max"]] | None = None,
        group_by: str | None = None,
        include_deleted: bool = False,
        **filters,
    ) -> list[AggregationResult]:
        """
        Выполнить агрегацию данных.

        :param field: Поле для агрегации
        :param operations: Список операций агрегации
        :param group_by: Поле для группировки
        :param include_deleted: Включать ли soft-deleted объекты
        :param filters: Фильтры для агрегации
        :return: Результаты агрегации

        Example:
            ```python
            # Статистика по пользователям
            stats = await repository.aggregate(
                field="age",
                operations=["count", "avg", "min", "max"],
                group_by="status",
                is_active=True
            )

            for stat in stats:
                print(f"Status: {stat.group_by}")
                print(f"Count: {stat.count}, Avg age: {stat.avg}")
            ```
        """
        try:
            if not hasattr(self._model, field):
                logger.error(f"Field '{field}' not found in model {self._model.__name__}")
                return []

            if operations is None:
                operations = ["count"]

            field_attr = getattr(self._model, field)
            select_expressions = []

            # Добавляем агрегационные функции
            for operation in operations:
                if operation == "count":
                    select_expressions.append(func.count(field_attr).label("count"))
                elif operation == "sum":
                    select_expressions.append(func.sum(field_attr).label("sum"))
                elif operation == "avg":
                    select_expressions.append(func.avg(field_attr).label("avg"))
                elif operation == "min":
                    select_expressions.append(func.min(field_attr).label("min"))
                elif operation == "max":
                    select_expressions.append(func.max(field_attr).label("max"))

            # Добавляем группировку
            if group_by and hasattr(self._model, group_by):
                group_field = getattr(self._model, group_by)
                select_expressions.append(group_field.label("group_by_field"))
                query = select(*select_expressions).group_by(group_field)
            else:
                query = select(*select_expressions)

            # Применяем фильтр deleted_at
            if not include_deleted and hasattr(self._model, "deleted_at"):
                query = query.where(self._model.deleted_at.is_(None))

            # Применяем остальные фильтры
            if filters:
                temp_query = self._qb.get_list_query(include_deleted)
                temp_query = self._qb.apply_filters(temp_query, filters, use_advanced_operators=True)
                if temp_query.whereclause is not None:
                    query = query.where(temp_query.whereclause)

            result = await self._db.execute(query)
            rows = result.all()

            # Преобразуем результаты
            results = []
            for row in rows:
                row_dict = dict(row._mapping)

                result_obj = AggregationResult(
                    field_name=field,
                    count=row_dict.get("count"),
                    sum=float(row_dict["sum"]) if row_dict.get("sum") is not None else None,
                    avg=float(row_dict["avg"]) if row_dict.get("avg") is not None else None,
                    min=row_dict.get("min"),
                    max=row_dict.get("max"),
                    group_by={group_by: row_dict.get("group_by_field")} if group_by else None,
                )
                results.append(result_obj)

            return results

        except Exception as e:
            logger.error(f"Error in aggregation for {self._model.__name__}: {e}")
            return []

    async def paginate_cursor(
        self,
        *,
        cursor_field: str = "id",
        cursor_value: Any = None,
        direction: Literal["next", "prev"] = "next",
        limit: int = 20,
        include_total: bool = False,
        include_deleted: bool = False,
        order_by: str | None = None,
        **filters,
    ) -> CursorPaginationResult[ModelType]:
        """
        Курсорная пагинация для больших наборов данных.

        :param cursor_field: Поле для курсора (должно быть уникальным и сортируемым)
        :param cursor_value: Значение курсора для начала выборки
        :param direction: Направление пагинации (next/prev)
        :param limit: Количество записей на страницу
        :param include_total: Включать ли общее количество записей (дорого!)
        :param include_deleted: Включать ли soft-deleted объекты
        :param order_by: Дополнительное поле для сортировки
        :param filters: Фильтры для выборки
        :return: Результат курсорной пагинации

        Example:
            ```python
            # Первая страница
            page1 = await repository.paginate_cursor(
                cursor_field="created_at",
                direction="next",
                limit=10,
                status="active"
            )

            # Следующая страница
            if page1.has_next:
                page2 = await repository.paginate_cursor(
                    cursor_field="created_at",
                    cursor_value=page1.next_cursor,
                    direction="next",
                    limit=10,
                    status="active"
                )
            ```
        """
        try:
            if not hasattr(self._model, cursor_field):
                logger.error(f"Cursor field '{cursor_field}' not found in model {self._model.__name__}")
                return CursorPaginationResult(items=[])

            cursor_attr = getattr(self._model, cursor_field)

            # Базовый запрос
            query = self._qb.get_list_query(include_deleted)
            query = self._qb.apply_filters(query, filters, use_advanced_operators=True)

            # Применяем курсор для фильтрации
            if cursor_value is not None:
                if direction == "next":
                    query = query.where(cursor_attr > cursor_value)
                else:  # prev
                    query = query.where(cursor_attr < cursor_value)

            # Сортировка
            sort_fields = []
            if order_by and hasattr(self._model, order_by):
                order_field = getattr(self._model, order_by)
                if direction == "next":
                    sort_fields.append(asc(order_field))
                else:
                    sort_fields.append(desc(order_field))

            # Добавляем сортировку по полю курсора
            if direction == "next":
                sort_fields.append(asc(cursor_attr))
            else:
                sort_fields.append(desc(cursor_attr))

            query = query.order_by(*sort_fields)

            # Получаем на одну запись больше для проверки has_next/has_prev
            query = query.limit(limit + 1)

            result = await self._db.execute(query)
            items = list(result.scalars().all())

            # Определяем наличие следующей/предыдущей страницы
            has_more = len(items) > limit
            if has_more:
                items = items[:limit]  # Убираем лишнюю запись

            # Определяем курсоры
            next_cursor = None
            prev_cursor = None

            if items:
                if direction == "next":
                    has_next = has_more
                    has_prev = cursor_value is not None
                    next_cursor = str(getattr(items[-1], cursor_field)) if has_next else None
                    prev_cursor = str(getattr(items[0], cursor_field)) if has_prev else None
                else:  # prev
                    has_next = cursor_value is not None
                    has_prev = has_more
                    # Для обратной пагинации разворачиваем список
                    items = list(reversed(items))
                    next_cursor = str(getattr(items[-1], cursor_field)) if has_next else None
                    prev_cursor = str(getattr(items[0], cursor_field)) if has_prev else None
            else:
                has_next = False
                has_prev = cursor_value is not None

            # Подсчет общего количества (дорогая операция)
            total_count = None
            if include_total:
                count_query = select(func.count(self._model.id))
                if not include_deleted and hasattr(self._model, "deleted_at"):
                    count_query = count_query.where(self._model.deleted_at.is_(None))

                if filters:
                    temp_query = self._qb.get_list_query(include_deleted)
                    temp_query = self._qb.apply_filters(temp_query, filters, use_advanced_operators=True)
                    if temp_query.whereclause is not None:
                        count_query = count_query.where(temp_query.whereclause)

                count_result = await self._db.execute(count_query)
                total_count = count_result.scalar() or 0

            return CursorPaginationResult(
                items=items,
                next_cursor=next_cursor,
                prev_cursor=prev_cursor,
                has_next=has_next,
                has_prev=has_prev,
                total_count=total_count,
            )

        except Exception as e:
            logger.error(f"Error in cursor pagination for {self._model.__name__}: {e}")
            return CursorPaginationResult(items=[])
