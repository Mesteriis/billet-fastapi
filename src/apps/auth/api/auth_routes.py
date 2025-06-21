"""
Authentication API routes.

This module provides FastAPI routes for user authentication operations including
registration, login, logout, password management, and token operations.

Example:
    ```bash
    curl -X POST "http://localhost:8000/auth/register" \
         -H "Content-Type: application/json" \
         -d '{
           "username": "johndoe",
           "email": "john@example.com",
           "password": "securepass123"
         }'
    ```
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from apps.auth.depends import CurrentActiveUserDep, JWTServiceDep, OrbitalServiceDep, SessionServiceDep
from apps.auth.exceptions import (
    AuthEmailVerificationAPIException,
    AuthInvalidCredentialsAPIException,
    AuthLoginAPIException,
    AuthPasswordResetAPIException,
    AuthRegistrationAPIException,
    AuthSessionNotFoundAPIException,
    AuthSessionRevokeAPIException,
    AuthTokenExpiredAPIException,
)
from apps.auth.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    EmailVerificationRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegistrationRequest,
    TokenResponse,
)
from apps.users.depends import UserServiceDep
from apps.users.models.user_models import User
from apps.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    response: Response,
    registration_data: RegistrationRequest,
    user_service: UserServiceDep,
    jwt_service: JWTServiceDep,
    session_service: SessionServiceDep,
    orbital_service: OrbitalServiceDep,
) -> AuthResponse:
    """
    Register a new user account.

    Creates a new user account, generates authentication tokens, establishes a web session,
    and initiates email verification process.

    Args:
        request (Request): FastAPI request object containing client information
        response (Response): FastAPI response object for setting cookies
        registration_data (RegistrationRequest): User registration details
        user_service (UserService): Service for user operations
        jwt_service (JWTService): Service for JWT token operations
        session_service (SessionService): Service for web session management
        orbital_service (OrbitalService): Service for orbital token operations

    Returns:
        AuthResponse: Authentication response containing access token, refresh token,
                     user information, and verification status

    Raises:
        HTTPException: 400 if registration data is invalid
        HTTPException: 500 if registration process fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/auth/register" \
             -H "Content-Type: application/json" \
             -d '{
               "username": "johndoe",
               "email": "john@example.com",
               "password": "securepass123",
               "remember_me": true
             }'
        ```
        
        Response:
        ```json
        {
          "access_token": "eyJ0eXAiOiJKV1Q...",
          "refresh_token": "eyJ0eXAiOiJKV1Q...",
          "token_type": "bearer",
          "expires_in": 3600,
          "user": {
            "id": 1,
            "username": "johndoe",
            "email": "john@example.com"
          },
          "requires_verification": true
        }
        ```
    """
    try:
        # Создаем пользователя напрямую с данными регистрации
        user = await user_service.create_user(registration_data)

        # Создаем токены
        access_token = await jwt_service.create_access_token(
            user=user, device_fingerprint=request.headers.get("user-agent", "")[:100]
        )

        refresh_token, _ = await jwt_service.create_refresh_token(
            user=user,
            device_info=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            device_fingerprint=request.headers.get("user-agent", "")[:100],
            remember_me=registration_data.remember_me,
        )

        # Создаем веб-сессию
        session = await session_service.create_session(
            user=user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            remember_me=registration_data.remember_me,
        )

        # Устанавливаем session cookie
        max_age = 60 * 60 * 24 * 30 if registration_data.remember_me else 60 * 60 * 24  # 30 дней или 1 день
        response.set_cookie(
            key="session_id", value=session.session_id, max_age=max_age, httponly=True, secure=True, samesite="lax"
        )

        # Создаем токен для верификации email
        verification_token, _ = await orbital_service.create_email_verification_token(
            user=user, custom_lifetime_hours=24
        )

        # TODO: Отправка email с токеном верификации
        # await email_service.send_verification_email(user.email, verification_token)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=3600,  # 1 час
            user=UserResponse.model_validate(user),
            requires_verification=True,
            csrf_token=session.csrf_token,
        )

    except ValueError as e:
        raise AuthRegistrationAPIException(detail=str(e))
    except Exception as e:
        raise AuthRegistrationAPIException(detail="Registration failed")


@router.post("/login", response_model=AuthResponse)
async def login_user(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    user_service: UserServiceDep,
    jwt_service: JWTServiceDep,
    session_service: SessionServiceDep,
) -> AuthResponse:
    """
    Authenticate user and create session.

    Validates user credentials, generates authentication tokens, and establishes
    a web session with optional persistent login.

    Args:
        request (Request): FastAPI request object containing client information
        response (Response): FastAPI response object for setting cookies
        login_data (LoginRequest): User login credentials
        user_service (UserService): Service for user operations
        jwt_service (JWTService): Service for JWT token operations
        session_service (SessionService): Service for web session management

    Returns:
        AuthResponse: Authentication response with tokens and user information

    Raises:
        HTTPException: 401 if credentials are invalid
        HTTPException: 500 if login process fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/auth/login" \
             -H "Content-Type: application/json" \
             -d '{
               "email_or_username": "john@example.com",
               "password": "securepass123",
               "remember_me": false
             }'
        ```
        
        Response:
        ```json
        {
          "access_token": "eyJ0eXAiOiJKV1Q...",
          "refresh_token": "eyJ0eXAiOiJKV1Q...",
          "token_type": "bearer",
          "expires_in": 3600,
          "user": {
            "id": 1,
            "username": "johndoe",
            "email": "john@example.com"
          },
          "requires_verification": false
        }
        ```
    """
    # Аутентификация пользователя
    user = await user_service.authenticate_user(
        email_or_username=login_data.email_or_username, password=login_data.password
    )

    if not user:
        raise AuthInvalidCredentialsAPIException(detail="Invalid credentials")

    try:
        # Создаем токены
        device_fingerprint = request.headers.get("user-agent", "")[:100]

        access_token = await jwt_service.create_access_token(user=user, device_fingerprint=device_fingerprint)

        refresh_token, _ = await jwt_service.create_refresh_token(
            user=user,
            device_info=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            device_fingerprint=device_fingerprint,
            remember_me=login_data.remember_me,
        )

        # Создаем веб-сессию
        session = await session_service.create_session(
            user=user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            remember_me=login_data.remember_me,
        )

        # Устанавливаем session cookie
        max_age = 60 * 60 * 24 * 30 if login_data.remember_me else 60 * 60 * 24
        response.set_cookie(
            key="session_id", value=session.session_id, max_age=max_age, httponly=True, secure=True, samesite="lax"
        )

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=3600,
            user=UserResponse.model_validate(user),
            requires_verification=not user.is_verified,
            csrf_token=session.csrf_token,
        )

    except Exception as e:
        raise AuthLoginAPIException(detail="Login failed")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_data: RefreshTokenRequest,
    jwt_service: JWTServiceDep,
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Validates the provided refresh token and issues a new access token pair.

    Args:
        refresh_data (RefreshTokenRequest): Refresh token data
        jwt_service (JWTService): Service for JWT token operations

    Returns:
        TokenResponse: New access and refresh tokens

    Raises:
        HTTPException: 401 if refresh token is invalid or expired

    Example:
        ```bash
        curl -X POST "http://localhost:8000/auth/refresh" \
             -H "Content-Type: application/json" \
             -d '{
               "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
             }'
        ```
        
        Response:
        ```json
        {
          "access_token": "eyJ0eXAiOiJKV1Q...",
          "refresh_token": "eyJ0eXAiOiJKV1Q...",
          "token_type": "bearer",
          "expires_in": 3600
        }
        ```
    """
    result = await jwt_service.refresh_access_token(refresh_data.refresh_token)

    if not result:
        raise AuthTokenExpiredAPIException(detail="Invalid or expired refresh token")

    new_access_token, new_refresh_token = result

    return TokenResponse(
        access_token=new_access_token, refresh_token=new_refresh_token, token_type="bearer", expires_in=3600
    )


