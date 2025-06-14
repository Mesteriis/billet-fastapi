"""
Доменный слой для управления пользователями.

Содержит бизнес-логику, правила и сущности домена пользователей.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from apps.base.contracts import AlreadyExistsError, DomainException, ValidationException
from apps.base.models import EmailStr, PasswordStr, PhoneStr, UsernameStr
from tools.pydantic import BaseModel


# Доменные объекты-значения
class Email(BaseModel):
    """Объект-значение для email адреса."""
    
    value: EmailStr
    
    def __init__(self, value: str):
        # Валидация email
        if not self._is_valid_email(value):
            raise ValidationException("Invalid email format", field="email")
        super().__init__(value=value)
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Проверка корректности email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def __str__(self) -> str:
        return self.value


class Username(BaseModel):
    """Объект-значение для имени пользователя."""
    
    value: UsernameStr
    
    def __init__(self, value: str):
        # Валидация username
        if not self._is_valid_username(value):
            raise ValidationException(
                "Username must be 3-30 characters, alphanumeric and underscores only", 
                field="username"
            )
        super().__init__(value=value)
    
    @staticmethod
    def _is_valid_username(username: str) -> bool:
        """Проверка корректности username."""
        if len(username) < 3 or len(username) > 30:
            return False
        pattern = r'^[a-zA-Z0-9_]+$'
        return bool(re.match(pattern, username))
    
    def __str__(self) -> str:
        return self.value


class Password(BaseModel):
    """Объект-значение для пароля."""
    
    value: PasswordStr
    
    def __init__(self, value: str):
        # Валидация пароля
        if not self._is_strong_password(value):
            raise ValidationException(
                "Password must be at least 8 characters with uppercase, lowercase, digit and special character",
                field="password"
            )
        super().__init__(value=value)
    
    @staticmethod
    def _is_strong_password(password: str) -> bool:
        """Проверка надежности пароля."""
        if len(password) < 8:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=" for c in password)
        
        return has_upper and has_lower and has_digit and has_special
    
    def __str__(self) -> str:
        return "*" * len(self.value)  # Скрываем пароль


# Доменные сущности
UserRole = Literal["user", "admin", "moderator"]
UserStatus = Literal["active", "inactive", "suspended", "pending_verification"]


class UserDomain(BaseModel):
    """Доменная сущность пользователя."""
    
    id: Annotated[uuid.UUID, "Уникальный идентификатор пользователя"]
    email: Annotated[Email, "Email адрес пользователя"]
    username: Annotated[Username, "Имя пользователя"]
    full_name: Annotated[str, "Полное имя пользователя"]
    
    # Статус и роли
    status: Annotated[UserStatus, "Статус пользователя"] = "pending_verification"
    role: Annotated[UserRole, "Роль пользователя"] = "user"
    
    # Флаги
    is_active: Annotated[bool, "Активен ли пользователь"] = True
    is_verified: Annotated[bool, "Подтвержден ли email"] = False
    is_superuser: Annotated[bool, "Является ли суперпользователем"] = False
    
    # Метаданные
    created_at: Annotated[datetime, "Дата создания"]
    updated_at: Annotated[datetime, "Дата обновления"]
    last_login_at: Annotated[datetime | None, "Дата последнего входа"] = None
    
    # Дополнительные поля
    phone: Annotated[str | None, "Номер телефона"] = None
    avatar_url: Annotated[str | None, "URL аватара"] = None
    bio: Annotated[str | None, "Биография пользователя"] = None
    
    def activate(self) -> None:
        """Активировать пользователя."""
        self.is_active = True
        self.status = "active"
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Деактивировать пользователя."""
        self.is_active = False
        self.status = "inactive"
        self.updated_at = datetime.utcnow()
    
    def suspend(self, reason: str | None = None) -> None:
        """Заблокировать пользователя."""
        self.is_active = False
        self.status = "suspended"
        self.updated_at = datetime.utcnow()
        # TODO: логирование причины блокировки
    
    def verify_email(self) -> None:
        """Подтвердить email пользователя."""
        self.is_verified = True
        if self.status == "pending_verification":
            self.status = "active"
        self.updated_at = datetime.utcnow()
    
    def update_last_login(self) -> None:
        """Обновить время последнего входа."""
        self.last_login_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def change_role(self, new_role: UserRole) -> None:
        """Изменить роль пользователя."""
        if new_role == "admin" and not self.is_verified:
            raise DomainException("Cannot assign admin role to unverified user")
        
        self.role = new_role
        if new_role == "admin":
            self.is_superuser = True
        self.updated_at = datetime.utcnow()
    
    def update_profile(
        self,
        *,
        full_name: str | None = None,
        phone: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None
    ) -> None:
        """Обновить профиль пользователя."""
        if full_name is not None:
            if len(full_name.strip()) < 2:
                raise ValidationException("Full name must be at least 2 characters", field="full_name")
            self.full_name = full_name.strip()
        
        if phone is not None:
            if phone and not self._is_valid_phone(phone):
                raise ValidationException("Invalid phone format", field="phone")
            self.phone = phone
        
        if bio is not None:
            if len(bio) > 500:
                raise ValidationException("Bio must be less than 500 characters", field="bio")
            self.bio = bio
        
        if avatar_url is not None:
            self.avatar_url = avatar_url
        
        self.updated_at = datetime.utcnow()
    
    @staticmethod
    def _is_valid_phone(phone: str) -> bool:
        """Проверка корректности номера телефона."""
        # Простая проверка - можно расширить
        pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone.replace(" ", "").replace("-", "")))
    
    def can_perform_admin_action(self) -> bool:
        """Проверить, может ли пользователь выполнять административные действия."""
        return self.is_active and self.is_verified and (self.is_superuser or self.role == "admin")
    
    def can_moderate_content(self) -> bool:
        """Проверить, может ли пользователь модерировать контент."""
        return (
            self.is_active 
            and self.is_verified 
            and self.role in ("admin", "moderator")
        )


