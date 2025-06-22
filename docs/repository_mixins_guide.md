# 🧩 Модульная архитектура репозиториев

## 📋 Обзор

Система репозиториев переработана в модульную архитектуру с использованием миксинов. Это позволяет использовать только нужные функции и улучшает производительность.

## 🏗️ Архитектура

```
BaseRepository (DEPRECATED)
├── QueryBuilder (отдельный класс)
├── BaseCrudMixin (уровень 1) - Базовые CRUD операции
├── AdvancedMixin (уровень 2) - Продвинутые возможности
├── EnterpriseMixin (уровень 3) - Корпоративные функции
└── EventMixin (опциональная функциональность) - Система событий
```

## 📊 Уровень 1: BaseCrudMixin

**Базовые CRUD операции для простых проектов**

### Функциональность

- ✅ `create()` - создание объекта
- ✅ `get()` - получение по ID
- ✅ `update()` - обновление объекта
- ✅ `remove()` - удаление (soft/hard)
- ✅ `restore()` - восстановление soft-deleted
- ✅ `list()` - простой список с offset/limit
- ✅ `count()` - подсчет записей
- ✅ `exists()` - проверка существования
- ✅ `get_by()` - поиск по простым фильтрам

### Поддерживаемые операторы

- `eq`, `ne`, `lt`, `lte`, `gt`, `gte` (сравнение)
- `isnull`, `isnotnull` (проверка NULL)

### Пример использования

```python
from src.core.base.repo import BaseCrudMixin

class UserRepository(BaseCrudMixin[User, CreateUserSchema, UpdateUserSchema]):
    pass

user_repo = UserRepository(User, db_session)

# Создание
user = await user_repo.create({"name": "John", "email": "john@example.com"})

# Получение
user = await user_repo.get(user_id)

# Список с простыми фильтрами
users = await user_repo.list(
    status="active",
    age__gt=18,
    deleted_at__isnull=True,
    limit=10
)

# Подсчет
total_users = await user_repo.count(status="active")
```

---

## 🚀 Уровень 2: AdvancedMixin

**Продвинутые возможности для средних проектов**

### Функциональность

- ✅ **Расширенная фильтрация:** все 40+ операторов
- ✅ **Полнотекстовый поиск:** PostgreSQL с поддержкой языков
- ✅ **Курсорная пагинация:** для больших данных
- ✅ **Сложные фильтры:** AND/OR/NOT условия
- ✅ **Агрегации:** SUM, AVG, MAX, MIN, COUNT, GROUP BY
- ✅ **JOIN операции:** автоматические JOIN через фильтры

### Дополнительные операторы

- **Строковые:** `like`, `ilike`, `startswith`, `endswith`, `contains`, `regex`
- **Коллекции:** `in`, `not_in`, `between`, `not_between`
- **Даты:** `date`, `year`, `month`, `day`, `week`, `quarter`
- **JSON:** `json_contains`, `json_has_key`, `json_extract`
- **Полнотекстовый поиск:** `search`, `search_phrase`, `search_websearch`

### Пример использования

```python
from src.core.base.repo import BaseCrudMixin, AdvancedMixin

class UserRepository(BaseCrudMixin[User, CreateUserSchema, UpdateUserSchema],
                    AdvancedMixin[User, CreateUserSchema, UpdateUserSchema]):
    pass

user_repo = UserRepository(User, db_session)

# Расширенная фильтрация
users = await user_repo.list(
    email__icontains="@company.com",
    created_at__date_gte=date(2023, 1, 1),
    status__in=["active", "pending"],
    age__between=[18, 65]
)

# Полнотекстовый поиск
results = await user_repo.fulltext_search(
    search_fields=["name", "bio", "skills"],
    query_text="python developer",
    search_type="websearch",
    language="english",
    min_rank=0.1,
    limit=20,
    include_rank=True
)

# Сложные фильтры
complex_filters = {
    "and_filters": {"status": "active", "age__gt": 18},
    "or_filters": [
        {"role": "admin"},
        {"permissions__contains": "write"}
    ],
    "not_filters": {"deleted_at__isnotnull": True}
}

users = await user_repo.list_with_complex_filters(
    complex_filters,
    limit=20,
    order_by="created_at"
)

# Агрегации
stats = await user_repo.aggregate(
    field="age",
    operations=["count", "avg", "min", "max"],
    group_by="department",
    status="active"
)

# Курсорная пагинация
page1 = await user_repo.paginate_cursor(
    cursor_field="created_at",
    direction="next",
    limit=10,
    status="active"
)

if page1.has_next:
    page2 = await user_repo.paginate_cursor(
        cursor_field="created_at",
        cursor_value=page1.next_cursor,
        direction="next",
        limit=10,
        status="active"
    )
```

