"""
Сервис для работы с JWT токенами.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.models.auth_models import RefreshToken
from apps.auth.repo.refresh_token_repo import RefreshTokenRepository
from apps.auth.schemas.token_schemas import JWTPayload, RefreshTokenPayload
from core.config import get_settings

if TYPE_CHECKING:
    from apps.users.interfaces import UserIdentity

logger = logging.getLogger("auth.jwt_service")
settings = get_settings()


class JWTService:
    """
    Сервис для работы с JWT токенами.

    Обеспечивает создание, валидацию и управление access и refresh токенами.
    Поддерживает безопасное хранение refresh токенов в БД с хешированием.
    """

    def __init__(self, refresh_token_repo: RefreshTokenRepository, user_repo):
        self._refresh_token_repo = refresh_token_repo
        self._user_repo = user_repo
        self._secret_key = settings.SECRET_KEY
        self._algorithm = settings.ALGORITHM
        self._access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self._refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def _generate_jti(self) -> str:
        """Генерировать уникальный JWT ID."""
        return str(uuid.uuid4())

    def _hash_token(self, token: str) -> str:
        """Хешировать токен для безопасного хранения в БД."""
        return hashlib.sha256(token.encode()).hexdigest()

    def _create_jwt_payload(
        self,
        user: "UserIdentity",
        token_type: str = "access",
        expires_delta: timedelta | None = None,
        additional_claims: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Создать полезную нагрузку JWT токена.

        :param user: Пользователь
        :param token_type: Тип токена (access/refresh)
        :param expires_delta: Время жизни токена
        :param additional_claims: Дополнительные поля
        :return: Словарь с payload
        """
        now = datetime.utcnow()

        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self._access_token_expire_minutes)

        # Базовые claims
        payload = {
            "sub": str(user.id),
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_superuser": user.is_superuser,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": self._generate_jti(),
            "token_type": token_type,
        }

        # Добавляем дополнительные claims
        if additional_claims:
            payload.update(additional_claims)

        return payload

    async def create_access_token(
        self,
        user: "UserIdentity",
        expires_delta: timedelta | None = None,
        device_fingerprint: str | None = None,
        **additional_claims,
    ) -> str:
        """
        Создать access токен.

        :param user: Пользователь
        :param expires_delta: Время жизни токена
        :param device_fingerprint: Отпечаток устройства
        :param additional_claims: Дополнительные поля
        :return: Закодированный JWT токен
        """
        logger.info(f"Creating access token for user {user.id}")

        claims = additional_claims.copy()
        if device_fingerprint:
            claims["device_fingerprint"] = device_fingerprint

        # Добавляем права пользователя
        permissions = self._get_user_permissions(user)
        claims["permissions"] = permissions

        payload = self._create_jwt_payload(
            user=user, token_type="access", expires_delta=expires_delta, additional_claims=claims
        )

        try:
            token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
            logger.debug(f"Access token created for user {user.id}")
            return token
        except Exception as e:
            logger.error(f"Failed to create access token for user {user.id}: {e}")
            raise

    async def create_refresh_token(
        self,
        user: "UserIdentity",
        device_info: str | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
        remember_me: bool = False,
    ) -> tuple[str, RefreshToken]:
        """
        Создать refresh токен и сохранить в БД.

        :param user: Пользователь
        :param device_info: Информация об устройстве
        :param ip_address: IP адрес
        :param device_fingerprint: Отпечаток устройства
        :param remember_me: Увеличить время жизни токена
        :return: Кортеж (токен, объект RefreshToken)
        """
        logger.info(f"Creating refresh token for user {user.id}")

        # Определяем время жизни токена
        expire_days = self._refresh_token_expire_days
        if remember_me:
            expire_days *= 2  # Удваиваем время жизни если "запомнить меня"

        expires_delta = timedelta(days=expire_days)
        expires_at = datetime.utcnow() + expires_delta

        # Создаем payload для refresh токена
        payload = {
            "sub": str(user.id),
            "user_id": str(user.id),
            "token_id": str(uuid.uuid4()),
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": self._generate_jti(),
            "token_type": "refresh",
        }

        if device_fingerprint:
            payload["device_fingerprint"] = device_fingerprint

        try:
            # Кодируем токен
            token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
            token_hash = self._hash_token(token)

            # Сохраняем в БД
            refresh_token_data = {
                "user_id": user.id,
                "token_hash": token_hash,
                "expires_at": expires_at,
                "device_info": device_info,
                "ip_address": ip_address,
                "device_fingerprint": device_fingerprint,
                "is_revoked": False,
            }

            refresh_token_obj = await self._refresh_token_repo.create(refresh_token_data)

            logger.debug(f"Refresh token created and saved for user {user.id}")
            return token, refresh_token_obj

        except Exception as e:
            logger.error(f"Failed to create refresh token for user {user.id}: {e}")
            raise

    async def verify_access_token(self, token: str) -> JWTPayload | None:
        """
        Верифицировать access токен.

        :param token: JWT токен
        :return: Payload токена или None если невалидный
        """
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])

            # Проверяем тип токена
            if payload.get("token_type") != "access":
                logger.warning("Invalid token type for access token verification")
                return None

            # Создаем объект JWTPayload
            jwt_payload = JWTPayload(**payload)

            # Проверяем истечение
            if jwt_payload.is_expired:
                logger.debug("Access token has expired")
                return None

            logger.debug(f"Access token verified for user {jwt_payload.user_id}")
            return jwt_payload

        except jwt.ExpiredSignatureError:
            logger.debug("Access token signature has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid access token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying access token: {e}")
            return None

    async def verify_refresh_token(self, token: str) -> RefreshToken | None:
        """
        Верифицировать refresh токен.

        :param token: JWT refresh токен
        :return: Объект RefreshToken из БД или None если невалидный
        """
        try:
            # Декодируем токен
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])

            # Проверяем тип токена
            if payload.get("token_type") != "refresh":
                logger.warning("Invalid token type for refresh token verification")
                return None

            # Проверяем в БД
            token_hash = self._hash_token(token)
            refresh_token = await self._refresh_token_repo.get_valid_token(token_hash)

            if not refresh_token:
                logger.debug("Refresh token not found or invalid in database")
                return None

            # Обновляем время последнего использования
            await self._refresh_token_repo.update_last_used(token_hash)

            logger.debug(f"Refresh token verified for user {refresh_token.user_id}")
            return refresh_token

        except jwt.ExpiredSignatureError:
            logger.debug("Refresh token signature has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying refresh token: {e}")
            return None

    async def revoke_refresh_token(self, token: str) -> bool:
        """
        Отозвать refresh токен.

        :param token: JWT refresh токен
        :return: True если токен был отозван
        """
        try:
            token_hash = self._hash_token(token)
            success = await self._refresh_token_repo.revoke_token(token_hash)

            if success:
                logger.info(f"Refresh token revoked: {token_hash[:16]}...")
            else:
                logger.warning(f"Failed to revoke refresh token: {token_hash[:16]}...")

            return success

        except Exception as e:
            logger.error(f"Error revoking refresh token: {e}")
            return False

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        """
        Отозвать все refresh токены пользователя.

        :param user_id: ID пользователя
        :return: Количество отозванных токенов
        """
        try:
            count = await self._refresh_token_repo.revoke_all_user_tokens(user_id)
            logger.info(f"Revoked {count} refresh tokens for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Error revoking all tokens for user {user_id}: {e}")
            return 0

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str] | None:
        """
        Обновить access токен используя refresh токен.

        :param refresh_token: Refresh токен
        :return: Кортеж (новый access токен, новый refresh токен) или None
        """
        logger.info("Refreshing access token")

        # Верифицируем refresh токен
        refresh_token_obj = await self.verify_refresh_token(refresh_token)
        if not refresh_token_obj:
            logger.warning("Invalid refresh token for access token refresh")
            return None

        # Загружаем пользователя
        user = refresh_token_obj.user
        if not user or not user.can_login:
            logger.warning(f"User {refresh_token_obj.user_id} cannot login")
            return None

        try:
            # Создаем новый access токен
            new_access_token = await self.create_access_token(
                user=user, device_fingerprint=refresh_token_obj.device_fingerprint
            )

            # Создаем новый refresh токен
            new_refresh_token, _ = await self.create_refresh_token(
                user=user,
                device_info=refresh_token_obj.device_info,
                ip_address=refresh_token_obj.ip_address,
                device_fingerprint=refresh_token_obj.device_fingerprint,
            )

            # Отзываем старый refresh токен
            await self.revoke_refresh_token(refresh_token)

            logger.info(f"Access token refreshed for user {user.id}")
            return new_access_token, new_refresh_token

        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None

    def _get_user_permissions(self, user: "UserIdentity") -> list[str]:
        """
        Получить список разрешений пользователя на основе роли.

        :param user: Пользователь
        :return: Список разрешений
        """
        permissions = ["read:profile"]  # Базовые права

        if user.is_verified:
            permissions.extend(["write:profile", "create:posts", "comment:posts"])

        user_role = user.role.value if hasattr(user.role, "value") else user.role

        if user_role == "moderator":
            permissions.extend(["moderate:posts", "moderate:comments", "read:users"])

        if user_role == "admin":
            permissions.extend(["read:users", "write:users", "delete:users", "read:admin", "moderate:all"])

        if user.is_superuser:
            permissions.extend(["write:admin", "delete:admin", "manage:system", "access:all"])

        return list(set(permissions))  # Убираем дубликаты

    async def get_active_tokens_count(self, user_id: uuid.UUID) -> int:
        """
        Получить количество активных refresh токенов пользователя.

        :param user_id: ID пользователя
        :return: Количество активных токенов
        """
        return await self._refresh_token_repo.count_active_tokens(user_id)

    async def cleanup_expired_tokens(self) -> int:
        """
        Очистить истекшие refresh токены.

        :return: Количество удаленных токенов
        """
        try:
            count = await self._refresh_token_repo.cleanup_expired_tokens()
            logger.info(f"Cleaned up {count} expired refresh tokens")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {e}")
            return 0

    async def get_user_tokens_info(self, user_id: uuid.UUID) -> dict[str, Any]:
        """
        Получить информацию о токенах пользователя.

        :param user_id: ID пользователя
        :return: Информация о токенах
        """
        try:
            active_tokens = await self._refresh_token_repo.list_active_tokens(user_id)
            total_tokens = await self._refresh_token_repo.count(user_id=user_id, include_deleted=False)

            return {
                "user_id": user_id,
                "active_tokens_count": len(active_tokens),
                "total_tokens_count": total_tokens,
                "active_tokens": [
                    {
                        "id": str(token.id),
                        "device_info": token.device_info,
                        "ip_address": token.ip_address,
                        "created_at": token.created_at,
                        "last_used_at": token.last_used_at,
                        "expires_at": token.expires_at,
                    }
                    for token in active_tokens
                ],
            }
        except Exception as e:
            logger.error(f"Error getting user tokens info: {e}")
            return {"user_id": user_id, "error": str(e)}
