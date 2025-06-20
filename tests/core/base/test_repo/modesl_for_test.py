from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pytz import utc
from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .enums import PostStatus, Priority


# Отдельный DeclarativeBase для тестовых моделей
class TestBaseModel(DeclarativeBase, AsyncAttrs):
    """Базовая модель для тестов репозитория."""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

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


post_tags_table = Table(
    "test_post_tags",
    TestBaseModel.metadata,
    Column("post_id", ForeignKey("test_posts.id"), primary_key=True),
    Column("tag_id", ForeignKey("test_tags.id"), primary_key=True),
)


class TestUser(TestBaseModel):
    """Модель пользователя."""

    __tablename__ = "test_users"

    # Основная информация
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Аутентификация
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Дополнительная информация
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Метаданные
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped["TestProfile"] = relationship("TestProfile", uselist=False, back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"

    @hybrid_property
    def is_email_verified(self) -> bool:
        """Проверка верификации email."""
        return self.email_verified_at is not None

    def verify_email(self) -> None:
        """Верификация email пользователя."""
        self.email_verified_at = datetime.now(tz=utc)
        self.is_verified = True

    def update_last_login(self) -> None:
        """Обновление времени последнего входа."""
        self.last_login_at = datetime.now(tz=utc)


class TestPost(TestBaseModel):
    """
    Модель поста для тестирования полнотекстового поиска, JSON полей,
    дат, агрегаций и сложных связей.
    """

    __tablename__ = "test_posts"

    # Основные поля
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Enum поле
    status: Mapped[PostStatus] = mapped_column(String(20), default=PostStatus.DRAFT, nullable=False)
    priority: Mapped[Priority] = mapped_column(String(10), default=Priority.MEDIUM, nullable=False)

    # Числовые поля для агрегаций
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Даты для тестирования date операторов
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Булевы поля
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_comments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # JSON поля для тестирования JSON операторов
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    seo_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Полнотекстовый поиск
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    # Связи
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_users.id"), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("test_categories.id"), nullable=True)

    # Relationships
    author: Mapped["TestUser"] = relationship("TestUser")
    category: Mapped["TestCategory | None"] = relationship("TestCategory", back_populates="posts")
    comments: Mapped[list["TestComment"]] = relationship("TestComment", back_populates="post")
    tags: Mapped[list["TestTag"]] = relationship("TestTag", secondary=post_tags_table, back_populates="posts")

    # Индексы для тестирования
    __table_args__ = (
        Index("idx_post_status_published", "status", "published_at"),
        Index("idx_post_author_status", "author_id", "status"),
        Index("idx_post_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_post_extra_metadata", "extra_metadata", postgresql_using="gin"),
        CheckConstraint("views_count >= 0", name="check_views_positive"),
        CheckConstraint("likes_count >= 0", name="check_likes_positive"),
        CheckConstraint("rating >= 0.0 AND rating <= 5.0", name="check_rating_range"),
    )


class TestCategory(TestBaseModel):
    """Категория для тестирования иерархических связей и группировок."""

    __tablename__ = "test_categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Иерархия
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("test_categories.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Статистика для агрегаций
    posts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Связи
    parent: Mapped["TestCategory | None"] = relationship("TestCategory", remote_side="TestCategory.id")
    children: Mapped[list["TestCategory"]] = relationship("TestCategory", back_populates="parent")
    posts: Mapped[list[TestPost]] = relationship("TestPost", back_populates="category")


class TestTag(TestBaseModel):
    """Тег для тестирования связей многие-ко-многим."""

    __tablename__ = "test_tags"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # HEX цвет
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Связи
    posts: Mapped[list[TestPost]] = relationship("TestPost", secondary=post_tags_table, back_populates="tags")


class TestComment(TestBaseModel):
    """Комментарий для тестирования вложенных связей и курсорной пагинации."""

    __tablename__ = "test_comments"

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Иерархия
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("test_comments.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Модерация
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_spam: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Метрики
    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Связи
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_posts.id"), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_users.id"), nullable=False)

    post: Mapped[TestPost] = relationship("TestPost", back_populates="comments")
    author: Mapped["TestUser"] = relationship("TestUser")
    parent: Mapped["TestComment | None"] = relationship("TestComment", remote_side="TestComment.id")
    children: Mapped[list["TestComment"]] = relationship("TestComment", back_populates="parent")


class TestProfile(TestBaseModel):
    """Профиль для тестирования связей один-к-одному."""

    __tablename__ = "test_profiles"

    # Контактная информация
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Адрес
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Настройки
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # JSON настройки
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Связь один-к-одному с User
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_users.id"), unique=True, nullable=False)
    user: Mapped[TestUser] = relationship("TestUser", back_populates="profile")  # Настройки
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # JSON настройки
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Связь один-к-одному с User
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_users.id"), unique=True, nullable=False)
    user: Mapped[TestUser] = relationship("TestUser", back_populates="profile")