---

## 🏢 Уровень 3: EnterpriseMixin

**Корпоративные функции для крупных проектов**

### Функциональность

- ✅ **Кэширование:** интеграция с Redis/Memory
- ✅ **Cache Management:** статистика, прогрев, инвалидация
- ✅ **Bulk операции:** массовые операции с батчингом
- ✅ **Мониторинг:** статистика производительности

### Пример использования

```python
from src.core.base.repo import (
    BaseCrudMixin, AdvancedMixin, EnterpriseMixin, CacheManager
)

class UserRepository(BaseCrudMixin[User, CreateUserSchema, UpdateUserSchema],
                    AdvancedMixin[User, CreateUserSchema, UpdateUserSchema],
                    EnterpriseMixin[User, CreateUserSchema, UpdateUserSchema]):
    pass

# С кэшированием
cache_manager = CacheManager(redis_client=redis_client)
user_repo = UserRepository(User, db_session, cache_manager)

# Bulk создание
users_data = [
    {"name": "User1", "email": "user1@example.com"},
    {"name": "User2", "email": "user2@example.com"},
    # ... еще 1000 пользователей
]

created_users = await user_repo.bulk_create(
    users_data,
    batch_size=500
)

# Bulk обновление
updated_count = await user_repo.bulk_update(
    filters={"status": "inactive"},
    update_data={"status": "archived", "updated_at": datetime.utcnow()}
)

# Bulk удаление
deleted_count = await user_repo.bulk_delete(
    filters={"created_at__lt": cutoff_date},
    soft_delete=True
)

# Управление кэшем
await user_repo.invalidate_cache("*")  # Очистить весь кэш
await user_repo.warm_cache([
    {"status": "active", "limit": 10},
    {"role": "admin"},
])

# Статистика кэша
stats = await user_repo.get_cache_stats()
print(f"Cache enabled: {stats['cache_enabled']}")
print(f"Active entries: {stats['memory']['active_entries']}")
```

---

## 🎭 EventMixin

**Система событий для проектов с архитектурой событий**

### Функциональность

- ✅ **Event Integration:** CreateEvent, UpdateEvent, DeleteEvent
- ✅ **Event Control:** параметры `emit_event` во всех операциях
- ✅ **Event Hooks:** настраиваемые хуки для событий
- ✅ **Bulk Events:** события для массовых операций

### Пример использования

```python
from src.core.base.repo import BaseCrudMixin, EventMixin

class UserRepository(BaseCrudMixin[User, CreateUserSchema, UpdateUserSchema],
                    EventMixin[User, CreateUserSchema, UpdateUserSchema]):
    pass

user_repo = UserRepository(User, db_session)

# Создание с событием
user = await user_repo.create_with_event({
    "name": "John",
    "email": "john@example.com"
})

# Обновление с событием
updated_user = await user_repo.update_with_event(
    user,
    {"status": "active", "last_login": datetime.utcnow()}
)

# Удаление с событием
deleted_user = await user_repo.remove_with_event(
    user_id,
    soft_delete=True
)

# Восстановление с событием
restored_user = await user_repo.restore_with_event(user_id)

# Bulk операции с событиями
created_users = await user_repo.bulk_create_with_events(
    users_data,
    emit_events=True
)

# Создание без события
user = await user_repo.create_with_event(
    user_data,
    emit_event=False
)

# Настройка источника событий
class CustomUserRepository(BaseCrudMixin, EventMixin):
    _event_source = "user_service"
    _event_version = "2.0"

    async def _before_create_event(self, data):
        # Кастомная логика перед созданием
        data["created_by"] = "system"
        return data

    async def _after_update_event(self, db_obj, old_data, new_data):
        # Кастомная логика после обновления
        print(f"User {db_obj.id} updated: {list(new_data.keys())}")
```

