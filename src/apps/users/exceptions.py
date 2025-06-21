"""
Users application exceptions.

This module defines all exceptions for the Users application following
the three-level hierarchy: App -> Layer -> Specific.

All Users exceptions inherit from UsersAppException to enable catching
any users-related error through a single parent class.
"""

from fastapi import status

from core.exceptions.base import BaseAPIException, BaseDependsException, BaseRepoException, BaseServiceException

# ============================================================================
# PARENT EXCEPTION FOR ALL USERS APPLICATION EXCEPTIONS
# ============================================================================


class UsersAppException(Exception):
    """
    Parent exception for all Users application exceptions.

    This allows catching any users-related error through a single class:

    Example:
        try:
            # Any users operations
            await user_service.create_user(user_data)
            await profile_service.update_profile(profile_data)
        except UsersAppException as e:
            logger.error(f"Users application error: {e}")
            await notify_developers("Users app error", str(e))
    """

    pass


# ============================================================================
# BASE LAYER EXCEPTIONS FOR USERS APPLICATION
# ============================================================================


class UsersAPIException(BaseAPIException, UsersAppException):
    """Base exception for Users API layer."""

    pass


class UsersServiceException(BaseServiceException, UsersAppException):
    """Base exception for Users Service layer."""

    pass


class UsersRepoException(BaseRepoException, UsersAppException):
    """Base exception for Users Repository layer."""

    pass


class UsersDependsException(BaseDependsException, UsersAppException):
    """Base exception for Users Depends layer."""

    pass


# ============================================================================
# SPECIALIZED API LAYER EXCEPTIONS
# ============================================================================


