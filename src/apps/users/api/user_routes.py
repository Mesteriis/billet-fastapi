"""
User management API routes.

This module provides FastAPI routes for user management operations including
user listing, creation, updates, deletion, and administrative functions.

Example:
    ```bash
    curl -X GET "http://localhost:8000/users/?page=1&size=20" \
         -H "Authorization: Bearer your_access_token"
    ```
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from apps.auth.depends.base import (
    CurrentActiveUserDep,
    RequireAdminDep,
    RequireModeratorDep,
    get_current_active_user,
    require_role,
)
from apps.users.depends import RequireVerifiedDep, UserFromPathDep, UserServiceDep
from apps.users.exceptions import (
    UserCreationAPIException,
    UserNotFoundAPIException,
    UserPermissionDeniedAPIException,
    UserSelfModificationAPIException,
    UserUpdateAPIException,
    UserValidationAPIException,
)
from apps.users.models.user_models import User
from apps.users.schemas import (
    UserCreateRequest,
    UserFilters,
    UserResponse,
    UserRoleUpdateRequest,
    UsersListResponse,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)
from core.enums import UserRole

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=UsersListResponse)
async def get_users_list(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_service: UserServiceDep,
    # Pagination
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Page size"),
    # Filtering
    search: str | None = Query(default=None, description="Search by username, email, first_name, last_name"),
    role: str | None = Query(default=None, description="Filter by role"),
    status: str | None = Query(default=None, description="Filter by status"),
    is_verified: bool | None = Query(default=None, description="Filter by verification status"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    # Sorting
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order"),
) -> UsersListResponse:
    """
    Get paginated list of users with filtering and sorting.

    Provides comprehensive user listing with pagination, search, filtering by various
    criteria, and sorting options. Access control ensures proper data visibility.

    Args:
        current_user (User): Currently authenticated user
        user_service (UserService): Service for user operations
        page (int): Page number (default: 1, minimum: 1)
        size (int): Page size (default: 20, range: 1-100)
        search (str | None): Search query for username, email, names
        role (str | None): Filter by user role
        status (str | None): Filter by user status
        is_verified (bool | None): Filter by verification status
        is_active (bool | None): Filter by active status
        sort_by (str): Sort field (default: "created_at")
        sort_order (str): Sort order - "asc" or "desc" (default: "desc")

    Returns:
        UsersListResponse: Paginated list of users with metadata

    Note:
        Regular users see only public profiles, while moderators and admins
        have access to extended information.

            Example:
            ```bash
            curl -X GET "http://localhost:8000/users/?search=john&role=user&is_verified=true&page=1&size=10" \
                 -H "Authorization: Bearer your_access_token"
            ```
            
            Response:
            ```json
            {
              "users": [
                {
                  "id": 1,
                  "username": "johndoe",
                  "email": "john@example.com",
                  "role": "user",
                  "is_verified": true,
                  "created_at": "2024-01-15T10:30:00Z"
                }
              ],
              "total_count": 1,
              "page": 1,
              "size": 10,
              "pages": 1
            }
            ```
    """
    # Создаем фильтры
    filters = UserFilters(
        search=search,
        role=role,
        status=status,
        is_verified=is_verified,
        is_active=is_active,
    )

    # Проверяем права доступа для расширенной информации
    role_value = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    can_see_private = role_value in ["admin", "moderator"]

    # Получаем список пользователей
    users_data = await user_service.get_users_list(
        filters=filters, page=page, size=size, sort_by=sort_by, sort_order=sort_order, include_private=can_see_private
    )

    return users_data


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    user_service: UserServiceDep,
) -> UserResponse:
    """
    Create new user account (admin only).

    Administrative function to create new user accounts with specified details.
    Only accessible to users with admin role.

    Args:
        user_data (UserCreateRequest): User creation data
        current_user (User): Currently authenticated admin user
        user_service (UserService): Service for user operations

    Returns:
        UserResponse: Created user information

    Raises:
        HTTPException: 400 if user data is invalid
        HTTPException: 403 if user lacks admin privileges
        HTTPException: 500 if user creation fails

    Example:
        >>> user_data = {
        ...     "username": "newuser",
        ...     "email": "newuser@example.com",
        ...     "password": "securepass123",
        ...     "role": "user"
        ... }
        ```bash
        curl -X POST "http://localhost:8000/users/" \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer admin_access_token" \
             -d '{
               "username": "newuser",
               "email": "newuser@example.com",
               "password": "securepass123",
               "role": "user"
             }'
        ```
        
        Response:
        ```json
        {
          "id": 2,
          "username": "newuser",
          "email": "newuser@example.com",
          "is_active": true,
          "is_verified": false,
          "role": "user",
          "created_at": "2024-01-01T10:00:00Z"
        }
        ```
    """
    try:
        user = await user_service.create_user_by_admin(user_data=user_data, created_by=current_user.id)

        return UserResponse.model_validate(user)

    except ValueError as e:
        raise UserValidationAPIException(detail=str(e))
    except Exception as e:
        raise UserCreationAPIException(detail="User creation failed")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user: UserFromPathDep,
    current_user: Annotated[User, Depends(CurrentActiveUserDep)],
    user_service: UserServiceDep,
) -> UserResponse:
    """
    Get user information by ID.

    Retrieves user profile information with appropriate access control.
    Users can view their own profiles and public profiles of others.

    Args:
        user (User): User object from path parameter
        current_user (User): Currently authenticated user
        user_service (UserService): Service for user operations

    Returns:
        UserResponse: User profile information

    Raises:
        HTTPException: 404 if user not found or profile is private
        HTTPException: 403 if access denied

    Note:
        Access levels:
        - Own profile: Full access
        - Moderator/Admin: Extended information
        - Regular user: Public profiles only

    Example:
        ```bash
        curl -X GET "http://localhost:8000/users/123" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "id": 123,
          "username": "johndoe",
          "email": "john@example.com",
          "is_active": true,
          "is_verified": true,
          "role": "user",
          "created_at": "2024-01-01T10:00:00Z"
        }
        ```
        >>> # Public profile fields are always visible
        >>> assert response.username is not None
    """
    # Проверяем права доступа
    role_value = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    can_see_private = role_value in ["admin", "moderator"]

    # Если не можем видеть приватную информацию, проверяем публичность профиля
    if not can_see_private:
        if not user.profile or not user.profile.is_public:
            raise UserNotFoundAPIException(detail="User not found or profile is private")

    # Получаем полную информацию о пользователе
    user_data = await user_service.get_user_with_profile(user_id=user.id, include_private=can_see_private)

    if not user_data:
        raise UserNotFoundAPIException(detail="User not found")

    return UserResponse.model_validate(user_data)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserUpdateRequest,
    current_user: Annotated[User, Depends(CurrentActiveUserDep)],
    user_service: UserServiceDep,
) -> UserResponse:
    """
    Update user information.

    Updates user profile information with proper authorization checks.
    Users can edit their own profiles, admins can edit any profile.

    Args:
        user_id (int): ID of user to update
        update_data (UserUpdateRequest): User update data
        current_user (User): Currently authenticated user
        user_service (UserService): Service for user operations

    Returns:
        UserResponse: Updated user information

    Raises:
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if user not found
        HTTPException: 400 if update data is invalid
        HTTPException: 500 if update fails

    Example:
        >>> update_data = {
        ...     "first_name": "John",
        ...     "last_name": "Doe",
        ...     "bio": "Software developer"
        ... }
        ```bash
        curl -X PUT "http://localhost:8000/users/123" \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer your_access_token" \
             -d '{
               "first_name": "John",
               "last_name": "Doe",
               "bio": "Software developer"
             }'
        ```
        
        Response:
        ```json
        {
          "id": 123,
          "username": "johndoe",
          "first_name": "John",
          "last_name": "Doe",
          "bio": "Software developer",
          "updated_at": "2024-01-01T12:00:00Z"
        }
        ```
    """
    # Проверяем права доступа
    role_value = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if user_id != current_user.id and role_value != "admin":
        raise UserPermissionDeniedAPIException(detail="Not enough permissions to update this user")

    try:
        # Обновляем пользователя
        updated_user = await user_service.update_user(
            user_id=user_id, update_data=update_data, updated_by=current_user.id
        )

        if not updated_user:
            raise UserNotFoundAPIException(detail="User not found")

        return UserResponse.model_validate(updated_user)

    except ValueError as e:
        raise UserValidationAPIException(detail=str(e))
    except Exception as e:
        raise UserUpdateAPIException(detail="User update failed")


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: RequireAdminDep,
    user_service: UserServiceDep,
):
    """
    Delete user account (admin only).

    Performs soft deletion by deactivating the user account.
    Only accessible to admin users. Self-deletion is prohibited.

    Args:
        user_id (int): ID of user to delete
        current_user (User): Currently authenticated admin user
        user_service (UserService): Service for user operations

    Returns:
        dict: Success message

    Raises:
        HTTPException: 400 if trying to delete own account
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if user not found

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/users/123" \
             -H "Authorization: Bearer admin_access_token"
        ```
        
        Response:
        ```json
        {
          "message": "User deleted successfully"
        }
        ```
    """
    if user_id == current_user.id:
        raise UserSelfModificationAPIException(detail="Cannot delete yourself")

    success = await user_service.delete_user(user_id=user_id)

    if not success:
        raise UserNotFoundAPIException(detail="User not found")

    return {"message": "User deleted successfully"}


@router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    status_data: UserStatusUpdateRequest,
    current_user: RequireModeratorDep,
    user_service: UserServiceDep,
) -> UserResponse:
    """
    Update user status (moderator/admin only).

    Changes user status (active, suspended, banned) with optional reason.
    Available to moderators and administrators. Self-modification prohibited.

    Args:
        user_id (int): ID of user to update
        status_data (UserStatusUpdateRequest): Status update data with reason
        current_user (User): Currently authenticated moderator/admin user
        user_service (UserService): Service for user operations

    Returns:
        UserResponse: Updated user information

    Raises:
        HTTPException: 400 if trying to modify own status or invalid data
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if user not found

    Example:
        >>> status_data = {
        ...     "status": "suspended",
        ...     "reason": "Policy violation"
        ... }
        ```bash
        curl -X PATCH "http://localhost:8000/users/123/status" \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer moderator_access_token" \
             -d '{
               "status": "suspended",
               "reason": "Policy violation"
             }'
        ```
        
        Response:
        ```json
        {
          "id": 123,
          "username": "johndoe",
          "status": "suspended",
          "status_reason": "Policy violation",
          "updated_at": "2024-01-01T12:00:00Z"
        }
        ```
    """
    if user_id == current_user.id:
        raise UserSelfModificationAPIException(detail="Cannot change your own status")

    try:
        updated_user = await user_service.update_user_status(
            user_id=user_id, new_status=status_data.status, reason=status_data.reason, updated_by=current_user.id
        )

        if not updated_user:
            raise UserNotFoundAPIException(detail="User not found")

        return UserResponse.model_validate(updated_user)

    except ValueError as e:
        raise UserValidationAPIException(detail=str(e))


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_data: UserRoleUpdateRequest,
    current_user: RequireAdminDep,
    user_service: UserServiceDep,
) -> UserResponse:
    """
    Update user role (admin only).

    Changes user role with optional reason. Only accessible to administrators.
    Self-role modification is prohibited for security.

    Args:
        user_id (int): ID of user to update
        role_data (UserRoleUpdateRequest): Role update data with reason
        current_user (User): Currently authenticated admin user
        user_service (UserService): Service for user operations

    Returns:
        UserResponse: Updated user information

    Raises:
        HTTPException: 400 if trying to modify own role or invalid data
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if user not found

    Example:
        >>> role_data = {
        ...     "role": "moderator",
        ...     "reason": "Promotion to moderator"
        ... }
        ```bash
        curl -X PATCH "http://localhost:8000/users/123/role" \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer admin_access_token" \
             -d '{
               "role": "moderator",
               "reason": "Promotion to moderator"
             }'
        ```
        
        Response:
        ```json
        {
          "id": 123,
          "username": "johndoe",
          "role": "moderator",
          "role_change_reason": "Promotion to moderator",
          "updated_at": "2024-01-01T12:00:00Z"
        }
        ```
    """
    if user_id == current_user.id:
        raise UserSelfModificationAPIException(detail="Cannot change your own role")

    try:
        updated_user = await user_service.update_user_role(
            user_id=user_id, new_role=role_data.role, reason=role_data.reason, updated_by=current_user.id
        )

        if not updated_user:
            raise UserNotFoundAPIException(detail="User not found")

        return UserResponse.model_validate(updated_user)

    except ValueError as e:
        raise UserValidationAPIException(detail=str(e))


@router.post("/{user_id}/verify")
async def verify_user_manually(
    user_id: int,
    current_user: RequireModeratorDep,
    user_service: UserServiceDep,
):
    """
    Manually verify user (moderator/admin only).

    Manually marks user as verified, bypassing email verification process.
    Available to moderators and administrators.

    Args:
        user_id (int): ID of user to verify
        current_user (User): Currently authenticated moderator/admin user
        user_service (UserService): Service for user operations

    Returns:
        dict: Success message

    Raises:
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if user not found or already verified

    Example:
        ```bash
        curl -X POST "http://localhost:8000/users/123/verify" \
             -H "Authorization: Bearer moderator_access_token"
        ```
        
        Response:
        ```json
        {
          "message": "User verified successfully"
        }
        ```
    """
    success = await user_service.verify_user_manually(user_id=user_id, verified_by=current_user.id)

    if not success:
        raise UserNotFoundAPIException(detail="User not found or already verified")

    return {"message": "User verified successfully"}


@router.post("/{user_id}/unverify")
async def unverify_user(
    user_id: int,
    current_user: RequireAdminDep,
    user_service: UserServiceDep,
):
    """
    Revoke user verification (admin only).

    Removes verification status from user account. Only accessible to administrators.
    Useful for handling compromised or suspicious accounts.

    Args:
        user_id (int): ID of user to unverify
        current_user (User): Currently authenticated admin user
        user_service (UserService): Service for user operations

    Returns:
        dict: Success message

    Raises:
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if user not found or not verified

    Example:
        ```bash
        curl -X POST "http://localhost:8000/users/123/unverify" \
             -H "Authorization: Bearer admin_access_token"
        ```
        
        Response:
        ```json
        {
          "message": "User verification revoked successfully"
        }
        ```
    """
    success = await user_service.unverify_user(user_id=user_id, unverified_by=current_user.id)

    if not success:
        raise UserNotFoundAPIException(detail="User not found or not verified")

    return {"message": "User verification revoked successfully"}


@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: int,
    current_user: Annotated[User, Depends(CurrentActiveUserDep)],
    user_service: UserServiceDep,
    days: int = Query(default=30, ge=1, le=365, description="Activity period in days"),
):
    """
    Get user activity information.

    Retrieves user activity data for specified time period.
    Users can view their own activity, moderators/admins can view any user's activity.

    Args:
        user_id (int): ID of user to get activity for
        current_user (User): Currently authenticated user
        user_service (UserService): Service for user operations
        days (int): Activity period in days (default: 30, range: 1-365)

    Returns:
        dict: User activity information including login history, actions, etc.

    Raises:
        HTTPException: 403 if insufficient permissions to view activity
        HTTPException: 404 if user not found

    Example:
        ```bash
        curl -X GET "http://localhost:8000/users/123/activity?days=7" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "activity": {
            "login_count": 5,
            "posts_created": 3,
            "comments_made": 12,
            "last_activity": "2024-01-01T11:30:00Z"
          },
          "period": "7 days"
        }
        ```
        >>> assert "login_count" in response["activity"]
    """
    # Проверяем права доступа
    role_value = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if user_id != current_user.id and role_value not in ["admin", "moderator"]:
        raise UserPermissionDeniedAPIException(detail="Not enough permissions to view this user's activity")

    activity = await user_service.get_user_activity(user_id=user_id, days=days)

    if activity is None:
        raise UserNotFoundAPIException(detail="User not found")

    return activity


@router.get("/{user_id}/statistics")
async def get_user_statistics(
    user_id: int,
    current_user: RequireModeratorDep,
    user_service: UserServiceDep,
):
    """
    Get user statistics (moderator/admin only).

    Retrieves comprehensive user statistics including activity metrics,
    content creation, and behavioral data. Administrative function only.

    Args:
        user_id (int): ID of user to get statistics for
        current_user (User): Currently authenticated moderator/admin user
        user_service (UserService): Service for user operations

    Returns:
        dict: Comprehensive user statistics

    Raises:
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if user not found

    Example:
        ```bash
        curl -X GET "http://localhost:8000/users/123/statistics" \
             -H "Authorization: Bearer moderator_access_token"
        ```
        
        Response:
        ```json
        {
          "statistics": {
            "total_logins": 156,
            "total_posts": 45,
            "total_comments": 123,
            "registration_date": "2023-01-01T10:00:00Z",
            "last_login": "2024-01-01T11:30:00Z",
            "activity_score": 85.5
          }
        }
        ```
    """
    statistics = await user_service.get_user_statistics(user_id)

    if not statistics:
        raise UserNotFoundAPIException(detail="User not found")

    return statistics
