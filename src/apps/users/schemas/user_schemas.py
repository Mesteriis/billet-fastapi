"""
Схемы валидации для пользователей.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import EmailStr, Field, field_validator

from apps.users.exceptions import UsersPasswordMismatchError, UsersPasswordValidationError, UsersUsernameValidationError
from apps.users.models.enums import UserLanguage, UserRole, UserStatus
from core.base.models import BaseSchema


class UserBase(BaseSchema):
    """Базовая схема пользователя."""

    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя")
    email: EmailStr = Field(..., description="Email адрес")
    first_name: str | None = Field(None, max_length=100, description="Имя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия")
    avatar_url: str | None = Field(None, max_length=500, description="URL аватара")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Валидация имени пользователя."""
        if not v.isalnum() and "_" not in v and "-" not in v:
            msg = "Имя пользователя может содержать только буквы, цифры, _ и -"
            raise UsersUsernameValidationError(msg)

        if v.startswith(("_", "-")) or v.endswith(("_", "-")):
            msg = "Имя пользователя не может начинаться или заканчиваться на _ или -"
            raise UsersUsernameValidationError(msg)

        return v.lower()

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        """Валидация URL аватара."""
        if v and not v.startswith(("http://", "https://")):
            msg = "URL аватара должен начинаться с http:// или https://"
            raise UsersUsernameValidationError(msg)
        return v


class UserCreate(UserBase):
    """Схема создания пользователя."""

    password: str = Field(..., min_length=8, max_length=128, description="Пароль")
    confirm_password: str = Field(..., description="Подтверждение пароля")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля."""
        if not any(c.islower() for c in v):
            msg = "Пароль должен содержать хотя бы одну строчную букву"
            raise UsersPasswordValidationError(msg)

        if not any(c.isupper() for c in v):
            msg = "Пароль должен содержать хотя бы одну заглавную букву"
            raise UsersPasswordValidationError(msg)

        if not any(c.isdigit() for c in v):
            msg = "Пароль должен содержать хотя бы одну цифру"
            raise UsersPasswordValidationError(msg)

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            msg = "Пароль должен содержать хотя бы один специальный символ"
            raise UsersPasswordValidationError(msg)

        return v

    def model_post_init(self, __context: Any) -> None:
        """Валидация после инициализации модели."""
        super().model_post_init(__context)
        if self.password != self.confirm_password:
            msg = "Пароли не совпадают"
            raise UsersPasswordMismatchError(msg)


class UserUpdate(BaseSchema):
    """Схема обновления пользователя."""

    username: str | None = Field(None, min_length=3, max_length=50, description="Имя пользователя")
    email: EmailStr | None = Field(None, description="Email адрес")
    first_name: str | None = Field(None, max_length=100, description="Имя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия")
    avatar_url: str | None = Field(None, max_length=500, description="URL аватара")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """Валидация имени пользователя."""
        if v is None:
            return v

        if not v.isalnum() and "_" not in v and "-" not in v:
            msg = "Имя пользователя может содержать только буквы, цифры, _ и -"
            raise UsersUsernameValidationError(msg)

        if v.startswith(("_", "-")) or v.endswith(("_", "-")):
            msg = "Имя пользователя не может начинаться или заканчиваться на _ или -"
            raise UsersUsernameValidationError(msg)

        return v.lower()

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        """Валидация URL аватара."""
        if v and not v.startswith(("http://", "https://")):
            msg = "URL аватара должен начинаться с http:// или https://"
            raise UsersUsernameValidationError(msg)
        return v


class UserPasswordUpdate(BaseSchema):
    """Схема обновления пароля пользователя."""

    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., min_length=8, max_length=128, description="Новый пароль")
    confirm_new_password: str = Field(..., description="Подтверждение нового пароля")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля."""
        if not any(c.islower() for c in v):
            msg = "Пароль должен содержать хотя бы одну строчную букву"
            raise UsersPasswordValidationError(msg)

        if not any(c.isupper() for c in v):
            msg = "Пароль должен содержать хотя бы одну заглавную букву"
            raise UsersPasswordValidationError(msg)

        if not any(c.isdigit() for c in v):
            msg = "Пароль должен содержать хотя бы одну цифру"
            raise UsersPasswordValidationError(msg)

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            msg = "Пароль должен содержать хотя бы один специальный символ"
            raise UsersPasswordValidationError(msg)

        return v

    def model_post_init(self, __context: Any) -> None:
        """Валидация после инициализации модели."""
        super().model_post_init(__context)
        if self.new_password != self.confirm_new_password:
            msg = "Новые пароли не совпадают"
            raise UsersPasswordMismatchError(msg)

        if self.current_password == self.new_password:
            msg = "Новый пароль должен отличаться от текущего"
            raise UsersPasswordValidationError(msg)


class UserAdminUpdate(UserUpdate):
    """Схема обновления пользователя администратором."""

    role: UserRole | None = Field(None, description="Роль пользователя")
    status: UserStatus | None = Field(None, description="Статус пользователя")
    is_active: bool | None = Field(None, description="Активен ли пользователь")
    is_verified: bool | None = Field(None, description="Подтвержден ли email")
    is_superuser: bool | None = Field(None, description="Является ли суперпользователем")


class UserResponse(UserBase):
    """Схема ответа с информацией о пользователе."""

    id: uuid.UUID
    role: UserRole
    status: UserStatus
    is_active: bool
    is_verified: bool
    is_superuser: bool
    last_login_at: datetime | None
    email_verified_at: datetime | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.username

    @property
    def display_name(self) -> str:
        """Отображаемое имя для UI."""
        return self.full_name if (self.first_name or self.last_name) else self.username


class UserPublicResponse(BaseSchema):
    """Публичная схема ответа с информацией о пользователе."""

    id: uuid.UUID
    username: str
    first_name: str | None
    last_name: str | None
    avatar_url: str | None
    created_at: datetime

    @property
    def display_name(self) -> str:
        """Отображаемое имя для UI."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.username


class UserListResponse(BaseSchema):
    """Схема ответа для списка пользователей."""

    users: list[UserResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class UserStatsResponse(BaseSchema):
    """Схема ответа со статистикой пользователя."""

    total_users: int
    active_users: int
    verified_users: int
    new_users_today: int
    new_users_week: int
    new_users_month: int
    users_by_role: dict[str, int]
    users_by_status: dict[str, int]


# Alias для соответствия API роутерам
UserCreateRequest = UserCreate
UserUpdateRequest = UserUpdate
UsersListResponse = UserListResponse


class UserStatusUpdateRequest(BaseSchema):
    """
    Request schema for updating user status.
    """

    status: UserStatus = Field(..., description="New user status")
    reason: str | None = Field(None, max_length=500, description="Reason for status change")


class UserRoleUpdateRequest(BaseSchema):
    """
    Request schema for updating user role.
    """

    role: UserRole = Field(..., description="New user role")
    reason: str | None = Field(None, max_length=500, description="Reason for role change")


class UserFilters(BaseSchema):
    """
    Filters for user list queries.
    """

    search: str | None = None
    role: str | None = None
    status: str | None = None
    is_verified: bool | None = None
    is_active: bool | None = None


__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserPasswordUpdate",
    "UserAdminUpdate",
    "UserResponse",
    "UserPublicResponse",
    "UserListResponse",
    "UserStatsResponse",
    "UserCreateRequest",
    "UserUpdateRequest",
    "UsersListResponse",
    "UserStatusUpdateRequest",
    "UserRoleUpdateRequest",
    "UserFilters",
]
