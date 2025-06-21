"""
Core exceptions system for layered architecture.

This module provides a comprehensive exception hierarchy for FastAPI applications
with strict layer isolation and structured error handling.

Architecture:
- Base exceptions for each layer (API, Service, Repository, Depends)
- App-specific exceptions inheriting from base + app parent
- Specialized exceptions for specific error cases
- Global exception handlers and middleware
- Developer notification system for critical errors

Usage:
    from core.exceptions import BaseAPIException, BaseServiceException
    from apps.auth.exceptions import AuthAppException, AuthLoginError
"""

from .base import (  # Base layer exceptions
    BaseAPIException,
    BaseDependsException,
    BaseRepoException,
    BaseServiceException,
)
from .core_base import (  # Core infrastructure exceptions
    CoreAppException,
    CoreConfigMissingError,
    CoreConfigurationException,
    CoreConfigValidationError,
    CoreConfigValueError,
    CoreMessagingAPIException,
    CoreMessagingConnectionError,
    CoreMessagingConsumeError,
    CoreMessagingException,
    CoreMessagingPublishError,
    CoreRealtimeAPIException,
    CoreRealtimeAuthError,
    CoreRealtimeConnectionError,
    CoreRealtimeException,
    CoreRealtimeMessageError,
    CoreRepositoryException,
    CoreRepositoryQueryError,
    CoreRepositoryValueError,
    CoreStreamingAPIException,
    CoreStreamingConnectionError,
    CoreStreamingException,
    CoreStreamingValueError,
    CoreTaskiqBrokerError,
    CoreTaskiqException,
    CoreTaskiqValidationError,
    CoreTaskiqWorkerError,
    CoreTelegramConfigError,
    CoreTelegramException,
    CoreTelegramValueError,
    CoreToolsConnectionError,
    CoreToolsException,
    CoreToolsTypeError,
    CoreToolsValidationError,
)
from .handlers import ExceptionContext, format_error_response, setup_exception_handlers
from .middleware import ExceptionHandlingMiddleware, ExceptionLoggingMiddleware
from .notifications import EmailNotifier, NotificationManager, SlackNotifier, TelegramNotifier

__all__ = [
    # Base layer exceptions
    "BaseAPIException",
    "BaseServiceException",
    "BaseRepoException",
    "BaseDependsException",
    # Core infrastructure exceptions
    "CoreAppException",
    "CoreConfigurationException",
    "CoreConfigValueError",
    "CoreConfigMissingError",
    "CoreConfigValidationError",
    "CoreMessagingException",
    "CoreMessagingConnectionError",
    "CoreMessagingPublishError",
    "CoreMessagingConsumeError",
    "CoreRealtimeException",
    "CoreRealtimeConnectionError",
    "CoreRealtimeAuthError",
    "CoreRealtimeMessageError",
    "CoreStreamingException",
    "CoreStreamingConnectionError",
    "CoreStreamingValueError",
    "CoreTaskiqException",
    "CoreTaskiqWorkerError",
    "CoreTaskiqBrokerError",
    "CoreTaskiqValidationError",
    "CoreTelegramException",
    "CoreTelegramConfigError",
    "CoreTelegramValueError",
    "CoreRepositoryException",
    "CoreRepositoryValueError",
    "CoreRepositoryQueryError",
    "CoreToolsException",
    "CoreToolsTypeError",
    "CoreToolsValidationError",
    "CoreMessagingAPIException",
    "CoreRealtimeAPIException",
    "CoreStreamingAPIException",
    "CoreToolsConnectionError",
    # Handlers and middleware
    "setup_exception_handlers",
    "ExceptionContext",
    "format_error_response",
    "ExceptionHandlingMiddleware",
    "ExceptionLoggingMiddleware",
    # Notifications
    "NotificationManager",
    "TelegramNotifier",
    "EmailNotifier",
    "SlackNotifier",
]
