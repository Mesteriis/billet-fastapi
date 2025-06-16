import uuid
from datetime import datetime, date
from typing import Any

from pydantic import BaseModel as PydanticBaseModel, Field

from .enums import Priority
from .modesl_for_test import PostStatus


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