"""User Application Interfaces.

This module defines Protocol interfaces for the users application
to reduce coupling between modules and avoid circular imports.

The interfaces provide contracts for:
- User identity and authorization data
- User profile information management
- Administrative user management
- User statistics and activity tracking
- User search and discovery

Example:
    Using user identity interface::

        from apps.users.interfaces import UserIdentity

        def check_admin_access(user: UserIdentity) -> bool:
            return user.is_admin and user.can_login()

    Profile data management::

        from apps.users.interfaces import UserProfileData

        def update_user_settings(profile: UserProfileData, theme: str):
            profile.theme = theme
            if profile.public_profile:
                notify_followers_of_change(profile.user_id)

    User search functionality::

        from apps.users.interfaces import UserSearchResult

        def format_search_results(results: list[UserSearchResult]) -> list[dict]:
            return [
                {
                    "id": result.id,
                    "username": result.username,
                    "verified": result.is_verified,
                    "avatar": result.avatar_url
                }
                for result in results
                if result.public_profile
            ]

Note:
    These interfaces use Protocol typing to provide structural subtyping,
    allowing any class that implements the required methods and attributes
    to satisfy the interface contract without explicit inheritance.
"""

import uuid
from datetime import datetime
from typing import Any, Literal, Optional, Protocol, Union

# Type aliases for SQLAlchemy compatibility
IdType = Union[uuid.UUID, Any]  # Support Mapped[UUID] and UUID
StrType = Union[str, Any]  # Support Mapped[str] and str
BoolType = Union[bool, Any]  # Support Mapped[bool] and bool
DateType = Union[datetime, Any]  # Support Mapped[datetime] and datetime

# Enum literals to avoid imports
UserRoleType = Union[Literal["user", "moderator", "admin", "superuser"], Any]
UserStatusType = Union[Literal["active", "inactive", "suspended", "banned"], Any]
UserThemeType = Union[Literal["light", "dark", "auto"], Any]
UserLanguageType = Union[Literal["en", "ru", "es", "fr", "de"], Any]


class UserReference(Protocol):
    """Basic user interface for references and relationships.

    Used when only basic user information is needed for references,
    foreign keys, or simple user identification.

    Attributes:
        id (IdType): Unique user identifier
        username (StrType): User's username
        email (StrType): User's email address
        first_name (Optional[StrType]): User's first name
        last_name (Optional[StrType]): User's last name

    Example:
        Creating user references::

            def get_post_author(post_id: int) -> UserReference:
                post = get_post(post_id)
                return post.author  # Returns UserReference

        Using full name property::

            def display_user_name(user: UserReference) -> str:
                full_name = user.full_name
                return full_name if full_name.strip() else user.username
    """

    id: IdType
    username: StrType
    email: StrType
    first_name: Optional[StrType]
    last_name: Optional[StrType]

    @property
    def full_name(self) -> str:
        """Get user's full name.

        Returns:
            str: Combined first and last name, or empty string if not available
        """
        ...


class UserIdentity(Protocol):
    """User interface for authorization and JWT tokens.

    Contains information necessary for creating tokens and checking
    access permissions. Used in authentication and authorization flows.

    Attributes:
        id (IdType): Unique user identifier
        username (StrType): User's username
        email (StrType): User's email address
        role (UserRoleType): User's role in the system
        status (UserStatusType): User's current status
        is_verified (BoolType): Whether user's email is verified
        is_active (BoolType): Whether user account is active
        is_superuser (BoolType): Whether user has superuser privileges

    Example:
        JWT token creation::

            def create_access_token(user: UserIdentity) -> str:
                if not user.can_login():
                    raise ValueError("User cannot login")

                payload = {
                    "user_id": str(user.id),
                    "username": user.username,
                    "role": user.role,
                    "is_admin": user.is_admin
                }
                return jwt.encode(payload, SECRET_KEY)

        Permission checking::

            def check_admin_permission(user: UserIdentity) -> bool:
                return user.has_role("admin") or user.is_superuser
    """

    id: IdType
    username: StrType
    email: StrType
    role: UserRoleType
    status: UserStatusType
    is_verified: BoolType
    is_active: BoolType
    is_superuser: BoolType

    # Permission checking methods
    def has_role(self, role: UserRoleType) -> bool:
        """Check if user has specific role.

        Args:
            role (UserRoleType): Role to check

        Returns:
            bool: True if user has the specified role
        """
        ...

    def can_login(self) -> bool:
        """Check if user can log into the system.

        Returns:
            bool: True if user can login (active, not banned, etc.)
        """
        ...

    @property
    def is_admin(self) -> bool:
        """Check if user is an administrator.

        Returns:
            bool: True if user has admin privileges
        """
        ...


