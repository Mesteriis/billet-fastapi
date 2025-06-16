# Data Factories - Фабрики для генерации тестовых данных

## Обзор

Data Factories - это система классов для генерации тестовых данных в виде словарей. В отличие от factory_boy, которая создает модели БД, наши фабрики создают только словари с данными, что делает их быстрыми и независимыми от базы данных.

## Основные возможности

- ✅ **Уникальные данные** - автоматическая генерация уникальных email и username
- ✅ **Предсказуемые данные** - для тестов, требующих точных утверждений
- ✅ **Специализированные сценарии** - для различных типов тестирования
- ✅ **Batch операции** - создание множества записей одновременно
- ✅ **Полная кастомизация** - переопределение любых полей
- ✅ **Реалистичные распределения** - вероятностная генерация булевых значений

## Архитектура

### Базовые классы

```python
from tests.factories.data_factories import DataFactoryManager

# Создаем менеджер фабрик
factory = DataFactoryManager()
```

### Доступные фабрики

1. **`factory.user`** - Базовая фабрика пользователей
2. **`factory.admin`** - Фабрика администраторов
3. **`factory.predictable`** - Предсказуемая фабрика
4. **`factory.complex_filter`** - Для тестирования сложных фильтров
5. **`factory.pagination`** - Для тестирования пагинации
6. **`factory.specialized`** - Специализированные сценарии

## Примеры использования

### 1. Базовое использование

```python
from tests.factories.data_factories import DataFactoryManager

factory = DataFactoryManager()

# Создание одного пользователя
user_data = factory.user.create()
print(user_data)
# {
#     'email': 'user_a1b2c3d4@example.com',
#     'username': 'user_x9y8',
#     'full_name': 'John Doe',
#     'hashed_password': '$2b$12$...',
#     'is_active': True,
#     'is_verified': False,
#     'is_superuser': False,
#     'bio': 'Some bio text...'
# }

# Создание администратора
admin_data = factory.admin.create()
# Всегда: is_active=True, is_verified=True, is_superuser=True
```

### 2. Batch создание

```python
# Создание нескольких пользователей
users = factory.user.create_batch(count=5)
print(f"Создано {len(users)} пользователей")

# Все email и username будут уникальными
emails = [user['email'] for user in users]
assert len(set(emails)) == 5  # Все уникальны
```

### 3. Кастомизация данных

```python
# Переопределение любых полей
custom_user = factory.user.create(
    full_name="Тестовый Пользователь",
    is_active=False,
    bio="Кастомная биография"
)

# Кастомизация в batch операциях
inactive_users = factory.user.create_batch(
    count=3,
    is_active=False
)
```

### 4. Предсказуемые данные

```python
# Для тестов, требующих точных утверждений
predictable_users = factory.predictable.create_batch(count=6)

# Логика верификации: четные пользователи верифицированы
assert predictable_users[0]['is_verified'] == False  # 1-й
assert predictable_users[1]['is_verified'] == True   # 2-й
assert predictable_users[2]['is_verified'] == False  # 3-й
assert predictable_users[3]['is_verified'] == True   # 4-й

# Предсказуемые email
assert predictable_users[0]['email'] == 'predictable_user_1@testdomain.com'
assert predictable_users[1]['email'] == 'predictable_user_2@testdomain.com'
```

### 5. Сложные фильтры

```python
# Создание набора для тестирования фильтров
complex_data = factory.complex_filter.create_set()
# Возвращает список из 4 пользователей:
# 1. Администратор компании (@company.com, superuser=True)
# 2. Менеджер компании (@company.com, superuser=False)
# 3. Внешний пользователь (не @company.com, verified=False)
# 4. Неактивный пользователь компании (active=False)

admin, manager, external, inactive = complex_data

# Или создание отдельных типов
company_admin = factory.complex_filter.create_company_admin()
external_user = factory.complex_filter.create_external_user()
```

### 6. Пагинация

```python
# Данные для тестирования пагинации
pagination_data = factory.pagination.create_batch(count=15)

# Логика: каждый третий пользователь верифицирован
verified_users = [user for user in pagination_data if user['is_verified']]
# Будут верифицированы пользователи с индексами 2, 5, 8, 11, 14 (3-й, 6-й, 9-й, 12-й, 15-й)
```

### 7. Специализированные сценарии

```python
# Пользователи с биографией и без
user_with_bio = factory.specialized.create_user_with_bio()
user_without_bio = factory.specialized.create_user_without_bio()

assert user_with_bio['bio'] is not None
assert user_without_bio['bio'] is None

# Данные для различных типов тестов
comparison_data = factory.specialized.create_comparison_test_data()  # 2 пользователя
stress_data = factory.specialized.create_stress_test_data(count=100)  # Для нагрузочных тестов
concurrent_data = factory.specialized.create_concurrent_test_data(count=5)  # Для конкурентных операций
batch_data = factory.specialized.create_batch_test_data(count=20)  # Для batch операций
```

