"""
Сервис для работы с JWT токенами.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import jwt
from opentelemetry import trace
from pydantic import ValidationError

from core.config import get_settings
from tools.pydantic import BaseModel

tracer = trace.get_tracer(__name__)
settings = get_settings()


class JWTClaims(BaseModel):
    """Структура JWT токена."""

    sub: str  # Subject (user ID)
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    token_type: str  # "access" или "refresh"
    exp: int  # Expiration time
    iat: int  # Issued at
    jti: str  # JWT ID (для refresh токена)


class JWTService:
    """Сервис для работы с JWT токенами."""

    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 30)

    def create_access_token(
        self,
        user_id: str,
        email: str,
        username: str,
        is_active: bool = True,
        is_superuser: bool = False,
        is_verified: bool = False,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Создать access токен.

        Args:
            user_id: ID пользователя
            email: Email пользователя
            username: Имя пользователя
            is_active: Активность пользователя
            is_superuser: Суперпользователь
            is_verified: Верификация пользователя
            expires_delta: Время жизни токена

        Returns:
            JWT access токен
        """
        with tracer.start_as_current_span("jwt_service.create_access_token") as span:
            span.set_attribute("user.id", user_id)
            span.set_attribute("user.email", email)
            span.set_attribute("token.type", "access")

            if expires_delta:
                expire = datetime.now(tz=utc)() + expires_delta
            else:
                expire = datetime.now(tz=utc)() + timedelta(minutes=self.access_token_expire_minutes)

            now = datetime.now(tz=utc)()

            claims = JWTClaims(
                sub=user_id,
                email=email,
                username=username,
                is_active=is_active,
                is_superuser=is_superuser,
                is_verified=is_verified,
                token_type="access",
                exp=int(expire.timestamp()),
                iat=int(now.timestamp()),
                jti="",  # Не используется для access токенов
            )

            token = jwt.encode(claims.model_dump(exclude={"jti"}), self.secret_key, algorithm=self.algorithm)

            span.set_attribute("token.expires_at", expire.isoformat())
            return token

    def create_refresh_token(
        self,
        user_id: str,
        email: str,
        username: str,
        is_active: bool = True,
        is_superuser: bool = False,
        is_verified: bool = False,
        expires_delta: timedelta | None = None,
    ) -> tuple[str, str]:
        """Создать refresh токен.

        Args:
            user_id: ID пользователя
            email: Email пользователя
            username: Имя пользователя
            is_active: Активность пользователя
            is_superuser: Суперпользователь
            is_verified: Верификация пользователя
            expires_delta: Время жизни токена

        Returns:
            Tuple из JWT refresh токена и JTI
        """
        with tracer.start_as_current_span("jwt_service.create_refresh_token") as span:
            span.set_attribute("user.id", user_id)
            span.set_attribute("user.email", email)
            span.set_attribute("token.type", "refresh")

            if expires_delta:
                expire = datetime.now(tz=utc)() + expires_delta
            else:
                expire = datetime.now(tz=utc)() + timedelta(days=self.refresh_token_expire_days)

            now = datetime.now(tz=utc)()
            jti = str(uuid.uuid4())

            claims = JWTClaims(
                sub=user_id,
                email=email,
                username=username,
                is_active=is_active,
                is_superuser=is_superuser,
                is_verified=is_verified,
                token_type="refresh",
                exp=int(expire.timestamp()),
                iat=int(now.timestamp()),
                jti=jti,
            )

            token = jwt.encode(claims.model_dump(), self.secret_key, algorithm=self.algorithm)

            span.set_attribute("token.jti", jti)
            span.set_attribute("token.expires_at", expire.isoformat())
            return token, jti

    def verify_token(self, token: str, expected_type: str = "access") -> JWTClaims | None:
        """Проверить и декодировать токен.

        Args:
            token: JWT токен
            expected_type: Ожидаемый тип токена ("access" или "refresh")

        Returns:
            Данные токена или None если токен невалидный
        """
        with tracer.start_as_current_span("jwt_service.verify_token") as span:
            span.set_attribute("token.type", expected_type)

            try:
                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

                # Добавляем jti если его нет (для обратной совместимости)
                if "jti" not in payload:
                    payload["jti"] = ""

                claims = JWTClaims.model_validate(payload)

                # Проверяем тип токена
                if claims.token_type != expected_type:
                    span.set_attribute("error", f"Wrong token type: {claims.token_type}")
                    return None

                # Проверяем срок действия
                if datetime.now(tz=utc)().timestamp() > claims.exp:
                    span.set_attribute("error", "Token expired")
                    return None

                span.set_attribute("user.id", claims.sub)
                span.set_attribute("user.email", claims.email)
                span.set_attribute("token.valid", True)

                return claims

            except jwt.ExpiredSignatureError:
                span.set_attribute("error", "Token expired")
                return None
            except jwt.InvalidTokenError:
                span.set_attribute("error", "Invalid token")
                return None
            except ValidationError as e:
                span.set_attribute("error", f"Validation error: {e!s}")
                return None

    def create_token_pair(
        self,
        user_id: str,
        email: str,
        username: str,
        is_active: bool = True,
        is_superuser: bool = False,
        is_verified: bool = False,
    ) -> tuple[str, str, str]:
        """Создать пару токенов (access + refresh).

        Args:
            user_id: ID пользователя
            email: Email пользователя
            username: Имя пользователя
            is_active: Активность пользователя
            is_superuser: Суперпользователь
            is_verified: Верификация пользователя

        Returns:
            Tuple из access токена, refresh токена и JTI
        """
        with tracer.start_as_current_span("jwt_service.create_token_pair") as span:
            span.set_attribute("user.id", user_id)
            span.set_attribute("user.email", email)

            access_token = self.create_access_token(
                user_id=user_id,
                email=email,
                username=username,
                is_active=is_active,
                is_superuser=is_superuser,
                is_verified=is_verified,
            )

            refresh_token, jti = self.create_refresh_token(
                user_id=user_id,
                email=email,
                username=username,
                is_active=is_active,
                is_superuser=is_superuser,
                is_verified=is_verified,
            )

            return access_token, refresh_token, jti

    def get_token_expiry(self, token_type: str = "access") -> datetime:
        """Получить время истечения токена.

        Args:
            token_type: Тип токена ("access" или "refresh")

        Returns:
            Время истечения
        """
        now = datetime.now(tz=utc)()
        if token_type == "access":
            return now + timedelta(minutes=self.access_token_expire_minutes)
        elif token_type == "refresh":
            return now + timedelta(days=self.refresh_token_expire_days)
        else:
            raise ValueError(f"Unknown token type: {token_type}")


# Синглтон сервиса
jwt_service = JWTService()
