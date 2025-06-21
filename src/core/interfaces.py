"""
Core interfaces to break circular dependencies between apps.

This module defines common interfaces and protocols that are used
across different applications to avoid circular import issues.
"""

from typing import Protocol, runtime_checkable
from uuid import UUID

from core.enums import UserRole


@runtime_checkable
class UserProtocol(Protocol):
    """Protocol for User model to avoid circular imports."""

    id: UUID
    username: str
    email: str
    is_active: bool
    is_verified: bool
    is_superuser: bool

    @property
    def can_login(self) -> bool:
        """Check if user can login."""
        ...

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has required role."""
        ...


@runtime_checkable
class UserServiceProtocol(Protocol):
    """Protocol for UserService to avoid circular imports."""

    async def get_user_by_id(self, user_id: UUID) -> UserProtocol | None:
        """Get user by ID."""
        ...

    async def get_user_by_email(self, email: str) -> UserProtocol | None:
        """Get user by email."""
        ...

    async def get_user_by_username(self, username: str) -> UserProtocol | None:
        """Get user by username."""
        ...
