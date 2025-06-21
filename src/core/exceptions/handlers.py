"""
Exception handlers for converting exceptions to HTTP responses.

This module provides centralized exception handling for the FastAPI application,
including structured logging, error formatting, and integration with monitoring systems.
"""

import logging
import traceback
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .base import BaseAPIException, BaseDependsException, BaseRepoException, BaseServiceException
from .notifications import NotificationManager

logger = structlog.get_logger(__name__)


class ExceptionContext:
    """
    Context information for exception handling.

    Provides structured data about the request and exception for logging and monitoring.
    """

    def __init__(
        self,
        request: Request,
        exception: Exception,
        trace_id: str | None = None,
        user_id: str | None = None,
    ):
        self.request = request
        self.exception = exception
        self.trace_id = trace_id or self._generate_trace_id()
        self.user_id = user_id
        self.method = request.method
        self.url = str(request.url)
        self.headers = dict(request.headers)
        self.client_ip = self._get_client_ip(request)

    def _generate_trace_id(self) -> str:
        """Generate unique trace ID for request tracking."""
        import uuid

        return str(uuid.uuid4())

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers."""
        # Check for common proxy headers
        for header in ["X-Forwarded-For", "X-Real-IP", "X-Client-IP"]:
            if header in request.headers:
                return request.headers[header].split(",")[0].strip()

        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "method": self.method,
            "url": self.url,
            "client_ip": self.client_ip,
            "exception_type": self.exception.__class__.__name__,
            "exception_message": str(self.exception),
        }


def format_error_response(
    context: ExceptionContext,
    status_code: int,
    detail: str,
    error_code: str | None = None,
    include_trace: bool = False,
) -> dict[str, Any]:
    """
    Format standardized error response.

    Args:
        context: Exception context information
        status_code: HTTP status code
        detail: User-friendly error message
        error_code: Optional error code for programmatic handling
        include_trace: Whether to include trace information (dev mode only)

    Returns:
        Formatted error response dictionary
    """
    response = {
        "error": True,
        "message": detail,
        "timestamp": context.exception.timestamp.isoformat() if hasattr(context.exception, "timestamp") else None,
        "trace_id": context.trace_id,
    }

    if error_code:
        response["error_code"] = error_code

    if include_trace:
        response["trace"] = traceback.format_exc()
        response["context"] = {
            "method": context.method,
            "url": context.url,
            "client_ip": context.client_ip,
        }

    return response


async def handle_api_exception(request: Request, exc: BaseAPIException) -> JSONResponse:
    """
    Handle API layer exceptions.

    Args:
        request: FastAPI request object
        exc: API exception instance

    Returns:
        JSON response with formatted error
    """
    context = ExceptionContext(request, exc)

    # Log the exception
    logger.warning(
        "API exception occurred",
        exception_data=exc.to_dict(),
        request_context=context.to_dict(),
    )

    # Format response
    response_data = format_error_response(
        context=context,
        status_code=exc.status_code,
        detail=exc.detail,
        error_code=getattr(exc, "error_code", None),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
    )


async def handle_service_exception(request: Request, exc: BaseServiceException) -> JSONResponse:
    """
    Handle Service layer exceptions.

    Service exceptions are converted to appropriate HTTP responses.

    Args:
        request: FastAPI request object
        exc: Service exception instance

    Returns:
        JSON response with formatted error
    """
    context = ExceptionContext(request, exc)

    # Log the exception
    logger.error(
        "Service exception occurred",
        exception_data=exc.to_dict(),
        request_context=context.to_dict(),
    )

    # Map service exceptions to HTTP status codes
    status_code = _map_service_exception_to_status(exc)

    # Format response
    response_data = format_error_response(
        context=context,
        status_code=status_code,
        detail="Service error occurred",  # Generic message for security
        error_code=exc.error_code,
    )

    return JSONResponse(
        status_code=status_code,
        content=response_data,
    )


async def handle_repo_exception(request: Request, exc: BaseRepoException) -> JSONResponse:
    """
    Handle Repository layer exceptions.

    Repository exceptions typically indicate data access issues.

    Args:
        request: FastAPI request object
        exc: Repository exception instance

    Returns:
        JSON response with formatted error
    """
    context = ExceptionContext(request, exc)

    # Log the exception with high severity
    logger.error(
        "Repository exception occurred",
        exception_data=exc.to_dict(),
        request_context=context.to_dict(),
    )

    # Notify developers about critical database issues
    notification_manager = NotificationManager()
    await notification_manager.notify_critical_error(
        title="Database Error",
        message=f"Repository exception in {exc.table or 'unknown table'}: {exc.message}",
        context=context.to_dict(),
        exception_data=exc.to_dict(),
    )

    # Repository errors are always internal server errors
    response_data = format_error_response(
        context=context,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error occurred",  # Generic message
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data,
    )


async def handle_depends_exception(request: Request, exc: BaseDependsException) -> JSONResponse:
    """
    Handle Depends layer exceptions.

    Depends exceptions typically indicate validation or authorization issues.

    Args:
        request: FastAPI request object
        exc: Depends exception instance

    Returns:
        JSON response with formatted error
    """
    context = ExceptionContext(request, exc)

    # Log the exception
    logger.warning(
        "Depends exception occurred",
        exception_data=exc.to_dict(),
        request_context=context.to_dict(),
    )

    # Map depends exceptions to HTTP status codes
    status_code = _map_depends_exception_to_status(exc)

    # Format response
    response_data = format_error_response(
        context=context,
        status_code=status_code,
        detail=exc.message,
    )

    return JSONResponse(
        status_code=status_code,
        content=response_data,
    )


async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    This is the fallback handler for any exception not caught by specific handlers.

    Args:
        request: FastAPI request object
        exc: Generic exception instance

    Returns:
        JSON response with formatted error
    """
    context = ExceptionContext(request, exc)

    # Log the exception with critical severity
    logger.critical(
        "Unhandled exception occurred",
        exception_type=exc.__class__.__name__,
        exception_message=str(exc),
        traceback=traceback.format_exc(),
        request_context=context.to_dict(),
    )

    # Notify developers about unhandled exceptions
    notification_manager = NotificationManager()
    await notification_manager.notify_critical_error(
        title="Unhandled Exception",
        message=f"Unexpected error: {exc.__class__.__name__}: {str(exc)}",
        context=context.to_dict(),
        exception_data={
            "type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        },
    )

    # Generic error response
    response_data = format_error_response(
        context=context,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data,
    )


def _map_service_exception_to_status(exc: BaseServiceException) -> int:
    """Map service exception to appropriate HTTP status code."""
    error_code = getattr(exc, "error_code", None)

    # Common business logic error mappings
    if error_code in ["VALIDATION_ERROR", "INVALID_DATA"]:
        return status.HTTP_400_BAD_REQUEST
    elif error_code in ["NOT_FOUND", "RESOURCE_NOT_FOUND"]:
        return status.HTTP_404_NOT_FOUND
    elif error_code in ["UNAUTHORIZED", "AUTH_REQUIRED"]:
        return status.HTTP_401_UNAUTHORIZED
    elif error_code in ["FORBIDDEN", "ACCESS_DENIED"]:
        return status.HTTP_403_FORBIDDEN
    elif error_code in ["CONFLICT", "ALREADY_EXISTS"]:
        return status.HTTP_409_CONFLICT
    elif error_code in ["RATE_LIMIT", "TOO_MANY_REQUESTS"]:
        return status.HTTP_429_TOO_MANY_REQUESTS
    else:
        return status.HTTP_500_INTERNAL_SERVER_ERROR


def _map_depends_exception_to_status(exc: BaseDependsException) -> int:
    """Map depends exception to appropriate HTTP status code."""
    dependency_name = getattr(exc, "dependency_name", "")

    # Common dependency error mappings
    if "auth" in dependency_name.lower() or "token" in dependency_name.lower():
        return status.HTTP_401_UNAUTHORIZED
    elif "permission" in dependency_name.lower() or "access" in dependency_name.lower():
        return status.HTTP_403_FORBIDDEN
    elif "validation" in dependency_name.lower():
        return status.HTTP_400_BAD_REQUEST
    else:
        return status.HTTP_500_INTERNAL_SERVER_ERROR


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(BaseAPIException)
    async def api_exception_handler(request: Request, exc: BaseAPIException):
        return await handle_api_exception(request, exc)

    @app.exception_handler(BaseServiceException)
    async def service_exception_handler(request: Request, exc: BaseServiceException):
        return await handle_service_exception(request, exc)

    @app.exception_handler(BaseRepoException)
    async def repo_exception_handler(request: Request, exc: BaseRepoException):
        return await handle_repo_exception(request, exc)

    @app.exception_handler(BaseDependsException)
    async def depends_exception_handler(request: Request, exc: BaseDependsException):
        return await handle_depends_exception(request, exc)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return await handle_generic_exception(request, exc)

    logger.info("Exception handlers registered successfully")