## Использование в тестах

### Pytest фикстура

```python
import pytest
from tests.factories.data_factories import DataFactoryManager

@pytest.fixture
def data_factory():
    """Фикстура для менеджера фабрик."""
    return DataFactoryManager()

def test_user_creation(data_factory):
    """Тест создания пользователя."""
    user = data_factory.user.create()
    assert '@' in user['email']
    assert isinstance(user['is_active'], bool)

def test_batch_operations(data_factory):
    """Тест batch операций."""
    users = data_factory.user.create_batch(count=10)
    assert len(users) == 10

    # Проверяем уникальность
    emails = [user['email'] for user in users]
    assert len(set(emails)) == 10
```

### Обновление существующих фикстур

```python
# В conftest.py
@pytest.fixture
def user_data(data_factory):
    """Данные пользователя."""
    return data_factory.user.create()

@pytest.fixture
def bulk_users_data(data_factory):
    """Данные для bulk операций."""
    return data_factory.user.create_batch(count=10)

@pytest.fixture
def bulk_users_data_predictable(data_factory):
    """Предсказуемые данные для точных утверждений."""
    return data_factory.predictable.create_batch(count=10)
```

## Вероятностные распределения

Фабрики используют реалистичные вероятности для булевых полей:

### UserDataFactory

- `is_active`: 85% вероятность True
- `is_verified`: 60% вероятность True
- `is_superuser`: 5% вероятность True

### PaginationDataFactory

- `is_active`: 95% вероятность True
- `is_verified`: каждый 3-й пользователь (детерминированно)

## Уникальность данных

Все фабрики гарантируют уникальность ключевых полей:

- **Email**: используется UUID + домен от Faker
- **Username**: используется UUID + префикс
- **Предсказуемые данные**: используется счетчик

```python
# Пример генерации уникальных данных
emails = [factory.user.create()['email'] for _ in range(100)]
assert len(set(emails)) == 100  # Все уникальны
```

## Кастомизация Faker

```python
from faker import Faker

# Использование русской локали
russian_faker = Faker('ru_RU')
factory = DataFactoryManager(russian_faker)

user = factory.user.create()
# Теперь full_name будет на русском языке
```

## Лучшие практики

### 1. Используйте правильную фабрику для задачи

```python
# ✅ Правильно - для точных утверждений
predictable_users = factory.predictable.create_batch(count=4)
assert predictable_users[1]['is_verified'] == True  # 2-й пользователь

# ❌ Неправильно - случайные данные для точных утверждений
random_users = factory.user.create_batch(count=4)
assert random_users[1]['is_verified'] == True  # Может провалиться!
```

### 2. Кастомизируйте только необходимые поля

```python
# ✅ Правильно
user = factory.user.create(is_active=False)

# ❌ Избыточно
user = factory.user.create(
    email="test@example.com",  # Лучше оставить автогенерацию
    username="testuser",       # Лучше оставить автогенерацию
    is_active=False
)
```

### 3. Используйте batch для множественных данных

```python
# ✅ Правильно
users = factory.user.create_batch(count=10)

# ❌ Неэффективно
users = [factory.user.create() for _ in range(10)]
```

### 4. Выбирайте подходящий тип фабрики

```python
# Для обычных тестов
user = factory.user.create()

# Для тестов администраторов
admin = factory.admin.create()

# Для тестов фильтрации
filter_data = factory.complex_filter.create_set()

# Для тестов пагинации
page_data = factory.pagination.create_batch(count=25)
```

## Расширение системы

Для добавления новых типов данных создайте новую фабрику:

```python
class CustomDataFactory(BaseDataFactory):
    """Кастомная фабрика."""

    def create_special_user(self, **kwargs):
        """Создает специального пользователя."""
        defaults = {
            "email": self._generate_unique_email("special"),
            "username": self._generate_unique_username("special"),
            # ... другие поля
        }
        defaults.update(kwargs)
        return defaults

# Добавьте в DataFactoryManager
class DataFactoryManager:
    def __init__(self, faker_instance=None):
        # ... существующий код ...
        self.custom = CustomDataFactory(self.faker)
```

## Заключение

Data Factories предоставляют мощную и гибкую систему для генерации тестовых данных. Они обеспечивают:

- **Быстроту** - нет обращений к БД
- **Гибкость** - полная кастомизация
- **Надежность** - гарантированная уникальность
- **Удобство** - простой API для всех сценариев

Используйте подходящую фабрику для каждой задачи и наслаждайтесь стабильными, быстрыми тестами!
