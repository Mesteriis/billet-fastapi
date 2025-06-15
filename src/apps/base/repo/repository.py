from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, joinedload
from sqlalchemy.orm import aliased
from sqlalchemy.inspection import inspect

from .events import CreateEvent, DeleteEvent, UpdateEvent
from apps.base.models import BaseModel, BaseSchema

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseSchema)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseSchema)

OPERATORS = {
    "eq": lambda f, v: f == v,
    "ne": lambda f, v: f != v,
    "lt": lambda f, v: f < v,
    "lte": lambda f, v: f <= v,
    "gt": lambda f, v: f > v,
    "gte": lambda f, v: f >= v,
    "like": lambda f, v: f.like(f"%{v}%"),
    "ilike": lambda f, v: f.ilike(f"%{v}%"),
    "in": lambda f, v: f.in_(v),
    "isnull": lambda f, v: f.is_(None) if v else f.is_not(None),
}

def model_to_dict(obj: Any) -> dict[str, Any]:
    """
    Convert SQLAlchemy model instance into a dictionary.
    Only includes direct column attributes.
    """
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}

class QueryBuilder:
    """
    QueryBuilder for building SQLAlchemy queries with support for nested filters and joins.

    :param model: SQLAlchemy model class (e.g., User)
    """
    _model: type[BaseModel]
    _joins: dict[str, Any]
    def __init__(self, model: type[BaseModel]):
        self._model = model
        self._joins: dict[str, Any] = {}

    def apply_filters(self, query: Select[Any], filters: dict[str, Any]) -> Select[Any]:
        """
        Apply filters to the SQLAlchemy query.
        :param query: SQLAlchemy Select query object
        :param filters:  Dictionary of filters where keys are field names with optional operators
        :return: SQLAlchemy Select query with applied filters
        """
        for raw_key, value in filters.items():
            *path, field_or_op = raw_key.split("__")
            op = "eq"

            if field_or_op in OPERATORS:
                op = field_or_op
                field = path.pop()
            else:
                field = field_or_op

            if not path:
                attr = getattr(self._model, field, None)
                if isinstance(attr, InstrumentedAttribute) and value is not None:
                    query = query.where(OPERATORS[op](attr, value))
            else:
                query, related = self.get_or_create_join(query, self._model, path)
                attr = getattr(related, field, None)
                if isinstance(attr, InstrumentedAttribute) and value is not None:
                    query = query.where(OPERATORS[op](attr, value))

        return query

    def get_or_create_join(self, query: Select, base: Any, path: list[str]) -> tuple[Select, Any]:
        """
        Get or create a join for the given path in the query.
        :param query: SQLAlchemy Select query object
        :param base: Base model class to start the join from
        :param path: List of path components to join on
        :return: SQLAlchemy Select query with join applied and the last aliased model
        """
        current = base
        for depth in range(1, len(path) + 1):
            key = "__".join(path[:depth])
            if key not in self._joins:
                aliased_model = aliased(getattr(current, path[depth - 1]).property.mapper.class_)
                query = query.join(aliased_model, getattr(current, path[depth - 1]))
                self._joins[key] = aliased_model
            current = self._joins[key]
        return query, current

    def get_loader_options(self) -> list:
        """
        Get SQLAlchemy loader options for joined loading based on the joins defined.
        :return: SQLAlchemy loader options for joined loading
        """
        loaders = []
        for key in self._joins.keys():
            parts = key.split("__")
            attr = getattr(self._model, parts[0])
            loader = joinedload(attr)
            current_model = attr.property.mapper.class_
            for part in parts[1:]:
                attr = getattr(current_model, part)
                loader = loader.joinedload(attr)
                current_model = attr.property.mapper.class_
            loaders.append(loader)
        return loaders

    def get_list_query(self, include_deleted: bool = False) -> Select[tuple[ModelType]]:
        """
        Get a base query for listing objects of the model.
        :param include_deleted: Whether to include soft-deleted objects in the query
        :return: SQLAlchemy Select query for listing objects
        """
        query = select(self._model)
        if not include_deleted:
            query = query.where(self._model.deleted_at.is_(None))
        return query

    def get_object_query(self, id: uuid.UUID, include_deleted: bool = False) -> Select[tuple[ModelType]]:
        """
        Get a query for retrieving a single object by its ID.
        :param id: UUID of the object to retrieve
        :param include_deleted: Whether to include soft-deleted objects in the query
        :return: SQLAlchemy Select query for the object
        """
        return self.get_list_query(include_deleted).where(self._model.id == id)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    BaseRepository async for CRUD operations with SQLAlchemy models.

    :param model: SQLAlchemy model class (e.g., User)
    :param db: async SQLAlchemy session
    """
    _model: type[ModelType]
    _db: AsyncSession
    _qb: QueryBuilder

    def __init__(self, model: type[ModelType], db: AsyncSession):
        """
        Initialize the repository with a model and database session.
        :param model: SQLAlchemy model class (e.g., User)
        :param db: async SQLAlchemy session
        """
        self._model = model
        self._db = db
        self._qb = QueryBuilder(model)



    async def list(self, *, offset: int | None = None, limit: int | None = None, include_deleted: bool = False, order_by: str = "created_at", **filters) -> Sequence[ModelType]:
        """
        List objects of the model with optional filters, pagination, and ordering.
        :param offset: Offset for pagination
        :param limit: Limit for pagination
        :param include_deleted: Whether to include soft-deleted objects
        :param order_by: Field to order by, can be a nested field using "__" (e.g., "related_model__field")
        :param filters: Filters to apply to the query, can include nested fields using "__" (e.g., "related_model__field__eq=value")
        :return: List of model instances matching the query
        """
        query = self._qb.apply_filters(
            self._qb.get_list_query(include_deleted),
            filters
        )

        if "__" in order_by:
            *path, field = order_by.split("__")
            query, related = self._qb.get_or_create_join(query, self._model, path)
            attr = getattr(related, field, None)
            if isinstance(attr, InstrumentedAttribute):
                query = query.order_by(attr)
        elif hasattr(self._model, order_by):
            query = query.order_by(getattr(self._model, order_by))

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        for loader in self._qb.get_loader_options():
            query = query.options(loader)

        result = await self._db.execute(query)
        return result.scalars().all()

    async def get(self, id: uuid.UUID, include_deleted: bool = False) -> ModelType | None:
        """
        Get a single object by its ID.
        :param id: UUID of the object to retrieve
        :param include_deleted: Whether to include soft-deleted objects in the query
        :return: Model instance if found, otherwise None
        """
        result = await self._db.execute(self._qb.get_object_query(id, include_deleted))
        return result.scalar_one_or_none()

    async def get_by(self, **filters) -> ModelType | None:
        """
        Get a single object by applying filters.
        :param filters: Dictionary of filters where keys are field names with optional operators
        :return: Model instance if found, otherwise None
        """
        query = self._qb.apply_filters(self._qb.get_list_query(), filters).limit(1)
        for loader in self._qb.get_loader_options():
            query = query.options(loader)
        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def exists(self, **filters) -> bool:
        """
        Check if an object exists in the database based on filters.
        :param filters: Dictionary of filters where keys are field names with optional operators
        :return: True if an object exists, otherwise False
        """
        query = select(func.count()).select_from(self._model)
        query = self._qb.apply_filters(query, filters)
        result = await self._db.execute(query)
        return result.scalar_one() > 0

    async def count(self, include_deleted: bool = False, **filters) -> int:
        """
        Count the number of objects in the database based on filters.
        :param include_deleted: Whether to include soft-deleted objects in the count
        :param filters: Dictionary of filters where keys are field names with optional operators
        :return: Count of objects matching the filters
        """
        base_query = self._qb.apply_filters(self._qb.get_list_query(include_deleted), filters)
        query = select(func.count()).select_from(base_query.subquery())
        result = await self._db.execute(query)
        return result.scalar_one()

    async def create(self, data: CreateSchemaType | dict[str, Any], *, emit_event: bool = True) -> ModelType:
        """
        Create a new object in the database.
        :param data: Data for creating the object, can be a Pydantic model or a dictionary
        :param emit_event: Whether to emit a creation event after creating the object
        :return: Created model instance
        """
        if not isinstance(data, dict):
            data = data.model_dump()
        db_obj = self._model(**data)
        self._db.add(db_obj)
        await self._db.flush()
        await self._db.refresh(db_obj)
        if emit_event:
            CreateEvent(entity_data=model_to_dict(db_obj)).emit()
        return db_obj

    async def update(self, db_obj: ModelType, data: UpdateSchemaType | dict[str, Any], *, emit_event: bool = True) -> ModelType:
        """
        Update an existing object in the database.
        :param db_obj: Existing model instance to update
        :param data: Data for updating the object, can be a Pydantic model or a dictionary
        :param emit_event: Whether to emit an update event after updating the object
        :return: Updated model instance
        """
        old_data = model_to_dict(db_obj) if emit_event else None
        update_data = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
        changed_fields = []
        for field, value in update_data.items():
            if hasattr(db_obj, field) and getattr(db_obj, field) != value:
                setattr(db_obj, field, value)
                changed_fields.append(field)
        await self._db.flush()
        await self._db.refresh(db_obj)
        if emit_event and changed_fields:
            UpdateEvent(entity_id=str(db_obj.id), old_data=old_data, new_data=model_to_dict(db_obj), changed_fields=changed_fields).emit()
        return db_obj

    async def remove(self, id: uuid.UUID, *, soft_delete: bool = True, emit_event: bool = True) -> ModelType | None:
        """
        Remove an object from the database by its ID.
        :param id: UUID of the object to remove
        :param soft_delete: Whether to perform a soft delete (mark as deleted) or hard delete (remove from database)
        :param emit_event: Whether to emit a deletion event after removing the object
        :return: Removed model instance if found, otherwise None
        """
        db_obj = await self.get(id=id)
        if not db_obj:
            return None
        entity_data = model_to_dict(db_obj) if emit_event else None
        if soft_delete:
            db_obj.soft_delete()
            await self._db.flush()
            await self._db.refresh(db_obj)
        else:
            await self._db.delete(db_obj)
        if emit_event:
            DeleteEvent(entity_id=str(id), entity_data=entity_data, soft_delete=soft_delete).emit()
        return db_obj

    async def restore(self, id: uuid.UUID, *, emit_event: bool = True) -> ModelType | None:
        """
        Restore a soft-deleted object by its ID.
        :param id: UUID of the object to restore
        :param emit_event: Whether to emit a restoration event after restoring the object
        :return: Restored model instance if found, otherwise None
        """
        db_obj = await self.get(id=id, include_deleted=True)
        if not db_obj or not db_obj.is_deleted:
            return None
        db_obj.restore()
        await self._db.flush()
        await self._db.refresh(db_obj)
        if emit_event:
            event = CreateEvent(entity_data=model_to_dict(db_obj))
            event.metadata["restored"] = True
            event.emit()
        return db_obj
