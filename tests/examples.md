```python
import uuid
from datetime import datetime, timedelta

import pytest

from async_factory_boy.factory.sqlalchemy import AsyncSQLAlchemyFactory
from factory import LazyAttribute, Sequence, SubFactory, RelatedFactory
from pytz import utc

from apps.auth import RefreshToken
from apps.users import User

from factory.faker import Faker

class RefreshTokenFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания тестовых токенов обновления."""

    class Meta:
        model = RefreshToken
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    jti = ''.join([str(uuid.uuid4()) for _ in range(5)])  # добавь логику
    expires_at = LazyAttribute(lambda _: datetime.now(tz=utc) + timedelta(days=30))  # Токен действителен 30 дней
    # остальные поля поставь по аналогии, не должно быть недосказаности в фабриках, и все должно быть на фейкерах и связано чере SubFactory

class UserFactory(AsyncSQLAlchemyFactory):
    """Фабрика для создания тестовых пользователей."""

    class Meta:
        model = User  # Замените на вашу модель пользователя
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    email = Sequence(lambda o: f"user_{o}@example.com")
    username = Sequence(lambda o: f"user_{o}")
    full_name = Faker("name")

    hashed_password = LazyAttribute(lambda _: "hashed_password")  # Замени на функции где в качестве raw пароля будет password
    is_active = True
    is_verified = False
    is_superuser = False

    refresh_tokens = RelatedFactory(RefreshTokenFactory, factory_related_name="user")  # Связь с токенами обновления
    
@pytest.fixture
def user_factory(async_session):
    """Фикстура для фабрики."""
    setattr(UserFactory._meta, "sqlalchemy_session", async_session)
    setattr(RefreshTokenFactory._meta, "sqlalchemy_session", async_session)
    return UserFactory

@pytest.fixture
async def user(user_factory):
    """Фикстура для создания тестового пользователя."""
    return await user_factory.create()

async def test_request(api_client, user):
    """Тест логирования запросов и ответов в AsyncApiTestClient."""
    url = api_client.url_for("sse_endpoint")
    # Выполняем запрос к тестовому эндпоинту
    await api_client.force_auth(user)
    response = await api_client.get(url)
    assert response.status_code == 200

```