# Доменные события
class UserEvent(BaseModel):
    """Базовое событие пользователя."""
    
    user_id: uuid.UUID
    event_type: str
    timestamp: datetime = datetime.utcnow()
    metadata: dict[str, str] = {}


class UserRegisteredEvent(UserEvent):
    """Событие регистрации пользователя."""
    
    event_type: str = "user_registered"
    email: str
    username: str


class UserVerifiedEvent(UserEvent):
    """Событие подтверждения email."""
    
    event_type: str = "user_verified"


class UserLoginEvent(UserEvent):
    """Событие входа пользователя."""
    
    event_type: str = "user_login"
    ip_address: str | None = None
    user_agent: str | None = None


class UserSuspendedEvent(UserEvent):
    """Событие блокировки пользователя."""
    
    event_type: str = "user_suspended"
    reason: str | None = None
    by_admin_id: uuid.UUID | None = None


# Доменные сервисы
class UserDomainService:
    """Доменный сервис для работы с пользователями."""
    
    @staticmethod
    def can_user_be_promoted(user: UserDomain, target_role: UserRole) -> bool:
        """Проверить, может ли пользователь быть повышен до роли."""
        if not user.is_active or not user.is_verified:
            return False
        
        if target_role == "admin" and user.role != "moderator":
            return False  # Можно стать админом только из модератора
        
        if target_role == "moderator" and user.role != "user":
            return False  # Можно стать модератором только из обычного пользователя
        
        return True
    
    @staticmethod
    def validate_user_for_action(user: UserDomain, action: str) -> None:
        """Валидировать пользователя для выполнения действия."""
        if not user.is_active:
            raise DomainException(f"User is not active, cannot perform {action}")
        
        if action in ("admin_action", "moderate_content") and not user.is_verified:
            raise DomainException(f"User is not verified, cannot perform {action}")
    
    @staticmethod
    def generate_username_suggestions(base_username: str, existing_usernames: list[str]) -> list[str]:
        """Сгенерировать предложения для имени пользователя."""
        suggestions = []
        
        # Очищаем базовое имя
        clean_base = re.sub(r'[^a-zA-Z0-9_]', '', base_username.lower())
        
        if clean_base and clean_base not in existing_usernames:
            suggestions.append(clean_base)
        
        # Добавляем числовые суффиксы
        for i in range(1, 100):
            suggestion = f"{clean_base}{i}"
            if suggestion not in existing_usernames:
                suggestions.append(suggestion)
            
            if len(suggestions) >= 5:
                break
        
        return suggestions 