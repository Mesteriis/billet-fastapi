# Расширенный тестовый клиент AsyncApiTestClient

Улучшенный асинхронный тестовый клиент для FastAPI приложений с расширенными возможностями аутентификации и интеллектуальной обработкой ошибок.

## 🚀 Основные возможности

### ✨ Интеллектуальная обработка ошибок URL

- **Автоматическое предложение похожих URL**: При ошибке в `url_for()` клиент предлагает похожие имена routes
- **Алгоритм диффа**: Использует продвинутый алгоритм для поиска наиболее похожих имен
- **Контекстная помощь**: Показывает все доступные routes с их процентом схожести

### 🔐 Продвинутая аутентификация

- **Гибкое создание пользователей**: Поддержка различных типов пользователей (обычные, админы, верифицированные)
- **JWT токены**: Автоматическое создание и управление JWT токенами
- **Множественные пользователи**: Возможность переключения между пользователями в одном тесте
- **Временная аутентификация**: Автоматическое восстановление состояния после запросов

### 📊 Трекинг производительности

- **Метрики запросов**: Время ответа, размер запроса/ответа, статистика
- **Агрегированная статистика**: Среднее/минимальное/максимальное время, RPS
- **Сессии тестирования**: Группировка метрик по тестовым сценариям
- **Экспорт данных**: Сохранение метрик для анализа

### 📸 Снимки API (API Snapshots)

- **Регрессионное тестирование**: Создание снимков состояния API
- **Валидация схем**: Автоматическая проверка структуры ответов
- **Сравнение версий**: Обнаружение изменений в API между версиями
- **Автоматическое сохранение**: Снимки сохраняются в файлы для версионирования

### 🔄 Retry механизмы

- **Умные повторы**: Автоматические повторы при временных сбоях
- **Гибкие стратегии**: Линейная, экспоненциальная, Фибоначчи
- **Настраиваемые условия**: Выбор кодов статусов для retry
- **Контроль времени**: Настройка задержек и максимального времени ожидания

### 🔗 Chain тестирование

- **Последовательные сценарии**: Выполнение цепочек связанных запросов
- **Извлечение данных**: Передача данных между шагами цепочки
- **Валидация ответов**: Проверка корректности на каждом шаге
- **Контекстные запросы**: Использование результатов предыдущих запросов

### 🎭 Мокирование внешних API

- **Замещение внешних сервисов**: Мокирование HTTP запросов к внешним API
- **Настраиваемые ответы**: Контроль статус кодов, данных, задержек
- **История вызовов**: Отслеживание всех замоканных запросов
- **Эмуляция сбоев**: Тестирование обработки ошибок внешних сервисов

## 📋 Быстрый старт

### Базовое использование

```python
from tests.utils_test.api_test_client import AsyncApiTestClient
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}

async with AsyncApiTestClient(app=app) as client:
    # Генерация URL
    url = client.url_for("get_user", user_id=123)
    print(url)  # "/users/123"

    # Выполнение запроса
    response = await client.get(url)
    assert response.status_code == 200
```

### Аутентификация пользователей

```python
async with AsyncApiTestClient(app=app) as client:
    # Создание и аутентификация обычного пользователя
    user = await client.force_auth(
        email="user@example.com",
        email_verified=True,
        is_active=True
    )

    # Создание администратора
    admin = await client.force_auth(
        email="admin@example.com",
        is_superuser=True,
        email_verified=True
    )

    # Проверка статуса аутентификации
    assert client.is_authenticated()
    assert client.get_current_user() == admin
```

### Работа с несколькими пользователями

```python
async with AsyncApiTestClient(app=app) as client:
    # Создание пользователей
    user1 = await UserFactory.create(email="user1@test.com")
    user2 = await UserFactory.create(email="user2@test.com", is_superuser=True)

    # Запросы от имени разных пользователей
    response1 = await client.get_as_user("/profile", user=user1)
    response2 = await client.get_as_user("/admin/panel", user=user2)

    # Клиент автоматически переключается между пользователями
```

### Обработка ошибок URL с предложениями

```python
async with AsyncApiTestClient(app=app) as client:
    try:
        # Опечатка в имени route
        client.url_for("get_usr", user_id=123)  # Должно быть "get_user"
    except ValueError as e:
        print(str(e))
        # Route 'get_usr' не найден.
        #
        # Возможно, вы имели в виду один из этих routes:
        #   - get_user (схожесть: 85.71%)
        #   - get_user_posts (схожесть: 76.92%)
        #   - get_user_profile (схожесть: 72.73%)
        #
        # Все доступные routes (3):
        #   - get_user
        #   - get_user_posts
        #   - get_user_profile
```

## 🔧 API Reference

### AsyncApiTestClient

#### Конструктор

```python
AsyncApiTestClient(app: Optional[FastAPI] = None, **kwargs)
```

**Параметры:**

- `app`: Экземпляр FastAPI приложения
- `**kwargs`: Дополнительные параметры для httpx.AsyncClient

#### Основные методы

##### url_for(name: str, /, \*\*path_params) -> str

Генерация URL для endpoint с интеллектуальной обработкой ошибок.

**Параметры:**

- `name`: Имя route функции
- `**path_params`: Параметры пути

**Возвращает:** Сгенерированный URL

**Raises:** `ValueError` с предложениями похожих routes

##### force_auth(\*\*kwargs) -> User

Принудительная аутентификация пользователя.

**Параметры:**

