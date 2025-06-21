# 🔍 Inter-App Imports Linter

**Линтер для контроля импортов между приложениями** - инструмент для поддержания архитектурной целостности проекта путем контроля зависимостей между модулями в папке `apps/`.

## 🎯 Цель

Обеспечить **слабую связанность** между приложениями, разрешая взаимодействие только через:

- 🔗 **Интерфейсы** (`interfaces.py`)
- 🔒 **TYPE_CHECKING блоки** (для типизации)
- 🤝 **Shared модули** (общие компоненты)

## 📋 Правила Импортов

| Тип импорта                           | Разрешено | Пример                                                 |
| ------------------------------------- | --------- | ------------------------------------------------------ |
| **Прямые импорты между приложениями** | ❌        | `from apps.users.models import User`                   |
| **Импорты интерфейсов**               | ✅        | `from apps.users.interfaces import UserIdentity`       |
| **Импорты в TYPE_CHECKING**           | ✅        | `if TYPE_CHECKING: from apps.users.models import User` |
| **Импорты из разрешенных путей**      | ✅        | `from core.database import get_db`                     |

## 🚀 Использование

### Запуск через Make

```bash
# Проверить импорты в приложениях
make check-imports

# Подробная проверка
make check-imports-verbose

# Проверить весь проект
make check-imports-all
```

### Прямой запуск

```bash
# Базовая проверка
python scripts/inter_app_imports_linter.py src/apps

# С подробным выводом
python scripts/inter_app_imports_linter.py src/apps --verbose

# Проверить конкретный файл
python scripts/inter_app_imports_linter.py src/apps/users/api/user_routes.py
```

### Pre-commit хук

Линтер автоматически запускается при коммитах:

```bash
# Установить pre-commit хуки
make pre-commit-install

# Запустить все хуки
make pre-commit-run
```

## ⚙️ Конфигурация

Настройки в `pyproject.toml`:

```toml
[tool.inter_app_imports_linter]
# Пути для проверки
paths = ["src/apps"]
# Паттерны исключений
exclude_patterns = ["__pycache__", ".venv", "test_*", "*.pyc"]
# Строгий режим
strict_mode = true
# Разрешенные пути для импортов (общие модули)
allow_shared_imports = [
    "apps.shared",     # Общие модули между приложениями
    "core",            # Ядро системы
    "constants",       # Константы проекта
    "utils",           # Утилиты
    "exceptions",      # Общие исключения
]
# Имя модуля интерфейсов
interfaces_module = "interfaces"
```

### 🔧 Варианты Конфигурации

**Минимальная конфигурация:**

```toml
[tool.inter_app_imports_linter]
allow_shared_imports = ["core"]
```

**Для микросервисной архитектуры:**

```toml
[tool.inter_app_imports_linter]
allow_shared_imports = [
    "shared.models",
    "shared.utils",
    "shared.exceptions",
    "common.database",
    "common.auth",
]
```

**Для монолитной архитектуры:**

```toml
[tool.inter_app_imports_linter]
allow_shared_imports = [
    "apps.shared",
    "core.database",
    "core.auth",
    "core.cache",
    "utils",
    "constants",
    "exceptions",
]
```

**Обратная совместимость (старый формат):**

```toml
[tool.inter_app_imports_linter]
allow_shared_imports = true  # Эквивалентно ["apps.shared"]
```

## 🔧 Примеры Исправлений

### ❌ Неправильно: Прямой импорт

```python
# НАРУШЕНИЕ: Прямая зависимость между приложениями
from apps.users.models import User
from apps.auth.services import JWTService
```

### ✅ Правильно: Через интерфейсы

```python
# РЕШЕНИЕ 1: Использовать интерфейсы
from apps.users.interfaces import UserIdentity
from apps.auth.interfaces import TokenPayload

def create_token(user: UserIdentity) -> str:
    # Работает с любым объектом реализующим UserIdentity
    return f"token-{user.id}"
```

### ✅ Правильно: TYPE_CHECKING блок

```python
# РЕШЕНИЕ 2: Импорты для типизации
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.models import User
    from apps.auth.services import JWTService

def process_user(user: "User") -> dict:
    # Типизация без прямой зависимости
    return {"id": user.id}
```

### ✅ Правильно: Разрешенные пути

```python
# РЕШЕНИЕ 3: Импорты из разрешенных общих модулей
from core.database import get_db
from constants import DEFAULT_PAGE_SIZE
from utils.validators import validate_email
from exceptions import ValidationError

def process_data():
    # Использование общих модулей разрешено
    db = get_db()
    if not validate_email("test@example.com"):
        raise ValidationError("Invalid email")
    return {"page_size": DEFAULT_PAGE_SIZE}
```

