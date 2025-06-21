"""
Простые тесты для user enums для увеличения покрытия.
"""

from apps.users.models.enums import NotificationLevel, UserLanguage, UserRole, UserStatus, UserTheme


class TestUserEnums:
    """Тесты для user enum'ов."""

    def test_user_role_enum(self):
        """Test UserRole enum values."""
        assert UserRole.USER.value == "user"
        assert UserRole.MODERATOR.value == "moderator"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.SUPERUSER.value == "superuser"

        # Test string representation
        assert str(UserRole.USER) == "user"
        assert str(UserRole.ADMIN) == "admin"

    def test_user_status_enum(self):
        """Test UserStatus enum values."""
        assert UserStatus.PENDING.value == "pending"
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.BANNED.value == "banned"
        assert UserStatus.DELETED.value == "deleted"

        # Test string representation
        assert str(UserStatus.ACTIVE) == "active"
        assert str(UserStatus.SUSPENDED) == "suspended"

    def test_user_status_properties(self):
        """Test UserStatus properties."""
        # Test is_active_status
        assert UserStatus.ACTIVE.is_active_status is True
        assert UserStatus.SUSPENDED.is_active_status is False
        assert UserStatus.BANNED.is_active_status is False

        # Test is_blocked_status
        assert UserStatus.SUSPENDED.is_blocked_status is True
        assert UserStatus.BANNED.is_blocked_status is True
        assert UserStatus.ACTIVE.is_blocked_status is False

    def test_user_theme_enum(self):
        """Test UserTheme enum values."""
        assert UserTheme.LIGHT.value == "light"
        assert UserTheme.DARK.value == "dark"
        assert UserTheme.AUTO.value == "auto"

        # Test string representation
        assert str(UserTheme.DARK) == "dark"
        assert str(UserTheme.LIGHT) == "light"

    def test_user_language_enum(self):
        """Test UserLanguage enum values."""
        assert UserLanguage.EN.value == "en"
        assert UserLanguage.RU.value == "ru"
        assert UserLanguage.DE.value == "de"
        assert UserLanguage.FR.value == "fr"
        assert UserLanguage.ES.value == "es"

        # Test string representation
        assert str(UserLanguage.EN) == "en"
        assert str(UserLanguage.RU) == "ru"

    def test_user_language_display_names(self):
        """Test UserLanguage display names."""
        assert UserLanguage.get_display_name(UserLanguage.EN) == "English"
        assert UserLanguage.get_display_name(UserLanguage.RU) == "Русский"
        assert UserLanguage.get_display_name(UserLanguage.DE) == "Deutsch"

    def test_notification_level_enum(self):
        """Test NotificationLevel enum values."""
        assert NotificationLevel.ALL.value == "all"
        assert NotificationLevel.IMPORTANT.value == "important"
        assert NotificationLevel.MENTIONS.value == "mentions"
        assert NotificationLevel.DISABLED.value == "disabled"

        # Test string representation
        assert str(NotificationLevel.ALL) == "all"
        assert str(NotificationLevel.DISABLED) == "disabled"

    def test_enum_membership(self):
        """Test enum membership checks."""
        # Test UserRole membership
        assert UserRole.USER in UserRole

        # Test UserStatus membership
        assert UserStatus.ACTIVE in UserStatus
        assert UserStatus.BANNED in UserStatus
