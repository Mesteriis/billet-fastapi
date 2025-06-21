"""
User profile management API routes.

This module provides FastAPI routes for user profile operations including
profile viewing, updating, privacy settings, and profile search functionality.

Example:
    ```bash
    curl -X GET "http://localhost:8000/profiles/?page=1&size=10"
    ```
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from apps.auth.depends.base import CurrentActiveUserDep, get_current_active_user
from apps.users.depends import ProfileFromPathDep, ProfileServiceDep, UserFromPathDep
from apps.users.exceptions import (
    ProfileAccessDeniedAPIException,
    ProfileNotFoundAPIException,
    ProfileUpdateAPIException,
    ProfileValidationAPIException,
)
from apps.users.models.user_models import User

from ..schemas import ProfileResponse, ProfileSearchFilters, ProfilesListResponse, ProfileUpdateRequest

router = APIRouter(prefix="/profiles", tags=["User Profiles"])


@router.get("/", response_model=ProfilesListResponse)
async def get_public_profiles(
    profile_service: ProfileServiceDep,
    # Pagination
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Page size"),
    # Search and filtering
    search: str | None = Query(default=None, description="Search by display name, bio, location"),
    location: str | None = Query(default=None, description="Filter by location"),
    # Sorting
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order"),
) -> ProfilesListResponse:
    """
    Get list of public user profiles.

    Retrieves paginated list of public user profiles with optional search
    and filtering capabilities. Only shows profiles marked as public.

    Args:
        profile_service (ProfileService): Service for profile operations
        page (int): Page number (default: 1, minimum: 1)
        size (int): Page size (default: 20, range: 1-100)
        search (str | None): Search query for display name, bio, location
        location (str | None): Filter by location
        sort_by (str): Sort field (default: "created_at")
        sort_order (str): Sort order - "asc" or "desc" (default: "desc")

    Returns:
        ProfilesListResponse: Paginated list of public profiles

            Example:
            ```bash
            curl -X GET "http://localhost:8000/profiles/?search=developer&location=New%20York&page=1&size=10"
            ```

            Response:
            ```json
            {
              "profiles": [
                {
                  "user_id": 1,
                  "display_name": "John Developer",
                  "bio": "Full-stack developer",
                  "location": "New York",
                  "is_public": true,
                  "created_at": "2024-01-15T10:30:00Z"
                }
              ],
              "total_count": 1,
              "page": 1,
              "size": 10
            }
            ```
    """
    # Вычисляем offset для пагинации
    offset = (page - 1) * size

    # Получаем список публичных профилей
    profiles = await profile_service.search_public_profiles(query=search, location=location, limit=size, offset=offset)

    # Формируем ответ с правильными полями
    total = len(profiles)  # Упрощенно - реальный count нужен из repo
    pages = max(1, (total + size - 1) // size)  # Рассчитываем общее количество страниц

    profiles_data = ProfilesListResponse(
        profiles=[profile for profile in profiles],
        total=total,
        page=page,
        pages=pages,
        size=size,
    )

    return profiles_data


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_user_profile(
    user: UserFromPathDep,
    current_user: CurrentActiveUserDep,
    profile_service: ProfileServiceDep,
) -> ProfileResponse:
    """
    Get user profile by user ID.

    Retrieves user profile information with appropriate access control.
    Users can view their own profiles and public profiles of others.

    Args:
        user (User): User object from path parameter
        current_user (User): Currently authenticated user
        profile_service (ProfileService): Service for profile operations

    Returns:
        ProfileResponse: User profile information

    Raises:
        HTTPException: 404 if profile not found or is private

    Note:
        Access control:
        - Own profile: Full access including private information
        - Other users: Only public profiles are accessible

    Example:
        ```bash
        curl -X GET "http://localhost:8000/profiles/123" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "user_id": 123,
          "display_name": "John Doe",
          "bio": "Software developer",
          "avatar_url": "https://example.com/avatar.jpg",
          "is_public": true,
          "created_at": "2024-01-01T10:00:00Z"
        }
        ```
        >>> # If viewing own profile, private fields are included
        >>> if target_user.id == current_user.id:
        ...     assert hasattr(response, "private_field")
    """
    # Проверяем права доступа
    can_see_private = user.id == current_user.id

    # Получаем профиль
    profile = await profile_service.get_profile_by_user_id(user_id=user.id)

    if not profile:
        raise ProfileNotFoundAPIException(detail="Profile not found")

    # Если профиль не публичный и пользователь не является владельцем
    if not can_see_private and not profile.public_profile:
        raise ProfileNotFoundAPIException(detail="Profile not found or is private")

    return ProfileResponse.model_validate(profile)


@router.put("/{user_id}", response_model=ProfileResponse)
async def update_user_profile(
    user_id: int,
    profile_data: ProfileUpdateRequest,
    current_user: Annotated[User, Depends(CurrentActiveUserDep)],
    profile_service: ProfileServiceDep,
) -> ProfileResponse:
    """
    Update user profile by user ID.

    Updates user profile information. Users can only update their own profiles.
    Profile visibility and other settings can be modified.

    Args:
        user_id (int): ID of user whose profile to update
        profile_data (ProfileUpdateRequest): Profile update data
        current_user (User): Currently authenticated user
        profile_service (ProfileService): Service for profile operations

    Returns:
        ProfileResponse: Updated profile information

    Raises:
        HTTPException: 403 if trying to update someone else's profile
        HTTPException: 404 if profile not found
        HTTPException: 400 if profile data is invalid
        HTTPException: 500 if update fails

    Example:
        >>> profile_data = {
        ...     "display_name": "John Developer",
        ...     "bio": "Full-stack developer",
        ...     "location": "San Francisco",
        ...     "is_public": True
        ... }
        ```bash
        curl -X PUT "http://localhost:8000/profiles/123" \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer your_access_token" \
             -d '{
               "display_name": "John Developer",
               "bio": "Senior developer and tech lead",
               "avatar_url": "https://example.com/avatar.jpg"
             }'
        ```
        
        Response:
        ```json
        {
          "user_id": 123,
          "display_name": "John Developer",
          "bio": "Senior developer and tech lead",
          "avatar_url": "https://example.com/avatar.jpg",
          "updated_at": "2024-01-01T12:00:00Z"
        }
        ```
    """
    # Проверяем права доступа - только свой профиль
    if user_id != current_user.id:
        raise ProfileAccessDeniedAPIException(detail="Not enough permissions to update this profile")

    try:
        # Обновляем профиль
        updated_profile = await profile_service.update_profile(user_id=user_id, profile_data=profile_data)

        if not updated_profile:
            raise ProfileNotFoundAPIException(detail="Profile not found")

        return ProfileResponse.model_validate(updated_profile)

    except ValueError as e:
        raise ProfileValidationAPIException(detail=str(e))
    except Exception as e:
        raise ProfileUpdateAPIException(detail="Profile update failed")


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: Annotated[User, Depends(CurrentActiveUserDep)],
    profile_service: ProfileServiceDep,
) -> ProfileResponse:
    """
    Get current user's profile with full information.

    Retrieves the authenticated user's complete profile including private information.
    This endpoint provides access to all profile fields regardless of privacy settings.

    Args:
        current_user (User): Currently authenticated user
        profile_service (ProfileService): Service for profile operations

    Returns:
        ProfileResponse: Complete user profile information

    Raises:
        HTTPException: 404 if profile not found

    Example:
        ```bash
        curl -X GET "http://localhost:8000/profiles/me" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "user_id": 123,
          "display_name": "John Doe",
          "bio": "Software developer",
          "avatar_url": "https://example.com/avatar.jpg",
          "is_public": true,
          "privacy_settings": {
            "email_visible": false,
            "activity_visible": true
          }
        }
        ```
        >>> # All fields are accessible for own profile
        >>> assert hasattr(response, "email")
        >>> assert hasattr(response, "is_public")
    """
    profile = await profile_service.get_profile_by_user_id(user_id=current_user.id)

    if not profile:
        raise ProfileNotFoundAPIException(detail="Profile not found")

    return ProfileResponse.model_validate(profile)


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    profile_data: ProfileUpdateRequest,
    current_user: Annotated[User, Depends(CurrentActiveUserDep)],
    profile_service: ProfileServiceDep,
) -> ProfileResponse:
    """
    Update current user's profile.

    Updates the authenticated user's profile information. All profile fields
    can be modified including privacy settings and personal information.

    Args:
        profile_data (ProfileUpdateRequest): Profile update data
        current_user (User): Currently authenticated user
        profile_service (ProfileService): Service for profile operations

    Returns:
        ProfileResponse: Updated profile information

    Raises:
        HTTPException: 404 if profile not found
        HTTPException: 400 if profile data is invalid
        HTTPException: 500 if update fails

    Example:
        >>> profile_data = {
        ...     "display_name": "Jane Smith",
        ...     "bio": "UX Designer passionate about accessibility",
        ...     "website": "https://janesmith.design"
        ... }
        ```bash
        curl -X PUT "http://localhost:8000/profiles/me" \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer your_access_token" \
             -d '{
               "display_name": "Jane Smith",
               "bio": "Updated bio text",
               "is_public": true
             }'
        ```
        
        Response:
        ```json
        {
          "user_id": 123,
          "display_name": "Jane Smith",
          "bio": "Updated bio text",
          "is_public": true,
          "updated_at": "2024-01-01T12:00:00Z"
        }
        ```
    """
    try:
        updated_profile = await profile_service.update_profile(user_id=current_user.id, profile_data=profile_data)

        if not updated_profile:
            raise ProfileNotFoundAPIException(detail="Profile not found")

        return ProfileResponse.model_validate(updated_profile)

    except ValueError as e:
        raise ProfileValidationAPIException(detail=str(e))
    except Exception as e:
        raise ProfileUpdateAPIException(detail="Profile update failed")


@router.post("/me/privacy/public")
async def make_profile_public(
    current_user: Annotated[User, Depends(CurrentActiveUserDep)],
    profile_service: ProfileServiceDep,
):
    """
    Make current user's profile public.

    Sets profile visibility to public, making it discoverable in search results
    and viewable by all users. This affects profile discoverability.

    Args:
        current_user (User): Currently authenticated user
        profile_service (ProfileService): Service for profile operations

    Returns:
        dict: Success message

    Raises:
        HTTPException: 404 if profile not found

    Example:
        ```bash
        curl -X POST "http://localhost:8000/profiles/me/public" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "message": "Profile is now public"
        }
        ```
    """
    success = await profile_service.update_privacy_settings(user_id=current_user.id, public_profile=True)

    if not success:
        raise ProfileNotFoundAPIException(detail="Profile not found")

    return {"message": "Profile is now public"}


@router.post("/me/privacy/private")
async def make_profile_private(
    current_user: Annotated[User, Depends(CurrentActiveUserDep)],
    profile_service: ProfileServiceDep,
):
    """
    Make current user's profile private.

    Sets profile visibility to private, hiding it from search results and
    making it viewable only by the profile owner.

    Args:
        current_user (User): Currently authenticated user
        profile_service (ProfileService): Service for profile operations

    Returns:
        dict: Success message

    Raises:
        HTTPException: 404 if profile not found

    Example:
        ```bash
        curl -X POST "http://localhost:8000/profiles/me/private" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "message": "Profile is now private"
        }
        ```
    """
    success = await profile_service.update_privacy_settings(user_id=current_user.id, public_profile=False)

    if not success:
        raise ProfileNotFoundAPIException(detail="Profile not found")

    return {"message": "Profile is now private"}


@router.get("/search", response_model=ProfilesListResponse)
async def search_profiles(
    profile_service: ProfileServiceDep,
    # Search parameters
    q: str = Query(..., min_length=2, description="Search query"),
    # Pagination
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=50, description="Page size"),
    # Filtering
    location: str | None = Query(default=None, description="Filter by location"),
    # Sorting
    sort_by: str = Query(default="relevance", description="Sort field (relevance, created_at, display_name)"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order"),
) -> ProfilesListResponse:
    """
    Search profiles by query string.

    Performs full-text search across profile fields including display name,
    bio, and location. Only searches among public profiles for privacy.

    Args:
        profile_service (ProfileService): Service for profile operations
        q (str): Search query (minimum 2 characters)
        page (int): Page number (default: 1, minimum: 1)
        size (int): Page size (default: 20, range: 1-50)
        location (str | None): Filter results by location
        sort_by (str): Sort field - "relevance", "created_at", "display_name" (default: "relevance")
        sort_order (str): Sort order - "asc" or "desc" (default: "desc")

    Returns:
        ProfilesListResponse: Search results with matching profiles

    Example:
        ```bash
        curl -X GET "http://localhost:8000/profiles/search?q=python%20developer&location=Remote&page=1&size=20" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "profiles": [
            {
              "user_id": 123,
              "display_name": "John Doe",
              "bio": "Python developer",
              "location": "Remote",
              "skills": ["python", "fastapi"]
            }
          ],
          "total": 1,
          "page": 1,
          "size": 20
        }
        ```
    """
    # Выполняем поиск
    search_results = await profile_service.search_public_profiles(
        query=q, location=location, limit=size, offset=(page - 1) * size
    )

    # Формируем ответ
    return ProfilesListResponse(
        profiles=search_results,
        total=len(search_results),
        page=page,
        pages=max(1, (len(search_results) + size - 1) // size),
        size=size,
    )


@router.get("/statistics/my")
async def get_my_profile_statistics(
    current_user: Annotated[User, Depends(CurrentActiveUserDep)],
    profile_service: ProfileServiceDep,
):
    """
    Get current user's profile statistics.

    Retrieves comprehensive statistics about the user's profile including
    view counts, interaction metrics, and activity data.

    Args:
        current_user (User): Currently authenticated user
        profile_service (ProfileService): Service for profile operations

    Returns:
        dict: Profile statistics including views, interactions, and metrics

    Raises:
        HTTPException: 404 if profile not found

    Example:
        ```bash
        curl -X GET "http://localhost:8000/profiles/me/statistics" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "profile_views": 125,
          "followers": 18,
          "following": 24,
          "posts_count": 45,
          "last_updated": "2024-01-01T12:00:00Z",
          "completion_score": 89.5
        }
        ```
        >>> assert isinstance(response["profile_views"], int)
    """
    statistics = await profile_service.get_profile_stats()

    if not statistics:
        raise ProfileNotFoundAPIException(detail="Profile not found")

    return statistics