@router.post("/logout")
async def logout_user(
    response: Response,
    logout_data: LogoutRequest,
    current_user: CurrentActiveUserDep,
    jwt_service: JWTServiceDep,
    session_service: SessionServiceDep,
):
    """
    Logout user and revoke authentication.

    Revokes refresh tokens, invalidates sessions, and clears authentication cookies.
    Supports logout from current device only or all devices.

    Args:
        response (Response): FastAPI response object for clearing cookies
        logout_data (LogoutRequest): Logout configuration
        current_user (User): Currently authenticated user
        jwt_service (JWTService): Service for JWT token operations
        session_service (SessionService): Service for web session management

    Returns:
        dict: Success message

    Raises:
        HTTPException: 500 if logout process fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/auth/logout" \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer your_access_token" \
             -d '{
               "logout_all_devices": true,
               "refresh_token": "eyJ..."
             }'
        ```
        
        Response:
        ```json
        {
          "message": "Logged out successfully"
        }
        ```
    """
    try:
        # Отзываем refresh токен если предоставлен
        if logout_data.refresh_token:
            await jwt_service.revoke_refresh_token(logout_data.refresh_token)

        # Деактивируем все сессии или только текущую
        if logout_data.logout_all_devices:
            await jwt_service.revoke_all_user_tokens(current_user.id)
            await session_service.invalidate_all_user_sessions(current_user.id)
        else:
            # Деактивируем только текущую сессию если есть session_id в cookies
            # Это можно сделать через additional dependency
            pass

        # Удаляем session cookie
        response.delete_cookie(key="session_id", httponly=True, secure=True, samesite="lax")

        return {"message": "Logged out successfully"}

    except Exception as e:
        raise AuthLoginAPIException(detail="Logout failed")


