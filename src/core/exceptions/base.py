"""
Base exceptions for layered architecture.

This module defines the foundational exception classes for each architectural layer:
- API layer (HTTP-related exceptions)
- Service layer (business logic exceptions)
- Repository layer (data access exceptions)
- Depends layer (dependency injection exceptions)

Each layer has a base exception class that should be inherited by app-specific exceptions.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """
    Base exception for API layer.

    Inherits from FastAPI's HTTPException to provide HTTP status codes and details.
    All API layer exceptions should inherit from this class.

    Args:
        detail: Error message for the user
        status_code: HTTP status code (default: 500)
        headers: Optional HTTP headers

    Example:
        class UserNotFoundError(BaseAPIException):
            def __init__(self, user_id: str):
                super().__init__(
                    detail=f"User with ID {user_id} not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.timestamp = datetime.utcnow()
        self.error_id = str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring."""
        return {
            "error_id": self.error_id,
            "error_type": self.__class__.__name__,
            "detail": self.detail,
            "status_code": self.status_code,
            "timestamp": self.timestamp.isoformat(),
            "layer": "api",
        }


class BaseServiceException(Exception):
    """
    Base exception for Service layer.

    Service layer handles business logic and should not directly expose HTTP details.
    These exceptions are typically caught and converted to API exceptions.

    Args:
        message: Error message describing the business logic failure
        error_code: Optional error code for programmatic handling
        context: Optional context data for debugging

    Example:
        class EmailAlreadyExistsError(BaseServiceException):
            def __init__(self, email: str):
                super().__init__(
                    message=f"Email {email} is already registered",
                    error_code="EMAIL_EXISTS"
                )
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.error_id = str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring."""
        return {
            "error_id": self.error_id,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "layer": "service",
        }


class BaseRepoException(Exception):
    """
    Base exception for Repository layer.

    Repository layer handles data access and database operations.
    These exceptions typically indicate database errors, connection issues, or data integrity problems.

    Args:
        message: Error message describing the database/data access failure
        operation: The operation that failed (create, read, update, delete)
        table: Optional table/collection name where error occurred
        context: Optional context data for debugging

    Example:
        class UserCreateError(BaseRepoException):
            def __init__(self, user_data: dict):
                super().__init__(
                    message="Failed to create user in database",
                    operation="create",
                    table="users",
                    context={"user_data": user_data}
                )
    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        table: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.table = table
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.error_id = str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring."""
        return {
            "error_id": self.error_id,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "operation": self.operation,
            "table": self.table,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "layer": "repository",
        }


class BaseDependsException(Exception):
    """
    Base exception for Depends layer.

    Depends layer handles dependency injection and validation.
    These exceptions typically indicate dependency resolution failures, validation errors, or access control issues.

    Args:
        message: Error message describing the dependency failure
        dependency_name: Name of the dependency that failed
        context: Optional context data for debugging

    Example:
        class TokenValidationError(BaseDependsException):
            def __init__(self, token: str):
                super().__init__(
                    message="Invalid or expired token",
                    dependency_name="current_user",
                    context={"token_length": len(token)}
                )
    """

    def __init__(
        self,
        message: str,
        dependency_name: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.dependency_name = dependency_name
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.error_id = str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring."""
        return {
            "error_id": self.error_id,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "dependency_name": self.dependency_name,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "layer": "depends",
        }


# ============================================================================
# CORE APPLICATION EXCEPTIONS
# ============================================================================


class CoreAppException(Exception):
    """
    Parent exception for all Core application exceptions.

    This allows catching any Core-related error:
    try:
        # core operations
    except CoreAppException as e:
        # Handle any core-related error
    """

    pass


class CoreAPIException(BaseAPIException, CoreAppException):
    """Base exception for Core API layer"""

    pass


class CoreServiceException(BaseServiceException, CoreAppException):
    """Base exception for Core Service layer"""

    pass


class CoreRepoException(BaseRepoException, CoreAppException):
    """Base exception for Core Repository layer"""

    pass


class CoreDependsException(BaseDependsException, CoreAppException):
    """Base exception for Core Depends layer"""

    pass


# ============================================================================
# SPECIALIZED CORE EXCEPTIONS
# ============================================================================


class CoreConfigurationError(CoreServiceException):
    """Core configuration error"""

    def __init__(self, config_key: str, message: str | None = None):
        message = message or f"Configuration error for key: {config_key}"
        super().__init__(message=message, error_code="CONFIG_ERROR", context={"config_key": config_key})


class CoreDatabaseConnectionError(CoreRepoException):
    """Core database connection error"""

    def __init__(self, database_url: str | None = None):
        super().__init__(
            message="Failed to connect to database", operation="connect", context={"database_url": database_url}
        )


class CoreCacheError(CoreRepoException):
    """Core cache system error"""

    def __init__(self, cache_key: str, operation: str):
        super().__init__(
            message=f"Cache {operation} failed for key: {cache_key}",
            operation=operation,
            context={"cache_key": cache_key},
        )


class CoreValidationError(CoreDependsException):
    """Core validation error"""

    def __init__(self, field: str, value: Any, message: str | None = None):
        message = message or f"Validation failed for field: {field}"
        super().__init__(message=message, dependency_name="validation", context={"field": field, "value": str(value)})
