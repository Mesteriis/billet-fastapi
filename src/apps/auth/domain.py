"""
Доменный слой для аутентификации и авторизации.

Содержит бизнес-логику работы с токенами, сессиями и правами доступа.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Annotated, Literal

from apps.base.contracts import DomainException, UnauthorizedError, ValidationException
from apps.base.models import TokenStr
from tools.pydantic import BaseModel


# Доменные объекты-значения
class JWTToken(BaseModel):
    """Объект-значение для JWT токена."""
    
    value: TokenStr
    token_type: Literal["access", "refresh"]
    expires_at: datetime
    user_id: uuid.UUID
    jti: str  # JWT ID для отзыва
    
    def is_expired(self) -> bool:
        """Проверить, истек ли токен."""
        return datetime.utcnow() >= self.expires_at
    
    def expires_in_seconds(self) -> int:
        """Получить время до истечения в секундах."""
        if self.is_expired():
            return 0
        return int((self.expires_at - datetime.utcnow()).total_seconds())
    
    def expires_in_minutes(self) -> int:
        """Получить время до истечения в минутах."""
        return self.expires_in_seconds() // 60


class TokenPair(BaseModel):
    """Пара токенов: access и refresh."""
    
    access_token: JWTToken
    refresh_token: JWTToken
    
    def to_response_dict(self) -> dict[str, str | int]:
        """Преобразовать в словарь для HTTP ответа."""
        return {
            "access_token": self.access_token.value,
            "refresh_token": self.refresh_token.value,
            "token_type": "bearer",
            "expires_in": self.access_token.expires_in_seconds(),
        }


# Доменные сущности
SessionStatus = Literal["active", "expired", "revoked", "invalid"]
DeviceType = Literal["web", "mobile", "desktop", "api"]


class UserSession(BaseModel):
    """Доменная сущность пользовательской сессии."""
    
    id: Annotated[uuid.UUID, "Уникальный идентификатор сессии"]
    user_id: Annotated[uuid.UUID, "ID пользователя"]
    refresh_token_jti: Annotated[str, "JWT ID refresh токена"]
    
    # Метаданные устройства и сессии
    device_type: Annotated[DeviceType, "Тип устройства"] = "web"
    device_name: Annotated[str | None, "Название устройства"] = None
    ip_address: Annotated[str | None, "IP адрес"] = None
    user_agent: Annotated[str | None, "User Agent"] = None
    location: Annotated[str | None, "Географическое местоположение"] = None
    
    # Статус и время
    status: Annotated[SessionStatus, "Статус сессии"] = "active"
    created_at: Annotated[datetime, "Время создания сессии"]
    expires_at: Annotated[datetime, "Время истечения сессии"]
    last_activity_at: Annotated[datetime, "Время последней активности"]
    revoked_at: Annotated[datetime | None, "Время отзыва сессии"] = None
    
    def is_active(self) -> bool:
        """Проверить, активна ли сессия."""
        return (
            self.status == "active" 
            and not self.is_expired() 
            and self.revoked_at is None
        )
    
    def is_expired(self) -> bool:
        """Проверить, истекла ли сессия."""
        return datetime.utcnow() >= self.expires_at
    
    def revoke(self, reason: str = "user_logout") -> None:
        """Отозвать сессию."""
        self.status = "revoked"
        self.revoked_at = datetime.utcnow()
    
    def update_activity(self) -> None:
        """Обновить время последней активности."""
        self.last_activity_at = datetime.utcnow()
    
    def extend_expiry(self, extend_by: timedelta) -> None:
        """Продлить время жизни сессии."""
        if self.is_active():
            self.expires_at += extend_by
    
    def is_suspicious(self) -> bool:
        """Проверить, подозрительна ли сессия."""
        # Сессия подозрительна если:
        # 1. Нет активности более 24 часов
        # 2. Смена IP адреса (требует дополнительных данных)
        
        if self.last_activity_at:
            inactive_hours = (datetime.utcnow() - self.last_activity_at).total_seconds() / 3600
            return inactive_hours > 24
        
        return False


# Доменные события
class AuthEvent(BaseModel):
    """Базовое событие аутентификации."""
    
    user_id: uuid.UUID
    session_id: uuid.UUID | None = None
    event_type: str
    timestamp: datetime = datetime.utcnow()
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, str] = {}


class LoginSuccessEvent(AuthEvent):
    """Событие успешного входа."""
    
    event_type: str = "login_success"
    login_method: str = "email_password"


class LoginFailedEvent(AuthEvent):
    """Событие неудачного входа."""
    
    event_type: str = "login_failed"
    failure_reason: str
    email_attempted: str | None = None


class TokenRefreshedEvent(AuthEvent):
    """Событие обновления токена."""
    
    event_type: str = "token_refreshed"


class LogoutEvent(AuthEvent):
    """Событие выхода из системы."""
    
    event_type: str = "logout"
    logout_type: str = "user_initiated"  # user_initiated, expired, revoked, admin


class SuspiciousActivityEvent(AuthEvent):
    """Событие подозрительной активности."""
    
    event_type: str = "suspicious_activity"
    activity_type: str
    risk_level: Literal["low", "medium", "high"] = "medium"


# Доменные сервисы
class AuthDomainService:
    """Доменный сервис для бизнес-логики аутентификации."""
    
    @staticmethod
    def validate_login_attempt(
        email: str, 
        password: str, 
        failed_attempts: int = 0,
        last_failed_at: datetime | None = None
    ) -> None:
        """Валидировать попытку входа."""
        # Проверка блокировки после множественных неудачных попыток
        if failed_attempts >= 5:
            if last_failed_at:
                lockout_period = timedelta(minutes=15)
                if datetime.utcnow() - last_failed_at < lockout_period:
                    raise UnauthorizedError("Account temporarily locked due to multiple failed attempts")
        
        # Базовая валидация
        if not email or not password:
            raise ValidationException("Email and password are required")
        
        if len(password) < 1:  # Минимальная проверка для попытки входа
            raise ValidationException("Password cannot be empty")
    
    @staticmethod
    def calculate_session_expiry(device_type: DeviceType, remember_me: bool = False) -> datetime:
        """Рассчитать время истечения сессии."""
        base_expiry = {
            "web": timedelta(hours=8),
            "mobile": timedelta(days=30),
            "desktop": timedelta(days=7),
            "api": timedelta(hours=1),
        }
        
        expiry_delta = base_expiry.get(device_type, timedelta(hours=8))
        
        # Если пользователь выбрал "запомнить меня"
        if remember_me and device_type in ("web", "desktop"):
            expiry_delta = timedelta(days=30)
        
        return datetime.utcnow() + expiry_delta
    
    @staticmethod
    def should_require_2fa(
        user_has_2fa: bool,
        device_type: DeviceType,
        is_new_device: bool = False,
        is_suspicious_location: bool = False
    ) -> bool:
        """Определить, требуется ли двухфакторная аутентификация."""
        if not user_has_2fa:
            return False
        
        # Всегда требуем 2FA для API доступа
        if device_type == "api":
            return True
        
        # Требуем 2FA для новых устройств или подозрительных локаций
        if is_new_device or is_suspicious_location:
            return True
        
        # Для мобильных приложений 2FA менее строгая
        if device_type == "mobile":
            return is_new_device
        
        return True
    
    @staticmethod
    def detect_session_anomalies(
        current_session: UserSession,
        recent_sessions: list[UserSession]
    ) -> list[str]:
        """Обнаружить аномалии в сессии."""
        anomalies = []
        
        # Проверка на множественные активные сессии
        active_sessions = [s for s in recent_sessions if s.is_active()]
        if len(active_sessions) > 5:
            anomalies.append("too_many_active_sessions")
        
        # Проверка на быструю смену IP адресов
        if current_session.ip_address:
            recent_ips = [s.ip_address for s in recent_sessions[-3:] if s.ip_address]
            unique_ips = set(recent_ips)
            if len(unique_ips) > 2:
                anomalies.append("rapid_ip_change")
        
        # Проверка на подозрительное время активности
        if current_session.is_suspicious():
            anomalies.append("long_inactivity")
        
        return anomalies
    
    @staticmethod
    def calculate_token_expiry(token_type: Literal["access", "refresh"]) -> datetime:
        """Рассчитать время истечения токена."""
        if token_type == "access":
            return datetime.utcnow() + timedelta(minutes=30)
        elif token_type == "refresh":
            return datetime.utcnow() + timedelta(days=30)
        else:
            raise ValueError(f"Unknown token type: {token_type}")
    
    @staticmethod
    def validate_token_refresh(
        refresh_token: JWTToken,
        session: UserSession
    ) -> None:
        """Валидировать возможность обновления токена."""
        if refresh_token.is_expired():
            raise UnauthorizedError("Refresh token has expired")
        
        if not session.is_active():
            raise UnauthorizedError("Session is not active")
        
        if session.refresh_token_jti != refresh_token.jti:
            raise UnauthorizedError("Token does not match session")


class PasswordDomainService:
    """Доменный сервис для работы с паролями."""
    
    @staticmethod
    def validate_password_strength(password: str) -> dict[str, bool]:
        """Проверить надежность пароля и вернуть детальную информацию."""
        checks = {
            "min_length": len(password) >= 8,
            "has_uppercase": any(c.isupper() for c in password),
            "has_lowercase": any(c.islower() for c in password),
            "has_digit": any(c.isdigit() for c in password),
            "has_special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password),
            "not_common": not PasswordDomainService._is_common_password(password),
            "no_sequential": not PasswordDomainService._has_sequential_chars(password),
        }
        
        checks["is_strong"] = all(checks.values())
        
        return checks
    
    @staticmethod
    def _is_common_password(password: str) -> bool:
        """Проверить, является ли пароль часто используемым."""
        common_passwords = {
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "dragon", "master"
        }
        return password.lower() in common_passwords
    
    @staticmethod
    def _has_sequential_chars(password: str) -> bool:
        """Проверить наличие последовательных символов."""
        for i in range(len(password) - 2):
            if (ord(password[i]) + 1 == ord(password[i + 1]) and 
                ord(password[i + 1]) + 1 == ord(password[i + 2])):
                return True
        return False
    
    @staticmethod
    def generate_password_requirements_message(checks: dict[str, bool]) -> str:
        """Сгенерировать сообщение о требованиях к паролю."""
        requirements = []
        
        if not checks["min_length"]:
            requirements.append("минимум 8 символов")
        if not checks["has_uppercase"]:
            requirements.append("заглавная буква")
        if not checks["has_lowercase"]:
            requirements.append("строчная буква")
        if not checks["has_digit"]:
            requirements.append("цифра")
        if not checks["has_special"]:
            requirements.append("специальный символ")
        if not checks["not_common"]:
            requirements.append("не должен быть часто используемым")
        if not checks["no_sequential"]:
            requirements.append("не должен содержать последовательные символы")
        
        if not requirements:
            return "Пароль соответствует всем требованиям"
        
        return f"Пароль должен содержать: {', '.join(requirements)}" 