@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerificationRequest,
    user_service: UserServiceDep,
    orbital_service: OrbitalServiceDep,
):
    """
    Verify user email address.

    Validates email verification token and marks user email as verified.

    Args:
        verification_data (EmailVerificationRequest): Email verification token data
        user_service (UserService): Service for user operations
        orbital_service (OrbitalService): Service for orbital token operations

    Returns:
        dict: Success message

    Raises:
        HTTPException: 400 if verification token is invalid or expired
        HTTPException: 400 if email verification fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/auth/verify-email" \
             -H "Content-Type: application/json" \
             -d '{
               "token": "verification_token_here",
               "email": "john@example.com"
             }'
        ```
        
        Response:
        ```json
        {
          "message": "Email verified successfully"
        }
        ```
    """
    # Верифицируем orbital токен
    orbital_token = await orbital_service.verify_token(
        token=verification_data.token, purpose=f"email_verification:{verification_data.email}", auto_consume=True
    )

    if not orbital_token:
        raise AuthEmailVerificationAPIException(detail="Invalid or expired verification token")

    # Подтверждаем email пользователя
    success = await user_service.verify_email(orbital_token.user_id)

    if not success:
        raise AuthEmailVerificationAPIException(detail="Email verification failed")

    return {"message": "Email verified successfully"}


@router.post("/reset-password")
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    user_service: UserServiceDep,
    orbital_service: OrbitalServiceDep,
):
    """
    Request password reset.

    Generates a password reset token and sends it via email. Always returns
    success message for security reasons, regardless of email existence.

    Args:
        request (Request): FastAPI request object containing client information
        reset_data (PasswordResetRequest): Password reset request data
        user_service (UserService): Service for user operations
        orbital_service (OrbitalService): Service for orbital token operations

    Returns:
        dict: Generic success message

    Example:
        ```bash
        curl -X POST "http://localhost:8000/auth/reset-password" \
             -H "Content-Type: application/json" \
             -d '{
               "email": "john@example.com"
             }'
        ```
        
        Response:
        ```json
        {
          "message": "Password reset email sent if account exists"
        }
        ```
    """
    # Ищем пользователя по email
    user = await user_service.get_user_by_email(reset_data.email)

    if not user:
        # Возвращаем успех даже если пользователь не найден (безопасность)
        return {"message": "Password reset email sent if account exists"}

    try:
        # Создаем токен для сброса пароля
        reset_token, _ = await orbital_service.create_password_reset_token(
            user=user, ip_address=request.client.host if request.client else None
        )

        # TODO: Отправка email с токеном сброса
        # await email_service.send_password_reset_email(user.email, reset_token)

        return {"message": "Password reset email sent if account exists"}

    except Exception as e:
        # Не раскрываем детали ошибки
        return {"message": "Password reset email sent if account exists"}


