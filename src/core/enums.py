"""
Core application enumerations.

This module defines common enumerations used across different applications
to avoid circular dependencies and provide shared types.
"""

from enum import Enum


class UserRole(str, Enum):
    """
    User role enumeration with hierarchical permissions.

    Defines user roles in the system with built-in permission hierarchy.
    Higher roles inherit permissions from lower roles.

    Attributes:
        USER: Basic user role with standard permissions
        MODERATOR: Moderation role with enhanced permissions
        ADMIN: Administrative role with full system access
        SUPERUSER: Highest role with unrestricted access

    Example:
        >>> role = UserRole.ADMIN
        >>> assert role.has_permission(UserRole.USER)
        >>> assert role.has_permission(UserRole.MODERATOR)
        >>> hierarchy = UserRole.get_hierarchy()
        >>> assert hierarchy[UserRole.ADMIN] > hierarchy[UserRole.USER]
    """

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPERUSER = "superuser"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def get_hierarchy(cls) -> dict[str, int]:
        """
        Get role hierarchy mapping for permission checks.

        Returns:
            dict[str, int]: Mapping of role values to hierarchy levels,
                           where higher numbers indicate higher permissions

        Example:
            >>> hierarchy = UserRole.get_hierarchy()
            >>> assert hierarchy["admin"] > hierarchy["user"]
            >>> assert hierarchy["superuser"] == 4
        """
        return {
            cls.USER: 1,
            cls.MODERATOR: 2,
            cls.ADMIN: 3,
            cls.SUPERUSER: 4,
        }

    def has_permission(self, required_role: "UserRole") -> bool:
        """
        Check if current role has permission for required role level.

        Args:
            required_role (UserRole): Minimum required role for permission

        Returns:
            bool: True if current role has sufficient permissions

        Example:
            >>> admin = UserRole.ADMIN
            >>> assert admin.has_permission(UserRole.USER)
            >>> assert admin.has_permission(UserRole.MODERATOR)
            >>> assert not UserRole.USER.has_permission(UserRole.ADMIN)
        """
        hierarchy = self.get_hierarchy()
        return hierarchy.get(self.value, 0) >= hierarchy.get(required_role.value, 0)