- `user`: Существующий пользователь (приоритет над email)
- `email`: Email для поиска/создания пользователя
- `email_verified`: Статус верификации email (default: True)
- `is_superuser`: Права суперпользователя (default: False)
- `is_active`: Активность пользователя (default: True)
- `**user_kwargs`: Дополнительные параметры для создания пользователя

**Возвращает:** Аутентифицированный пользователь

##### force_logout() -> None

Выход из системы - удаление токенов авторизации.

#### HTTP методы с аутентификацией

```python
# Запросы от имени конкретного пользователя
async def get_as_user(url: str, user: Optional[User] = None, **kwargs) -> Response
async def post_as_user(url: str, user: Optional[User] = None, **kwargs) -> Response
async def put_as_user(url: str, user: Optional[User] = None, **kwargs) -> Response
async def delete_as_user(url: str, user: Optional[User] = None, **kwargs) -> Response
```

#### Утилиты

```python
def is_authenticated() -> bool              # Проверка аутентификации
def get_current_user() -> Optional[User]    # Получение текущего пользователя
def get_auth_headers() -> dict[str, str]    # Получение заголовков авторизации
def clear_cache() -> None                   # Очистка кеша routes
```

## 🎯 Продвинутые паттерны

### Тестирование с разными ролями

```python
@pytest.mark.parametrize("user_type,expected_status", [
    ("regular", 403),
    ("admin", 200),
    ("superuser", 200)
])
async def test_endpoint_access(user_type, expected_status):
    async with AsyncApiTestClient(app=app) as client:
        if user_type == "regular":
            await client.force_auth(is_superuser=False)
        elif user_type == "admin":
            await client.force_auth(is_superuser=True)

        response = await client.get("/admin/endpoint")
        assert response.status_code == expected_status
```

### Тестирование workflow с несколькими пользователями

```python
async def test_collaboration_workflow():
    async with AsyncApiTestClient(app=app) as client:
        # Создание пользователей для сценария
        author = await UserFactory.create(email="author@test.com")
        reviewer = await UserFactory.create(email="reviewer@test.com", is_superuser=True)

        # 1. Автор создает документ
        response = await client.post_as_user(
            "/documents",
            user=author,
            json={"title": "New Document", "content": "Draft content"}
        )
        doc_id = response.json()["id"]

        # 2. Рецензент просматривает документ
        response = await client.get_as_user(f"/documents/{doc_id}", user=reviewer)
        assert response.status_code == 200

        # 3. Рецензент одобряет документ
        response = await client.post_as_user(
            f"/documents/{doc_id}/approve",
            user=reviewer
        )
        assert response.status_code == 200
```

### Оптимизация производительности

```python
async def test_performance_optimization():
    async with AsyncApiTestClient(app=app) as client:
        # Предварительное заполнение кеша routes
        available_routes = client._get_available_routes()
        print(f"Доступно routes: {len(available_routes)}")

        # Пакетная аутентификация пользователей
        users = []
        for i in range(10):
            user = await client.force_auth(email=f"user{i}@test.com")
            users.append(user)

        # Параллельное выполнение запросов
        tasks = []
        for user in users:
            task = client.get_as_user("/profile", user=user)
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        assert all(r.status_code == 200 for r in responses)
```

## 🚨 Важные особенности

### Безопасность типов

Клиент использует строгую типизацию для предотвращения ошибок времени выполнения:

```python
# ✅ Правильно
user: Optional[User] = None
email: Optional[str] = None

# ❌ Неправильно
user: User = None  # Type error!
email: str = None  # Type error!
```

### Управление памятью

При работе с большим количеством пользователей используйте context manager:

```python
# ✅ Автоматическая очистка
async with AsyncApiTestClient(app=app) as client:
    await client.force_auth(...)
    # Пользователь автоматически разлогинится при выходе

# ❌ Ручная очистка (может привести к утечкам)
client = AsyncApiTestClient(app=app)
await client.force_auth(...)
# Нужно вручную вызвать client.force_logout()
```

### Кеширование routes

Кеш routes автоматически обновляется, но при динамическом изменении routes используйте:

```python
client.clear_cache()  # Принудительная очистка кеша
```

## 🛠 Альтернативы и расширения

### Альтернативные подходы

1. **Использование pytest fixtures**:

```python
@pytest.fixture
async def authenticated_client(app):
    async with AsyncApiTestClient(app=app) as client:
        await client.force_auth(is_superuser=True)
        yield client
```

2. **Создание специализированных клиентов**:

```python
class AdminTestClient(AsyncApiTestClient):
    async def __aenter__(self):
        await super().__aenter__()
        await self.force_auth(is_superuser=True)
        return self
```

### Будущие улучшения

1. **Интеграция с OpenAPI**: Автоматическая генерация URL на основе OpenAPI схемы
2. **Поддержка WebSocket**: Расширение для тестирования WebSocket соединений
3. **Интеграция с базой данных**: Автоматическое создание тестовых данных в БД
4. **Поддержка файлов**: Упрощенная загрузка файлов в тестах
5. **Метрики производительности**: Встроенный профилирование запросов

## 📝 Заключение

`AsyncApiTestClient` предоставляет мощные инструменты для тестирования FastAPI приложений с акцентом на удобство использования, безопасность типов и продвинутую обработку ошибок. Интеллектуальные предложения при ошибках URL значительно ускоряют разработку тестов и снижают количество опечаток.
