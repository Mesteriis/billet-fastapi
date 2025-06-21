"""
Схемы валидации для авторизации.
"""

import uuid
from datetime import datetime

# Forward reference для избежания циклических импортов
from typing import TYPE_CHECKING, Any

from pydantic import EmailStr, Field, field_validator

from apps.auth.exceptions import (
    AuthPasswordMismatchError,
    AuthPasswordValidationError,
    AuthTermsAcceptanceError,
    AuthUsernameValidationError,
)
from core.base.models import BaseSchema

if TYPE_CHECKING:
    from apps.users.schemas.user_schemas import UserResponse


class LoginRequest(BaseSchema):
    """Схема запроса авторизации."""

    email_or_username: str = Field(..., description="Email адрес или имя пользователя")
    password: str = Field(..., min_length=1, description="Пароль")
    remember_me: bool = Field(False, description="Запомнить меня (увеличивает срок действия refresh токена)")
    device_info: str | None = Field(None, max_length=500, description="Информация об устройстве")


class RegistrationRequest(BaseSchema):
    """Схема запроса регистрации."""

    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя")
    email: EmailStr = Field(..., description="Email адрес")
    password: str = Field(..., min_length=8, max_length=128, description="Пароль")
    confirm_password: str = Field(..., description="Подтверждение пароля")
    first_name: str | None = Field(None, max_length=100, description="Имя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия")
    accept_terms: bool = Field(..., description="Согласие с условиями использования")
    remember_me: bool = Field(False, description="Запомнить меня (увеличивает срок действия токенов)")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Валидация имени пользователя."""
        if not v.isalnum() and "_" not in v and "-" not in v:
            msg = "Имя пользователя может содержать только буквы, цифры, _ и -"
            raise AuthUsernameValidationError(msg)

        if v.startswith(("_", "-")) or v.endswith(("_", "-")):
            msg = "Имя пользователя не может начинаться или заканчиваться на _ или -"
            raise AuthUsernameValidationError(msg)

        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля."""
        if not any(c.islower() for c in v):
            msg = "Пароль должен содержать хотя бы одну строчную букву"
            raise AuthPasswordValidationError(msg)

        if not any(c.isupper() for c in v):
            msg = "Пароль должен содержать хотя бы одну заглавную букву"
            raise AuthPasswordValidationError(msg)

        if not any(c.isdigit() for c in v):
            msg = "Пароль должен содержать хотя бы одну цифру"
            raise AuthPasswordValidationError(msg)

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            msg = "Пароль должен содержать хотя бы один специальный символ"
            raise AuthPasswordValidationError(msg)

        return v

    @field_validator("accept_terms")
    @classmethod
    def validate_accept_terms(cls, v: bool) -> bool:
        """Валидация согласия с условиями."""
        if not v:
            msg = "Необходимо согласиться с условиями использования"
            raise AuthTermsAcceptanceError(msg)
        return v

    def model_post_init(self, __context: Any) -> None:
        """Валидация после инициализации модели."""
        super().model_post_init(__context)
        if self.password != self.confirm_password:
            msg = "Пароли не совпадают"
            raise AuthPasswordMismatchError(msg)

    def to_user_create(self) -> dict[str, Any]:
        """
        Конвертировать в данные для создания пользователя.

        :return: Словарь с данными для UserCreate
        """
        return {
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "confirm_password": self.confirm_password,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }


class TokenResponse(BaseSchema):
    """Схема ответа с токенами."""

    access_token: str = Field(..., description="Access токен для авторизации")
    refresh_token: str = Field(..., description="Refresh токен для обновления access токена")
    token_type: str = Field("bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время действия access токена в секундах")
    user_id: uuid.UUID = Field(..., description="ID пользователя")


class RefreshTokenRequest(BaseSchema):
    """Схема запроса обновления токена."""

    refresh_token: str = Field(..., description="Refresh токен")


class PasswordResetRequest(BaseSchema):
    """Схема запроса сброса пароля."""

    email: EmailStr = Field(..., description="Email адрес")


