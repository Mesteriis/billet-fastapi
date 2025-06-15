"""
Основной сервис аутентификации.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User
from apps.users.repository import UserRepository
from apps.users.schemas import UserCreate, UserResponse

from .jwt_service import JWTService, jwt_service
from .models import RefreshToken
from .password_service import password_service
from .schemas import LoginResponse, TokenPair

tracer = trace.get_tracer(__name__)


class AuthService:
    """Сервис аутентификации."""

    def __init__(self, jwt_service_instance: JWTService | None = None):
        self.user_repository = UserRepository()
        self._jwt_service = jwt_service_instance or jwt_service

    async def register_user(
        self, db: AsyncSession, *, user_data: UserCreate, auto_verify: bool = False
    ) -> UserResponse:
        """Регистрация нового пользователя.

        Args:
            db: Сессия базы данных
            user_data: Данные для регистрации
            auto_verify: Автоматически верифицировать пользователя

        Returns:
            Данные созданного пользователя

        Raises:
            HTTPException: Если email или username уже заняты
        """
        with tracer.start_as_current_span("auth_service.register_user") as span:
            span.set_attribute("user.email", user_data.email)
            span.set_attribute("user.username", user_data.username)
            span.set_attribute("auto_verify", auto_verify)

            # Проверяем, не занят ли email
            if await self.user_repository.is_email_taken(db, email=user_data.email):
                span.set_attribute("error", "Email already taken")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует"
                )

            # Проверяем, не занято ли имя пользователя
            if await self.user_repository.is_username_taken(db, username=user_data.username):
                span.set_attribute("error", "Username already taken")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким именем уже существует"
                )

            # Проверяем силу пароля
            is_strong, errors = password_service.is_password_strong(user_data.password)
            if not is_strong:
                span.set_attribute("error", "Weak password")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Слабый пароль: {', '.join(errors)}"
                )

            # Хешируем пароль
            hashed_password = password_service.hash_password(user_data.password)

            # Создаем пользователя
            user_dict = user_data.model_dump(exclude={"password", "password_confirm"})
            user_dict["hashed_password"] = hashed_password

            if auto_verify:
                user_dict["is_verified"] = True
                user_dict["email_verified_at"] = datetime.now(tz=utc)()

            user = await self.user_repository.create(db, obj_in=user_dict)
            await db.commit()

            span.set_attribute("user.id", str(user.id))
            span.set_attribute("user.created", True)

            return UserResponse.model_validate(user)

    async def authenticate_user(self, db: AsyncSession, *, email: str, password: str) -> User | None:
        """Аутентификация пользователя.

        Args:
            db: Сессия базы данных
            email: Email пользователя
            password: Пароль

        Returns:
            Пользователь если аутентификация успешна, None если нет
        """
        with tracer.start_as_current_span("auth_service.authenticate_user") as span:
            span.set_attribute("user.email", email)

            user = await self.user_repository.get_by_email(db, email=email)
            if not user:
                span.set_attribute("error", "User not found")
                return None

            span.set_attribute("user.id", str(user.id))
            span.set_attribute("user.is_active", user.is_active)

            if not user.is_active:
                span.set_attribute("error", "User inactive")
                return None

            if not password_service.verify_password(password, user.hashed_password):
                span.set_attribute("error", "Invalid password")
                return None

            # Обновляем время последнего входа
            user.update_last_login()
            await db.commit()

            span.set_attribute("auth.success", True)
            return user

    async def login(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> LoginResponse:
        """Вход пользователя в систему.

        Args:
            db: Сессия базы данных
            email: Email пользователя
            password: Пароль
            user_agent: User Agent
            ip_address: IP адрес

        Returns:
            Ответ с токенами и данными пользователя

        Raises:
            HTTPException: Если аутентификация не удалась
        """
        with tracer.start_as_current_span("auth_service.login") as span:
            span.set_attribute("user.email", email)

            user = await self.authenticate_user(db, email=email, password=password)
            if not user:
                span.set_attribute("error", "Authentication failed")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Неверный email или пароль",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Создаем токены
            access_token, refresh_token, jti = self._jwt_service.create_token_pair(
                user_id=str(user.id),
                email=user.email,
                username=user.username,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                is_verified=user.is_verified,
            )

            # Сохраняем refresh токен в БД
            refresh_token_data = {
                "user_id": user.id,
                "jti": jti,
                "expires_at": self._jwt_service.get_token_expiry("refresh"),
                "user_agent": user_agent,
                "ip_address": ip_address,
            }

            refresh_token_obj = RefreshToken(**refresh_token_data)
            db.add(refresh_token_obj)
            await db.commit()

            tokens = TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self._jwt_service.access_token_expire_minutes * 60,
            )

            user_data = UserResponse.model_validate(user)

            span.set_attribute("user.id", str(user.id))
            span.set_attribute("login.success", True)

            return LoginResponse(user=user_data.model_dump(), tokens=tokens)

    async def refresh_token(
        self, db: AsyncSession, *, refresh_token: str, user_agent: str | None = None, ip_address: str | None = None
    ) -> TokenPair:
        """Обновление access токена.

        Args:
            db: Сессия базы данных
            refresh_token: Refresh токен
            user_agent: User Agent
            ip_address: IP адрес

        Returns:
            Новая пара токенов

        Raises:
            HTTPException: Если refresh токен невалидный
        """
        with tracer.start_as_current_span("auth_service.refresh_token") as span:
            # Проверяем refresh токен
            claims = self._jwt_service.verify_token(refresh_token, "refresh")
            if not claims:
                span.set_attribute("error", "Invalid refresh token")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный refresh токен")

            # Проверяем токен в БД
            db_token = await db.get(RefreshToken, {"jti": claims.jti})
            if not db_token or not db_token.is_valid:
                span.set_attribute("error", "Refresh token not found or invalid")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh токен отозван или не найден"
                )

            # Получаем пользователя
            user = await self.user_repository.get(db, id=uuid.UUID(claims.sub))
            if not user or not user.is_active:
                span.set_attribute("error", "User not found or inactive")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден или неактивен"
                )

            # Отзываем старый refresh токен
            db_token.revoke()

            # Создаем новые токены
            access_token, new_refresh_token, new_jti = self._jwt_service.create_token_pair(
                user_id=str(user.id),
                email=user.email,
                username=user.username,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                is_verified=user.is_verified,
            )

            # Сохраняем новый refresh токен
            new_refresh_token_data = {
                "user_id": user.id,
                "jti": new_jti,
                "expires_at": self._jwt_service.get_token_expiry("refresh"),
                "user_agent": user_agent,
                "ip_address": ip_address,
            }

            new_refresh_token_obj = RefreshToken(**new_refresh_token_data)
            db.add(new_refresh_token_obj)
            await db.commit()

            span.set_attribute("user.id", str(user.id))
            span.set_attribute("refresh.success", True)

            return TokenPair(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=self._jwt_service.access_token_expire_minutes * 60,
            )

    async def logout(
        self,
        db: AsyncSession,
        *,
        refresh_token: str | None = None,
        user_id: uuid.UUID | None = None,
        revoke_all: bool = False,
    ) -> None:
        """Выход пользователя из системы.

        Args:
            db: Сессия базы данных
            refresh_token: Refresh токен для отзыва
            user_id: ID пользователя
            revoke_all: Отозвать все токены пользователя
        """
        with tracer.start_as_current_span("auth_service.logout") as span:
            span.set_attribute("revoke_all", revoke_all)

            if revoke_all and user_id:
                # Отзываем все токены пользователя
                user = await self.user_repository.get(db, id=user_id)
                if user:
                    for token in user.refresh_tokens:
                        if token.is_valid:
                            token.revoke()
                    await db.commit()
                    span.set_attribute("revoked_tokens", len(user.refresh_tokens))
            elif refresh_token:
                # Отзываем конкретный токен
                claims = self._jwt_service.verify_token(refresh_token, "refresh")
                if claims:
                    db_token = await db.get(RefreshToken, {"jti": claims.jti})
                    if db_token and db_token.is_valid:
                        db_token.revoke()
                        await db.commit()
                        span.set_attribute("token_revoked", True)

            span.set_attribute("logout.success", True)

    async def verify_access_token(self, db: AsyncSession, *, access_token: str) -> User | None:
        """Проверка access токена и получение пользователя.

        Args:
            db: Сессия базы данных
            access_token: Access токен

        Returns:
            Пользователь если токен валидный, None если нет
        """
        with tracer.start_as_current_span("auth_service.verify_access_token") as span:
            claims = self._jwt_service.verify_token(access_token, "access")
            if not claims:
                span.set_attribute("error", "Invalid access token")
                return None

            user = await self.user_repository.get(db, id=uuid.UUID(claims.sub))
            if not user or not user.is_active:
                span.set_attribute("error", "User not found or inactive")
                return None

            span.set_attribute("user.id", str(user.id))
            span.set_attribute("token.valid", True)

            return user


# Синглтон сервиса
auth_service = AuthService()
