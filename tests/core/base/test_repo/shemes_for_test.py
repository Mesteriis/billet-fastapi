import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field

from .enums import Priority
from .modesl_for_test import PostStatus


class TestUserCreate(PydanticBaseModel):
    username: str = Field(..., max_length=50)
    email: str = Field(..., max_length=255)
    full_name: str | None = Field(None, max_length=255)
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    avatar_url: str | None = None
    bio: str | None = None


class TestUserUpdate(PydanticBaseModel):
    username: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    full_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None
    avatar_url: str | None = None
    bio: str | None = None
    last_login_at: datetime | None = None
    email_verified_at: datetime | None = None


class TestPostCreate(PydanticBaseModel):
    title: str = Field(..., max_length=300)
    slug: str = Field(..., max_length=300)
    content: str
    excerpt: str | None = None
    status: PostStatus = PostStatus.DRAFT
    priority: Priority = Priority.MEDIUM
    published_at: datetime | None = None
    scheduled_at: date | None = None
    is_featured: bool = False
    is_premium: bool = False
    allow_comments: bool = True
    extra_metadata: dict[str, Any] | None = None
    seo_data: dict[str, Any] | None = None
    author_id: uuid.UUID
    category_id: uuid.UUID | None = None


class TestPostUpdate(PydanticBaseModel):
    title: str | None = None
    content: str | None = None
    excerpt: str | None = None
    status: PostStatus | None = None
    priority: Priority | None = None
    views_count: int | None = Field(None, ge=0)
    likes_count: int | None = Field(None, ge=0)
    rating: float | None = Field(None, ge=0.0, le=5.0)
    published_at: datetime | None = None
    scheduled_at: date | None = None
    is_featured: bool | None = None
    is_premium: bool | None = None
    allow_comments: bool | None = None
    extra_metadata: dict[str, Any] | None = None
    seo_data: dict[str, Any] | None = None
    category_id: uuid.UUID | None = None