class PasswordResetConfirm(BaseSchema):
    """Схема подтверждения сброса пароля."""

    token: str = Field(..., description="Токен сброса пароля")
    new_password: str = Field(..., min_length=8, max_length=128, description="Новый пароль")
    confirm_new_password: str = Field(..., description="Подтверждение нового пароля")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля."""
        if not any(c.islower() for c in v):
            msg = "Пароль должен содержать хотя бы одну строчную букву"
            raise AuthPasswordValidationError(msg)

        if not any(c.isupper() for c in v):
            msg = "Пароль должен содержать хотя бы одну заглавную букву"
            raise AuthPasswordValidationError(msg)

        if not any(c.isdigit() for c in v):
            msg = "Пароль должен содержать хотя бы одну цифру"
            raise AuthPasswordValidationError(msg)

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            msg = "Пароль должен содержать хотя бы один специальный символ"
            raise AuthPasswordValidationError(msg)

        return v

    def model_post_init(self, __context: Any) -> None:
        """Валидация после инициализации модели."""
        super().model_post_init(__context)
        if self.new_password != self.confirm_new_password:
            msg = "Пароли не совпадают"
            raise AuthPasswordMismatchError(msg)


class EmailVerificationRequest(BaseSchema):
    """Схема запроса подтверждения email."""

    token: str = Field(..., description="Токен подтверждения email")
    email: EmailStr = Field(..., description="Email адрес для подтверждения")


class ResendEmailVerificationRequest(BaseSchema):
    """Схема запроса повторной отправки подтверждения email."""

    email: EmailStr = Field(..., description="Email адрес")


class ChangePasswordRequest(BaseSchema):
    """Схема запроса смены пароля."""

    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., min_length=8, max_length=128, description="Новый пароль")
    confirm_new_password: str = Field(..., description="Подтверждение нового пароля")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля."""
        if not any(c.islower() for c in v):
            msg = "Пароль должен содержать хотя бы одну строчную букву"
            raise AuthPasswordValidationError(msg)

        if not any(c.isupper() for c in v):
            msg = "Пароль должен содержать хотя бы одну заглавную букву"
            raise AuthPasswordValidationError(msg)

        if not any(c.isdigit() for c in v):
            msg = "Пароль должен содержать хотя бы одну цифру"
            raise AuthPasswordValidationError(msg)

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            msg = "Пароль должен содержать хотя бы один специальный символ"
            raise AuthPasswordValidationError(msg)

        return v

    def model_post_init(self, __context: Any) -> None:
        """Валидация после инициализации модели."""
        super().model_post_init(__context)
        if self.new_password != self.confirm_new_password:
            msg = "Пароли не совпадают"
            raise AuthPasswordMismatchError(msg)

        if self.current_password == self.new_password:
            msg = "Новый пароль должен отличаться от текущего"
            raise AuthPasswordValidationError(msg)


class LogoutRequest(BaseSchema):
    """Схема запроса выхода."""

    refresh_token: str | None = Field(None, description="Refresh токен для отзыва (опционально)")
    logout_all_devices: bool = Field(False, description="Выйти на всех устройствах")


class AuthResponse(BaseSchema):
    """Схема ответа после успешной авторизации."""

    access_token: str = Field(..., description="Access токен для авторизации")
    refresh_token: str = Field(..., description="Refresh токен для обновления access токена")
    token_type: str = Field("bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время действия access токена в секундах")
    user: "UserResponse" = Field(..., description="Информация о пользователе")
    requires_verification: bool = Field(False, description="Требуется ли подтверждение email")
    csrf_token: str | None = Field(None, description="CSRF токен для защиты сессии")


class SessionResponse(BaseSchema):
    """Схема ответа с информацией о сессии."""

    session_id: str = Field(..., description="ID сессии")
    user_id: uuid.UUID = Field(..., description="ID пользователя")
    expires_at: datetime = Field(..., description="Время истечения сессии")
    ip_address: str | None = Field(None, description="IP адрес")
    user_agent: str | None = Field(None, description="User Agent браузера")
    created_at: datetime = Field(..., description="Время создания сессии")
    last_activity_at: datetime = Field(..., description="Время последней активности")


class ActiveSessionsResponse(BaseSchema):
    """Схема ответа со списком активных сессий."""

    sessions: list[SessionResponse] = Field(..., description="Список активных сессий")
    current_session_id: str = Field(..., description="ID текущей сессии")


__all__ = [
    "LoginRequest",
    "RegistrationRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "EmailVerificationRequest",
    "ResendEmailVerificationRequest",
    "ChangePasswordRequest",
    "LogoutRequest",
    "AuthResponse",
    "SessionResponse",
    "ActiveSessionsResponse",
]