## 🔍 Анализ Нарушений

Линтер выводит подробную информацию:

```bash
🔍 Inter-App Import Violations Found:

📄 src/apps/auth/api/auth_routes.py:
  Line 24: apps.users.models.user_models
    💡 Use interface: from apps.users.interfaces import [InterfaceName]
  Line 25: apps.users.schemas
    💡 Use interface: from apps.users.interfaces import [InterfaceName]

❌ Found 2 violations in 1 files

📋 Quick Fix Guide:
  1. ✅ Use interfaces: from apps.users.interfaces import UserIdentity
  2. ✅ Use TYPE_CHECKING: if TYPE_CHECKING: from apps.users.models import User
  3. ✅ Allowed shared paths: from core import ... (configurable)
```

## 🏗️ Архитектурные Паттерны

### Интерфейсы (Protocol)

```python
# apps/users/interfaces.py
from typing import Protocol

class UserIdentity(Protocol):
    """Интерфейс для идентификации пользователя."""
    id: str
    email: str
    is_active: bool
```

### Использование в других приложениях

```python
# apps/auth/services/jwt_service.py
from apps.users.interfaces import UserIdentity

class JWTService:
    def create_token(self, user: UserIdentity) -> str:
        # Работает с любым объектом реализующим UserIdentity
        return self._encode({"user_id": user.id, "email": user.email})
```

## 🧪 Тестирование

### Mock объекты для тестов

```python
# tests/mocks/user_mock.py
from apps.users.interfaces import UserIdentity

class MockUser:
    """Mock объект для тестирования."""

    def __init__(self, user_id: str, email: str):
        self.id = user_id
        self.email = email
        self.is_active = True

# Проверка совместимости
def test_mock_implements_interface():
    mock_user = MockUser("123", "test@example.com")
    assert isinstance(mock_user, UserIdentity)  # Работает благодаря Protocol
```

## 📊 Интеграция с CI/CD

### GitHub Actions

```yaml
# .github/workflows/quality.yml
- name: Check Inter-App Imports
  run: |
    python scripts/inter_app_imports_linter.py src/apps
    if [ $? -eq 1 ]; then
      echo "❌ Found inter-app import violations!"
      exit 1
    fi
```

### Pre-commit

```yaml
# .pre-commit-config.yaml
- id: inter-app-imports-check
  name: Inter-App Imports Check
  entry: python scripts/inter_app_imports_linter.py
  language: system
  args: ["src/apps"]
  pass_filenames: false
  always_run: true
```

## 🚨 Исключения

### Временные исключения

Если нужно временно отключить проверку для файла:

```python
# my_file.py
# inter-app-imports: disable

from apps.users.models import User  # Не будет проверяться
```

### Конфигурация исключений

```toml
[tool.inter_app_imports_linter]
exclude_files = [
    "src/apps/legacy/*.py",
    "src/apps/*/migrations/*.py"
]
```

## 🎁 Преимущества

### ✅ Слабая связанность

- Модули не зависят напрямую друг от друга
- Легче рефакторинг и изменения
- Возможность независимой разработки команд

### ✅ Тестируемость

- Mock объекты через интерфейсы
- Изолированное тестирование модулей
- Внедрение зависимостей

### ✅ Производительность

- Избежание циклических импортов
- Ленивая загрузка через TYPE_CHECKING
- Быстрее запуск приложения

## 🔄 Миграция Существующего Кода

### Шаг 1: Анализ

```bash
# Найти все нарушения
make check-imports > violations.txt
```

### Шаг 2: Создание интерфейсов

```python
# apps/users/interfaces.py
class UserRef(Protocol):
    id: str
    email: str
```

### Шаг 3: Замена импортов

```python
# Было
from apps.users.models import User

# Стало
from apps.users.interfaces import UserRef
```

### Шаг 4: Обновление типов

```python
# Было
def process_user(user: User) -> dict:

# Стало
def process_user(user: UserRef) -> dict:
```

## 📖 Best Practices

1. **Создавайте интерфейсы перед импортами**
2. **Используйте TYPE_CHECKING для типизации**
3. **Группируйте связанные интерфейсы**
4. **Документируйте интерфейсы**
5. **Тестируйте совместимость через isinstance()**

## 🤝 Совместимость

- **Python**: 3.11+
- **FastAPI**: Любая версия
- **SQLAlchemy**: Полная поддержка через Protocol
- **Pydantic**: Интеграция через Union типы

---

**💡 Помните**: Цель линтера - поддержание чистой архитектуры, а не создание препятствий для разработки. Интерфейсы делают код более гибким и тестируемым!
