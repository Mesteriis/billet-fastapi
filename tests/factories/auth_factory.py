"""
Фабрики для создания тестовых данных аутентификации.
"""

import uuid
from datetime import datetime, timedelta

from faker import Faker

from apps.auth.models import RefreshToken
from apps.users.models import User

fake = Faker()


def refresh_token_factory(user: User | None = None, **kwargs) -> RefreshToken:
    """Создает refresh token."""
    defaults = {
        "jti": str(uuid.uuid4()),
        "user_id": user.id if user else uuid.uuid4(),
        "expires_at": datetime.utcnow() + timedelta(days=30),
        "user_agent": fake.user_agent(),
        "ip_address": fake.ipv4(),
        "is_revoked": False,
    }
    defaults.update(kwargs)

    return RefreshToken(**defaults)


def create_refresh_tokens_batch(user: User, count: int = 3) -> list[RefreshToken]:
    """Создает партию refresh токенов для пользователя."""
    return [refresh_token_factory(user=user) for _ in range(count)]
