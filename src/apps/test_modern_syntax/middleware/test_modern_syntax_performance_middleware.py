"""
TestModernSyntax performance middleware for Enterprise level.

Template Version: v1.0.0 (Complete)
Features: Performance tracking, Resource monitoring, Optimization hints
"""

import time
import psutil
from typing import Callable
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("performance.test_modern_syntax")


class TestModernSyntaxPerformanceMiddleware(BaseHTTPMiddleware):
    """
    Enterprise performance monitoring middleware.
    
    Features:
    - Request performance tracking
    - Memory usage monitoring
    - CPU utilization tracking
    - Resource optimization alerts
    """

    def __init__(
        self,
        app,
        app_name: str = "test_modern_syntax",
        memory_threshold: float = 0.85,  # 85% memory usage alert
        response_time_threshold: float = 5.0  # 5 seconds slow request
    ):
        """Initialize performance middleware."""
        super().__init__(app)
        self.app_name = app_name
        self.memory_threshold = memory_threshold
        self.response_time_threshold = response_time_threshold

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance monitoring."""
        # Start performance tracking
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate performance metrics
            response_time = time.time() - start_time
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_diff = end_memory - start_memory
            
            # Add performance headers
            response.headers["X-Performance-Time"] = f"{response_time:.3f}s"
            response.headers["X-Memory-Usage"] = f"{end_memory:.1f}MB"
            response.headers["X-Memory-Delta"] = f"{memory_diff:+.1f}MB"
            
            # Log performance metrics
            self._log_performance(request, response_time, end_memory, memory_diff)
            
            # Check for performance issues
            self._check_performance_alerts(request, response_time, end_memory)
            
            return response
            
        except Exception as e:
            # Log performance on error
            error_time = time.time() - start_time
            logger.error(
                f"Request error with performance impact: {error_time:.3f}s",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "response_time": error_time
                }
            )
            raise

    def _log_performance(self, request: Request, response_time: float, memory_mb: float, memory_delta: float):
        """Log performance metrics."""
        logger.info(
            f"Performance: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "response_time": response_time,
                "memory_usage": memory_mb,
                "memory_delta": memory_delta,
                "app": self.app_name
            }
        )

    def _check_performance_alerts(self, request: Request, response_time: float, memory_mb: float):
        """Check for performance alerts."""
        # Slow request alert
        if response_time > self.response_time_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                extra={
                    "response_time": response_time,
                    "threshold": self.response_time_threshold,
                    "alert_type": "slow_request"
                }
            )
        
        # Memory usage alert
        memory_percent = psutil.virtual_memory().percent / 100
        if memory_percent > self.memory_threshold:
            logger.warning(
                f"High memory usage: {memory_percent:.1%}",
                extra={
                    "memory_percent": memory_percent,
                    "threshold": self.memory_threshold,
                    "alert_type": "high_memory"
                }
            ) 