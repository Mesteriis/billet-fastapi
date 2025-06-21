"""
User application enumerations.

This module defines various enumerations used throughout the user application
including user roles, statuses, preferences, and notification settings.

Example:
    >>> from apps.users.models.enums import UserRole, UserStatus
    >>> admin_role = UserRole.ADMIN
    >>> assert admin_role.has_permission(UserRole.USER)
    >>> active_status = UserStatus.ACTIVE
    >>> assert active_status.is_active_status
"""

from enum import Enum
from typing import Any

# Импортируем UserRole из core для совместимости
from core.enums import UserRole


class UserStatus(str, Enum):
    """
    User account status enumeration.

    Defines possible states of user accounts throughout their lifecycle,
    from registration to deletion.

    Attributes:
        PENDING: User registered but email not verified
        ACTIVE: Fully active user account
        SUSPENDED: Temporarily blocked account
        BANNED: Permanently blocked account
        DELETED: Soft-deleted account

    Example:
        >>> status = UserStatus.ACTIVE
        >>> assert status.is_active_status
        >>> suspended = UserStatus.SUSPENDED
        >>> assert suspended.is_blocked_status
    """

    PENDING = "pending"  # Awaiting email confirmation
    ACTIVE = "active"  # Active user
    SUSPENDED = "suspended"  # Temporarily blocked
    BANNED = "banned"  # Permanently blocked
    DELETED = "deleted"  # Soft deleted

    def __str__(self) -> str:
        return self.value

    @property
    def is_active_status(self) -> bool:
        """
        Check if status represents an active user.

        Returns:
            bool: True if user can perform normal operations

        Example:
            >>> assert UserStatus.ACTIVE.is_active_status
            >>> assert not UserStatus.SUSPENDED.is_active_status
        """
        return self in [UserStatus.ACTIVE]

    @property
    def is_blocked_status(self) -> bool:
        """
        Check if status represents a blocked user.

        Returns:
            bool: True if user is blocked from system access

        Example:
            >>> assert UserStatus.BANNED.is_blocked_status
            >>> assert UserStatus.SUSPENDED.is_blocked_status
            >>> assert not UserStatus.ACTIVE.is_blocked_status
        """
        return self in [UserStatus.SUSPENDED, UserStatus.BANNED, UserStatus.DELETED]


class UserTheme(str, Enum):
    """
    User interface theme enumeration.

    Defines available UI themes for user personalization.

    Attributes:
        LIGHT: Light theme with bright colors
        DARK: Dark theme with dark colors
        AUTO: Automatic theme based on system preferences

    Example:
        >>> theme = UserTheme.DARK
        >>> assert str(theme) == "dark"
    """

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"

    def __str__(self) -> str:
        return self.value


class UserLanguage(str, Enum):
    """
    User interface language enumeration.

    Defines supported languages for the application interface.

    Attributes:
        EN: English language
        RU: Russian language
        DE: German language
        FR: French language
        ES: Spanish language

    Example:
        >>> lang = UserLanguage.EN
        >>> display = UserLanguage.get_display_name(lang)
        >>> assert display == "English"
    """

    EN = "en"  # English
    RU = "ru"  # Русский
    DE = "de"  # Deutsch
    FR = "fr"  # Français
    ES = "es"  # Español

    def __str__(self) -> str:
        return self.value

    @classmethod
    def get_display_name(cls, language: "UserLanguage") -> str:
        """
        Get human-readable display name for language.

        Args:
            language (UserLanguage): Language enum value

        Returns:
            str: Localized display name for the language

        Example:
            >>> name = UserLanguage.get_display_name(UserLanguage.EN)
            >>> assert name == "English"
            >>> name = UserLanguage.get_display_name(UserLanguage.DE)
            >>> assert name == "Deutsch"
        """
        display_names = {
            cls.EN: "English",
            cls.RU: "Русский",
            cls.DE: "Deutsch",
            cls.FR: "Français",
            cls.ES: "Español",
        }
        return display_names.get(language, language.value)


class NotificationLevel(str, Enum):
    """
    Notification level enumeration.

    Defines notification delivery preferences for users.

    Attributes:
        ALL: Receive all notifications
        IMPORTANT: Receive only important notifications
        MENTIONS: Receive only direct mentions
        DISABLED: Disable all notifications

    Example:
        >>> level = NotificationLevel.IMPORTANT
        >>> assert str(level) == "important"
    """

    ALL = "all"  # All notifications
    IMPORTANT = "important"  # Only important notifications
    MENTIONS = "mentions"  # Only mentions
    DISABLED = "disabled"  # Disabled

    def __str__(self) -> str:
        return self.value
