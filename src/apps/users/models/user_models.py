"""
Модели пользователей и профилей.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base.models import BaseModel

from .enums import NotificationLevel, UserLanguage, UserRole, UserStatus, UserTheme

if TYPE_CHECKING:
    from apps.auth.models.auth_models import OrbitalToken, RefreshToken, UserSession


class User(BaseModel):
    """
    Основная модель пользователя.

    Содержит базовую информацию для аутентификации и авторизации:
    - Учетные данные (username, email, пароль)
    - Основные персональные данные
    - Статусы и роли
    - Метаданные активности
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
    )

    # Основные учетные данные
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="Уникальное имя пользователя")

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="Email адрес пользователя")

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="Хеш пароля пользователя")

    # Основные персональные данные
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Имя пользователя")

    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Фамилия пользователя")

    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="URL аватара пользователя")

    # Роли и статусы
    role: Mapped[UserRole] = mapped_column(
        String(20), nullable=False, default=UserRole.USER, comment="Роль пользователя"
    )

    status: Mapped[UserStatus] = mapped_column(
        String(20), nullable=False, default=UserStatus.PENDING, comment="Статус пользователя"
    )

    # Флаги активности
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="Активен ли пользователь")

    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Подтвержден ли email пользователя"
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Является ли пользователь суперпользователем"
    )

    # Метаданные активности
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Время последнего входа"
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Время подтверждения email"
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Время последней активности"
    )

    # Связи с другими моделями
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="select"
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    orbital_tokens: Mapped[list["OrbitalToken"]] = relationship(
        "OrbitalToken", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    def __str__(self) -> str:
        return f"User(username={self.username}, email={self.email})"

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} email={self.email}>"

    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.username

    @property
    def display_name(self) -> str:
        """Отображаемое имя для UI."""
        return self.full_name if (self.first_name or self.last_name) else self.username

    @property
    def is_admin(self) -> bool:
        """Является ли пользователь администратором."""
        return self.role in [UserRole.ADMIN, UserRole.SUPERUSER]

    @property
    def is_staff(self) -> bool:
        """Является ли пользователь сотрудником (модератор+)."""
        return self.role in [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPERUSER]

    @property
    def can_login(self) -> bool:
        """Может ли пользователь войти в систему."""
        return self.is_active and self.status == UserStatus.ACTIVE and not self.is_deleted

    def has_role(self, role: UserRole) -> bool:
        """Проверка наличия роли или выше."""
        return self.role.has_permission(role)

    def update_last_seen(self) -> None:
        """Обновить время последней активности."""
        self.last_seen_at = datetime.utcnow()

    def update_last_login(self) -> None:
        """Обновить время последнего входа."""
        self.last_login_at = datetime.utcnow()

    def verify_email(self) -> None:
        """Подтвердить email пользователя."""
        self.is_verified = True
        self.email_verified_at = datetime.utcnow()
        if self.status == UserStatus.PENDING:
            self.status = UserStatus.ACTIVE

    def activate(self) -> None:
        """Активировать пользователя."""
        self.is_active = True
        self.status = UserStatus.ACTIVE

    def deactivate(self) -> None:
        """Деактивировать пользователя."""
        self.is_active = False
        self.status = UserStatus.SUSPENDED

    def ban(self) -> None:
        """Заблокировать пользователя."""
        self.is_active = False
        self.status = UserStatus.BANNED


class UserProfile(BaseModel):
    """
    Расширенный профиль пользователя.

    Содержит дополнительную информацию о пользователе:
    - Персональные данные (био, телефон, дата рождения)
    - Настройки интерфейса
    - Предпочтения уведомлений
    """

    __tablename__ = "user_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_profiles_user_id"),)

    # Связь с пользователем
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID пользователя",
    )

    # Дополнительная персональная информация
    bio: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Биография пользователя")

    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Телефон пользователя")

    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="Дата рождения")

    location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Местоположение пользователя")

    website: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Веб-сайт пользователя")

    # Настройки локализации
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="UTC", comment="Временная зона пользователя"
    )

    language: Mapped[UserLanguage] = mapped_column(
        String(5), nullable=False, default=UserLanguage.EN, comment="Язык интерфейса"
    )

    # Настройки интерфейса
    theme: Mapped[UserTheme] = mapped_column(
        String(10), nullable=False, default=UserTheme.LIGHT, comment="Тема интерфейса"
    )

    # Настройки уведомлений
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Включены ли уведомления"
    )

    notification_level: Mapped[NotificationLevel] = mapped_column(
        String(20), nullable=False, default=NotificationLevel.ALL, comment="Уровень уведомлений"
    )

    email_notifications: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Email уведомления"
    )

    push_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="Push уведомления")

    # Настройки приватности
    public_profile: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="Публичный ли профиль")

    show_email: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Показывать ли email в профиле"
    )

    show_phone: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Показывать ли телефон в профиле"
    )

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="profile", lazy="select")

    def __str__(self) -> str:
        return f"UserProfile(user_id={self.user_id})"

    def __repr__(self) -> str:
        return f"<UserProfile id={self.id} user_id={self.user_id}>"

    @property
    def age(self) -> int | None:
        """Возраст пользователя."""
        if not self.birth_date:
            return None
        from datetime import date

        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )

    def get_notification_settings(self) -> dict[str, Any]:
        """Получить настройки уведомлений."""
        return {
            "enabled": self.notifications_enabled,
            "email": self.email_notifications,
            "push": self.push_notifications,
            "level": self.notification_level.value,
        }

    def get_privacy_settings(self) -> dict[str, bool]:
        """Получить настройки приватности."""
        return {
            "public_profile": self.public_profile,
            "show_email": self.show_email,
            "show_phone": self.show_phone,
        }
