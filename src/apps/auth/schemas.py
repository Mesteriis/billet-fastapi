"""
Pydantic схемы для аутентификации.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from apps.base.models import BaseSchema, CreateSchema, TimestampSchema


class TokenPair(BaseSchema):
    """Схема пары токенов."""

    access_token: str = Field(..., description="Access токен")
    refresh_token: str = Field(..., description="Refresh токен")
    token_type: str = Field(default="bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время жизни access токена в секундах")


class TokenCreate(CreateSchema):
    """Схема для создания токена."""

    user_id: uuid.UUID = Field(..., description="ID пользователя")
    jti: str = Field(..., description="JWT ID")
    expires_at: datetime = Field(..., description="Время истечения")
    user_agent: str | None = Field(None, description="User Agent")
    ip_address: str | None = Field(None, description="IP адрес")


class RefreshTokenRequest(BaseSchema):
    """Схема запроса обновления токена."""

    refresh_token: str = Field(..., description="Refresh токен")


class RefreshTokenResponse(TimestampSchema):
    """Схема ответа с данными refresh токена."""

    user_id: uuid.UUID = Field(..., description="ID пользователя")
    jti: str = Field(..., description="JWT ID")
    expires_at: datetime = Field(..., description="Время истечения")
    is_revoked: bool = Field(..., description="Отозван ли токен")
    user_agent: str | None = Field(None, description="User Agent")
    ip_address: str | None = Field(None, description="IP адрес")


class LoginResponse(BaseSchema):
    """Схема ответа при входе."""

    user: dict = Field(..., description="Данные пользователя")
    tokens: TokenPair = Field(..., description="Токены")


class LogoutRequest(BaseSchema):
    """Схема запроса выхода."""

    refresh_token: str | None = Field(None, description="Refresh токен для отзыва")
    revoke_all: bool = Field(default=False, description="Отозвать все токены пользователя")


class TokenValidationResponse(BaseSchema):
    """Схема ответа валидации токена."""

    valid: bool = Field(..., description="Валидность токена")
    user_id: str | None = Field(None, description="ID пользователя")
    email: str | None = Field(None, description="Email пользователя")
    username: str | None = Field(None, description="Имя пользователя")
    token_type: str | None = Field(None, description="Тип токена")
    expires_at: datetime | None = Field(None, description="Время истечения")
    error: str | None = Field(None, description="Ошибка валидации")