class UserNotFoundAPIException(UsersAPIException):
    """User not found."""

    def __init__(self, detail: str = "User not found"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class UserPermissionDeniedAPIException(UsersAPIException):
    """Insufficient permissions to access user resource."""

    def __init__(self, detail: str = "Not enough permissions to access this user"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class UserSelfModificationAPIException(UsersAPIException):
    """Error when trying to modify self in prohibited ways."""

    def __init__(self, detail: str = "Cannot modify yourself"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class UserCreationAPIException(UsersAPIException):
    """User creation failed."""

    def __init__(self, detail: str = "User creation failed"):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserUpdateAPIException(UsersAPIException):
    """User update failed."""

    def __init__(self, detail: str = "User update failed"):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserValidationAPIException(UsersAPIException):
    """User data validation failed."""

    def __init__(self, detail: str = "User data validation failed"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class ProfileNotFoundAPIException(UsersAPIException):
    """User profile not found."""

    def __init__(self, detail: str = "Profile not found"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class ProfileAccessDeniedAPIException(UsersAPIException):
    """Access to profile denied."""

    def __init__(self, detail: str = "Access denied to this profile"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class ProfileUpdateAPIException(UsersAPIException):
    """Profile update failed."""

    def __init__(self, detail: str = "Profile update failed"):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileIsPrivateAPIException(UsersAPIException):
    """Profile is private and cannot be accessed."""

    def __init__(self, detail: str = "Profile is private"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,  # Hide existence for privacy
        )


class ProfileValidationAPIException(UsersAPIException):
    """Profile data validation failed."""

    def __init__(self, detail: str = "Profile data validation failed"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# BACKWARD COMPATIBILITY ALIASES (FOR MIGRATION)
# ============================================================================

# These aliases provide backward compatibility during migration
UserNotFoundError = UserNotFoundAPIException
UserPermissionDeniedError = UserPermissionDeniedAPIException
UserSelfModificationError = UserSelfModificationAPIException
UserCreationError = UserCreationAPIException
UserUpdateError = UserUpdateAPIException
ProfileNotFoundError = ProfileNotFoundAPIException
ProfileAccessDeniedError = ProfileAccessDeniedAPIException
ProfileUpdateError = ProfileUpdateAPIException
ProfileIsPrivateError = ProfileIsPrivateAPIException


# ============================================================================
# SPECIALIZED SERVICE LAYER EXCEPTIONS
# ============================================================================


class UserServiceError(UsersServiceException):
    """Base user service error."""

    def __init__(self, message: str, error_code: str = "USER_SERVICE_ERROR"):
        super().__init__(message=message, error_code=error_code)


class UserEmailAlreadyExistsError(UserServiceError):
    """User email already exists."""

    def __init__(self, email: str):
        super().__init__(message=f"User with email {email} already exists", error_code="EMAIL_ALREADY_EXISTS")


class UserUsernameAlreadyExistsError(UserServiceError):
    """Username already exists."""

    def __init__(self, username: str):
        super().__init__(message=f"Username {username} already exists", error_code="USERNAME_ALREADY_EXISTS")


class UserStatusChangeError(UserServiceError):
    """Failed to change user status."""

    def __init__(self, message: str = "Failed to change user status"):
        super().__init__(message=message, error_code="USER_STATUS_CHANGE_ERROR")


class UserRoleChangeError(UserServiceError):
    """Failed to change user role."""

    def __init__(self, message: str = "Failed to change user role"):
        super().__init__(message=message, error_code="USER_ROLE_CHANGE_ERROR")


class UserValidationError(UserServiceError):
    """User data validation failed."""

    def __init__(self, message: str = "User data validation failed"):
        super().__init__(message=message, error_code="USER_VALIDATION_ERROR")


class UserDataValidationError(UserServiceError):
    """User data validation failed."""

    def __init__(self, message: str = "User data validation failed"):
        super().__init__(message=message, error_code="USER_DATA_VALIDATION_ERROR")


class UserBusinessLogicError(UserServiceError):
    """User business logic validation failed."""

    def __init__(self, message: str = "User business logic validation failed"):
        super().__init__(message=message, error_code="USER_BUSINESS_LOGIC_ERROR")


class ProfileServiceError(UsersServiceException):
    """Base profile service error."""

    def __init__(self, message: str, error_code: str = "PROFILE_SERVICE_ERROR"):
        super().__init__(message=message, error_code=error_code)


class ProfileAlreadyExistsError(ProfileServiceError):
    """Profile already exists for user."""

    def __init__(self, user_id: int):
        super().__init__(message=f"Profile for user {user_id} already exists", error_code="PROFILE_ALREADY_EXISTS")


class ProfileCreationError(ProfileServiceError):
    """Failed to create profile."""

    def __init__(self, message: str = "Failed to create profile"):
        super().__init__(message=message, error_code="PROFILE_CREATION_ERROR")


class ProfileValidationError(ProfileServiceError):
    """Profile data validation failed."""

    def __init__(self, message: str = "Profile data validation failed"):
        super().__init__(message=message, error_code="PROFILE_VALIDATION_ERROR")


class ProfileBusinessLogicError(ProfileServiceError):
    """Profile business logic validation failed."""

    def __init__(self, message: str = "Profile business logic validation failed"):
        super().__init__(message=message, error_code="PROFILE_BUSINESS_LOGIC_ERROR")


# ============================================================================
# SPECIALIZED REPOSITORY LAYER EXCEPTIONS
# ============================================================================


class UserRepoError(UsersRepoException):
    """User repository error."""

    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(message=message, operation=operation, table="users")


class UserCreateError(UserRepoError):
    """Failed to create user in database."""

    def __init__(self, message: str = "Failed to create user"):
        super().__init__(message=message, operation="create")


class UserRepoUpdateError(UserRepoError):
    """Failed to update user in database."""

    def __init__(self, message: str = "Failed to update user"):
        super().__init__(message=message, operation="update")


class UserDeleteError(UserRepoError):
    """Failed to delete user from database."""

    def __init__(self, message: str = "Failed to delete user"):
        super().__init__(message=message, operation="delete")


class UserQueryError(UserRepoError):
    """Failed to query user from database."""

    def __init__(self, message: str = "Failed to query user"):
        super().__init__(message=message, operation="read")


class UserUniqueConstraintError(UserRepoError):
    """User unique constraint violation."""

    def __init__(self, constraint: str, value: str):
        super().__init__(message=f"Unique constraint violation: {constraint} = {value}", operation="create")


class ProfileRepoError(UsersRepoException):
    """Profile repository error."""

    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(message=message, operation=operation, table="profiles")


class ProfileCreateError(ProfileRepoError):
    """Failed to create profile in database."""

    def __init__(self, message: str = "Failed to create profile"):
        super().__init__(message=message, operation="create")


class ProfileRepoUpdateError(ProfileRepoError):
    """Failed to update profile in database."""

    def __init__(self, message: str = "Failed to update profile"):
        super().__init__(message=message, operation="update")


class ProfileDeleteError(ProfileRepoError):
    """Failed to delete profile from database."""

    def __init__(self, message: str = "Failed to delete profile"):
        super().__init__(message=message, operation="delete")


class ProfileQueryError(ProfileRepoError):
    """Failed to query profile from database."""

    def __init__(self, message: str = "Failed to query profile"):
        super().__init__(message=message, operation="read")


# ============================================================================
# SPECIALIZED DEPENDS LAYER EXCEPTIONS
# ============================================================================


class UserAccessValidationError(UsersDependsException):
    """User access validation failed in dependency."""

    def __init__(self, message: str = "User access validation failed"):
        super().__init__(message=message, dependency_name="user_access_validation")


class ProfileAccessValidationError(UsersDependsException):
    """Profile access validation failed in dependency."""

    def __init__(self, message: str = "Profile access validation failed"):
        super().__init__(message=message, dependency_name="profile_access_validation")


class UserPermissionValidationError(UsersDependsException):
    """User permission validation failed in dependency."""

    def __init__(self, message: str = "User permission validation failed"):
        super().__init__(message=message, dependency_name="user_permission_validation")


class UserResourceOwnershipError(UsersDependsException):
    """User does not own the requested resource."""

    def __init__(self, message: str = "User does not own this resource"):
        super().__init__(message=message, dependency_name="resource_ownership_check")


class UserStatusValidationError(UsersDependsException):
    """User status validation failed in dependency."""

    def __init__(self, message: str = "User status validation failed"):
        super().__init__(message=message, dependency_name="user_status_validation")


class UserVerificationValidationError(UsersDependsException):
    """User verification validation failed in dependency."""

    def __init__(self, message: str = "User verification validation failed"):
        super().__init__(message=message, dependency_name="user_verification_validation")


class ProfilePrivacyValidationError(UsersDependsException):
    """Profile privacy validation failed in dependency."""

    def __init__(self, message: str = "Profile privacy validation failed"):
        super().__init__(message=message, dependency_name="profile_privacy_validation")


# ============================================================================
# SPECIALIZED SCHEMA VALIDATION EXCEPTIONS
# ============================================================================


class UsersSchemaValidationError(UsersServiceException):
    """Base schema validation error for Users schemas."""

    def __init__(self, message: str, field_name: str | None = None):
        super().__init__(message=message, error_code="SCHEMA_VALIDATION_ERROR")
        self.field_name = field_name


class UsersUsernameValidationError(UsersSchemaValidationError):
    """Username validation failed in schema."""

    def __init__(self, message: str = "Invalid username format"):
        super().__init__(message=message, field_name="username")


class UsersEmailValidationError(UsersSchemaValidationError):
    """Email validation failed in schema."""

    def __init__(self, message: str = "Invalid email format"):
        super().__init__(message=message, field_name="email")


class UsersPasswordValidationError(UsersSchemaValidationError):
    """Password validation failed in schema."""

    def __init__(self, message: str = "Invalid password format"):
        super().__init__(message=message, field_name="password")


class UsersPasswordMismatchError(UsersSchemaValidationError):
    """Password confirmation does not match."""

    def __init__(self, message: str = "Passwords do not match"):
        super().__init__(message=message, field_name="confirm_password")


class UsersAgeValidationError(UsersSchemaValidationError):
    """Age validation failed in schema."""

    def __init__(self, message: str = "Invalid age"):
        super().__init__(message=message, field_name="age")


class UsersPhoneValidationError(UsersSchemaValidationError):
    """Phone number validation failed in schema."""

    def __init__(self, message: str = "Invalid phone number"):
        super().__init__(message=message, field_name="phone")


class UsersDateValidationError(UsersSchemaValidationError):
    """Date validation failed in schema."""

    def __init__(self, message: str = "Invalid date", field_name: str = "date"):
        super().__init__(message=message, field_name=field_name)
