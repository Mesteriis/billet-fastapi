"""
Схемы валидации приложения авторизации.
"""

from .auth_schemas import (
    ActiveSessionsResponse,
    AuthResponse,
    ChangePasswordRequest,
    EmailVerificationRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegistrationRequest,
    ResendEmailVerificationRequest,
    SessionResponse,
    TokenResponse,
)
from .token_schemas import (
    ActiveTokensResponse,
    JWTPayload,
    OrbitalTokenPayload,
    OrbitalTokenType,
    RefreshTokenPayload,
    RevokeTokenRequest,
    RevokeTokenResponse,
    TokenInfo,
    TokenValidationResult,
)

__all__ = [
    # Auth schemas
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
    # Token schemas
    "JWTPayload",
    "RefreshTokenPayload",
    "OrbitalTokenPayload",
    "OrbitalTokenType",
    "TokenValidationResult",
    "TokenInfo",
    "ActiveTokensResponse",
    "RevokeTokenRequest",
    "RevokeTokenResponse",
]