class UserProfileData(Protocol):
    """User profile data interface.

    Used for working with profile information without being tied
    to a specific model implementation.

    Attributes:
        user_id (IdType): Associated user identifier
        display_name (Optional[StrType]): Public display name
        bio (Optional[StrType]): User biography
        location (Optional[StrType]): User location
        website (Optional[StrType]): User website URL
        avatar_url (Optional[StrType]): Profile picture URL
        birth_date (Optional[DateType]): User's birth date
        language (UserLanguageType): Preferred language
        theme (UserThemeType): UI theme preference
        timezone (StrType): User's timezone
        public_profile (BoolType): Whether profile is public
        show_email (BoolType): Whether to show email publicly
        show_location (BoolType): Whether to show location publicly

    Example:
        Profile customization::

            def update_profile_theme(profile: UserProfileData, theme: str):
                if theme in ["light", "dark", "auto"]:
                    profile.theme = theme
                    save_profile_preferences(profile)

        Privacy settings::

            def set_profile_privacy(profile: UserProfileData, is_public: bool):
                profile.public_profile = is_public
                if not is_public:
                    # Hide sensitive info when private
                    profile.show_email = False
                    profile.show_location = False

        Age calculation::

            def can_view_adult_content(profile: UserProfileData) -> bool:
                age = profile.age
                return age is not None and age >= 18
    """

    user_id: IdType
    display_name: Optional[StrType]
    bio: Optional[StrType]
    location: Optional[StrType]
    website: Optional[StrType]
    avatar_url: Optional[StrType]
    birth_date: Optional[DateType]

    # Settings
    language: UserLanguageType
    theme: UserThemeType
    timezone: StrType

    # Privacy settings
    public_profile: BoolType
    show_email: BoolType
    show_location: BoolType

    @property
    def age(self) -> Optional[int]:
        """Calculate user's age from birth date.

        Returns:
            Optional[int]: User's age in years, or None if birth date not set
        """
        ...


class UserManagement(Protocol):
    """Interface for administrative user management.

    Contains extended information for moderators and administrators
    to manage users in the system.

    Attributes:
        id (IdType): Unique user identifier
        username (StrType): User's username
        email (StrType): User's email address
        role (UserRoleType): User's role
        status (UserStatusType): User's status
        is_verified (BoolType): Email verification status
        is_active (BoolType): Account active status
        created_at (DateType): Account creation date
        updated_at (DateType): Last update date
        last_login_at (Optional[DateType]): Last login timestamp
        email_verified_at (Optional[DateType]): Email verification date
        login_attempts (int): Total login attempts
        failed_login_attempts (int): Failed login attempts count

    Example:
        User moderation::

            def moderate_user(user: UserManagement, moderator: UserIdentity):
                if not user.can_be_managed_by(moderator):
                    raise PermissionError("Cannot manage this user")

                if user.failed_login_attempts > 5:
                    suspend_user_account(user.id)

        Administrative reporting::

            def generate_user_report(user: UserManagement) -> dict:
                return {
                    "user_id": user.id,
                    "status": user.status,
                    "verified": user.is_verified,
                    "last_login": user.last_login_at,
                    "failed_attempts": user.failed_login_attempts,
                    "account_age_days": (datetime.utcnow() - user.created_at).days
                }
    """

    id: IdType
    username: StrType
    email: StrType
    role: UserRoleType
    status: UserStatusType
    is_verified: BoolType
    is_active: BoolType

    # Metadata
    created_at: DateType
    updated_at: DateType
    last_login_at: Optional[DateType]
    email_verified_at: Optional[DateType]

    # Counters
    login_attempts: int
    failed_login_attempts: int

    def can_be_managed_by(self, manager: "UserIdentity") -> bool:
        """Check if user can be managed by given manager.

        Args:
            manager (UserIdentity): The user attempting to manage

        Returns:
            bool: True if manager has permission to manage this user
        """
        ...


