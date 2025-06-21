"""
Core application exceptions.

This module defines exceptions for Core infrastructure components.
Unlike business applications (Auth/Users), Core provides infrastructure
services and has different exception organization by components.

Architecture:
    CoreAppException (parent)
    ├── CoreConfigurationException (component)
    │   ├── CoreConfigValueError
    │   └── CoreConfigMissingError
    ├── CoreMessagingException (component)
    │   ├── CoreMessagingConnectionError
    │   └── CoreMessagingPublishError
    └── ... (other components)
"""

import uuid
from datetime import datetime
from typing import Any

# ============================================================================
# PARENT EXCEPTION FOR ALL CORE INFRASTRUCTURE
# ============================================================================


class CoreAppException(Exception):
    """
    Parent exception for all Core infrastructure exceptions.

    Core provides infrastructure services (config, messaging, realtime, etc.)
    that are used by business applications but are not business logic themselves.

    Example:
        try:
            # Any core infrastructure operations
            await messaging_client.publish(message)
            config_value = get_config("DATABASE_URL")
        except CoreAppException as e:
            logger.error(f"Core infrastructure error: {e}")
            await notify_developers("Core infra error", str(e))
    """

    def __init__(self, message: str, component: str | None = None, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.component = component
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.error_id = str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging and monitoring."""
        return {
            "error_id": self.error_id,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "component": self.component,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "layer": "core",
        }


# ============================================================================
# COMPONENT-BASED EXCEPTIONS
# ============================================================================


class CoreConfigurationException(CoreAppException):
    """
    Base exception for configuration-related errors.

    Handles environment variables, settings validation, config loading.
    """

    def __init__(self, message: str, config_key: str | None = None, **kwargs):
        super().__init__(message=message, component="configuration", **kwargs)
        self.config_key = config_key


class CoreMessagingException(CoreAppException):
    """
    Base exception for messaging system errors.

    Handles RabbitMQ, Redis, message publishing/consuming.
    """

    def __init__(self, message: str, broker: str | None = None, **kwargs):
        super().__init__(message=message, component="messaging", **kwargs)
        self.broker = broker


class CoreRealtimeException(CoreAppException):
    """
    Base exception for realtime communication errors.

    Handles WebSocket connections, SSE, WebRTC.
    """

    def __init__(self, message: str, connection_type: str | None = None, **kwargs):
        super().__init__(message=message, component="realtime", **kwargs)
        self.connection_type = connection_type


class CoreStreamingException(CoreAppException):
    """
    Base exception for streaming-related errors.

    Handles data streaming, connection management.
    """

    def __init__(self, message: str, stream_type: str | None = None, **kwargs):
        super().__init__(message=message, component="streaming", **kwargs)
        self.stream_type = stream_type


class CoreTaskiqException(CoreAppException):
    """
    Base exception for TaskIQ worker errors.

    Handles task execution, worker management, queues.
    """

    def __init__(self, message: str, task_name: str | None = None, **kwargs):
        super().__init__(message=message, component="taskiq", **kwargs)
        self.task_name = task_name


class CoreTelegramException(CoreAppException):
    """
    Base exception for Telegram bot errors.

    Handles bot operations, webhook management.
    """

    def __init__(self, message: str, bot_operation: str | None = None, **kwargs):
        super().__init__(message=message, component="telegram", **kwargs)
        self.bot_operation = bot_operation


class CoreRepositoryException(CoreAppException):
    """
    Base exception for base repository errors.

    Handles generic repository operations, ORM, database.
    """

    def __init__(self, message: str, operation: str | None = None, **kwargs):
        super().__init__(message=message, component="repository", **kwargs)
        self.operation = operation


class CoreToolsException(CoreAppException):
    """
    Base exception for tools and utilities errors.

    Handles migrations, class finder, utilities.
    """

    def __init__(self, message: str, tool_name: str | None = None, **kwargs):
        super().__init__(message=message, component="tools", **kwargs)
        self.tool_name = tool_name


# ============================================================================
# CONFIGURATION COMPONENT EXCEPTIONS
# ============================================================================


class CoreConfigValueError(CoreConfigurationException):
    """Invalid configuration value."""

    def __init__(self, config_key: str, value: Any, reason: str | None = None):
        message = f"Invalid value for config key '{config_key}': {value}"
        if reason:
            message += f" - {reason}"
        super().__init__(message=message, config_key=config_key, context={"value": str(value), "reason": reason})


class CoreConfigMissingError(CoreConfigurationException):
    """Required configuration key is missing."""

    def __init__(self, config_key: str):
        message = f"Required configuration key '{config_key}' is missing"
        super().__init__(message=message, config_key=config_key)


class CoreConfigValidationError(CoreConfigurationException):
    """Configuration validation failed."""

    def __init__(self, config_key: str, validation_error: str):
        message = f"Validation failed for config key '{config_key}': {validation_error}"
        super().__init__(message=message, config_key=config_key, context={"validation_error": validation_error})


# ============================================================================
# MESSAGING COMPONENT EXCEPTIONS
# ============================================================================


class CoreMessagingConnectionError(CoreMessagingException):
    """Failed to connect to message broker."""

    def __init__(self, broker: str, connection_url: str | None = None):
        message = f"Failed to connect to {broker} broker"
        super().__init__(message=message, broker=broker, context={"connection_url": connection_url})


class CoreMessagingPublishError(CoreMessagingException):
    """Failed to publish message."""

    def __init__(self, broker: str, queue: str | None = None, message_size: int | None = None):
        message = f"Failed to publish message to {broker}"
        if queue:
            message += f" queue '{queue}'"
        super().__init__(message=message, broker=broker, context={"queue": queue, "message_size": message_size})


class CoreMessagingConsumeError(CoreMessagingException):
    """Failed to consume message."""

    def __init__(self, broker: str, queue: str | None = None):
        message = f"Failed to consume message from {broker}"
        if queue:
            message += f" queue '{queue}'"
        super().__init__(message=message, broker=broker, context={"queue": queue})


# ============================================================================
# REALTIME COMPONENT EXCEPTIONS
# ============================================================================


class CoreRealtimeConnectionError(CoreRealtimeException):
    """Realtime connection failed."""

    def __init__(self, connection_type: str, client_id: str | None = None):
        message = f"Failed to establish {connection_type} connection"
        super().__init__(message=message, connection_type=connection_type, context={"client_id": client_id})


class CoreRealtimeAuthError(CoreRealtimeException):
    """Realtime authentication failed."""

    def __init__(self, connection_type: str, reason: str | None = None):
        message = f"Authentication failed for {connection_type} connection"
        if reason:
            message += f": {reason}"
        super().__init__(message=message, connection_type=connection_type, context={"reason": reason})


class CoreRealtimeMessageError(CoreRealtimeException):
    """Realtime message processing failed."""

    def __init__(self, connection_type: str, message_type: str | None = None):
        message = f"Failed to process {connection_type} message"
        if message_type:
            message += f" of type '{message_type}'"
        super().__init__(message=message, connection_type=connection_type, context={"message_type": message_type})


# ============================================================================
# TASKIQ COMPONENT EXCEPTIONS
# ============================================================================


class CoreTaskiqWorkerError(CoreTaskiqException):
    """TaskIQ worker error."""

    def __init__(self, task_name: str, worker_id: str | None = None, error_details: str | None = None):
        message = f"TaskIQ worker error for task '{task_name}'"
        super().__init__(
            message=message, task_name=task_name, context={"worker_id": worker_id, "error_details": error_details}
        )


class CoreTaskiqBrokerError(CoreTaskiqException):
    """TaskIQ broker connection error."""

    def __init__(self, broker_url: str | None = None):
        message = "TaskIQ broker connection failed"
        super().__init__(message=message, context={"broker_url": broker_url})


class CoreTaskiqValidationError(CoreTaskiqException):
    """TaskIQ task validation error."""

    def __init__(self, task_name: str, validation_error: str):
        message = f"Task validation failed for '{task_name}': {validation_error}"
        super().__init__(message=message, task_name=task_name, context={"validation_error": validation_error})


# ============================================================================
# REPOSITORY COMPONENT EXCEPTIONS
# ============================================================================


class CoreRepositoryValueError(CoreRepositoryException):
    """Invalid value in repository operation."""

    def __init__(self, operation: str, field: str, value: Any):
        message = f"Invalid value for field '{field}' in {operation} operation: {value}"
        super().__init__(message=message, operation=operation, context={"field": field, "value": str(value)})


class CoreRepositoryQueryError(CoreRepositoryException):
    """Database query error in repository."""

    def __init__(self, operation: str, query_type: str | None = None):
        message = f"Query error in {operation} operation"
        if query_type:
            message += f" (query type: {query_type})"
        super().__init__(message=message, operation=operation, context={"query_type": query_type})


# ============================================================================
# TOOLS COMPONENT EXCEPTIONS
# ============================================================================


class CoreToolsTypeError(CoreToolsException):
    """Type error in tools/utilities."""

    def __init__(self, tool_name: str, expected_type: str, actual_type: str):
        message = f"Type error in {tool_name}: expected {expected_type}, got {actual_type}"
        super().__init__(
            message=message, tool_name=tool_name, context={"expected_type": expected_type, "actual_type": actual_type}
        )


class CoreToolsValidationError(CoreToolsException):
    """Validation error in tools/utilities."""

    def __init__(self, tool_name: str, validation_message: str):
        message = f"Validation error in {tool_name}: {validation_message}"
        super().__init__(message=message, tool_name=tool_name, context={"validation_message": validation_message})


# ============================================================================
# STREAMING COMPONENT EXCEPTIONS
# ============================================================================


class CoreStreamingConnectionError(CoreStreamingException):
    """Streaming connection error."""

    def __init__(self, stream_type: str, connection_details: str | None = None):
        message = f"Failed to establish {stream_type} streaming connection"
        super().__init__(message=message, stream_type=stream_type, context={"connection_details": connection_details})


class CoreStreamingValueError(CoreStreamingException):
    """Invalid value in streaming operation."""

    def __init__(self, stream_type: str, field: str, value: Any):
        message = f"Invalid value for {field} in {stream_type} streaming: {value}"
        super().__init__(message=message, stream_type=stream_type, context={"field": field, "value": str(value)})


class CoreStreamingAPIException(CoreStreamingException):
    """HTTP API exception for streaming endpoints."""

    def __init__(self, stream_type: str, detail: str, status_code: int = 500):
        message = f"Streaming API error ({stream_type}): {detail}"
        super().__init__(
            message=message, stream_type=stream_type, context={"detail": detail, "status_code": status_code}
        )
        self.detail = detail
        self.status_code = status_code


# ============================================================================
# TELEGRAM COMPONENT EXCEPTIONS
# ============================================================================


class CoreTelegramConfigError(CoreTelegramException):
    """Telegram configuration error."""

    def __init__(self, config_issue: str):
        message = f"Telegram configuration error: {config_issue}"
        super().__init__(message=message, bot_operation="configuration", context={"config_issue": config_issue})


class CoreTelegramValueError(CoreTelegramException):
    """Invalid value in Telegram operation."""

    def __init__(self, bot_operation: str, field: str, value: Any):
        message = f"Invalid value for {field} in {bot_operation}: {value}"
        super().__init__(message=message, bot_operation=bot_operation, context={"field": field, "value": str(value)})


# ============================================================================
# REALTIME COMPONENT EXCEPTIONS (EXTENDED)
# ============================================================================


class CoreRealtimeAPIException(CoreRealtimeException):
    """HTTP API exception for realtime endpoints."""

    def __init__(self, connection_type: str, detail: str, status_code: int = 500):
        message = f"Realtime API error ({connection_type}): {detail}"
        super().__init__(
            message=message, connection_type=connection_type, context={"detail": detail, "status_code": status_code}
        )
        self.detail = detail
        self.status_code = status_code


# ============================================================================
# MESSAGING COMPONENT EXCEPTIONS (EXTENDED)
# ============================================================================


class CoreMessagingAPIException(CoreMessagingException):
    """HTTP API exception for messaging endpoints."""

    def __init__(self, broker: str, detail: str, status_code: int = 500):
        message = f"Messaging API error ({broker}): {detail}"
        super().__init__(message=message, broker=broker, context={"detail": detail, "status_code": status_code})
        self.detail = detail
        self.status_code = status_code


# ============================================================================
# TOOLS COMPONENT EXCEPTIONS (EXTENDED)
# ============================================================================


class CoreToolsConnectionError(CoreToolsException):
    """Connection error in tools/clients."""

    def __init__(self, tool_name: str, connection_details: str | None = None):
        message = f"Connection failed in {tool_name}"
        if connection_details:
            message += f": {connection_details}"
        super().__init__(message=message, tool_name=tool_name, context={"connection_details": connection_details})
