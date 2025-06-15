"""
Модели для аутентификации.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.base.models import BaseEntity

if TYPE_CHECKING:
    from apps.users.models import User


class RefreshToken(BaseEntity):
    """Модель refresh токена."""

    __tablename__ = "refresh_tokens"
    __table_args__ = {"extend_existing": True}

    # Связь с пользователем
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Данные токена
    jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Метаданные
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Информация о клиенте
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 адрес может быть до 45 символов
        nullable=True,
    )

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, jti={self.jti[:8]}...)>"

    @property
    def is_expired(self) -> bool:
        """Проверка истечения токена."""
        return datetime.now(tz=utc)() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Проверка валидности токена."""
        return not self.is_revoked and not self.is_expired and not self.is_deleted

    def revoke(self) -> None:
        """Отзыв токена."""
        self.is_revoked = True
