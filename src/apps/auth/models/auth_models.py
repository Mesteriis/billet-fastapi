"""
Модели авторизации и сессий.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base.models import BaseModel

if TYPE_CHECKING:
    from apps.users.models.user_models import User


class RefreshToken(BaseModel):
    """
    Модель refresh токенов для JWT аутентификации.

    Содержит информацию о выданных refresh токенах:
    - Хеш токена для безопасности
    - Время истечения
    - Информация об устройстве и IP
    """

    __tablename__ = "refresh_tokens"

    # Связь с пользователем
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID пользователя",
    )

    # Данные токена
    token_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True, comment="Хеш refresh токена"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, comment="Время истечения токена"
    )

    # Метаданные устройства и сессии
    device_info: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Информация об устройстве (User-Agent)"
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # Поддержка IPv6
        nullable=True,
        comment="IP адрес клиента",
    )

    device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Отпечаток устройства")

    # Флаги состояния
    is_revoked: Mapped[bool] = mapped_column(nullable=False, default=False, comment="Отозван ли токен")

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Время последнего использования"
    )

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens", lazy="select")

    def __str__(self) -> str:
        return f"RefreshToken(user_id={self.user_id}, expires_at={self.expires_at})"

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} expires_at={self.expires_at}>"

    @property
    def is_expired(self) -> bool:
        """Проверка истечения токена."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Проверка валидности токена."""
        return not self.is_revoked and not self.is_expired

    def revoke(self) -> None:
        """Отозвать токен."""
        self.is_revoked = True

    def update_last_used(self) -> None:
        """Обновить время последнего использования."""
        self.last_used_at = datetime.utcnow()


class UserSession(BaseModel):
    """
    Модель веб-сессий пользователей.

    Содержит информацию о пользовательских сессиях:
    - ID сессии для cookie
    - Данные сессии в JSON формате
    - Информация о браузере и IP
    """

    __tablename__ = "user_sessions"

    # Связь с пользователем
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID пользователя",
    )

    # Данные сессии
    session_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True, comment="Уникальный ID сессии"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, comment="Время истечения сессии"
    )

    # Данные сессии в JSON
    data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="Данные сессии в JSON формате"
    )

    # Метаданные сессии
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # Поддержка IPv6
        nullable=True,
        comment="IP адрес клиента",
    )

    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True, comment="User-Agent браузера")

    csrf_token: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="CSRF токен для защиты")

    # Флаги состояния
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, comment="Активна ли сессия")

    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, comment="Время последней активности"
    )

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="sessions", lazy="select")

    def __str__(self) -> str:
        return f"UserSession(user_id={self.user_id}, session_id={self.session_id[:12]}...)"

    def __repr__(self) -> str:
        return f"<UserSession id={self.id} user_id={self.user_id} session_id={self.session_id[:12]}...>"

    @property
    def is_expired(self) -> bool:
        """Проверка истечения сессии."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Проверка валидности сессии."""
        return self.is_active and not self.is_expired

    def extend_expiry(self, minutes: int = 30) -> None:
        """Продлить время истечения сессии."""
        from datetime import timedelta

        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)

    def update_activity(self) -> None:
        """Обновить время последней активности."""
        self.last_activity_at = datetime.utcnow()

    def invalidate(self) -> None:
        """Деактивировать сессию."""
        self.is_active = False

    def set_data(self, key: str, value: Any) -> None:
        """Установить значение в данных сессии."""
        if self.data is None:
            self.data = {}
        self.data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Получить значение из данных сессии."""
        if self.data is None:
            return default
        return self.data.get(key, default)

    def clear_data(self) -> None:
        """Очистить данные сессии."""
        self.data = {}


class OrbitalToken(BaseModel):
    """
    Модель одноразовых токенов (orbital tokens).

    Используется для различных операций:
    - Подтверждение email
    - Сброс пароля
    - Двухфакторная аутентификация
    - Подтверждение телефона
    - Верификация входа с нового устройства
    """

    __tablename__ = "orbital_tokens"

    # Связь с пользователем
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID пользователя",
    )

    # Данные токена
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True, comment="Хеш токена")

    token_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Тип токена (email_verification, password_reset, etc.)"
    )

    purpose: Mapped[str] = mapped_column(String(255), nullable=False, comment="Назначение токена")

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, comment="Время истечения токена"
    )

    # Метаданные
    token_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="Дополнительные данные токена в JSON формате"
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # Поддержка IPv6
        nullable=True,
        comment="IP адрес при создании токена",
    )

    # Флаги состояния
    is_used: Mapped[bool] = mapped_column(nullable=False, default=False, comment="Использован ли токен")

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Время использования токена"
    )

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="orbital_tokens", lazy="select")

    def __str__(self) -> str:
        return f"OrbitalToken(user_id={self.user_id}, type={self.token_type}, purpose={self.purpose})"

    def __repr__(self) -> str:
        return f"<OrbitalToken id={self.id} user_id={self.user_id} type={self.token_type}>"

    @property
    def is_expired(self) -> bool:
        """Проверка истечения токена."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Проверка валидности токена."""
        return not self.is_used and not self.is_expired

    def consume(self) -> None:
        """Пометить токен как использованный."""
        self.is_used = True
        self.used_at = datetime.utcnow()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Получить метаданные токена."""
        if self.token_metadata is None:
            return default
        return self.token_metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Установить метаданные токена."""
        if self.token_metadata is None:
            self.token_metadata = {}
        self.token_metadata[key] = value