---

## 📦 Готовые классы репозиториев

### SimpleRepository

```python
from src.core.base.repo import SimpleRepository

class UserRepository(SimpleRepository[User, CreateUserSchema, UpdateUserSchema]):
    pass
```

### AdvancedRepository

```python
from src.core.base.repo import AdvancedRepository

class UserRepository(AdvancedRepository[User, CreateUserSchema, UpdateUserSchema]):
    pass
```

### EventDrivenRepository

```python
from src.core.base.repo import EventDrivenRepository

class UserRepository(EventDrivenRepository[User, CreateUserSchema, UpdateUserSchema]):
    pass
```

### EnterpriseRepository

```python
from src.core.base.repo import EnterpriseRepository

class UserRepository(EnterpriseRepository[User, CreateUserSchema, UpdateUserSchema]):
    pass

# С кэшированием
user_repo = UserRepository(User, db_session, cache_manager)
```

### FullRepository

```python
from src.core.base.repo import FullRepository

class UserRepository(FullRepository[User, CreateUserSchema, UpdateUserSchema]):
    pass

# Все возможности доступны
user_repo = UserRepository(User, db_session, cache_manager)
```

---

## 🔄 Миграция с BaseRepository

### Старый код (DEPRECATED)

```python
from src.core.base.repo import BaseRepository

class UserRepository(BaseRepository[User, CreateUserSchema, UpdateUserSchema]):
    pass

user_repo = UserRepository(User, db_session, cache_config)
```

### Новый код (РЕКОМЕНДУЕТСЯ)

```python
from src.core.base.repo import AdvancedRepository, CacheManager

class UserRepository(AdvancedRepository[User, CreateUserSchema, UpdateUserSchema]):
    pass

cache_manager = CacheManager(redis_client=redis_client)
user_repo = UserRepository(User, db_session)
```

---

## 🎯 Рекомендации по выбору

| Тип проекта           | Рекомендуемый репозиторий | Описание                                |
| --------------------- | ------------------------- | --------------------------------------- |
| 🔰 Простой проект     | `SimpleRepository`        | Базовые CRUD, простые фильтры           |
| 🚀 Средний проект     | `AdvancedRepository`      | + расширенные фильтры, поиск, агрегации |
| 🏢 Крупный проект     | `EnterpriseRepository`    | + кэширование, bulk операции            |
| 🎭 Проект с событиями | `EventDrivenRepository`   | Базовые CRUD + события                  |
| 🌟 Все возможности    | `FullRepository`          | Все функции (может быть избыточным)     |

---

## 💡 Преимущества модульной архитектуры

1. **📦 Модульность:** используйте только нужные функции
2. **⚡ Производительность:** меньше кода = быстрее загрузка
3. **🧪 Тестирование:** каждый миксин тестируется отдельно
4. **🔧 Расширяемость:** легко добавлять новые миксины
5. **📖 Читаемость:** каждый файл ~300-500 строк вместо 1400
6. **🎯 Целевое использование:** выбор репозитория под задачу

---

## 🔗 См. также

- [Документация по кэшированию](cache_system.md)
- [Система событий](events_system.md)
- [Примеры использования](repository_examples.md)
- [API референс](api_reference.md)
