"""
Модели пользователей.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base.models import BaseEntity

if TYPE_CHECKING:
    from ..auth.models import RefreshToken


class User(BaseEntity):
    """Модель пользователя."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    # Основная информация
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Аутентификация
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Дополнительная информация
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Метаданные
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Связи
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"

    @property
    def is_email_verified(self) -> bool:
        """Проверка верификации email."""
        return self.email_verified_at is not None

    def verify_email(self) -> None:
        """Верификация email пользователя."""
        self.email_verified_at = datetime.now(tz=utc)()
        self.is_verified = True

    def update_last_login(self) -> None:
        """Обновление времени последнего входа."""
        self.last_login_at = datetime.now(tz=utc)()
