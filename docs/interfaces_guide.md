# 📄 Руководство по использованию интерфейсов (Protocols)

Этот документ описывает систему интерфейсов в проекте, основанную на Python Protocols, которая обеспечивает **loose coupling** между модулями и упрощает тестирование.

---

## 🎯 Цель и преимущества

### Зачем нужны Protocol-интерфейсы?

- **✅ Безопасный импорт типов** без жесткой зависимости между модулями
- **🔄 Избежание циклических импортов** между приложениями
- **🧪 Упрощение тестирования** через мок-объекты
- **🔌 Реализация принципа loose coupling**
- **✅ Полная совместимость с mypy/Pyright/Pylance**

### Проблемы, которые решают интерфейсы

❌ **Без интерфейсов:**

```python
# apps/auth/services/jwt_service.py
from apps.users.models.user_models import User  # Жесткая зависимость!

class JWTService:
    def create_token(self, user: User) -> str:  # Привязка к конкретной модели
        return f"token-for-{user.id}"
```

✅ **С интерфейсами:**

```python
# apps/auth/services/jwt_service.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.interfaces import UserIdentity

class JWTService:
    def create_token(self, user: "UserIdentity") -> str:  # Гибкий контракт!
        return f"token-for-{user.id}"
```

---

## 📁 Структура интерфейсов

### Users App (`apps/users/interfaces.py`)

```python
from typing import Protocol
import uuid
from datetime import datetime

class UserIdentity(Protocol):
    """Интерфейс для авторизации и JWT токенов."""
    id: uuid.UUID
    username: str
    email: str
    role: str
    is_active: bool
    is_verified: bool

    def has_role(self, role: str) -> bool: ...
    def can_login(self) -> bool: ...

class UserProfileData(Protocol):
    """Интерфейс данных профиля."""
    user_id: uuid.UUID
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    public_profile: bool

# Type aliases для удобства
UserAuth = UserIdentity
ProfileData = UserProfileData
```

### Auth App (`apps/auth/interfaces.py`)

```python
class RefreshTokenData(Protocol):
    """Интерфейс refresh токена."""
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    is_revoked: bool

    @property
    def is_valid(self) -> bool: ...
    def revoke(self) -> None: ...

class SessionData(Protocol):
    """Интерфейс пользовательской сессии."""
    user_id: uuid.UUID
    session_id: str
    data: dict[str, Any]
    is_active: bool

    def set_data(self, key: str, value: Any) -> None: ...
    def get_data(self, key: str, default: Any = None) -> Any: ...
```

---

## 🛠️ Использование в сервисах

### JWT Service с интерфейсами

```python
# apps/auth/services/jwt_service.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.interfaces import UserIdentity

class JWTService:
    def create_access_token(self, user: "UserIdentity") -> str:
        """Создать access токен для любого объекта, реализующего UserIdentity."""
        payload = {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }
        return jwt.encode(payload, self._secret_key)

    def _get_user_permissions(self, user: "UserIdentity") -> list[str]:
        """Получить права пользователя на основе роли."""
        permissions = ["read:profile"]

        if user.is_verified:
            permissions.extend(["write:profile", "create:posts"])

        if user.has_role("admin"):
            permissions.extend(["manage:users", "access:admin"])

        return permissions
```

### Notification Service с интерфейсами

```python
# apps/notifications/services.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.interfaces import UserIdentity, UserProfileData

class NotificationService:
    def send_welcome_email(self, user: "UserIdentity") -> dict:
        """Отправить приветственное письмо."""
        if not user.is_verified:
            return {"success": False, "reason": "User not verified"}

        return {
            "success": True,
            "email": user.email,
            "subject": f"Welcome, {user.username}!",
        }

    def send_profile_reminder(self, user: "UserIdentity", profile: "UserProfileData") -> dict:
        """Напоминание о заполнении профиля."""
        completion = self._calculate_completion(profile)

        if completion >= 80:
            return {"success": False, "reason": "Profile complete"}

        return {
            "success": True,
            "completion": completion,
            "missing_fields": self._get_missing_fields(profile),
        }
```

---

## 🧪 Тестирование с интерфейсами

### Создание мок-объектов

```python
# tests/mocks/user_mocks.py
import uuid
from datetime import datetime

class MockUser:
    """Мок-объект, реализующий UserIdentity интерфейс."""

    def __init__(
        self,
        id: uuid.UUID = None,
        username: str = "testuser",
        email: str = "test@example.com",
        role: str = "user",
        is_active: bool = True,
        is_verified: bool = True,
    ):
        self.id = id or uuid.uuid4()
        self.username = username
        self.email = email
        self.role = role
        self.is_active = is_active
        self.is_verified = is_verified

    def has_role(self, role: str) -> bool:
        role_hierarchy = {"user": 1, "moderator": 2, "admin": 3}
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(role, 0)

    def can_login(self) -> bool:
        return self.is_active

class MockProfile:
    """Мок-объект профиля."""

    def __init__(self, user_id: uuid.UUID, **kwargs):
        self.user_id = user_id
        self.display_name = kwargs.get("display_name")
        self.bio = kwargs.get("bio")
        self.avatar_url = kwargs.get("avatar_url")
        self.public_profile = kwargs.get("public_profile", True)
```

### Тестирование сервисов

