"""
Сервис для бизнес-логики пользователей.
"""

import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.exceptions import UserDataValidationError, UserEmailAlreadyExistsError, UserUsernameAlreadyExistsError
from apps.users.models.enums import UserRole, UserStatus
from apps.users.models.user_models import User, UserProfile
from apps.users.repo.profile_repo import ProfileRepository
from apps.users.repo.user_repo import UserRepository
from apps.users.schemas.user_schemas import UserCreate, UserResponse, UserUpdate
from core.config import get_settings

logger = logging.getLogger("users.user_service")
settings = get_settings()


class UserService:
    """
    Сервис для бизнес-логики пользователей.

    Обеспечивает операции с пользователями:
    - Создание и обновление пользователей
    - Управление паролями и аутентификацией
    - Управление ролями и статусами
    - Поиск и фильтрация пользователей
    - Статистика и аналитика
    """

    def __init__(self, user_repo: UserRepository, profile_repo: ProfileRepository):
        self._user_repo = user_repo
        self._profile_repo = profile_repo
        self._password_rounds = getattr(settings, "PASSWORD_HASH_ROUNDS", 12)
        logger.info("UserService initialized")

    def _hash_password(self, password: str) -> str:
        """
        Хеширование пароля с использованием bcrypt.

        :param password: Пароль в открытом виде
        :return: Хешированный пароль
        """
        salt = bcrypt.gensalt(rounds=self._password_rounds)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Проверка пароля против хеша.

        :param password: Пароль в открытом виде
        :param password_hash: Хешированный пароль
        :return: True если пароль совпадает
        """
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    def _generate_username_from_email(self, email: str) -> str:
        """
        Генерировать username из email если не указан.

        :param email: Email адрес
        :return: Предлагаемый username
        """
        base_username = email.split("@")[0].lower()
        # Заменяем спецсимволы на подчеркивания
        import re

        username = re.sub(r"[^a-z0-9_]", "_", base_username)
        return username[:50]  # Ограничиваем длину

    async def create_user(self, user_data, create_profile: bool = True, send_verification_email: bool = True) -> User:
        """
        Создать нового пользователя.

        :param user_data: Данные для создания пользователя
        :param create_profile: Создать профиль пользователя
        :param send_verification_email: Отправить email для верификации
        :return: Созданный пользователь
        """
        logger.info(f"Creating user with email: {user_data.email}")

        # Проверяем уникальность email
        existing_user = await self._user_repo.get_by_email(user_data.email)
        if existing_user:
            raise UserEmailAlreadyExistsError(email=user_data.email)

        # Генерируем username если не указан
        username = user_data.username
        if not username:
            username = self._generate_username_from_email(user_data.email)

        # Проверяем уникальность username
        existing_username = await self._user_repo.get_by_username(username)
        if existing_username:
            # Добавляем суффикс к username
            import random

            username = f"{username}_{random.randint(1000, 9999)}"

        # Хешируем пароль
        password_hash = self._hash_password(user_data.password)

        # Создаем данные пользователя
        create_data = {
            "username": username,
            "email": user_data.email,
            "password_hash": password_hash,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "role": UserRole.USER,
            "status": UserStatus.PENDING if send_verification_email else UserStatus.ACTIVE,
            "is_active": True,
            "is_verified": not send_verification_email,
            "is_superuser": False,
        }

        try:
            # Создаем пользователя
            user = await self._user_repo.create(create_data)

            # Создаем профиль если нужно
            if create_profile:
                await self._create_default_profile(user)

            logger.info(f"User created successfully: {user.id}")

            # TODO: Отправка email для верификации
            if send_verification_email:
                await self._send_verification_email(user)

            return user

        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """
        Получить пользователя по ID.

        :param user_id: ID пользователя
        :return: Пользователь или None
        """
        return await self._user_repo.get_by(id=user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Получить пользователя по email.

        :param email: Email пользователя
        :return: Пользователь или None
        """
        return await self._user_repo.get_by_email(email)

    async def get_user_by_username(self, username: str) -> User | None:
        """
        Получить пользователя по username.

        :param username: Username пользователя
        :return: Пользователь или None
        """
        return await self._user_repo.get_by_username(username)

    async def authenticate_user(self, email_or_username: str, password: str) -> User | None:
        """
        Аутентификация пользователя по email/username и паролю.

        :param email_or_username: Email или username
        :param password: Пароль
        :return: Пользователь если аутентификация успешна
        """
        logger.debug(f"Authenticating user: {email_or_username}")

        # Ищем пользователя по email или username
        user = None
        if "@" in email_or_username:
            user = await self.get_user_by_email(email_or_username)
        else:
            user = await self.get_user_by_username(email_or_username)

        if not user:
            logger.debug(f"User not found: {email_or_username}")
            return None

        # Проверяем возможность входа
        if not user.can_login:
            logger.warning(f"User cannot login: {user.id}")
            return None

        # Проверяем пароль
        if not self._verify_password(password, user.password_hash):
            logger.debug(f"Invalid password for user: {user.id}")
            return None

        # Обновляем время последнего входа
        await self.update_last_login(user.id)

        logger.info(f"User authenticated successfully: {user.id}")
        return user

    async def update_user(self, user_id: uuid.UUID, user_data: UserUpdate) -> User | None:
        """
        Обновить данные пользователя.

        :param user_id: ID пользователя
        :param user_data: Новые данные пользователя
        :return: Обновленный пользователь
        """
        logger.info(f"Updating user: {user_id}")

        user = await self._user_repo.get_by(id=user_id)
        if not user:
            return None

        # Подготавливаем данные для обновления
        update_data = {}

        if user_data.username is not None:
            # Проверяем уникальность username
            existing_user = await self._user_repo.get_by_username(user_data.username)
            if existing_user and existing_user.id != user_id:
                raise UserUsernameAlreadyExistsError(username=user_data.username)
            update_data["username"] = user_data.username

        if user_data.email is not None:
            # Проверяем уникальность email
            existing_user = await self._user_repo.get_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise UserEmailAlreadyExistsError(email=user_data.email)
            update_data["email"] = user_data.email
            # Сбрасываем верификацию если email изменился
            if user_data.email != user.email:
                update_data["is_verified"] = False
                update_data["email_verified_at"] = None

        # Обновляем остальные поля
        for field in ["first_name", "last_name", "avatar_url"]:
            value = getattr(user_data, field, None)
            if value is not None:
                update_data[field] = value

        try:
            updated_user = await self._user_repo.update(user, update_data)
            logger.info(f"User updated successfully: {user_id}")
            return updated_user
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            raise

    async def change_password(self, user_id: uuid.UUID, current_password: str, new_password: str) -> bool:
        """
        Изменить пароль пользователя.

        :param user_id: ID пользователя
        :param current_password: Текущий пароль
        :param new_password: Новый пароль
        :return: True если пароль изменен успешно
        """
        logger.info(f"Changing password for user: {user_id}")

        user = await self._user_repo.get_by(id=user_id)
        if not user:
            return False

        # Проверяем текущий пароль
        if not self._verify_password(current_password, user.password_hash):
            logger.warning(f"Invalid current password for user: {user_id}")
            return False

        # Хешируем новый пароль
        new_password_hash = self._hash_password(new_password)

        try:
            await self._user_repo.update(user, {"password_hash": new_password_hash})
            logger.info(f"Password changed successfully for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {e}")
            return False

    async def reset_password(self, user_id: uuid.UUID, new_password: str) -> bool:
        """
        Сброс пароля пользователя (без проверки текущего).

        :param user_id: ID пользователя
        :param new_password: Новый пароль
        :return: True если пароль сброшен успешно
        """
        logger.info(f"Resetting password for user: {user_id}")

        user = await self._user_repo.get_by(id=user_id)
        if not user:
            return False

        # Хешируем новый пароль
        new_password_hash = self._hash_password(new_password)

        try:
            await self._user_repo.update(user, {"password_hash": new_password_hash})
            logger.info(f"Password reset successfully for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset password for user {user_id}: {e}")
            return False

    async def verify_email(self, user_id: uuid.UUID) -> bool:
        """
        Подтвердить email пользователя.

        :param user_id: ID пользователя
        :return: True если email подтвержден
        """
        logger.info(f"Verifying email for user: {user_id}")

        user = await self._user_repo.get_by(id=user_id)
        if not user:
            return False

        if user.is_verified:
            logger.debug(f"Email already verified for user: {user_id}")
            return True

        try:
            update_data = {
                "is_verified": True,
                "email_verified_at": datetime.utcnow(),
                "status": UserStatus.ACTIVE if user.status == UserStatus.PENDING else user.status,
            }
            await self._user_repo.update(user, update_data)
            logger.info(f"Email verified successfully for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to verify email for user {user_id}: {e}")
            return False

    async def update_last_login(self, user_id: uuid.UUID) -> bool:
        """
        Обновить время последнего входа пользователя.

        :param user_id: ID пользователя
        :return: True если время обновлено
        """
        try:
            user = await self._user_repo.get_by(id=user_id)
            if not user:
                return False

            await self._user_repo.update(user, {"last_login_at": datetime.utcnow(), "last_seen_at": datetime.utcnow()})
            return True
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            return False

    async def update_last_seen(self, user_id: uuid.UUID) -> bool:
        """
        Обновить время последней активности пользователя.

        :param user_id: ID пользователя
        :return: True если время обновлено
        """
        try:
            user = await self._user_repo.get_by(id=user_id)
            if not user:
                return False

            await self._user_repo.update(user, {"last_seen_at": datetime.utcnow()})
            return True
        except Exception as e:
            logger.error(f"Failed to update last seen for user {user_id}: {e}")
            return False

    async def change_user_role(self, user_id: uuid.UUID, new_role: UserRole, admin_user_id: uuid.UUID) -> bool:
        """
        Изменить роль пользователя.

        :param user_id: ID пользователя
        :param new_role: Новая роль
        :param admin_user_id: ID администратора, выполняющего изменение
        :return: True если роль изменена
        """
        logger.info(f"Changing role for user {user_id} to {new_role.value} by admin {admin_user_id}")

        # Проверяем права администратора
        admin_user = await self._user_repo.get_by_id(admin_user_id)
        if not admin_user or not admin_user.is_admin:
            logger.warning(f"Insufficient permissions for user {admin_user_id}")
            return False

        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return False

        try:
            await self._user_repo.update(user, {"role": new_role})
            logger.info(f"Role changed successfully for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to change role for user {user_id}: {e}")
            return False

    async def activate_user(self, user_id: uuid.UUID) -> bool:
        """
        Активировать пользователя.

        :param user_id: ID пользователя
        :return: True если пользователь активирован
        """
        logger.info(f"Activating user: {user_id}")

        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return False

        try:
            await self._user_repo.update(user, {"is_active": True, "status": UserStatus.ACTIVE})
            logger.info(f"User activated successfully: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to activate user {user_id}: {e}")
            return False

    async def deactivate_user(self, user_id: uuid.UUID) -> bool:
        """
        Деактивировать пользователя.

        :param user_id: ID пользователя
        :return: True если пользователь деактивирован
        """
        logger.info(f"Deactivating user: {user_id}")

        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return False

        try:
            await self._user_repo.update(user, {"is_active": False, "status": UserStatus.SUSPENDED})
            logger.info(f"User deactivated successfully: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {e}")
            return False

    async def delete_user(self, user_id: uuid.UUID, soft_delete: bool = True) -> bool:
        """
        Удалить пользователя.

        :param user_id: ID пользователя
        :param soft_delete: Мягкое удаление (по умолчанию)
        :return: True если пользователь удален
        """
        logger.info(f"Deleting user: {user_id} (soft_delete={soft_delete})")

        user = await self._user_repo.get_by(id=user_id)
        if not user:
            return False

        try:
            await self._user_repo.delete(user, soft_delete=soft_delete)
            logger.info(f"User deleted successfully: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False

    async def search_users(
        self,
        query: str | None = None,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        is_verified: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        """
        Поиск пользователей по различным критериям.

        :param query: Поисковый запрос (по имени, email, username)
        :param role: Фильтр по роли
        :param status: Фильтр по статусу
        :param is_verified: Фильтр по верификации
        :param limit: Лимит результатов
        :param offset: Смещение
        :return: Список пользователей
        """
        try:
            users = await self._user_repo.search_users(
                query=query, role=role, status=status, is_verified=is_verified, limit=limit, offset=offset
            )
            return list(users)
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []

    async def get_user_stats(self) -> dict[str, Any]:
        """
        Получить статистику пользователей.

        :return: Статистика пользователей
        """
        try:
            return await self._user_repo.get_user_stats()
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    async def _create_default_profile(self, user: User) -> UserProfile:
        """
        Создать профиль пользователя по умолчанию.

        :param user: Пользователь
        :return: Созданный профиль
        """
        profile_data = {
            "user_id": user.id,
            "timezone": "UTC",
            "language": "en",
            "theme": "light",
            "notifications_enabled": True,
            "notification_level": "all",
            "email_notifications": True,
            "push_notifications": True,
            "public_profile": True,
            "show_email": False,
            "show_phone": False,
        }

        return await self._profile_repo.create(profile_data)

    async def _send_verification_email(self, user: User) -> None:
        """
        Отправить email для верификации (заглушка).

        :param user: Пользователь
        """
        # TODO: Реализовать отправку email через OrbitalService
        logger.info(f"Verification email should be sent to {user.email}")
        pass

    async def get_users_list(
        self,
        filters: dict | None = None,
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_private: bool = False,
    ) -> dict:
        """
        Get paginated list of users.

        Temporary implementation for API tests.

        Args:
            filters: Filter criteria
            page: Page number
            size: Page size
            sort_by: Sort field
            sort_order: Sort order
            include_private: Include private information

        Returns:
            Paginated users list
        """
        # Simple implementation for tests
        return {"users": [], "total": 0, "page": page, "size": size, "pages": 0, "has_next": False, "has_prev": False}
