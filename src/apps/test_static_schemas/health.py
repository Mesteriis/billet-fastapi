"""
Health check module for TestStaticSchema application.

Template Version: v1.0.0 (Complete)
Level: Advanced
"""

from typing import Dict, Any
import logging
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.database import get_async_session

logger = logging.getLogger("health.test_static_schemas")

router = APIRouter(
    prefix="/health",
    tags=["health"],
    include_in_schema=True
)


@router.get("/", summary="Basic Health Check")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "test_static_schemas",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "v1.0.0",
        "level": "Advanced"
    }


@router.get("/detailed", summary="Detailed Health Check")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with database validation."""
    health_status = {
        "status": "healthy",
        "service": "test_static_schemas",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "v1.0.0",
        "level": "Advanced",
        "checks": {}
    }
    
    # Check database connectivity
    try:
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Add monitoring check
    try:
        from apps.test_static_schemas.middleware.test_static_schemas_monitoring_middleware import get_monitoring_health
        monitoring_health = await get_monitoring_health()
        health_status["checks"]["monitoring"] = monitoring_health
    except Exception as e:
        health_status["checks"]["monitoring"] = {
            "status": "error",
            "message": f"Monitoring check failed: {str(e)}"
        }
    
    return health_status


@router.get("/ready", summary="Readiness Check")
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes readiness probe endpoint."""
    # Check if service is ready to receive traffic
    try:
        # Validate database connection
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "service": "test_static_schemas",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "service": "test_static_schemas",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/live", summary="Liveness Check")
async def liveness_check() -> Dict[str, Any]:
    """Kubernetes liveness probe endpoint."""
    return {
        "status": "alive",
        "service": "test_static_schemas",
        "timestamp": datetime.utcnow().isoformat()
    } 