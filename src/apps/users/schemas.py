"""
Pydantic схемы для пользователей.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from core.base.models import BaseSchema


class UserBase(BaseSchema):
    """Базовая схема пользователя."""

    email: EmailStr = Field(..., description="Email пользователя")
    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя")
    full_name: str | None = Field(None, max_length=255, description="Полное имя")
    avatar_url: str | None = Field(None, description="URL аватара")
    bio: str | None = Field(None, max_length=1000, description="Биография")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Валидация имени пользователя."""
        if not v.isalnum():
            raise ValueError("Имя пользователя должно содержать только буквы и цифры")
        return v.lower()


class UserCreate(UserBase):
    """Схема для создания пользователя."""

    password: str = Field(..., min_length=8, description="Пароль")
    password_confirm: str = Field(..., description="Подтверждение пароля")

    @field_validator("password_confirm")
    @classmethod
    def validate_password_confirm(cls, v: str, info) -> str:
        """Валидация подтверждения пароля."""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Пароли не совпадают")
        return v


class UserUpdate(BaseSchema):
    """Схема для обновления пользователя."""

    email: EmailStr | None = Field(None, description="Email пользователя")
    username: str | None = Field(None, min_length=3, max_length=50, description="Имя пользователя")
    full_name: str | None = Field(None, max_length=255, description="Полное имя")
    avatar_url: str | None = Field(None, description="URL аватара")
    bio: str | None = Field(None, max_length=1000, description="Биография")
    is_active: bool | None = Field(None, description="Активность пользователя")
    is_verified: bool | None = Field(None, description="Верификация пользователя")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """Валидация имени пользователя."""
        if v and not v.isalnum():
            raise ValueError("Имя пользователя должно содержать только буквы и цифры")
        return v.lower() if v else v


class UserResponse(UserBase):
    """Схема для ответа с данными пользователя."""

    is_active: bool = Field(..., description="Активность пользователя")
    is_superuser: bool = Field(..., description="Суперпользователь")
    is_verified: bool = Field(..., description="Верификация пользователя")
    last_login_at: datetime | None = Field(None, description="Время последнего входа")
    email_verified_at: datetime | None = Field(None, description="Время верификации email")


class UserLogin(BaseSchema):
    """Схема для входа пользователя."""

    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")


class UserPasswordChange(BaseSchema):
    """Схема для смены пароля."""

    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., min_length=8, description="Новый пароль")
    new_password_confirm: str = Field(..., description="Подтверждение нового пароля")

    @field_validator("new_password_confirm")
    @classmethod
    def validate_password_confirm(cls, v: str, info) -> str:
        """Валидация подтверждения нового пароля."""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Пароли не совпадают")
        return v


class UserEmailVerification(BaseSchema):
    """Схема для верификации email."""

    token: str = Field(..., description="Токен верификации")


class UserPasswordReset(BaseSchema):
    """Схема для сброса пароля."""

    email: EmailStr = Field(..., description="Email пользователя")


class UserPasswordResetConfirm(BaseSchema):
    """Схема для подтверждения сброса пароля."""

    token: str = Field(..., description="Токен сброса пароля")
    new_password: str = Field(..., min_length=8, description="Новый пароль")
    new_password_confirm: str = Field(..., description="Подтверждение нового пароля")

    @field_validator("new_password_confirm")
    @classmethod
    def validate_password_confirm(cls, v: str, info) -> str:
        """Валидация подтверждения нового пароля."""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Пароли не совпадают")
        return v
