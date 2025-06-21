"""
Схемы валидации для профилей пользователей.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field, field_validator

from apps.users.exceptions import (
    UsersAgeValidationError,
    UsersDateValidationError,
    UsersPhoneValidationError,
    UsersSchemaValidationError,
)
from apps.users.models.enums import NotificationLevel, UserLanguage, UserTheme
from core.base.models import BaseSchema


class ProfileBase(BaseSchema):
    """Базовая схема профиля пользователя."""

    bio: str | None = Field(None, max_length=1000, description="Биография пользователя")
    phone: str | None = Field(None, max_length=20, description="Номер телефона")
    birth_date: date | None = Field(None, description="Дата рождения")
    location: str | None = Field(None, max_length=255, description="Местоположение")
    website: str | None = Field(None, max_length=500, description="Веб-сайт")
    timezone: str = Field("UTC", max_length=50, description="Временная зона")
    language: UserLanguage = Field(UserLanguage.EN, description="Язык интерфейса")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Валидация номера телефона."""
        if v is not None:
            # Простая валидация телефона
            import re

            phone_pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
            if not phone_pattern.match(v.replace(" ", "").replace("-", "")):
                msg = "Некорректный формат номера телефона"
                raise UsersPhoneValidationError(msg)
        return v

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v: date | None) -> date | None:
        """Валидация даты рождения."""
        if v is not None:
            if v > date.today():
                msg = "Дата рождения не может быть в будущем"
                raise UsersDateValidationError(msg)

            if v.year < 1900:
                msg = "Дата рождения должна быть после 1900 года"
                raise UsersDateValidationError(msg)

        return v

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: str | None) -> str | None:
        """Валидация веб-сайта."""
        if v is None:
            return v

        if not v.startswith(("http://", "https://")):
            msg = "URL веб-сайта должен начинаться с http:// или https://"
            raise UsersSchemaValidationError(msg)

        return v


class ProfileCreate(ProfileBase):
    """Схема создания профиля пользователя."""

    pass


class ProfileUpdate(BaseSchema):
    """Схема обновления профиля пользователя."""

    bio: str | None = Field(None, max_length=1000, description="Биография пользователя")
    phone: str | None = Field(None, max_length=20, description="Номер телефона")
    birth_date: date | None = Field(None, description="Дата рождения")
    location: str | None = Field(None, max_length=255, description="Местоположение")
    website: str | None = Field(None, max_length=500, description="Веб-сайт")
    timezone: str | None = Field(None, max_length=50, description="Временная зона")
    language: UserLanguage | None = Field(None, description="Язык интерфейса")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Валидация номера телефона."""
        if v is not None:
            # Простая валидация телефона
            import re

            phone_pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
            if not phone_pattern.match(v.replace(" ", "").replace("-", "")):
                msg = "Некорректный формат номера телефона"
                raise UsersPhoneValidationError(msg)
        return v

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v: date | None) -> date | None:
        """Валидация даты рождения."""
        if v is not None:
            if v > date.today():
                msg = "Дата рождения не может быть в будущем"
                raise UsersDateValidationError(msg)

            if v.year < 1900:
                msg = "Дата рождения должна быть после 1900 года"
                raise UsersDateValidationError(msg)

        return v

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: str | None) -> str | None:
        """Валидация веб-сайта."""
        if v is None:
            return v

        if not v.startswith(("http://", "https://")):
            msg = "URL веб-сайта должен начинаться с http:// или https://"
            raise UsersSchemaValidationError(msg)

        return v


class ProfileSettingsUpdate(BaseSchema):
    """Схема обновления настроек профиля."""

    theme: UserTheme | None = Field(None, description="Тема интерфейса")
    notifications_enabled: bool | None = Field(None, description="Включены ли уведомления")
    notification_level: NotificationLevel | None = Field(None, description="Уровень уведомлений")
    email_notifications: bool | None = Field(None, description="Email уведомления")
    push_notifications: bool | None = Field(None, description="Push уведомления")
    public_profile: bool | None = Field(None, description="Публичный ли профиль")
    show_email: bool | None = Field(None, description="Показывать ли email в профиле")
    show_phone: bool | None = Field(None, description="Показывать ли телефон в профиле")


class ProfileResponse(ProfileBase):
    """Схема ответа с информацией о профиле."""

    id: uuid.UUID
    user_id: uuid.UUID
    theme: UserTheme
    notifications_enabled: bool
    notification_level: NotificationLevel
    email_notifications: bool
    push_notifications: bool
    public_profile: bool
    show_email: bool
    show_phone: bool
    created_at: datetime
    updated_at: datetime

    @property
    def age(self) -> int | None:
        """Возраст пользователя."""
        if not self.birth_date:
            return None

        from datetime import date

        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )

    def get_notification_settings(self) -> dict[str, Any]:
        """Получить настройки уведомлений."""
        return {
            "enabled": self.notifications_enabled,
            "email": self.email_notifications,
            "push": self.push_notifications,
            "level": self.notification_level.value,
        }

    def get_privacy_settings(self) -> dict[str, bool]:
        """Получить настройки приватности."""
        return {
            "public_profile": self.public_profile,
            "show_email": self.show_email,
            "show_phone": self.show_phone,
        }


class ProfilePublicResponse(BaseSchema):
    """Публичная схема ответа с информацией о профиле."""

    id: uuid.UUID
    user_id: uuid.UUID
    bio: str | None
    location: str | None
    website: str | None
    created_at: datetime

    # Показываем только если пользователь разрешил
    phone: str | None = None

    @property
    def age(self) -> int | None:
        """Возраст пользователя (если дата рождения публична)."""
        # В публичном профиле возраст не показываем для приватности
        return None


# Alias для соответствия API роутерам
ProfileUpdateRequest = ProfileUpdate


class ProfilesListResponse(BaseSchema):
    """
    Response schema for profiles list with pagination.
    """

    profiles: list[ProfileResponse]
    total: int
    page: int
    pages: int
    size: int


class ProfileSearchFilters(BaseSchema):
    """
    Filters for profile search queries.
    """

    search: str | None = None
    location: str | None = None
    is_public: bool | None = None


__all__ = [
    "ProfileBase",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileSettingsUpdate",
    "ProfileResponse",
    "ProfilePublicResponse",
    "ProfileUpdateRequest",
    "ProfilesListResponse",
    "ProfileSearchFilters",
]
