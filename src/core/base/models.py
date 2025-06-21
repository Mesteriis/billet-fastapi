"""Base Model Classes for Database and Schema Operations.

This module provides base classes for SQLAlchemy models and Pydantic schemas
with common functionality including soft deletion, automatic timestamps,
and standard utility methods.

Features:
    - Base SQLAlchemy model with UUID primary keys
    - Automatic created_at and updated_at timestamps
    - Soft deletion support with is_deleted property
    - Model to dictionary conversion
    - Base Pydantic schema with common fields
    - SQL query debugging in development mode

Example:
    Creating a model::

        from core.base.models import BaseModel
        from sqlalchemy.orm import Mapped, mapped_column
        from sqlalchemy import String

        class User(BaseModel):
            __tablename__ = "users"

            username: Mapped[str] = mapped_column(String(50), unique=True)
            email: Mapped[str] = mapped_column(String(100), unique=True)

    Using soft deletion::

        user = User(username="john", email="john@example.com")

        # Soft delete
        user.soft_delete()
        print(user.is_deleted)  # True

        # Restore
        user.restore()
        print(user.is_deleted)  # False

    Model updates and conversion::

        user.update(username="john_doe", email="john.doe@example.com")
        user_dict = user.to_dict()
        print(user_dict)  # {"id": "...", "username": "john_doe", ...}

    Creating a schema::

        from core.base.models import BaseSchema
        from pydantic import Field

        class UserSchema(BaseSchema):
            username: str = Field(max_length=50)
            email: str = Field(max_length=100)

Note:
    SQL query debugging is automatically enabled when DEBUG=true environment
    variable is set. All models inherit UUID primary keys and timestamp fields.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field
from pytz import utc
from sqlalchemy import UUID, DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func

if os.environ.get("DEBUG", "false").lower() == "true":
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        print(f"Executing SQL: {statement} with params: {parameters}")
        return statement, parameters


class BaseModel(DeclarativeBase, AsyncAttrs):
    """Base SQLAlchemy model with common fields and soft deletion support.

    Provides a foundation for all database models with:
    - UUID primary key
    - Automatic timestamp fields (created_at, updated_at)
    - Soft deletion capability
    - Common utility methods

    Attributes:
        id (Mapped[uuid.UUID]): Primary key UUID, auto-generated
        created_at (Mapped[datetime]): Record creation timestamp
        updated_at (Mapped[datetime]): Last update timestamp
        deleted_at (Mapped[datetime | None]): Soft deletion timestamp

    Example:
        Creating a model class::

            class Product(BaseModel):
                __tablename__ = "products"

                name: Mapped[str] = mapped_column(String(100))
                price: Mapped[float] = mapped_column(Numeric(10, 2))

        Using the model::

            product = Product(name="Laptop", price=999.99)

            # Auto-generated fields are available
            print(product.id)  # UUID object
            print(product.created_at)  # Current datetime

        Soft deletion workflow::

            # Mark as deleted
            product.soft_delete()
            assert product.is_deleted == True

            # Restore if needed
            product.restore()
            assert product.is_deleted == False

        Model updates::

            product.update(name="Gaming Laptop", price=1299.99)
            # updated_at is automatically set

        Dictionary conversion::

            product_data = product.to_dict()
            # Returns all column values as dict

    Note:
        All models automatically inherit async support through AsyncAttrs.
        Timestamps are timezone-aware and use server-side defaults.
    """

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    @hybrid_property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted.

        Returns:
            bool: True if record has been soft deleted

        Example:
            Checking deletion status::

                user = User(username="test")
                print(user.is_deleted)  # False

                user.soft_delete()
                print(user.is_deleted)  # True

            Using in queries::

                # Filter out deleted records
                active_users = session.query(User).filter(~User.is_deleted)
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark record as deleted without removing from database.

        Sets deleted_at timestamp to current UTC time, effectively
        hiding the record from normal queries while preserving data.

        Example:
            Soft deletion::

                user = User(username="test")
                user.soft_delete()

                # Record is marked as deleted
                assert user.is_deleted == True
                assert user.deleted_at is not None

            Bulk soft deletion::

                users_to_delete = session.query(User).filter(User.active == False)
                for user in users_to_delete:
                    user.soft_delete()

        Note:
            This method only sets the timestamp. You still need to commit
            the database transaction to persist the change.
        """
        self.deleted_at = datetime.now(tz=utc)

    def restore(self) -> None:
        """Restore a soft deleted record.

        Clears the deleted_at timestamp, making the record visible
        in normal queries again.

        Example:
            Restoring a deleted record::

                user.soft_delete()
                print(user.is_deleted)  # True

                user.restore()
                print(user.is_deleted)  # False
                print(user.deleted_at)  # None

            Conditional restoration::

                if user.is_deleted and should_restore_user(user):
                    user.restore()
                    await session.commit()

        Note:
            This method only clears the timestamp. You still need to commit
            the database transaction to persist the change.
        """
        self.deleted_at = None

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary.

        Returns all column values as a dictionary with column names as keys.
        Useful for serialization and debugging.

        Returns:
            dict[str, Any]: Dictionary containing all column values

        Example:
            Basic conversion::

                user = User(username="john", email="john@example.com")
                data = user.to_dict()
                print(data)
                # {
                #     "id": UUID("..."),
                #     "username": "john",
                #     "email": "john@example.com",
                #     "created_at": datetime(...),
                #     "updated_at": datetime(...),
                #     "deleted_at": None
                # }

            Using for JSON serialization::

                import json
                from datetime import datetime

                def json_serializer(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    elif isinstance(obj, uuid.UUID):
                        return str(obj)
                    raise TypeError

                user_dict = user.to_dict()
                json_data = json.dumps(user_dict, default=json_serializer)

        Note:
            The returned dictionary contains raw SQLAlchemy values.
            UUIDs and datetimes may need custom serialization for JSON.
        """
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def update(self, **kwargs) -> None:
        """Update model attributes from keyword arguments.

        Updates only existing attributes, ignoring invalid keys.
        The updated_at field is automatically updated by SQLAlchemy.

        Args:
            **kwargs: Attribute names and values to update

        Example:
            Simple updates::

                user = User(username="john", email="john@example.com")
                user.update(username="john_doe", email="john.doe@example.com")

                print(user.username)  # "john_doe"
                print(user.email)     # "john.doe@example.com"

            Updating with validation::

                user.update(
                    username="new_username",
                    email="new@example.com",
                    invalid_field="ignored"  # This will be ignored
                )

            Bulk updates from form data::

                form_data = {
                    "username": request.form["username"],
                    "email": request.form["email"],
                    "bio": request.form["bio"]
                }
                user.update(**form_data)
                await session.commit()

        Note:
            Only existing model attributes are updated. Invalid keys are silently ignored.
            Remember to commit the session to persist changes to the database.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class BaseSchema(PydanticBaseModel):
    """Base Pydantic schema with common fields for API serialization.

    Provides a foundation for all API schemas with standard fields
    and configuration for SQLAlchemy model conversion.

    Attributes:
        id (uuid.UUID): Record identifier
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        deleted_at (datetime | None): Soft deletion timestamp
        is_deleted (bool): Soft deletion status

    Example:
        Creating a schema class::

            class UserSchema(BaseSchema):
                username: str = Field(max_length=50)
                email: str = Field(pattern=r'^[^@]+@[^@]+\\..*$')

        Using with SQLAlchemy models::

            user_model = User(username="john", email="john@example.com")
            user_schema = UserSchema.model_validate(user_model)

            # Schema automatically includes base fields
            print(user_schema.id)
            print(user_schema.created_at)
            print(user_schema.is_deleted)

        API response serialization::

            @app.get("/users/{user_id}", response_model=UserSchema)
            async def get_user(user_id: uuid.UUID):
                user = await session.get(User, user_id)
                return UserSchema.model_validate(user)

        Creating from dictionary::

            user_data = {
                "username": "jane",
                "email": "jane@example.com"
            }
            schema = UserSchema.model_validate(user_data)

    Note:
        The schema automatically handles SQLAlchemy model conversion
        through the from_attributes configuration.
    """

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    id: Annotated[uuid.UUID, Field(default_factory=uuid.uuid4)]
    created_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(tz=utc))]
    updated_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(tz=utc))]
    deleted_at: Annotated[datetime | None, Field(default_factory=lambda: None)]
    is_deleted: Annotated[bool, Field(default_factory=lambda: False)]