```python
# tests/test_notification_service.py
import pytest
from tests.mocks.user_mocks import MockUser, MockProfile
from apps.notifications.services import NotificationService

def test_send_welcome_email():
    """Тест отправки приветственного письма."""
    # Arrange
    user = MockUser(username="john", email="john@example.com", is_verified=True)
    service = NotificationService()

    # Act
    result = service.send_welcome_email(user)

    # Assert
    assert result["success"] is True
    assert result["email"] == "john@example.com"
    assert "john" in result["subject"]

def test_send_welcome_email_unverified():
    """Тест с неверифицированным пользователем."""
    # Arrange
    user = MockUser(is_verified=False)
    service = NotificationService()

    # Act
    result = service.send_welcome_email(user)

    # Assert
    assert result["success"] is False
    assert result["reason"] == "User not verified"

def test_profile_completion_reminder():
    """Тест напоминания о заполнении профиля."""
    # Arrange
    user = MockUser()
    profile = MockProfile(
        user_id=user.id,
        display_name="John",
        bio=None,  # Незаполненное поле
        avatar_url=None,  # Незаполненное поле
    )
    service = NotificationService()

    # Act
    result = service.send_profile_reminder(user, profile)

    # Assert
    assert result["success"] is True
    assert result["completion"] < 80
    assert "bio" in result["missing_fields"]
    assert "avatar_url" in result["missing_fields"]
```

---

## 🔌 Интеграция с существующими моделями

### Совместимость с SQLAlchemy

Интерфейсы спроектированы для совместимости с SQLAlchemy моделями:

```python
# apps/users/models/user_models.py (существующая модель)
class User(BaseModel):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)

    def has_role(self, role: UserRole) -> bool:
        # Реализация логики...
        pass

    def can_login(self) -> bool:
        return self.is_active and self.status == UserStatus.ACTIVE

# Эта модель автоматически совместима с UserIdentity интерфейсом!
```

### Type Aliases для совместимости

```python
# apps/users/interfaces.py
from typing import Union, Any

# Type aliases для совместимости с SQLAlchemy Mapped типами
IdType = Union[uuid.UUID, Any]  # Поддерживает Mapped[UUID] и UUID
StrType = Union[str, Any]       # Поддерживает Mapped[str] и str
BoolType = Union[bool, Any]     # Поддерживает Mapped[bool] и bool
RoleType = Union[UserRole, Any] # Поддерживает Mapped[UserRole] и UserRole

class UserIdentity(Protocol):
    id: IdType        # Работает с Mapped[UUID] и UUID
    username: StrType # Работает с Mapped[str] и str
    role: RoleType    # Работает с Mapped[UserRole] и UserRole
    # ...
```

---

## 📋 Best Practices

### 1. Использование TYPE_CHECKING

✅ **Правильно:**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.interfaces import UserIdentity

def process_user(user: "UserIdentity") -> dict:
    # Используем строковые аннотации
    pass
```

❌ **Неправильно:**

```python
from apps.users.interfaces import UserIdentity  # Runtime импорт!

def process_user(user: UserIdentity) -> dict:
    # Может вызвать циклические импорты
    pass
```

### 2. Минимальные интерфейсы

✅ **Правильно - узкий интерфейс:**

```python
class UserForNotifications(Protocol):
    email: str
    username: str
    is_verified: bool
```

❌ **Неправильно - толстый интерфейс:**

```python
class UserForNotifications(Protocol):
    # Слишком много полей, не все нужны для нотификаций
    id: UUID
    username: str
    email: str
    password_hash: str  # Не нужно!
    created_at: datetime  # Не нужно!
    # ... еще 20 полей
```

### 3. Осмысленные имена

```python
# Интерфейсы по назначению
UserIdentity      # Для авторизации
UserReference     # Для ссылок и связей
UserManagement    # Для административных операций
UserProfileData   # Для работы с профилем

# Type aliases для краткости
UserAuth = UserIdentity
UserRef = UserReference
ProfileData = UserProfileData
```

### 4. Версионирование интерфейсов

```python
# При изменении интерфейса создавайте новые версии
class UserIdentityV1(Protocol):
    id: UUID
    username: str

class UserIdentityV2(Protocol):
    id: UUID
    username: str
    email: str  # Новое поле

# Используйте alias для текущей версии
UserIdentity = UserIdentityV2
```

---

## 🚀 Примеры реального использования

### Email Service

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.interfaces import UserIdentity

class EmailService:
    def send_password_reset(self, user: "UserIdentity", token: str) -> bool:
        if not user.is_verified:
            return False

        return self._send_email(
            to=user.email,
            subject="Password Reset",
            template="password_reset",
            context={"username": user.username, "token": token}
        )
```

### Security Audit Service

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth.interfaces import RefreshTokenData
    from apps.users.interfaces import UserIdentity

class SecurityAuditService:
    def analyze_user_sessions(
        self,
        user: "UserIdentity",
        tokens: list["RefreshTokenData"]
    ) -> dict:
        risk_score = 0

        # Анализ по токенам
        unique_ips = set(token.ip_address for token in tokens if token.ip_address)
        if len(unique_ips) > 5:
            risk_score += 30

        # Анализ по пользователю
        if user.has_role("admin") and not user.is_verified:
            risk_score += 50

        return {
            "user_id": user.id,
            "risk_score": risk_score,
            "risk_level": "high" if risk_score > 70 else "medium" if risk_score > 30 else "low",
            "recommendations": self._get_recommendations(risk_score)
        }
```

---

## 🔗 Заключение

Система интерфейсов обеспечивает:

- **🔒 Безопасность** - избегание циклических импортов
- **🧪 Тестируемость** - легкое создание мок-объектов
- **🔌 Гибкость** - слабая связанность между модулями
- **📝 Типизация** - полная поддержка статического анализа
- **♻️ Переиспользование** - интерфейсы работают с любыми реализациями

**Используйте интерфейсы везде, где нужно работать с объектами из других приложений!**
