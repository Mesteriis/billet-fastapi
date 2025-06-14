# Система приложений с JWT аутентификацией

## 🎯 Обзор

Проект дополнен полноценной системой пользователей с JWT аутентификацией, базовыми компонентами для всех приложений и интеграцией с OpenTelemetry для трассировки.

## 📁 Структура

```
src/apps/
├── base/                   # Базовые компоненты
│   ├── events.py          # События (create/update/delete)
│   ├── models.py          # Базовые SQLAlchemy модели
│   └── repository.py      # CRUD репозиторий
├── users/                 # Система пользователей
│   ├── models.py          # User модель
│   ├── schemas.py         # Pydantic схемы
│   ├── repository.py      # Пользовательский репозиторий
│   └── service.py         # Бизнес-логика
└── auth/                  # Система аутентификации
    ├── models.py          # RefreshToken модель
    ├── schemas.py         # JWT схемы
    ├── jwt_service.py     # JWT токены
    ├── password_service.py # Пароли
    ├── auth_service.py    # Аутентификация
    └── dependencies.py    # FastAPI зависимости
```

## 🔧 Ключевые компоненты

### BaseRepository (CRUD с событиями)

```python
# Автоматическое отслеживание изменений
user = await repository.create(db, obj_in=user_data)  # Отправляет CreateEvent
await repository.update(db, db_obj=user, obj_in=update_data)  # UpdateEvent
await repository.remove(db, id=user_id)  # DeleteEvent (мягкое удаление)
```

### JWT Authentication

- **Access токены**: 30 минут
- **Refresh токены**: 30 дней (хранятся в БД)
- Возможность отзыва токенов

```python
# Создание пары токенов
access_token, refresh_token, jti = jwt_service.create_token_pair(
    user_id=str(user.id),
    email=user.email,
    username=user.username
)
```

### Система событий

```python
# Автоматически отправляется при операциях CRUD
class CreateEvent(BaseEvent[T]):
    entity_data: T

class UpdateEvent(BaseEvent[T]):
    old_data: T
    new_data: T
    changed_fields: list[str]
```

## 🚀 Использование

### Регистрация и вход

```python
# Регистрация
user_data = UserCreate(
    email="user@example.com",
    username="testuser",
    password="SecurePass123!",
    password_confirm="SecurePass123!"
)
user = await auth_service.register_user(db, user_data=user_data)

# Вход
response = await auth_service.login(db, email="user@example.com", password="SecurePass123!")
access_token = response.tokens.access_token
```

### Защищенные эндпоинты

```python
from apps.auth.dependencies import get_current_user, get_current_superuser

@app.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)

@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: User = Depends(get_current_superuser)
):
    await user_service.delete_user(db, user_id=user_id, current_user_id=admin.id)
```

## 📊 OpenTelemetry трассировка

Все операции автоматически трассируются:

- HTTP запросы
- База данных
- Бизнес-логика
- События системы

```python
# Автоматическая инструментация
with tracer.start_as_current_span("user_service.create_user") as span:
    span.set_attribute("user.email", user_data.email)
    # ... операции
```

## 🛡️ Безопасность

- **Пароли**: bcrypt хеширование + проверка силы
- **JWT**: короткие access токены + refresh ротация
- **Отзыв токенов**: возможность отзыва refresh токенов
- **Мягкое удаление**: пользователи не удаляются навсегда
- **Валидация**: строгая валидация всех входных данных

## 🔄 Миграции

```bash
# Создание миграции
alembic revision --autogenerate -m "Create users and auth tables"

# Применение
alembic upgrade head
```

## ⚙️ Настройки

```python
# В .env
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
TRACING_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
```

## 🚀 Дальнейшие улучшения

1. **API роуты** - создать FastAPI роуты для auth и users
2. **Email верификация** - подтверждение email при регистрации
3. **Социальная аутентификация** - OAuth с Google, GitHub
4. **Система ролей** - RBAC с гранулярными разрешениями
5. **Двухфакторная аутентификация** - TOTP/SMS
6. **Rate limiting** - защита от брут-форса
7. **Session management** - управление активными сессиями
8. **Аудит логи** - детальное логирование действий

## 📈 Альтернативы

- **Cookie auth** вместо JWT для веб-приложений
- **OAuth 2.0/OIDC** для enterprise
- **Redis sessions** для масштабируемости
- **GraphQL** API вместо REST
- **MongoDB** для гибких пользовательских данных

Система готова к продакшену и легко расширяется новыми приложениями и функциями!