@router.post("/reset-password/confirm")
async def confirm_password_reset(
    confirm_data: PasswordResetConfirm,
    user_service: UserServiceDep,
    orbital_service: OrbitalServiceDep,
    jwt_service: JWTServiceDep,
):
    """
    Confirm password reset.

    Validates password reset token and sets new password. Revokes all existing
    user tokens for security.

    Args:
        confirm_data (PasswordResetConfirm): Password reset confirmation data
        user_service (UserService): Service for user operations
        orbital_service (OrbitalService): Service for orbital token operations
        jwt_service (JWTService): Service for JWT token operations

    Returns:
        dict: Success message

    Raises:
        HTTPException: 400 if reset token is invalid or expired
        HTTPException: 400 if password reset fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/auth/reset-password/confirm" \
             -H "Content-Type: application/json" \
             -d '{
               "token": "reset_token_here",
               "new_password": "newsecurepass123"
             }'
        ```
        
        Response:
        ```json
        {
          "message": "Password reset successfully"
        }
        ```
    """
    # Верифицируем токен сброса пароля
    orbital_token = await orbital_service.verify_token(
        token=confirm_data.token, purpose="password_reset", auto_consume=True
    )

    if not orbital_token:
        raise AuthPasswordResetAPIException(detail="Invalid or expired reset token")

    # Сбрасываем пароль
    success = await user_service.reset_password(user_id=orbital_token.user_id, new_password=confirm_data.new_password)

    if not success:
        raise AuthPasswordResetAPIException(detail="Password reset failed")

    # Отзываем все токены пользователя для безопасности
    await jwt_service.revoke_all_user_tokens(orbital_token.user_id)

    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentActiveUserDep,
    user_service: UserServiceDep,
):
    """
    Change user password.

    Changes user password after validating current password. Requires authentication.

    Args:
        password_data (ChangePasswordRequest): Password change data
        current_user (User): Currently authenticated user
        user_service (UserService): Service for user operations

    Returns:
        dict: Success message

    Raises:
        HTTPException: 400 if current password is invalid or change fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/auth/change-password" \
             -H "Content-Type: application/json" \
             -H "Authorization: Bearer your_access_token" \
             -d '{
               "current_password": "oldpass123",
               "new_password": "newpass123"
             }'
        ```
        
        Response:
        ```json
        {
          "message": "Password changed successfully"
        }
        ```
    """
    success = await user_service.change_password(
        user_id=current_user.id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
    )

    if not success:
        raise AuthPasswordResetAPIException(detail="Invalid current password or password change failed")

    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentActiveUserDep) -> UserResponse:
    """
    Get current user information.

    Returns profile information for the currently authenticated user.

    Args:
        current_user (User): Currently authenticated user

    Returns:
        UserResponse: Current user profile information

    Example:
        ```bash
        curl -X GET "http://localhost:8000/auth/me" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "id": 1,
          "username": "johndoe",
          "email": "john@example.com",
          "is_active": true,
          "is_verified": true,
          "role": "user"
        }
        ```
    """
    return UserResponse.model_validate(current_user)


@router.get("/sessions")
async def get_user_sessions(
    current_user: CurrentActiveUserDep,
    session_service: SessionServiceDep,
):
    """
    Get user active sessions.

    Returns list of active sessions for the current user with device and location info.

    Args:
        current_user (User): Currently authenticated user
        session_service (SessionService): Service for web session management

    Returns:
        dict: Session information including active sessions list

    Example:
        ```bash
        curl -X GET "http://localhost:8000/auth/sessions" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "sessions": [
            {
              "session_id": "session_123",
              "device_info": "Mozilla/5.0...",
              "ip_address": "192.168.1.1",
              "created_at": "2024-01-01T10:00:00Z",
              "last_activity": "2024-01-01T12:00:00Z"
            }
          ]
        }
        ```
    """
    session_info = await session_service.get_user_session_info(current_user.id)
    return session_info


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: CurrentActiveUserDep,
    session_service: SessionServiceDep,
):
    """
    Revoke specific user session.

    Invalidates a specific session belonging to the current user.

    Args:
        session_id (str): Session identifier to revoke
        current_user (User): Currently authenticated user
        session_service (SessionService): Service for web session management

    Returns:
        dict: Success message

    Raises:
        HTTPException: 404 if session not found or doesn't belong to user
        HTTPException: 400 if session revocation fails

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/auth/sessions/session_123" \
             -H "Authorization: Bearer your_access_token"
        ```
        
        Response:
        ```json
        {
          "message": "Session revoked successfully"
        }
        ```
    """
    # Получаем сессию и проверяем принадлежность пользователю
    session = await session_service.get_session(session_id)

    if not session or session.user_id != current_user.id:
        raise AuthSessionNotFoundAPIException(detail="Session not found")

    success = await session_service.invalidate_session(session_id)

    if not success:
        raise AuthSessionRevokeAPIException(detail="Failed to revoke session")

    return {"message": "Session revoked successfully"}
