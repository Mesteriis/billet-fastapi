"""
Exception handling and logging middleware.

This module provides middleware components for centralized exception handling,
request/response logging, and performance monitoring.
"""

import logging
import time
import uuid
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .handlers import ExceptionContext
from .notifications import NotificationManager

logger = logging.getLogger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized exception handling.

    This middleware catches any unhandled exceptions and ensures they are
    properly logged and processed through the notification system.
    """

    def __init__(self, app, enable_notifications: bool = True):
        super().__init__(app)
        self.enable_notifications = enable_notifications
        self.notification_manager = NotificationManager() if enable_notifications else None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle any exceptions.

        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler

        Returns:
            Response object
        """
        try:
            # Add trace_id to request state for tracking
            if not hasattr(request.state, "trace_id"):
                request.state.trace_id = str(uuid.uuid4())

            # Process request
            response = await call_next(request)
            return response

        except Exception as exc:
            # Create exception context
            context = ExceptionContext(
                request=request,
                exception=exc,
                trace_id=getattr(request.state, "trace_id", None),
                user_id=getattr(request.state, "user_id", None),
            )

            # Log the exception
            logger.critical(
                "Unhandled exception in middleware",
                extra={
                    "exception_type": exc.__class__.__name__,
                    "exception_message": str(exc),
                    "trace_id": context.trace_id,
                    "method": context.method,
                    "url": context.url,
                    "client_ip": context.client_ip,
                },
            )

            # Send notification for critical errors
            if self.notification_manager:
                await self.notification_manager.notify_critical_error(
                    title="Middleware Exception",
                    message=f"Unhandled exception in middleware: {exc.__class__.__name__}: {str(exc)}",
                    context=context.to_dict(),
                    exception_data={
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    },
                )

            # Re-raise the exception to be handled by FastAPI exception handlers
            raise exc


class ExceptionLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging and performance monitoring.

    This middleware logs all requests and responses with performance metrics
    and provides structured logging for monitoring and debugging.
    """

    def __init__(
        self,
        app,
        log_requests: bool = True,
        log_responses: bool = True,
        log_performance: bool = True,
        slow_request_threshold: float = 1.0,
    ):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_performance = log_performance
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging and performance monitoring.

        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler

        Returns:
            Response object with added performance headers
        """
        # Start timing
        start_time = time.time()

        # Generate trace_id if not present
        if not hasattr(request.state, "trace_id"):
            request.state.trace_id = str(uuid.uuid4())

        # Log incoming request
        if self.log_requests:
            await self._log_request(request)

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add performance headers
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Trace-ID"] = request.state.trace_id

            # Log response
            if self.log_responses:
                await self._log_response(request, response, process_time)

            # Log slow requests
            if self.log_performance and process_time > self.slow_request_threshold:
                await self._log_slow_request(request, process_time)

            return response

        except Exception as exc:
            # Calculate processing time even for exceptions
            process_time = time.time() - start_time

            # Log exception with performance data
            logger.error(
                "Request failed with exception",
                extra={
                    "trace_id": request.state.trace_id,
                    "method": request.method,
                    "url": str(request.url),
                    "process_time": process_time,
                    "exception_type": exc.__class__.__name__,
                    "exception_message": str(exc),
                },
            )

            # Re-raise the exception
            raise exc

    async def _log_request(self, request: Request) -> None:
        """Log incoming request details."""
        # Get client IP
        client_ip = "unknown"
        if hasattr(request, "client") and request.client:
            client_ip = request.client.host

        # Check for proxy headers
        for header in ["X-Forwarded-For", "X-Real-IP", "X-Client-IP"]:
            if header in request.headers:
                client_ip = request.headers[header].split(",")[0].strip()
                break

        logger.info(
            "Incoming request",
            extra={
                "trace_id": request.state.trace_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": client_ip,
                "user_agent": request.headers.get("User-Agent", "unknown"),
                "content_type": request.headers.get("Content-Type"),
                "content_length": request.headers.get("Content-Length"),
            },
        )

    async def _log_response(self, request: Request, response: Response, process_time: float) -> None:
        """Log response details."""
        logger.info(
            "Request completed",
            extra={
                "trace_id": request.state.trace_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time,
                "response_size": response.headers.get("Content-Length"),
            },
        )

    async def _log_slow_request(self, request: Request, process_time: float) -> None:
        """Log slow request warning."""
        logger.warning(
            "Slow request detected",
            extra={
                "trace_id": request.state.trace_id,
                "method": request.method,
                "url": str(request.url),
                "process_time": process_time,
                "threshold": self.slow_request_threshold,
            },
        )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for managing request context.

    This middleware adds context information to requests that can be used
    throughout the application for logging, monitoring, and debugging.
    """

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add context information to request state.

        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler

        Returns:
            Response object
        """
        # Generate unique trace ID for request tracking
        request.state.trace_id = str(uuid.uuid4())

        # Add request timestamp
        request.state.start_time = time.time()

        # Extract user ID from token if available
        request.state.user_id = await self._extract_user_id(request)

        # Add client IP
        request.state.client_ip = self._get_client_ip(request)

        # Process request
        response = await call_next(request)

        return response

    async def _extract_user_id(self, request: Request) -> str | None:
        """
        Extract user ID from request headers or token.

        Args:
            request: FastAPI request object

        Returns:
            User ID if found, None otherwise
        """
        # Try to extract from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # This is a placeholder - in production you'd decode the JWT token
                # and extract the user ID
                return "extracted_user_id"
            except Exception:
                pass

        # Try to extract from custom headers
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id

        return None

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check for proxy headers first
        for header in ["X-Forwarded-For", "X-Real-IP", "X-Client-IP"]:
            if header in request.headers:
                return request.headers[header].split(",")[0].strip()

        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"


def setup_exception_middleware(app, enable_notifications: bool = True) -> None:
    """
    Setup exception handling middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        enable_notifications: Whether to enable developer notifications
    """
    # Add middleware in reverse order (last added = first executed)

    # Exception handling middleware (should be last to catch everything)
    app.add_middleware(ExceptionHandlingMiddleware, enable_notifications=enable_notifications)

    # Request logging middleware
    app.add_middleware(
        ExceptionLoggingMiddleware,
        log_requests=True,
        log_responses=True,
        log_performance=True,
        slow_request_threshold=1.0,
    )

    # Request context middleware (should be first to set up context)
    app.add_middleware(RequestContextMiddleware)

    logger.info("Exception handling middleware setup completed")
