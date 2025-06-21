"""
Auth application exceptions.

This module defines all exceptions for the Auth application following
the three-level hierarchy: App -> Layer -> Specific.

All Auth exceptions inherit from AuthAppException to enable catching
any auth-related error through a single parent class.
"""

from fastapi import status

from core.exceptions.base import BaseAPIException, BaseDependsException, BaseRepoException, BaseServiceException

# ============================================================================
# PARENT EXCEPTION FOR ALL AUTH APPLICATION EXCEPTIONS
# ============================================================================


class AuthAppException(Exception):
    """
    Parent exception for all Auth application exceptions.

    This allows catching any auth-related error through a single class:

    Example:
        try:
            # Any auth operations
            await auth_service.login(credentials)
            await session_service.create_session(user)
        except AuthAppException as e:
            logger.error(f"Auth application error: {e}")
            await notify_developers("Auth app error", str(e))
    """

    pass


# ============================================================================
# BASE LAYER EXCEPTIONS FOR AUTH APPLICATION
# ============================================================================


class AuthAPIException(BaseAPIException, AuthAppException):
    """Base exception for Auth API layer."""

    pass


class AuthServiceException(BaseServiceException, AuthAppException):
    """Base exception for Auth Service layer."""

    pass


class AuthRepoException(BaseRepoException, AuthAppException):
    """Base exception for Auth Repository layer."""

    pass


class AuthDependsException(BaseDependsException, AuthAppException):
    """Base exception for Auth Depends layer."""

    pass


# ============================================================================
# SPECIALIZED API LAYER EXCEPTIONS
# ============================================================================


