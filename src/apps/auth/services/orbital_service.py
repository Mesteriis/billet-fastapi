"""
Сервис для работы с одноразовыми токенами (orbital tokens).
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.models.auth_models import OrbitalToken
from apps.auth.repo.orbital_token_repo import OrbitalTokenRepository
from apps.auth.schemas.token_schemas import OrbitalTokenType
from core.config import get_settings

if TYPE_CHECKING:
    from apps.users.models.user_models import User

logger = logging.getLogger("auth.orbital_service")
settings = get_settings()


class OrbitalService:
    """
    Сервис для работы с одноразовыми токенами (orbital tokens).

    Обеспечивает создание, валидацию и управление одноразовыми токенами
    для различных операций: подтверждение email, сброс пароля, верификация и т.д.
    """

    # Время жизни токенов по типам (в минутах)
    TOKEN_LIFETIMES = {
        OrbitalTokenType.EMAIL_VERIFICATION: 60 * 24,  # 24 часа
        OrbitalTokenType.PASSWORD_RESET: 30,  # 30 минут
        OrbitalTokenType.TWO_FACTOR_AUTH: 5,  # 5 минут
        OrbitalTokenType.PHONE_VERIFICATION: 15,  # 15 минут
        OrbitalTokenType.ACCOUNT_ACTIVATION: 60 * 72,  # 72 часа
        OrbitalTokenType.LOGIN_VERIFICATION: 10,  # 10 минут
        OrbitalTokenType.CUSTOM: 60,  # 1 час (по умолчанию)
    }

    def __init__(self, orbital_token_repo: OrbitalTokenRepository, user_repo):
        self._orbital_token_repo = orbital_token_repo
        self._user_repo = user_repo

    def _generate_token(self, length: int = 32) -> str:
        """
        Генерировать криптографически стойкий токен.

        :param length: Длина токена в байтах
        :return: Hex-строка токена
        """
        return secrets.token_hex(length)

    def _generate_code(self, length: int = 6) -> str:
        """
        Генерировать цифровой код.

        :param length: Длина кода
        :return: Строка с цифрами
        """
        return "".join(secrets.choice("0123456789") for _ in range(length))

    def _hash_token(self, token: str) -> str:
        """
        Хешировать токен для безопасного хранения в БД.

        :param token: Токен для хеширования
        :return: SHA-256 хеш токена
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def _get_token_lifetime(self, token_type: OrbitalTokenType, custom_minutes: int | None = None) -> timedelta:
        """
        Получить время жизни токена по типу.

        :param token_type: Тип токена
        :param custom_minutes: Пользовательское время в минутах
        :return: Время жизни токена
        """
        if custom_minutes:
            return timedelta(minutes=custom_minutes)

        minutes = self.TOKEN_LIFETIMES.get(token_type, 60)
        return timedelta(minutes=minutes)

    async def create_token(
        self,
        user: "User",
        token_type: OrbitalTokenType,
        purpose: str,
        token_length: int = 32,
        custom_lifetime_minutes: int | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        use_numeric_code: bool = False,
    ) -> tuple[str, OrbitalToken]:
        """
        Создать новый одноразовый токен.

        :param user: Пользователь
        :param token_type: Тип токена
        :param purpose: Назначение токена
        :param token_length: Длина токена (для hex) или кода (для numeric)
        :param custom_lifetime_minutes: Пользовательское время жизни
        :param metadata: Дополнительные данные
        :param ip_address: IP адрес
        :param use_numeric_code: Использовать цифровой код вместо hex токена
        :return: Кортеж (токен, объект OrbitalToken)
        """
        logger.info(f"Creating {token_type.value} token for user {user.id}, purpose: {purpose}")

        # Генерируем токен
        if use_numeric_code:
            token = self._generate_code(token_length)
        else:
            token = self._generate_token(token_length)

        token_hash = self._hash_token(token)

        # Определяем время истечения
        lifetime = self._get_token_lifetime(token_type, custom_lifetime_minutes)
        expires_at = datetime.utcnow() + lifetime

        try:
            # Создаем запись в БД
            orbital_token_data = {
                "user_id": user.id,
                "token_hash": token_hash,
                "token_type": token_type,
                "purpose": purpose,
                "expires_at": expires_at,
                "token_metadata": metadata or {},
                "ip_address": ip_address,
                "is_used": False,
            }

            orbital_token_obj = await self._orbital_token_repo.create(orbital_token_data)

            logger.debug(f"Orbital token created for user {user.id}: {token_type.value}")
            return token, orbital_token_obj

        except Exception as e:
            logger.error(f"Failed to create orbital token for user {user.id}: {e}")
            raise

    async def verify_token(
        self,
        token: str,
        token_type: OrbitalTokenType | None = None,
        purpose: str | None = None,
        user_id: uuid.UUID | None = None,
        auto_consume: bool = True,
    ) -> OrbitalToken | None:
        """
        Верифицировать и опционально использовать токен.

        :param token: Токен для верификации
        :param token_type: Ожидаемый тип токена (опционально)
        :param purpose: Ожидаемое назначение (опционально)
        :param user_id: Ожидаемый ID пользователя (опционально)
        :param auto_consume: Автоматически пометить токен как использованный
        :return: Объект OrbitalToken или None если невалидный
        """
        token_hash = self._hash_token(token)

        try:
            # Ищем токен в БД
            orbital_token = await self._orbital_token_repo.get_valid_token(
                token_hash=token_hash, token_type=token_type, purpose=purpose, user_id=user_id
            )

            if not orbital_token:
                logger.debug(f"Orbital token not found or invalid: {token_hash[:16]}...")
                return None

            # Проверяем истечение
            if orbital_token.is_expired:
                logger.debug(f"Orbital token has expired: {orbital_token.id}")
                return None

            # Проверяем использование
            if orbital_token.is_used:
                logger.warning(f"Orbital token already used: {orbital_token.id}")
                return None

            # Автоматически помечаем как использованный
            if auto_consume:
                await self.consume_token(orbital_token.id)
                # Обновляем объект
                orbital_token.is_used = True
                orbital_token.used_at = datetime.utcnow()

            logger.info(f"Orbital token verified for user {orbital_token.user_id}: {orbital_token.token_type.value}")
            return orbital_token

        except Exception as e:
            logger.error(f"Error verifying orbital token: {e}")
            return None

    async def consume_token(self, token_id: uuid.UUID) -> bool:
        """
        Пометить токен как использованный.

        :param token_id: ID токена
        :return: True если токен был помечен как использованный
        """
        try:
            success = await self._orbital_token_repo.consume_token(token_id)

            if success:
                logger.info(f"Orbital token consumed: {token_id}")
            else:
                logger.warning(f"Failed to consume orbital token: {token_id}")

            return success

        except Exception as e:
            logger.error(f"Error consuming orbital token {token_id}: {e}")
            return False

    async def revoke_token(self, token_id: uuid.UUID) -> bool:
        """
        Отозвать токен (пометить как использованный принудительно).

        :param token_id: ID токена
        :return: True если токен был отозван
        """
        return await self.consume_token(token_id)

    async def revoke_user_tokens(
        self, user_id: uuid.UUID, token_type: OrbitalTokenType | None = None, purpose: str | None = None
    ) -> int:
        """
        Отозвать все токены пользователя определенного типа.

        :param user_id: ID пользователя
        :param token_type: Тип токенов (опционально)
        :param purpose: Назначение токенов (опционально)
        :return: Количество отозванных токенов
        """
        try:
            count = await self._orbital_token_repo.revoke_user_tokens(
                user_id=user_id, token_type=token_type, purpose=purpose
            )

            logger.info(f"Revoked {count} orbital tokens for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Error revoking user tokens: {e}")
            return 0

    async def cleanup_expired_tokens(self) -> int:
        """
        Очистить истекшие токены.

        :return: Количество удаленных токенов
        """
        try:
            count = await self._orbital_token_repo.cleanup_expired_tokens()
            logger.info(f"Cleaned up {count} expired orbital tokens")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up expired orbital tokens: {e}")
            return 0

    async def get_user_active_tokens(
        self, user_id: uuid.UUID, token_type: OrbitalTokenType | None = None
    ) -> list[OrbitalToken]:
        """
        Получить список активных токенов пользователя.

        :param user_id: ID пользователя
        :param token_type: Тип токенов (опционально)
        :return: Список активных токенов
        """
        try:
            return await self._orbital_token_repo.list_active_tokens(user_id=user_id, token_type=token_type)
        except Exception as e:
            logger.error(f"Error getting user active tokens: {e}")
            return []

    async def create_email_verification_token(
        self, user: "User", email: str | None = None, custom_lifetime_hours: int | None = None
    ) -> tuple[str, OrbitalToken]:
        """
        Создать токен для подтверждения email.

        :param user: Пользователь
        :param email: Email для подтверждения (по умолчанию user.email)
        :param custom_lifetime_hours: Пользовательское время жизни в часах
        :return: Кортеж (токен, объект OrbitalToken)
        """
        email = email or user.email
        metadata = {"email": email}

        custom_minutes = None
        if custom_lifetime_hours:
            custom_minutes = custom_lifetime_hours * 60

        return await self.create_token(
            user=user,
            token_type=OrbitalTokenType.EMAIL_VERIFICATION,
            purpose=f"email_verification:{email}",
            metadata=metadata,
            custom_lifetime_minutes=custom_minutes,
        )

    async def create_password_reset_token(
        self, user: "User", ip_address: str | None = None
    ) -> tuple[str, OrbitalToken]:
        """
        Создать токен для сброса пароля.

        :param user: Пользователь
        :param ip_address: IP адрес
        :return: Кортеж (токен, объект OrbitalToken)
        """
        # Отзываем все предыдущие токены сброса пароля
        await self.revoke_user_tokens(user_id=user.id, token_type=OrbitalTokenType.PASSWORD_RESET)

        metadata = {"email": user.email}

        return await self.create_token(
            user=user,
            token_type=OrbitalTokenType.PASSWORD_RESET,
            purpose="password_reset",
            metadata=metadata,
            ip_address=ip_address,
        )

    async def create_2fa_token(self, user: "User", method: str = "email") -> tuple[str, OrbitalToken]:
        """
        Создать токен для двухфакторной аутентификации.

        :param user: Пользователь
        :param method: Метод доставки (email, sms)
        :return: Кортеж (код, объект OrbitalToken)
        """
        metadata = {"method": method}

        return await self.create_token(
            user=user,
            token_type=OrbitalTokenType.TWO_FACTOR_AUTH,
            purpose=f"2fa_{method}",
            token_length=6,  # 6-значный код
            metadata=metadata,
            use_numeric_code=True,
        )

    async def create_phone_verification_token(self, user: "User", phone: str) -> tuple[str, OrbitalToken]:
        """
        Создать токен для подтверждения телефона.

        :param user: Пользователь
        :param phone: Номер телефона
        :return: Кортеж (код, объект OrbitalToken)
        """
        metadata = {"phone": phone}

        return await self.create_token(
            user=user,
            token_type=OrbitalTokenType.PHONE_VERIFICATION,
            purpose=f"phone_verification:{phone}",
            token_length=6,  # 6-значный код
            metadata=metadata,
            use_numeric_code=True,
        )

    async def create_login_verification_token(
        self, user: "User", ip_address: str | None = None, device_info: str | None = None
    ) -> tuple[str, OrbitalToken]:
        """
        Создать токен для верификации входа с нового устройства.

        :param user: Пользователь
        :param ip_address: IP адрес
        :param device_info: Информация об устройстве
        :return: Кортеж (код, объект OrbitalToken)
        """
        metadata = {"device_info": device_info, "verification_type": "new_device_login"}

        return await self.create_token(
            user=user,
            token_type=OrbitalTokenType.LOGIN_VERIFICATION,
            purpose="login_verification",
            token_length=6,  # 6-значный код
            metadata=metadata,
            ip_address=ip_address,
            use_numeric_code=True,
        )

    async def get_token_info(self, token_id: uuid.UUID) -> dict[str, Any] | None:
        """
        Получить информацию о токене.

        :param token_id: ID токена
        :return: Информация о токене
        """
        try:
            token = await self._orbital_token_repo.get_by_id(token_id)
            if not token:
                return None

            return {
                "id": str(token.id),
                "user_id": str(token.user_id),
                "token_type": token.token_type.value,
                "purpose": token.purpose,
                "created_at": token.created_at,
                "expires_at": token.expires_at,
                "used_at": token.used_at,
                "is_used": token.is_used,
                "is_expired": token.is_expired,
                "token_metadata": token.token_metadata,
                "ip_address": token.ip_address,
            }
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return None

    async def get_user_tokens_stats(self, user_id: uuid.UUID) -> dict[str, Any]:
        """
        Получить статистику токенов пользователя.

        :param user_id: ID пользователя
        :return: Статистика токенов
        """
        try:
            stats = await self._orbital_token_repo.get_user_tokens_stats(user_id)
            return {"user_id": str(user_id), **stats}
        except Exception as e:
            logger.error(f"Error getting user tokens stats: {e}")
            return {"user_id": str(user_id), "error": str(e)}
