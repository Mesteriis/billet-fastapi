"""
Сервис для работы с веб-сессиями пользователей.
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.models.auth_models import UserSession
from apps.auth.repo.user_session_repo import UserSessionRepository

if TYPE_CHECKING:
    from apps.users.models.user_models import User

from core.config import get_settings

logger = logging.getLogger("auth.session_service")
settings = get_settings()


class SessionService:
    """
    Сервис для работы с веб-сессиями пользователей.

    Обеспечивает создание, валидацию и управление пользовательскими сессиями:
    - Создание новых сессий при входе
    - Валидация и обновление активных сессий
    - Управление данными сессий
    - Очистка истекших сессий
    - CSRF защита
    """

    def __init__(self, session_repo: UserSessionRepository, user_repo):
        self._session_repo = session_repo
        self._user_repo = user_repo
        self._default_session_lifetime = getattr(settings, "SESSION_LIFETIME_MINUTES", 1440)  # 24 hours
        self._max_sessions_per_user = getattr(settings, "MAX_SESSIONS_PER_USER", 10)

    def _generate_session_id(self) -> str:
        """
        Генерировать уникальный ID сессии.

        :return: Уникальный ID сессии
        """
        return secrets.token_urlsafe(32)

    def _generate_csrf_token(self) -> str:
        """
        Генерировать CSRF токен для защиты от CSRF атак.

        :return: CSRF токен
        """
        return secrets.token_urlsafe(32)

    def _get_session_expiry(self, lifetime_minutes: int | None = None) -> datetime:
        """
        Получить время истечения сессии.

        :param lifetime_minutes: Время жизни сессии в минутах
        :return: Время истечения сессии
        """
        minutes = lifetime_minutes or self._default_session_lifetime
        return datetime.utcnow() + timedelta(minutes=minutes)

    async def create_session(
        self,
        user: "User",
        ip_address: str | None = None,
        user_agent: str | None = None,
        remember_me: bool = False,
        initial_data: dict[str, Any] | None = None,
    ) -> UserSession:
        """
        Создать новую сессию для пользователя.

        :param user: Пользователь
        :param ip_address: IP адрес пользователя
        :param user_agent: User-Agent браузера
        :param remember_me: Увеличить время жизни сессии
        :param initial_data: Начальные данные сессии
        :return: Объект UserSession
        """
        logger.info(f"Creating session for user {user.id}")

        # Проверяем лимит сессий
        await self._cleanup_excess_sessions(user.id)

        # Определяем время жизни сессии
        lifetime_minutes = self._default_session_lifetime
        if remember_me:
            lifetime_minutes *= 4  # Увеличиваем в 4 раза для "запомнить меня"

        # Создаем новую сессию
        session_data = {
            "user_id": user.id,
            "session_id": self._generate_session_id(),
            "expires_at": self._get_session_expiry(lifetime_minutes),
            "data": initial_data or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "csrf_token": self._generate_csrf_token(),
            "is_active": True,
            "last_activity_at": datetime.utcnow(),
        }

        try:
            session = await self._session_repo.create(session_data)
            logger.debug(f"Session created for user {user.id}: {session.session_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to create session for user {user.id}: {e}")
            raise

    async def get_session(self, session_id: str) -> UserSession | None:
        """
        Получить сессию по ID.

        :param session_id: ID сессии
        :return: Объект UserSession или None
        """
        try:
            session = await self._session_repo.get_by_session_id(session_id)

            if not session or not session.is_valid:
                logger.debug(f"Session not found or invalid: {session_id}")
                return None

            return session
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    async def validate_session(
        self, session_id: str, ip_address: str | None = None, user_agent: str | None = None, auto_extend: bool = True
    ) -> UserSession | None:
        """
        Валидировать сессию и опционально продлить её.

        :param session_id: ID сессии
        :param ip_address: IP адрес для проверки
        :param user_agent: User-Agent для проверки
        :param auto_extend: Автоматически продлить сессию
        :return: Объект UserSession или None
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        # Проверяем IP адрес (опционально)
        if ip_address and session.ip_address and session.ip_address != ip_address:
            logger.warning(f"IP address mismatch for session {session_id}: {session.ip_address} vs {ip_address}")
            # В production можно сделать более строгую проверку
            # return None

        # Обновляем активность
        await self._session_repo.update_activity(session_id)

        # Продлеваем сессию если нужно
        if auto_extend:
            await self.extend_session(session_id)

        logger.debug(f"Session validated: {session_id}")
        return session

    async def extend_session(self, session_id: str, minutes: int | None = None) -> bool:
        """
        Продлить время жизни сессии.

        :param session_id: ID сессии
        :param minutes: Дополнительное время в минутах
        :return: True если сессия была продлена
        """
        try:
            extend_minutes = minutes or self._default_session_lifetime
            success = await self._session_repo.extend_session(session_id, extend_minutes)

            if success:
                logger.debug(f"Session extended: {session_id}")
            else:
                logger.warning(f"Failed to extend session: {session_id}")

            return success
        except Exception as e:
            logger.error(f"Error extending session {session_id}: {e}")
            return False

    async def invalidate_session(self, session_id: str) -> bool:
        """
        Деактивировать сессию (logout).

        :param session_id: ID сессии
        :return: True если сессия была деактивирована
        """
        try:
            success = await self._session_repo.invalidate_session(session_id)

            if success:
                logger.info(f"Session invalidated: {session_id}")
            else:
                logger.warning(f"Failed to invalidate session: {session_id}")

            return success
        except Exception as e:
            logger.error(f"Error invalidating session {session_id}: {e}")
            return False

    async def invalidate_all_user_sessions(self, user_id: uuid.UUID, exclude_session_id: str | None = None) -> int:
        """
        Деактивировать все сессии пользователя.

        :param user_id: ID пользователя
        :param exclude_session_id: ID сессии для исключения
        :return: Количество деактивированных сессий
        """
        try:
            count = await self._session_repo.invalidate_all_user_sessions(user_id, exclude_session_id)
            logger.info(f"Invalidated {count} sessions for user {user_id}")
            return count
        except Exception as e:
            logger.error(f"Error invalidating all sessions for user {user_id}: {e}")
            return 0

    async def get_user_sessions(
        self, user_id: uuid.UUID, active_only: bool = True, limit: int = 50
    ) -> list[UserSession]:
        """
        Получить сессии пользователя.

        :param user_id: ID пользователя
        :param active_only: Только активные сессии
        :param limit: Максимальное количество сессий
        :return: Список сессий
        """
        try:
            sessions = await self._session_repo.list_by_user(user_id=user_id, active_only=active_only, limit=limit)
            return list(sessions)
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    async def set_session_data(self, session_id: str, key: str, value: Any) -> bool:
        """
        Установить данные в сессии.

        :param session_id: ID сессии
        :param key: Ключ данных
        :param value: Значение данных
        :return: True если данные были установлены
        """
        try:
            success = await self._session_repo.set_session_data(session_id, key, value)

            if success:
                logger.debug(f"Session data set: {session_id} -> {key}")
            else:
                logger.warning(f"Failed to set session data: {session_id} -> {key}")

            return success
        except Exception as e:
            logger.error(f"Error setting session data: {e}")
            return False

    async def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Получить данные из сессии.

        :param session_id: ID сессии
        :param key: Ключ данных
        :param default: Значение по умолчанию
        :return: Данные из сессии
        """
        try:
            return await self._session_repo.get_session_data(session_id, key, default)
        except Exception as e:
            logger.error(f"Error getting session data: {e}")
            return default

    async def clear_session_data(self, session_id: str) -> bool:
        """
        Очистить все данные сессии.

        :param session_id: ID сессии
        :return: True если данные были очищены
        """
        try:
            success = await self._session_repo.clear_session_data(session_id)

            if success:
                logger.debug(f"Session data cleared: {session_id}")

            return success
        except Exception as e:
            logger.error(f"Error clearing session data: {e}")
            return False

    async def verify_csrf_token(self, session_id: str, csrf_token: str) -> bool:
        """
        Верифицировать CSRF токен.

        :param session_id: ID сессии
        :param csrf_token: CSRF токен для проверки
        :return: True если токен валиден
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                return False

            return session.csrf_token == csrf_token
        except Exception as e:
            logger.error(f"Error verifying CSRF token: {e}")
            return False

    async def regenerate_csrf_token(self, session_id: str) -> str | None:
        """
        Перегенерировать CSRF токен для сессии.

        :param session_id: ID сессии
        :return: Новый CSRF токен или None
        """
        try:
            session = await self._session_repo.get_by_session_id(session_id)
            if not session:
                logger.warning(f"Session not found for CSRF token regeneration: {session_id}")
                return None

            new_csrf_token = self._generate_csrf_token()
            await self._session_repo.update(session, {"csrf_token": new_csrf_token})

            logger.debug(f"CSRF token regenerated for session: {session_id}")
            return new_csrf_token
        except Exception as e:
            logger.error(f"Error regenerating CSRF token: {e}")
            return None

    async def cleanup_expired_sessions(self) -> int:
        """
        Очистить истекшие сессии.

        :return: Количество удаленных сессий
        """
        try:
            count = await self._session_repo.cleanup_expired_sessions()
            logger.info(f"Cleaned up {count} expired sessions")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0

    async def get_session_stats(self) -> dict[str, Any]:
        """
        Получить статистику сессий.

        :return: Статистика сессий
        """
        try:
            return await self._session_repo.get_sessions_stats()
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {}

    async def get_user_session_info(self, user_id: uuid.UUID) -> dict[str, Any]:
        """
        Получить информацию о сессиях пользователя.

        :param user_id: ID пользователя
        :return: Информация о сессиях
        """
        try:
            sessions = await self.get_user_sessions(user_id, active_only=False)
            active_sessions = [s for s in sessions if s.is_active and not s.is_expired]

            return {
                "user_id": str(user_id),
                "total_sessions": len(sessions),
                "active_sessions": len(active_sessions),
                "sessions": [
                    {
                        "id": str(session.id),
                        "session_id": session.session_id,
                        "created_at": session.created_at,
                        "expires_at": session.expires_at,
                        "last_activity_at": session.last_activity_at,
                        "ip_address": session.ip_address,
                        "user_agent": session.user_agent,
                        "is_active": session.is_active,
                        "is_expired": session.is_expired,
                    }
                    for session in sessions
                ],
            }
        except Exception as e:
            logger.error(f"Error getting user session info: {e}")
            return {"user_id": str(user_id), "error": str(e)}

    async def _cleanup_excess_sessions(self, user_id: uuid.UUID) -> None:
        """
        Очистить лишние сессии пользователя если превышен лимит.

        :param user_id: ID пользователя
        """
        try:
            current_count = await self._session_repo.count_active_sessions(user_id)

            if current_count >= self._max_sessions_per_user:
                # Получаем все активные сессии пользователя
                sessions = await self._session_repo.list_by_user(user_id=user_id, active_only=True, limit=current_count)

                # Сортируем по времени активности (старые сначала)
                sessions_sorted = sorted(sessions, key=lambda s: s.last_activity_at)

                # Деактивируем самые старые сессии
                excess_count = current_count - self._max_sessions_per_user + 1
                for session in sessions_sorted[:excess_count]:
                    await self._session_repo.invalidate_session(session.session_id)

                logger.info(f"Cleaned up {excess_count} excess sessions for user {user_id}")
        except Exception as e:
            logger.error(f"Error cleaning up excess sessions: {e}")