class AuthRegistrationAPIException(AuthAPIException):
    """User registration failed."""

    def __init__(self, detail: str = "Registration failed"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class AuthLoginAPIException(AuthAPIException):
    """User login failed."""

    def __init__(self, detail: str = "Login failed"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthInvalidCredentialsAPIException(AuthAPIException):
    """Invalid login credentials."""

    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthTokenExpiredAPIException(AuthAPIException):
    """Authentication token has expired."""

    def __init__(self, detail: str = "Token has expired"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthTokenInvalidAPIException(AuthAPIException):
    """Authentication token is invalid."""

    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthEmailVerificationAPIException(AuthAPIException):
    """Email verification failed."""

    def __init__(self, detail: str = "Email verification failed"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class AuthPasswordResetAPIException(AuthAPIException):
    """Password reset failed."""

    def __init__(self, detail: str = "Password reset failed"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class AuthSessionNotFoundAPIException(AuthAPIException):
    """User session not found."""

    def __init__(self, detail: str = "Session not found"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class AuthSessionRevokeAPIException(AuthAPIException):
    """Failed to revoke session."""

    def __init__(self, detail: str = "Failed to revoke session"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# BACKWARD COMPATIBILITY ALIASES (FOR MIGRATION)
# ============================================================================

# These aliases provide backward compatibility during migration
AuthRegistrationError = AuthRegistrationAPIException
AuthLoginError = AuthLoginAPIException
AuthInvalidCredentialsError = AuthInvalidCredentialsAPIException
AuthTokenExpiredError = AuthTokenExpiredAPIException
AuthTokenInvalidError = AuthTokenInvalidAPIException
AuthEmailVerificationError = AuthEmailVerificationAPIException
AuthPasswordResetError = AuthPasswordResetAPIException
AuthSessionNotFoundError = AuthSessionNotFoundAPIException
AuthSessionRevokeError = AuthSessionRevokeAPIException


# ============================================================================
# SPECIALIZED SERVICE LAYER EXCEPTIONS
# ============================================================================


class JWTServiceError(AuthServiceException):
    """Base JWT service error."""

    def __init__(self, message: str, error_code: str = "JWT_ERROR"):
        super().__init__(message=message, error_code=error_code)


class JWTTokenGenerationError(JWTServiceError):
    """Failed to generate JWT token."""

    def __init__(self, message: str = "Failed to generate JWT token"):
        super().__init__(message=message, error_code="JWT_GENERATION_ERROR")


class JWTTokenValidationError(JWTServiceError):
    """JWT token validation failed."""

    def __init__(self, message: str = "JWT token validation failed"):
        super().__init__(message=message, error_code="JWT_VALIDATION_ERROR")


class JWTTokenExpiredError(JWTServiceError):
    """JWT token has expired."""

    def __init__(self, message: str = "JWT token has expired"):
        super().__init__(message=message, error_code="JWT_EXPIRED")


class SessionServiceError(AuthServiceException):
    """Base session service error."""

    def __init__(self, message: str, error_code: str = "SESSION_ERROR"):
        super().__init__(message=message, error_code=error_code)


class SessionCreationError(SessionServiceError):
    """Failed to create user session."""

    def __init__(self, message: str = "Failed to create session"):
        super().__init__(message=message, error_code="SESSION_CREATION_ERROR")


class SessionValidationError(SessionServiceError):
    """Session validation failed."""

    def __init__(self, message: str = "Session validation failed"):
        super().__init__(message=message, error_code="SESSION_VALIDATION_ERROR")


class SessionExpiredError(SessionServiceError):
    """Session has expired."""

    def __init__(self, message: str = "Session has expired"):
        super().__init__(message=message, error_code="SESSION_EXPIRED")


class SessionNotFoundError(SessionServiceError):
    """Session not found."""

    def __init__(self, message: str = "Session not found"):
        super().__init__(message=message, error_code="SESSION_NOT_FOUND")


class OrbitalServiceError(AuthServiceException):
    """Base orbital service error."""

    def __init__(self, message: str, error_code: str = "ORBITAL_ERROR"):
        super().__init__(message=message, error_code=error_code)


class OrbitalTokenCreationError(OrbitalServiceError):
    """Failed to create orbital token."""

    def __init__(self, message: str = "Failed to create orbital token"):
        super().__init__(message=message, error_code="ORBITAL_TOKEN_CREATION_ERROR")


class OrbitalTokenValidationError(OrbitalServiceError):
    """Orbital token validation failed."""

    def __init__(self, message: str = "Orbital token validation failed"):
        super().__init__(message=message, error_code="ORBITAL_TOKEN_VALIDATION_ERROR")


# ============================================================================
# SPECIALIZED REPOSITORY LAYER EXCEPTIONS
# ============================================================================


class RefreshTokenRepoError(AuthRepoException):
    """Refresh token repository error."""

    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(message=message, operation=operation, table="refresh_tokens")


class RefreshTokenCreateError(RefreshTokenRepoError):
    """Failed to create refresh token."""

    def __init__(self, message: str = "Failed to create refresh token"):
        super().__init__(message=message, operation="create")


class RefreshTokenUpdateError(RefreshTokenRepoError):
    """Failed to update refresh token."""

    def __init__(self, message: str = "Failed to update refresh token"):
        super().__init__(message=message, operation="update")


class RefreshTokenDeleteError(RefreshTokenRepoError):
    """Failed to delete refresh token."""

    def __init__(self, message: str = "Failed to delete refresh token"):
        super().__init__(message=message, operation="delete")


class UserSessionRepoError(AuthRepoException):
    """User session repository error."""

    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(message=message, operation=operation, table="user_sessions")


class UserSessionCreateError(UserSessionRepoError):
    """Failed to create user session."""

    def __init__(self, message: str = "Failed to create user session"):
        super().__init__(message=message, operation="create")


class UserSessionUpdateError(UserSessionRepoError):
    """Failed to update user session."""

    def __init__(self, message: str = "Failed to update user session"):
        super().__init__(message=message, operation="update")


class UserSessionDeleteError(UserSessionRepoError):
    """Failed to delete user session."""

    def __init__(self, message: str = "Failed to delete user session"):
        super().__init__(message=message, operation="delete")


class OrbitalTokenRepoError(AuthRepoException):
    """Orbital token repository error."""

    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(message=message, operation=operation, table="orbital_tokens")


class OrbitalTokenCreateError(OrbitalTokenRepoError):
    """Failed to create orbital token."""

    def __init__(self, message: str = "Failed to create orbital token"):
        super().__init__(message=message, operation="create")


class OrbitalTokenUpdateError(OrbitalTokenRepoError):
    """Failed to update orbital token."""

    def __init__(self, message: str = "Failed to update orbital token"):
        super().__init__(message=message, operation="update")


class OrbitalTokenDeleteError(OrbitalTokenRepoError):
    """Failed to delete orbital token."""

    def __init__(self, message: str = "Failed to delete orbital token"):
        super().__init__(message=message, operation="delete")


# ============================================================================
# SPECIALIZED DEPENDS LAYER EXCEPTIONS
# ============================================================================


class AuthTokenValidationError(AuthDependsException):
    """Authentication token validation failed in dependency."""

    def __init__(self, message: str = "Token validation failed"):
        super().__init__(message=message, dependency_name="auth_token_validation")


class AuthSessionValidationError(AuthDependsException):
    """Session validation failed in dependency."""

    def __init__(self, message: str = "Session validation failed"):
        super().__init__(message=message, dependency_name="auth_session_validation")


class AuthCSRFValidationError(AuthDependsException):
    """CSRF token validation failed in dependency."""

    def __init__(self, message: str = "CSRF token validation failed"):
        super().__init__(message=message, dependency_name="csrf_validation")


class AuthUserNotFoundError(AuthDependsException):
    """User not found in authentication dependency."""

    def __init__(self, message: str = "User not found"):
        super().__init__(message=message, dependency_name="current_user")


class AuthUserInactiveError(AuthDependsException):
    """User is inactive in authentication dependency."""

    def __init__(self, message: str = "User account is inactive"):
        super().__init__(message=message, dependency_name="current_user")


class AuthUserNotVerifiedError(AuthDependsException):
    """User is not verified in authentication dependency."""

    def __init__(self, message: str = "User account is not verified"):
        super().__init__(message=message, dependency_name="current_user")


class AuthInsufficientPermissionsError(AuthDependsException):
    """User has insufficient permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, dependency_name="permission_check")


# ============================================================================
# SPECIALIZED SCHEMA VALIDATION EXCEPTIONS
# ============================================================================


class AuthSchemaValidationError(AuthServiceException):
    """Base schema validation error for Auth schemas."""

    def __init__(self, message: str, field_name: str | None = None):
        super().__init__(message=message, error_code="SCHEMA_VALIDATION_ERROR")
        self.field_name = field_name


class AuthUsernameValidationError(AuthSchemaValidationError):
    """Username validation failed in schema."""

    def __init__(self, message: str = "Invalid username format"):
        super().__init__(message=message, field_name="username")


class AuthPasswordValidationError(AuthSchemaValidationError):
    """Password validation failed in schema."""

    def __init__(self, message: str = "Invalid password format"):
        super().__init__(message=message, field_name="password")


class AuthPasswordMismatchError(AuthSchemaValidationError):
    """Password confirmation does not match."""

    def __init__(self, message: str = "Passwords do not match"):
        super().__init__(message=message, field_name="confirm_password")


class AuthTermsAcceptanceError(AuthSchemaValidationError):
    """Terms of service not accepted."""

    def __init__(self, message: str = "Terms of service must be accepted"):
        super().__init__(message=message, field_name="accept_terms")
