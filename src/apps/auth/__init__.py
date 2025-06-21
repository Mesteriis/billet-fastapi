"""
Приложение авторизации.

Содержит модели, схемы, репозитории и сервисы для работы с JWT токенами,
orbital токенами, сессиями и авторизацией пользователей.
"""

from . import depends, models, repo, schemas, services
from .interfaces import (  # Type aliases
    AuthAttempt,
    AuthenticationAttempt,
    AuthenticationResult,
    AuthResult,
    EmailVerificationRequest,
    OrbitalToken,
    OrbitalTokenData,
    PasswordResetRequest,
    RefreshToken,
    RefreshTokenData,
    SecurityEvent,
    SecurityLog,
    Session,
    SessionData,
    TokenData,
    TokenPayload,
    TwoFA,
    TwoFactorAuth,
)

__all__ = [
    "depends",
    "models",
    "schemas",
    "repo",
    "services",
    # Interfaces
    "TokenPayload",
    "RefreshTokenData",
    "SessionData",
    "OrbitalTokenData",
    "AuthenticationResult",
    "AuthenticationAttempt",
    "PasswordResetRequest",
    "EmailVerificationRequest",
    "SecurityEvent",
    "TwoFactorAuth",
    # Type aliases
    "TokenData",
    "RefreshToken",
    "Session",
    "OrbitalToken",
    "AuthResult",
    "AuthAttempt",
    "SecurityLog",
    "TwoFA",
]