class UserStatistics(Protocol):
    """User statistics interface.

    Provides access to user activity statistics and metrics.

    Attributes:
        user_id (IdType): Associated user identifier
        total_logins (int): Total number of logins
        last_login_at (Optional[DateType]): Last login timestamp
        last_activity_at (Optional[DateType]): Last activity timestamp
        profile_views (int): Profile view count
        created_at (DateType): Statistics tracking start date

    Example:
        Activity tracking::

            def track_user_activity(stats: UserStatistics):
                stats.last_activity_at = datetime.utcnow()
                if is_login_event():
                    stats.total_logins += 1
                    stats.last_login_at = datetime.utcnow()

        Analytics reporting::

            def get_weekly_activity(stats: UserStatistics) -> dict:
                weekly_data = stats.get_activity_by_days(7)
                return {
                    "user_id": stats.user_id,
                    "total_logins": stats.total_logins,
                    "weekly_activity": weekly_data
                }
    """

    user_id: IdType
    total_logins: int
    last_login_at: Optional[DateType]
    last_activity_at: Optional[DateType]
    profile_views: int
    created_at: DateType

    # Activity methods
    def get_activity_by_days(self, days: int) -> dict[str, Any]:
        """Get user activity for the last N days.

        Args:
            days (int): Number of days to retrieve activity for

        Returns:
            dict[str, Any]: Activity data grouped by day
        """
        ...


class UserSearchResult(Protocol):
    """User search result interface.

    Represents a user in search results with appropriate
    privacy filtering applied.

    Attributes:
        id (IdType): User identifier
        username (StrType): User's username
        display_name (Optional[StrType]): Display name if available
        avatar_url (Optional[StrType]): Profile picture URL
        is_verified (BoolType): Verification status
        public_profile (BoolType): Whether profile is public
        email (Optional[StrType]): Email (admin/moderator only)
        role (Optional[UserRoleType]): Role (admin/moderator only)
        status (Optional[UserStatusType]): Status (admin/moderator only)

    Example:
        Public search results::

            def format_public_search_results(results: list[UserSearchResult]) -> list[dict]:
                return [
                    {
                        "id": result.id,
                        "username": result.username,
                        "display_name": result.display_name,
                        "avatar": result.avatar_url,
                        "verified": result.is_verified
                    }
                    for result in results
                    if result.public_profile
                ]

        Admin search results::

            def format_admin_search_results(results: list[UserSearchResult]) -> list[dict]:
                return [
                    {
                        "id": result.id,
                        "username": result.username,
                        "email": result.email,
                        "role": result.role,
                        "status": result.status,
                        "verified": result.is_verified
                    }
                    for result in results
                ]
    """

    id: IdType
    username: StrType
    display_name: Optional[StrType]
    avatar_url: Optional[StrType]
    is_verified: BoolType
    public_profile: BoolType

    # Only for admins/moderators
    email: Optional[StrType] = None
    role: Optional[UserRoleType] = None
    status: Optional[UserStatusType] = None


class UserActivityData(Protocol):
    """User activity data interface.

    Tracks user actions and activities for auditing and analytics.

    Attributes:
        user_id (IdType): Associated user identifier
        action_type (StrType): Type of action performed
        action_data (dict[str, Any]): Action-specific data
        ip_address (Optional[StrType]): Client IP address
        user_agent (Optional[StrType]): Client user agent
        timestamp (DateType): Action timestamp

    Example:
        Activity logging::

            def log_user_action(
                user_id: uuid.UUID,
                action: str,
                data: dict[str, Any]
            ) -> UserActivityData:
                activity = UserActivity(
                    user_id=user_id,
                    action_type=action,
                    action_data=data,
                    timestamp=datetime.utcnow()
                )
                return activity

        Privacy compliance::

            def export_user_data(user_id: uuid.UUID) -> list[dict]:
                activities = get_user_activities(user_id)
                # Anonymize sensitive data for export
                return [activity.anonymize() for activity in activities]
    """

    user_id: IdType
    action_type: StrType
    action_data: dict[str, Any]
    ip_address: Optional[StrType]
    user_agent: Optional[StrType]
    timestamp: DateType

    def anonymize(self) -> "UserActivityData":
        """Anonymize sensitive data for privacy compliance.

        Returns:
            UserActivityData: Activity data with sensitive information removed
        """
        ...


# Type aliases for convenience
UserRef = UserReference
UserAuth = UserIdentity
ProfileData = UserProfileData
UserAdmin = UserManagement
UserStats = UserStatistics
