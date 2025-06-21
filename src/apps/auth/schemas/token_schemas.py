"""
Схемы для JWT токенов и orbital токенов.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from core.base.models import BaseSchema
from core.enums import UserRole


class OrbitalTokenType(str, Enum):
    """Типы одноразовых токенов."""

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    TWO_FACTOR_AUTH = "two_factor_auth"
    PHONE_VERIFICATION = "phone_verification"
    ACCOUNT_ACTIVATION = "account_activation"
    LOGIN_VERIFICATION = "login_verification"
    CUSTOM = "custom"


class JWTPayload(BaseSchema):
    """Схема полезной нагрузки JWT токена."""

    sub: str = Field(..., description="Subject (User ID)")
    user_id: uuid.UUID = Field(..., description="ID пользователя")
    username: str = Field(..., description="Имя пользователя")
    email: str = Field(..., description="Email пользователя")
    role: UserRole = Field(..., description="Роль пользователя")
    is_active: bool = Field(..., description="Активен ли пользователь")
    is_verified: bool = Field(..., description="Подтвержден ли email")
    is_superuser: bool = Field(..., description="Является ли суперпользователем")
    iat: int = Field(..., description="Issued at (время выдачи)")
    exp: int = Field(..., description="Expiration time (время истечения)")
    jti: str = Field(..., description="JWT ID (уникальный идентификатор токена)")
    token_type: str = Field("access", description="Тип токена (access/refresh)")
    device_fingerprint: str | None = Field(None, description="Отпечаток устройства")
    permissions: list[str] = Field(default_factory=list, description="Список разрешений пользователя")

    @property
    def is_expired(self) -> bool:
        """Проверка истечения токена."""
        import time

        return time.time() > self.exp

    @property
    def time_to_expire(self) -> int:
        """Время до истечения в секундах."""
        import time

        return max(0, self.exp - int(time.time()))

    def has_permission(self, permission: str) -> bool:
        """Проверка наличия разрешения."""
        return permission in self.permissions

    def has_role(self, required_role: UserRole) -> bool:
        """Проверка наличия роли."""
        return self.role.has_permission(required_role)


class RefreshTokenPayload(BaseSchema):
    """Схема полезной нагрузки refresh токена."""

    sub: str = Field(..., description="Subject (User ID)")
    user_id: uuid.UUID = Field(..., description="ID пользователя")
    token_id: uuid.UUID = Field(..., description="ID токена в базе данных")
    iat: int = Field(..., description="Issued at (время выдачи)")
    exp: int = Field(..., description="Expiration time (время истечения)")
    jti: str = Field(..., description="JWT ID (уникальный идентификатор токена)")
    token_type: str = Field("refresh", description="Тип токена")
    device_fingerprint: str | None = Field(None, description="Отпечаток устройства")

    @property
    def is_expired(self) -> bool:
        """Проверка истечения токена."""
        import time

        return time.time() > self.exp


class OrbitalTokenPayload(BaseSchema):
    """Схема полезной нагрузки orbital токена."""

    sub: str = Field(..., description="Subject (User ID)")
    user_id: uuid.UUID = Field(..., description="ID пользователя")
    action: str = Field(..., description="Действие токена (email_verification, password_reset, etc.)")
    iat: int = Field(..., description="Issued at (время выдачи)")
    exp: int = Field(..., description="Expiration time (время истечения)")
    jti: str = Field(..., description="JWT ID (уникальный идентификатор токена)")
    token_type: str = Field("orbital", description="Тип токена")
    data: dict[str, Any] = Field(default_factory=dict, description="Дополнительные данные токена")
    single_use: bool = Field(True, description="Одноразовый ли токен")

    @property
    def is_expired(self) -> bool:
        """Проверка истечения токена."""
        import time

        return time.time() > self.exp

    def get_data(self, key: str, default: Any = None) -> Any:
        """Получить данные из токена."""
        return self.data.get(key, default)


class TokenValidationResult(BaseSchema):
    """Результат валидации токена."""

    valid: bool = Field(..., description="Валиден ли токен")
    payload: JWTPayload | RefreshTokenPayload | OrbitalTokenPayload | None = Field(
        None, description="Полезная нагрузка токена"
    )
    error: str | None = Field(None, description="Ошибка валидации")
    error_code: str | None = Field(None, description="Код ошибки")


class TokenInfo(BaseSchema):
    """Информация о токене."""

    token_id: str = Field(..., description="ID токена")
    user_id: uuid.UUID = Field(..., description="ID пользователя")
    token_type: str = Field(..., description="Тип токена")
    expires_at: datetime = Field(..., description="Время истечения")
    created_at: datetime = Field(..., description="Время создания")
    last_used_at: datetime | None = Field(None, description="Время последнего использования")
    device_info: str | None = Field(None, description="Информация об устройстве")
    ip_address: str | None = Field(None, description="IP адрес")
    is_revoked: bool = Field(False, description="Отозван ли токен")


class ActiveTokensResponse(BaseSchema):
    """Ответ со списком активных токенов."""

    access_tokens: list[TokenInfo] = Field(default_factory=list, description="Активные access токены")
    refresh_tokens: list[TokenInfo] = Field(default_factory=list, description="Активные refresh токены")
    total_count: int = Field(..., description="Общее количество токенов")


class RevokeTokenRequest(BaseSchema):
    """Запрос на отзыв токена."""

    token: str | None = Field(None, description="Токен для отзыва")
    token_id: str | None = Field(None, description="ID токена для отзыва")
    revoke_all: bool = Field(False, description="Отозвать все токены пользователя")
    reason: str | None = Field(None, max_length=255, description="Причина отзыва")


class RevokeTokenResponse(BaseSchema):
    """Ответ на отзыв токена."""

    revoked_count: int = Field(..., description="Количество отозванных токенов")
    message: str = Field(..., description="Сообщение о результате")
