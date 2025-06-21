"""Main API Router Configuration.

This module provides the main API router that aggregates all application routers
including authentication, user management, and profile endpoints.

The router is configured with a common prefix and includes all sub-application routers
to provide a unified API interface.

Example:
    Using the router in FastAPI app::

        from fastapi import FastAPI
        from apps.api_router import api_router

        app = FastAPI()
        app.include_router(api_router)

    Available endpoints::

        # Authentication endpoints
        POST /api/v1/auth/register
        POST /api/v1/auth/login
        POST /api/v1/auth/refresh
        POST /api/v1/auth/logout

        # User management endpoints
        GET /api/v1/users/me
        PUT /api/v1/users/me
        GET /api/v1/users/{user_id}

        # Profile endpoints
        GET /api/v1/profiles/me
        PUT /api/v1/profiles/me
        GET /api/v1/profiles/{user_id}

Note:
    All routes are prefixed with '/api/v1' for API versioning.
    Individual routers maintain their own sub-prefixes.
"""

from fastapi import APIRouter

from apps.auth.api import auth_router
from apps.users.api import profile_router, user_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include application routers
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(profile_router)

__all__ = [
    "api_router",
]
