# 🏗️ Система автогенерации приложений

## 📋 Обзор

Система автогенерации приложений с тремя уровнями сложности для быстрого создания CRUD функциональности.

**Ключевые особенности:**

- 🎯 **Конфигурация через TOML** - простая настройка приложения
- 🧪 **Автогенерация тестов** - полное покрытие всех компонентов
- 🚨 **Rich система исключений** - typing.Protocol + rich traceback + детальный контекст
- 📚 **Автоматическая документация** - README и комментарии к коду
- 🔧 **Модульная архитектура** - использование миксинов репозиториев
- 🏗️ **Unit of Work & DI** - корпоративные паттерны для Enterprise уровня

## 🎯 CLI пакет autogen

### Структура CLI пакета

```bash
autogen/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py          # Основной CLI entry point (typer)
│   ├── start.py         # Команда startapp
│   ├── init.py          # Команда initapp
│   └── interactive.py   # Интерактивный режим
├── templates/
│   ├── basic_crud/
│   │   ├── models.py.j2
│   │   ├── schemas.py.j2
│   │   ├── repository.py.j2
│   │   ├── service.py.j2
│   │   ├── api.py.j2
│   │   ├── exceptions.py.j2
│   │   └── tests/
│   │       ├── conftest.py.j2
│   │       ├── factories.py.j2
│   │       └── test_*.py.j2
│   ├── advanced/
│   │   ├── models.py.j2      # Наследует от basic_crud
│   │   ├── repository.py.j2  # AdvancedRepository
│   │   ├── interfaces.py.j2  # typing.Protocol интерфейсы
│   │   └── tests/
│   │       └── test_advanced_*.py.j2
│   ├── enterprise/
│   │   ├── repository.py.j2  # EnterpriseRepository + UoW
│   │   ├── di_container.py.j2 # DI контейнер
│   │   ├── unit_of_work.py.j2 # UoW паттерн
│   │   └── tests/
│   │       └── test_enterprise_*.py.j2
│   └── custom/           # Пользовательские шаблоны (override)
│       └── README.md     # Инструкции по созданию кастомных шаблонов
├── core/
│   ├── generators.py     # Генераторы компонентов
│   ├── migrations.py     # Alembic integration
│   ├── validators.py     # Валидация конфигураций
│   └── template_engine.py # Jinja2 обработка шаблонов
└── utils.py             # Утилиты (TOML, naming, paths)

```

### Команды CLI (typer)

#### 1. `autogen startapp <app-name>`

```bash
autogen startapp products
# Создает базовую структуру + app_config.toml + README.md
```

#### 2. `autogen initapp <app-name> [OPTIONS]`

```bash
autogen initapp products --level BasicCRUD --dry-run
autogen initapp articles --level Advanced --overwrite
autogen initapp customers --level Enterprise
```

**Опции:**

- `--level`: Явно указать уровень (BasicCRUD/Advanced/Enterprise)
- `--dry-run`: Показать что будет создано без реального создания
- `--overwrite`: Перезаписать существующие файлы
- `--template-dir`: Использовать кастомные шаблоны

#### 3. `autogen --interactive`

```bash
autogen --interactive
# Интерактивный режим конфигурации приложения
```

---

## 🏢 Три уровня приложений

### 🔰 Уровень 1: BasicCRUD

**Для простых приложений с базовыми CRUD операциями**

**Генерируемые компоненты:**

- ✅ Model (базовая модель)
- ✅ Schemas (Create/Update/Response)
- ✅ Repository (SimpleRepository)
- ✅ Service (базовый сервис)
- ✅ API routes (CRUD endpoints)
- ✅ Dependencies (базовые зависимости)
- ✅ Exceptions (5 базовых исключений)
- ✅ Tests (7 файлов: models, schemas, repo, service, api, factories, conftest + E2E)

**Функциональность:**

- Основные CRUD операции
- Простые фильтры (eq, ne, lt, gt)
- Базовая валидация
- Простые исключения
- **Базовый DI**: FastAPI Depends для инъекции зависимостей

---

### 🚀 Уровень 2: Advanced

**Для проектов с продвинутыми возможностями**

**Генерируемые компоненты:**

- ✅ Model (расширенная модель)
- ✅ Schemas (с дополнительными полями)
- ✅ Repository (AdvancedRepository)
- ✅ Service (продвинутый сервис)
- ✅ API routes (расширенные endpoints)
- ✅ Dependencies (продвинутые зависимости)
- ✅ Exceptions (10 исключений: 5 базовых + 5 продвинутых)
- ✅ Interfaces (интерфейсы для взаимодействия)
- ✅ Tests (9 файлов: базовые + расширенные тесты + фабрики + conftest + E2E)

**Дополнительная функциональность:**

- Расширенная фильтрация (40+ операторов)
- Полнотекстовый поиск
- Курсорная пагинация
- Агрегации
- Сложные фильтры (AND/OR/NOT)
- **Расширенный DI**: автоматическая регистрация зависимостей
- **Rich traceback**: красивые ошибки с контекстом
- **typing.Protocol**: интерфейсы для лучшей типизации

---

### 🏢 Уровень 3: Enterprise

**Для корпоративных приложений**

**Генерируемые компоненты:**

- ✅ Model (полная модель с аудитом)
- ✅ Schemas (полный набор схем)
- ✅ Repository (EnterpriseRepository)
- ✅ Service (корпоративный сервис)
- ✅ API routes (полный набор endpoints)
- ✅ Dependencies (все зависимости)
- ✅ Exceptions (15 исключений: 5+5+5)
- ✅ Interfaces (полные интерфейсы)
- ✅ Cache configuration (настройки кэширования)
- ✅ Events (система событий)
- ✅ Monitoring (метрики и мониторинг)
- ✅ Unit of Work (управление транзакциями)
- ✅ DI Container (полный контейнер зависимостей)
- ✅ Tests (11 файлов: все тесты + корпоративные + фабрики + conftest + E2E)

**Корпоративная функциональность:**

- Кэширование (Redis/Memory)
- Bulk операции
- Система событий
- Аудит изменений
- Метрики производительности
- Enterprise Security
- **Unit of Work паттерн** для управления транзакциями
- **Полный DI контейнер** с автоматической регистрацией
- **Rich traceback** с детальным контекстом ошибок
- **typing.Protocol** для строгой типизации интерфейсов

---

## 📁 Структура генерируемых приложений

### Базовая структура (создается `startapp`)

```bash
src/apps/app_name/
├── __init__.py
├── models/
│   ├── __init__.py
│   └── app_name_models.py      # Базовая модель
├── app_config.toml             # Конфигурация приложения
└── README.md                   # Инструкции по настройке
```

### Полная структура (создается `initapp`)

```bash
# Структура приложения
src/apps/app_name/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── app_name_models.py     # Полная модель
│   └── enums.py               # Енумы (если нужны)
├── schemas/
│   ├── __init__.py
│   └── app_name_schemas.py    # Pydantic схемы
├── repo/
│   ├── __init__.py
│   └── app_name_repo.py       # Репозиторий по уровню
├── services/
│   ├── __init__.py
│   └── app_name_service.py    # Сервис по уровню
├── api/
│   ├── __init__.py
│   └── app_name_routes.py     # API routes
├── depends/
│   ├── __init__.py
│   ├── repositories.py       # Зависимости репозиториев
│   ├── services.py           # Зависимости сервисов
│   └── examples.py           # Примеры данных (для Advanced/Enterprise)
├── exceptions.py              # Исключения по уровню
├── interfaces.py             # Интерфейсы (для Advanced/Enterprise)
├── middleware/               # Middleware (только для Enterprise)
│   └── __init__.py
├── events/                   # События (только для Enterprise)
│   └── __init__.py
├── app_config.toml           # Конфигурация приложения
└── README.md                 # Документация приложения

# Структура тестов (отдельно от приложения)
tests/apps/app_name/
├── __init__.py
├── conftest.py               # Фикстуры приложения
├── factories.py              # Фабрики данных
├── test_app_name_models.py   # Тесты моделей
├── test_app_name_schemas.py  # Тесты схем
├── test_app_name_repo.py     # Тесты репозитория
├── test_app_name_service.py  # Тесты сервиса
├── test_app_name_api.py      # Тесты API
└── e2e/                      # E2E тесты
    ├── __init__.py
    └── test_app_name_crud_e2e.py  # CRUD E2E тесты
```

---

## 🚨 Система исключений по уровням

### Базовые исключения (вне приложения)

```python
# Базовые исключения системы (core/exceptions/)
from typing import Protocol
from rich.traceback import install
from rich.console import Console

# Установка rich traceback для красивых ошибок
install(show_locals=True)
console = Console()

class ExceptionProtocol(Protocol):
    """Протокол для всех исключений системы."""

    def get_error_code(self) -> str:
        """Получить код ошибки."""
        ...

    def get_user_message(self) -> str:
        """Получить сообщение для пользователя."""
        ...

    def get_details(self) -> dict:
        """Получить детали ошибки."""
        ...

class BaseException(Exception):
    """Базовое исключение с rich traceback поддержкой."""

    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def get_error_code(self) -> str:
        return self.error_code

    def get_user_message(self) -> str:
        return str(self)

    def get_details(self) -> dict:
        return self.details

    def __rich__(self):
        """Rich display для красивого вывода."""
        return f"[red]{self.error_code}[/red]: {self.get_user_message()}"

class DBException(BaseException):
    pass

class RepoException(BaseException):
    pass

class ServiceException(BaseException):
    pass

class APIException(BaseException, HTTPException):
    pass
```

### Исключения приложения (внутри приложения)

### 🔰 BasicCRUD (5 исключений)

```python
# Базовые исключения приложения с rich traceback
class BaseAppNameException(BaseException):
    """Базовое исключение приложения AppName."""

    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message, error_code or "APP_NAME_ERROR", details)

class AppNameDBException(DBException, BaseAppNameException):
    """Исключения базы данных для AppName."""

    def __init__(self, message: str, query: str | None = None, **kwargs):
        details = {"query": query} if query else {}
        super().__init__(message, "APP_NAME_DB_ERROR", details)

class AppNameRepoException(RepoException, BaseAppNameException):
    """Исключения репозитория для AppName."""

    def __init__(self, message: str, entity_id: str | None = None, **kwargs):
        details = {"entity_id": entity_id} if entity_id else {}
        super().__init__(message, "APP_NAME_REPO_ERROR", details)

class AppNameServiceException(ServiceException, BaseAppNameException):
    """Исключения сервиса для AppName."""

    def __init__(self, message: str, operation: str | None = None, **kwargs):
        details = {"operation": operation} if operation else {}
        super().__init__(message, "APP_NAME_SERVICE_ERROR", details)

class AppNameAPIException(APIException, BaseAppNameException):
    """Исключения API для AppName."""

    def __init__(self, message: str, status_code: int = 400, endpoint: str | None = None, **kwargs):
        details = {"endpoint": endpoint} if endpoint else {}
        super().__init__(message, "APP_NAME_API_ERROR", details)
        self.status_code = status_code
```

### 🚀 Advanced (10 исключений: 5 базовых + 5 продвинутых)

```python
# Базовые + продвинутые исключения с rich traceback
class AppNameSearchException(AppNameRepoException):
    """Исключения полнотекстового поиска."""

    def __init__(self, message: str, search_query: str | None = None, **kwargs):
        details = {"search_query": search_query} if search_query else {}
        super().__init__(message, "APP_NAME_SEARCH_ERROR", details)

class AppNameFilterException(AppNameRepoException):
    """Исключения фильтрации данных."""

    def __init__(self, message: str, filters: dict | None = None, **kwargs):
        details = {"filters": filters} if filters else {}
        super().__init__(message, "APP_NAME_FILTER_ERROR", details)

class AppNameAggregationException(AppNameRepoException):
    """Исключения агрегации данных."""

    def __init__(self, message: str, aggregation_type: str | None = None, **kwargs):
        details = {"aggregation_type": aggregation_type} if aggregation_type else {}
        super().__init__(message, "APP_NAME_AGGREGATION_ERROR", details)

class AppNamePaginationException(AppNameRepoException):
    """Исключения пагинации."""

    def __init__(self, message: str, page_info: dict | None = None, **kwargs):
        details = {"page_info": page_info} if page_info else {}
        super().__init__(message, "APP_NAME_PAGINATION_ERROR", details)

class AppNameValidationException(AppNameServiceException):
    """Исключения валидации данных."""

    def __init__(self, message: str, validation_errors: list | None = None, **kwargs):
        details = {"validation_errors": validation_errors} if validation_errors else {}
        super().__init__(message, "APP_NAME_VALIDATION_ERROR", details)
```

### 🏢 Enterprise (15 исключений: 10 + 5 корпоративных)

```python
# Advanced + корпоративные исключения с rich traceback
class AppNameCacheException(AppNameRepoException):
    """Исключения кэширования."""

    def __init__(self, message: str, cache_key: str | None = None, cache_type: str | None = None, **kwargs):
        details = {
            "cache_key": cache_key,
            "cache_type": cache_type
        } if cache_key or cache_type else {}
        super().__init__(message, "APP_NAME_CACHE_ERROR", details)

class AppNameBulkOperationException(AppNameServiceException):
    """Исключения bulk операций."""

    def __init__(self, message: str, operation_type: str | None = None, failed_items: list | None = None, **kwargs):
        details = {
            "operation_type": operation_type,
            "failed_items": failed_items
        } if operation_type or failed_items else {}
        super().__init__(message, "APP_NAME_BULK_ERROR", details)

class AppNameEventException(AppNameServiceException):
    """Исключения системы событий."""

    def __init__(self, message: str, event_type: str | None = None, event_data: dict | None = None, **kwargs):
        details = {
            "event_type": event_type,
            "event_data": event_data
        } if event_type or event_data else {}
        super().__init__(message, "APP_NAME_EVENT_ERROR", details)

class AppNameMonitoringException(AppNameServiceException):
    """Исключения мониторинга."""

    def __init__(self, message: str, metric_name: str | None = None, metric_value: str | None = None, **kwargs):
        details = {
            "metric_name": metric_name,
            "metric_value": metric_value
        } if metric_name or metric_value else {}
        super().__init__(message, "APP_NAME_MONITORING_ERROR", details)

class AppNameSecurityException(AppNameAPIException):
    """Исключения безопасности."""

    def __init__(self, message: str, security_context: dict | None = None, **kwargs):
        details = {"security_context": security_context} if security_context else {}
        super().__init__(message, 403, "APP_NAME_SECURITY_ERROR", details)
```

---

## 🛠️ Шаблоны генерации

### 1. Модель-заглушка (startapp)

```python
"""AppName model definition."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.base.models import BaseModel


class AppName(BaseModel):
    """
    AppName model.

    TODO: Add your fields here
    Example:
        name: Mapped[str] = mapped_column(String(255), nullable=False)
        description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    """

    # Add your fields here
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="AppName name")

    def __repr__(self) -> str:
        return f"<AppName(id={self.id}, name='{self.name}')>"
```

### 2. Конфигурация приложения (app_config.toml)

```toml
[app]
# Уровень приложения: "BasicCRUD", "Advanced", "Enterprise"
level = "BasicCRUD"
name = "AppName"
description = "AppName application"

[database]
# Настройки таблицы
table_name = "app_names"
schema = "public"

[features]
# Включить/выключить функции
enable_soft_delete = true
enable_timestamps = true
enable_pagination = true
enable_caching = false  # Только для Enterprise
enable_events = false   # Только для Enterprise
enable_monitoring = false  # Только для Enterprise

[exceptions]
# Настройки системы исключений
enable_rich_traceback = true  # Rich traceback для красивых ошибок
enable_error_codes = true     # Уникальные коды ошибок
enable_detailed_context = true  # Детальный контекст в исключениях
log_exceptions = true         # Логирование исключений

[api]
# Настройки API
prefix = "/app-names"
tags = ["AppName"]
include_in_schema = true

[testing]
# Настройки тестирования
generate_factories = true
generate_fixtures = true
test_coverage_target = 80
```

### 3. README.md для приложения

````markdown
# AppName Application

## Настройка

1. **Отредактируйте модель** в `models/app_name_models.py`
2. **Выберите уровень приложения** в `app_config.toml`
3. **Запустите генерацию** компонентов:
   ```bash
   python scripts/initapp.py app_name
   ```
````

## Уровни приложения

- **BasicCRUD**: Основные CRUD операции
- **Advanced**: + Расширенная фильтрация, поиск, агрегации
- **Enterprise**: + Кэширование, bulk операции, события

## Структура

После выполнения `initapp` будет создана полная структура приложения с:

- Моделями и схемами
- Репозиторием и сервисом
- API роутами
- Исключениями
- Тестами

````

### 4. Repository по уровням

```python
# BasicCRUD
class AppNameRepository(SimpleRepository[AppName, CreateAppNameSchema, UpdateAppNameSchema]):
    pass

# Advanced
class AppNameRepository(AdvancedRepository[AppName, CreateAppNameSchema, UpdateAppNameSchema]):
    pass

# Enterprise
class AppNameRepository(EnterpriseRepository[AppName, CreateAppNameSchema, UpdateAppNameSchema]):
    def __init__(self, db: AsyncSession, cache_manager: CacheManager | None = None):
        super().__init__(AppName, db, cache_manager)
```

### 5. Service по уровням

```python
# BasicCRUD - только базовые методы
# Advanced - + поиск, агрегации, сложные фильтры
# Enterprise - + кэширование, bulk операции, события
```

### 6. API Routes по уровням

```python
# BasicCRUD: GET, POST, PUT, DELETE
# Advanced: + search, aggregate, complex filters
# Enterprise: + bulk operations, cache management
```

### 7. Тесты по уровням

#### BasicCRUD тесты (7 файлов + фабрики/фикстуры)

```python
# tests/apps/app_name/conftest.py - фикстуры
@pytest.fixture
async def app_name_factory():
    """Фабрика для создания AppName объектов."""
    pass

@pytest.fixture
async def app_name_obj():
    """Готовый AppName объект для тестов."""
    pass

# tests/apps/app_name/factories.py - фабрики данных
class AppNameFactory(AsyncSQLAlchemyFactory):
    """Фабрика для генерации тестовых данных AppName."""
    pass

# tests/apps/app_name/test_app_name_models.py - тесты модели
def test_model_creation():
    # Базовое создание объекта
    pass

def test_model_validation():
    # Валидация полей
    pass

# tests/apps/app_name/test_app_name_repo.py - тесты репозитория
def test_crud_operations():
    # Основные CRUD
    pass

def test_basic_filters():
    # Простые фильтры
    pass

# tests/apps/app_name/test_app_name_service.py - тесты сервиса
def test_service_create():
    pass

def test_service_get():
    pass

# tests/apps/app_name/test_app_name_api.py - тесты API
def test_create_endpoint():
    pass

def test_get_endpoint():
    pass

def test_list_endpoint():
    pass

# tests/apps/app_name/e2e/test_app_name_crud_e2e.py - E2E тесты
def test_full_crud_flow():
    """Полный цикл CRUD операций."""
    pass

def test_api_workflow():
    """Тестирование полного API workflow."""
    pass
```

#### Advanced тесты (дополнительно)

```python
# + тесты расширенной фильтрации
def test_advanced_filters():
    pass

def test_fulltext_search():
    pass

def test_aggregations():
    pass

def test_cursor_pagination():
    pass
```

#### Enterprise тесты (дополнительно)

```python
# + тесты корпоративных функций
def test_caching():
    pass

def test_bulk_operations():
    pass

def test_events():
    pass

def test_monitoring():
    pass

def test_unit_of_work():
    """Тесты Unit of Work паттерна."""
    pass

def test_dependency_injection():
    """Тесты DI контейнера."""
    pass

def test_rich_exceptions():
    """Тесты системы исключений с rich traceback."""
    pass

def test_exception_protocols():
    """Тесты typing.Protocol для исключений."""
    pass
```

---

## 🔧 CLI команды и скрипты

### Интерактивный режим `autogen --interactive`

```bash
autogen --interactive
```

**Пошаговый wizard:**
1. **Выбор имени приложения**
   - Валидация формата (snake_case, plural)
   - Проверка конфликтов с существующими приложениями

2. **Выбор уровня приложения**
   ```
   ? Выберите уровень приложения:
   ❯ BasicCRUD     - Простые CRUD операции
     Advanced      - + Поиск, фильтрация, агрегации
     Enterprise    - + Кэширование, события, UoW, DI
   ```

3. **Настройка модели**
   - Редактор полей модели
   - Автогенерация базовых полей
   - Валидация типов SQLAlchemy

4. **Конфигурация API**
   - API prefix (автогенерация из имени)
   - Включение/выключение эндпоинтов
   - Настройки OpenAPI документации

5. **Настройки функций по уровню**
   ```
   ? Включить дополнительные функции:
   [x] Soft delete
   [x] Timestamps
   [x] Pagination
   [ ] Caching (только Enterprise)
   [ ] Events (только Enterprise)
   ```

6. **Настройки тестирования**
   - Генерация фабрик
   - Target покрытия тестов
   - E2E тесты

7. **Предварительный просмотр**
   ```bash
   autogen --interactive --dry-run
   # Показывает что будет создано без реального создания
   ```

### Интеграция с Makefile

```makefile
# Новые команды с autogen
startapp:
	@read -p "Enter app name (plural): " app_name; \
	autogen startapp $$app_name

initapp:
	@read -p "Enter app name: " app_name; \
	autogen initapp $$app_name

initapp-interactive:
	autogen --interactive

initapp-dry-run:
	@read -p "Enter app name: " app_name; \
	autogen initapp $$app_name --dry-run

# Команды для работы с тестами
test-app:
	@read -p "Enter app name: " app_name; \
	pytest tests/apps/$$app_name/ -v

test-app-coverage:
	@read -p "Enter app name: " app_name; \
	pytest tests/apps/$$app_name/ --cov=src.apps.$$app_name --cov-report=html
```

---

## 📝 Алгоритм работы

### Шаг 1: `startapp AppName`

1. Создать директорию `src/apps/app_name/`
2. Создать базовые файлы `__init__.py`, `models/`
3. Сгенерировать модель-заглушку (без комментариев)
4. Создать `app_config.toml` с настройками по умолчанию
5. Создать `README.md` с инструкциями

### Шаг 2: Разработчик настраивает приложение

1. Редактирует модель, добавляет нужные поля
2. Выбирает уровень приложения в `app_config.toml`
3. Настраивает дополнительные параметры (API prefix, функции, тесты)

### Шаг 3: `autogen initapp app_name`

1. Читает конфигурацию из `app_config.toml`
2. Генерирует все компоненты согласно выбранному уровню
3. Создает исключения с правильным наследованием
4. Генерирует тесты в `tests/apps/app_name/` с фабриками и фикстурами
5. Создает E2E тесты для полного CRUD workflow
6. Регистрирует routes в главном router
7. **Создает миграцию через Alembic** (`alembic revision --autogenerate`)
8. Обновляет pyproject.toml с метаданными приложения
9. Обновляет документацию приложения

---

## 🗃️ Система миграций

### Ответственность за миграции

**Alembic (автоматически):**
- Автогенерация миграций при `autogen initapp`
- Команда: `alembic revision --autogenerate -m "Add {app_name} model"`
- Обнаружение изменений в моделях

**Ручной вызов (разработчик):**
- Кастомные миграции данных
- Команда: `alembic revision -m "Custom migration description"`
- Сложные изменения схемы БД
- Миграции, требующие бизнес-логики

### Workflow миграций в autogen

```bash
# При создании приложения
autogen initapp products
# → Автоматически: alembic revision --autogenerate -m "Add Product model"

# При изменении модели
# Разработчик редактирует модель вручную
alembic revision --autogenerate -m "Update Product model"

# Кастомные миграции данных
alembic revision -m "Populate default categories"
```

---

## 🧩 DI-контейнер по уровням

### Принципы DI-архитектуры
- **Гибкость**: легкая замена зависимостей
- **Простота**: минимум магии, максимум понятности
- **Производительность**: не влияет на скорость работы
- **Тестируемость**: простое мокирование для тестов

### BasicCRUD - Базовый DI (FastAPI Depends)
```python
# Простая инъекция через FastAPI Depends
def get_repository(db: AsyncSession = Depends(get_db)) -> AppNameRepository:
    return AppNameRepository(db)

def get_service(repo: AppNameRepository = Depends(get_repository)) -> AppNameService:
    return AppNameService(repo)

@app.get("/app-names/")
async def list_items(service: AppNameService = Depends(get_service)):
    return await service.list()
```

### Advanced - Расширенный DI (автоматическая регистрация)
```python
# Автоматическая регистрация зависимостей через декораторы
@register_dependency
class AppNameRepository(AdvancedRepository):
    pass

@register_dependency
class AppNameService:
    def __init__(self, repo: AppNameRepository):
        self.repo = repo

# FastAPI автоматически резолвит зависимости
@app.get("/app-names/")
async def list_items(service: AppNameService = Depends()):
    return await service.list()
```

### Enterprise - Полный DI (Unit of Work + контейнер)
```python
# Полноценный DI контейнер с Unit of Work
class DIContainer:
    def __init__(self):
        self._dependencies = {}
        self._singletons = {}

    def register(self, interface: type, implementation: type, lifetime: str = "transient"):
        self._dependencies[interface] = (implementation, lifetime)

    def resolve(self, interface: type):
        # Резолвинг зависимостей с учетом lifetime

@injectable
class AppNameUnitOfWork:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.app_names = AppNameRepository(db)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.db.rollback()
        else:
            await self.db.commit()

@injectable
class AppNameService:
    def __init__(self, uow: AppNameUnitOfWork):
        self.uow = uow

    async def create_with_related(self, data: CreateSchema):
        async with self.uow:
            # Автоматическое управление транзакциями
            item = await self.uow.app_names.create(data)
            await self.uow.related.create({"app_name_id": item.id})
            return item
```

---

## 🔧 Продакшен-проблемы и решения

### 🗂️ Версионирование шаблонов

**Проблема**: Через год шаблоны изменятся, и `autogen initapp --overwrite` сломает продакшн.

**Решение**: Семантическое версионирование шаблонов

```bash
autogen/
├── templates/
│   ├── v1.0/           # Стабильные шаблоны
│   │   ├── basic_crud/
│   │   ├── advanced/
│   │   └── enterprise/
│   ├── v1.1/           # Обратно совместимые изменения
│   └── v2.0/           # Breaking changes
└── migrations/         # Миграции между версиями шаблонов
    ├── v1.0_to_v1.1.py
    └── v1.1_to_v2.0.py
```

**pyproject.toml метаданные:**
```toml
[autogen.products]
level = "BasicCRUD"
template_version = "1.0"  # Версия шаблонов при создании
autogen_version = "0.1.0"  # Версия autogen при создании
last_updated = "2024-01-15T10:30:00Z"
```

**Команды миграции:**
```bash
# Проверка совместимости
autogen check products
# ⚠️  Warning: Template version 1.0 → 1.2 available (compatible)
# ❌ Error: App created with autogen 0.1.0, current 0.3.0 (breaking changes)

# Миграция шаблонов
autogen migrate products --from v1.0 --to v1.2 --dry-run
autogen migrate products --from v1.0 --to v1.2

# Принудительная миграция с пользовательскими правками
autogen migrate products --to v2.0 --strategy merge-conflicts
```

### 🛡️ Защита пользовательских изменений

**Проблема**: Простая перезапись убьет все ручные правки разработчика.

**Решение**: Система merge стратегий

```python
# autogen/core/merge_strategies.py
class MergeStrategy(Protocol):
    def merge_file(self,
                   original: str,      # Оригинальный сгенерированный файл
                   current: str,       # Текущий файл с правками пользователя
                   new_template: str   # Новый шаблон
                   ) -> MergeResult: ...

class MergeResult:
    content: str
    conflicts: List[Conflict]
    status: Literal["clean", "conflicts", "manual_required"]

# Стратегии merge
class SafeMergeStrategy:
    """Безопасное слияние с обнаружением конфликтов."""

    def merge_file(self, original, current, new_template) -> MergeResult:
        # 1. Определяем что изменил пользователь
        user_changes = diff(original, current)

        # 2. Определяем что изменилось в шаблоне
        template_changes = diff(original, new_template)

        # 3. Автоматическое слияние неконфликтующих изменений
        # 4. Маркировка конфликтов для ручного разрешения

        return MergeResult(...)

class RegenerateMergeStrategy:
    """Полная регенерация с сохранением пользовательских блоков."""

    # Использует специальные комментарии:
    # # autogen:skip-start
    # # Пользовательский код здесь
    # # autogen:skip-end
```

**Команды с merge стратегиями:**
```bash
# Безопасное обновление (по умолчанию)
autogen initapp products --overwrite --strategy safe
# → Автослияние + файл с конфликтами для ручного разрешения

# Полная регенерация с сохранением блоков
autogen initapp products --overwrite --strategy regenerate
# → Сохраняет только блоки между # autogen:skip-start/end

# Интерактивное разрешение конфликтов
autogen initapp products --overwrite --strategy interactive
# → Показывает diff и спрашивает что делать с каждым конфликтом

# Резервное копирование перед изменениями
autogen initapp products --overwrite --backup
# → Создает .backup/ с текущими файлами
```

### 🎯 API для кастомных шаблонов

**Проблема**: Кривой override кастомных шаблонов сломает генератор.

**Решение**: Строгое API с валидацией

```python
# autogen/core/template_api.py
class TemplateAPI:
    """Строгое API для кастомных шаблонов."""

    @staticmethod
    def validate_template(template_path: Path, level: str) -> ValidationResult:
        """Валидация кастомного шаблона."""
        required_files = REQUIRED_FILES_BY_LEVEL[level]
        required_variables = REQUIRED_VARIABLES_BY_LEVEL[level]

        errors = []

        # 1. Проверка обязательных файлов
        for file in required_files:
            if not (template_path / file).exists():
                errors.append(f"Missing required file: {file}")

        # 2. Проверка Jinja2 синтаксиса
        for template_file in template_path.glob("**/*.j2"):
            try:
                env.get_template(str(template_file))
            except TemplateSyntaxError as e:
                errors.append(f"Syntax error in {template_file}: {e}")

        # 3. Проверка обязательных переменных
        for template_file in template_path.glob("**/*.j2"):
            template_vars = extract_template_variables(template_file)
            missing_vars = required_variables - template_vars
            if missing_vars:
                errors.append(f"Missing variables in {template_file}: {missing_vars}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

# Обязательные файлы по уровням
REQUIRED_FILES_BY_LEVEL = {
    "BasicCRUD": [
        "models.py.j2", "schemas.py.j2", "repository.py.j2",
        "service.py.j2", "api.py.j2", "exceptions.py.j2"
    ],
    "Advanced": [
        # Наследует BasicCRUD + дополнительные
        "interfaces.py.j2"
    ],
    "Enterprise": [
        # Наследует Advanced + дополнительные
        "unit_of_work.py.j2", "di_container.py.j2"
    ]
}

# Обязательные переменные в шаблонах
REQUIRED_VARIABLES_BY_LEVEL = {
    "BasicCRUD": {
        "app_name", "model_name", "table_name", "api_prefix",
        "enable_soft_delete", "enable_timestamps"
    },
    "Advanced": {
        # Наследует BasicCRUD + дополнительные
        "enable_search", "enable_filters", "enable_aggregations"
    },
    "Enterprise": {
        # Наследует Advanced + дополнительные
        "enable_caching", "enable_events", "enable_monitoring"
    }
}
```

**Команды валидации:**
```bash
# Валидация кастомного шаблона
autogen validate-template ./my-custom-templates/enterprise/
# ✅ Template is valid for Enterprise level
# ❌ Missing required file: unit_of_work.py.j2
# ❌ Syntax error in api.py.j2: Unexpected end of template

# Использование валидированного шаблона
autogen initapp products --template-dir ./my-custom-templates/ --level Enterprise
```

### 🚨 Автоматическая интеграция исключений

**Проблема**: 95% разработчиков не будут реализовывать протоколы исключений руками.

**Решение**: Полная автоматизация + интеграция с инфраструктурой

```python
# Автогенерация протоколов исключений в шаблонах
# templates/basic_crud/exceptions.py.j2
"""
Auto-generated exceptions for {{ app_name }} app.
DO NOT EDIT: This file is managed by autogen.
"""

from typing import Protocol
from rich.traceback import install
from structlog import get_logger

# Автоматическая настройка rich traceback
install(show_locals=True, suppress=[requests, httpx])
logger = get_logger("{{ app_name }}")

# Автогенерированные протоколы
class {{ model_name }}ExceptionProtocol(Protocol):
    def get_error_code(self) -> str: ...
    def get_user_message(self) -> str: ...
    def get_telemetry_data(self) -> dict: ...  # Автоматические метрики
    def log_exception(self) -> None: ...       # Автоматическое логирование

# Автогенерированные исключения с полной интеграцией
class Base{{ model_name }}Exception(BaseException):
    def __init__(self, message: str, **context):
        super().__init__(message)
        self.context = context
        self.timestamp = datetime.utcnow()

        # Автоматическое логирование
        self.log_exception()

        # Автоматические метрики для мониторинга
        if settings.MONITORING_ENABLED:
            self._send_telemetry()

    def log_exception(self) -> None:
        """Автоматическое структурированное логирование."""
        logger.error(
            self.get_user_message(),
            error_code=self.get_error_code(),
            context=self.context,
            traceback=self.__traceback__,
            app="{{ app_name }}",
            model="{{ model_name }}"
        )

    def _send_telemetry(self) -> None:
        """Автоматические метрики в Prometheus/Grafana."""
        from core.telemetry import error_counter

        error_counter.labels(
            app="{{ app_name }}",
            error_code=self.get_error_code(),
            severity=self._get_severity()
        ).inc()

    def get_telemetry_data(self) -> dict:
        """Данные для APM систем (Sentry, DataDog)."""
        return {
            "app": "{{ app_name }}",
            "model": "{{ model_name }}",
            "error_code": self.get_error_code(),
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "severity": self._get_severity()
        }
```

**Автоматическая интеграция с мониторингом:**
```python
# autogen генерирует middleware для автоматического отлова исключений
# templates/basic_crud/middleware/exceptions.py.j2

class {{ model_name }}ExceptionMiddleware:
    """Автогенерированный middleware для отлова исключений {{ app_name }}."""

    async def __call__(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Base{{ model_name }}Exception as e:
            # Автоматический перехват всех исключений приложения

            # 1. Логирование уже произошло в __init__
            # 2. Метрики уже отправлены
            # 3. Формируем ответ пользователю

            return JSONResponse(
                status_code=getattr(e, 'status_code', 500),
                content={
                    "error": e.get_error_code(),
                    "message": e.get_user_message(),
                    "timestamp": e.timestamp.isoformat(),
                    {% if enable_detailed_errors %}
                    "details": e.context,
                    {% endif %}
                }
            )

# Автоматическая регистрация middleware
app.add_middleware({{ model_name }}ExceptionMiddleware)
```

### 🏗️ Продакшен-готовый DI контейнер

**Проблема**: Нет документации по циклическим зависимостям, скоупам, async интеграции.

**Решение**: Полноценный async-first DI контейнер

```python
# autogen/templates/enterprise/di_container.py.j2
"""
Production-ready DI Container for {{ app_name }}.
Features: async-first, scopes, circular dependency detection, performance monitoring.
"""

import asyncio
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar, get_type_hints
from contextlib import asynccontextmanager
import inspect
from dataclasses import dataclass, field

T = TypeVar('T')

class LifetimeScope(Enum):
    TRANSIENT = "transient"    # Новый экземпляр каждый раз
    SCOPED = "scoped"         # Один экземпляр на request/session
    SINGLETON = "singleton"    # Один экземпляр на все приложение

@dataclass
class DependencyRegistration:
    interface: Type
    implementation: Type | Callable
    lifetime: LifetimeScope
    factory: Optional[Callable] = None
    dependencies: set[Type] = field(default_factory=set)

class CircularDependencyError(Exception):
    """Исключение для циклических зависимостей."""

    def __init__(self, dependency_chain: list[Type]):
        self.dependency_chain = dependency_chain
        chain_str = " → ".join(dep.__name__ for dep in dependency_chain)
        super().__init__(f"Circular dependency detected: {chain_str}")

class {{ model_name }}DIContainer:
    """
    Production-ready DI Container with async support.

    Features:
    - Async-first design for FastAPI
    - Automatic circular dependency detection
    - Scoped lifetimes (request/session/singleton)
    - Performance monitoring and debugging
    - Automatic cleanup of scoped resources
    """

    def __init__(self):
        self._registrations: Dict[Type, DependencyRegistration] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._resolution_stack: list[Type] = []

    def register(self,
                interface: Type[T],
                implementation: Type[T] | Callable[[], T],
                lifetime: LifetimeScope = LifetimeScope.TRANSIENT) -> '{{ model_name }}DIContainer':
        """Регистрация зависимости."""

        # Автоматическое определение зависимостей через type hints
        if inspect.isclass(implementation):
            dependencies = self._extract_dependencies(implementation)
        else:
            dependencies = set()

        self._registrations[interface] = DependencyRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=lifetime,
            dependencies=dependencies
        )

        return self

    def _extract_dependencies(self, cls: Type) -> set[Type]:
        """Автоматическое извлечение зависимостей из __init__."""
        try:
            signature = inspect.signature(cls.__init__)
            type_hints = get_type_hints(cls.__init__)

            dependencies = set()
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue

                if param_name in type_hints:
                    dependencies.add(type_hints[param_name])

            return dependencies
        except Exception:
            return set()

    async def resolve(self, interface: Type[T], scope_id: str = "default") -> T:
        """
        Async разрешение зависимости с поддержкой скоупов.

        Args:
            interface: Интерфейс для разрешения
            scope_id: ID скоупа (например, request_id)
        """

        # Проверка циклических зависимостей
        if interface in self._resolution_stack:
            self._resolution_stack.append(interface)
            raise CircularDependencyError(self._resolution_stack.copy())

        self._resolution_stack.append(interface)

        try:
            registration = self._registrations.get(interface)
            if not registration:
                raise ValueError(f"No registration found for {interface}")

            # Разрешение в зависимости от lifetime
            if registration.lifetime == LifetimeScope.SINGLETON:
                return await self._resolve_singleton(registration)
            elif registration.lifetime == LifetimeScope.SCOPED:
                return await self._resolve_scoped(registration, scope_id)
            else:  # TRANSIENT
                return await self._resolve_transient(registration, scope_id)

        finally:
            self._resolution_stack.pop()

    async def _resolve_singleton(self, registration: DependencyRegistration) -> Any:
        """Разрешение singleton зависимости."""
        if registration.interface not in self._singletons:
            instance = await self._create_instance(registration, "singleton")
            self._singletons[registration.interface] = instance

        return self._singletons[registration.interface]

    async def _resolve_scoped(self, registration: DependencyRegistration, scope_id: str) -> Any:
        """Разрешение scoped зависимости."""
        if scope_id not in self._scoped_instances:
            self._scoped_instances[scope_id] = {}

        scope_dict = self._scoped_instances[scope_id]

        if registration.interface not in scope_dict:
            instance = await self._create_instance(registration, scope_id)
            scope_dict[registration.interface] = instance

        return scope_dict[registration.interface]

    async def _resolve_transient(self, registration: DependencyRegistration, scope_id: str) -> Any:
        """Разрешение transient зависимости."""
        return await self._create_instance(registration, scope_id)

    async def _create_instance(self, registration: DependencyRegistration, scope_id: str) -> Any:
        """Создание экземпляра с разрешением зависимостей."""
        implementation = registration.implementation

        if callable(implementation) and not inspect.isclass(implementation):
            # Factory function
            if asyncio.iscoroutinefunction(implementation):
                return await implementation()
            else:
                return implementation()

        # Class с автоматическим разрешением зависимостей
        resolved_deps = {}
        for dep_type in registration.dependencies:
            resolved_deps[self._get_param_name(implementation, dep_type)] = \
                await self.resolve(dep_type, scope_id)

        if asyncio.iscoroutinefunction(implementation.__init__):
            return await implementation(**resolved_deps)
        else:
            return implementation(**resolved_deps)

    def _get_param_name(self, cls: Type, dep_type: Type) -> str:
        """Получение имени параметра по типу."""
        signature = inspect.signature(cls.__init__)
        type_hints = get_type_hints(cls.__init__)

        for param_name, param_type in type_hints.items():
            if param_name != 'self' and param_type == dep_type:
                return param_name

        # Fallback to parameter name
        for param_name, param in signature.parameters.items():
            if param_name != 'self' and param.annotation == dep_type:
                return param_name

        raise ValueError(f"Cannot find parameter name for {dep_type} in {cls}")

    @asynccontextmanager
    async def scope(self, scope_id: str):
        """
        Контекстный менеджер для управления scoped зависимостями.

        Usage:
            async with container.scope("request_123"):
                service = await container.resolve(MyService)
                await service.do_something()
            # Автоматическая очистка scoped экземпляров
        """
        try:
            yield
        finally:
            await self._cleanup_scope(scope_id)

    async def _cleanup_scope(self, scope_id: str):
        """Очистка scoped экземпляров с вызовом cleanup методов."""
        if scope_id not in self._scoped_instances:
            return

        scope_dict = self._scoped_instances[scope_id]

        # Вызов cleanup методов в обратном порядке создания
        for instance in reversed(list(scope_dict.values())):
            if hasattr(instance, '__acleanup__'):
                await instance.__acleanup__()
            elif hasattr(instance, '__cleanup__'):
                instance.__cleanup__()

        # Удаление скоупа
        del self._scoped_instances[scope_id]

# Автогенерированная настройка DI для {{ app_name }}
def setup_{{ app_name }}_di() -> {{ model_name }}DIContainer:
    """Автоматическая настройка DI контейнера для {{ app_name }}."""
    container = {{ model_name }}DIContainer()

    # Автоматическая регистрация компонентов
    {% if level in ["BasicCRUD", "Advanced", "Enterprise"] %}
    container.register({{ model_name }}Repository, {{ model_name }}Repository, LifetimeScope.SCOPED)
    container.register({{ model_name }}Service, {{ model_name }}Service, LifetimeScope.SCOPED)
    {% endif %}

    {% if level in ["Enterprise"] %}
    container.register({{ model_name }}UnitOfWork, {{ model_name }}UnitOfWork, LifetimeScope.SCOPED)
    container.register(CacheManager, RedisCache, LifetimeScope.SINGLETON)
    {% endif %}

    return container

# Интеграция с FastAPI
async def get_{{ app_name }}_container() -> {{ model_name }}DIContainer:
    """FastAPI dependency для DI контейнера."""
    return setup_{{ app_name }}_di()

async def get_{{ app_name }}_scope_id() -> str:
    """Генерация уникального ID скоупа для request."""
    import uuid
    return f"request_{uuid.uuid4().hex[:8]}"
```

**Использование в FastAPI:**
```python
# Автогенерированные dependencies для FastAPI
async def get_{{ model_name }}_service(
    container: {{ model_name }}DIContainer = Depends(get_{{ app_name }}_container),
    scope_id: str = Depends(get_{{ app_name }}_scope_id)
) -> {{ model_name }}Service:
    """Автоматическое разрешение сервиса через DI."""
    async with container.scope(scope_id):
        return await container.resolve({{ model_name }}Service, scope_id)

@router.get("/{{ api_prefix }}/")
async def list_{{ app_name }}(
    service: {{ model_name }}Service = Depends(get_{{ model_name }}_service)
):
    """Эндпоинт с автоматической инъекцией зависимостей."""
    return await service.list()
```

---

## 🎯 Примеры использования

### Создание простого приложения (CLI режим)

```bash
# Способ 1: Пошаговый
autogen startapp products
# Редактируем модель и app_config.toml (level = "BasicCRUD")
autogen initapp products

# Способ 2: Быстрый с опциями
autogen initapp products --level BasicCRUD --dry-run
autogen initapp products --level BasicCRUD

# Результат:
# - src/apps/products/ - полная структура приложения
# - tests/apps/products/ - 7 файлов тестов + фабрики + E2E
# - Alembic миграция автоматически создана
```

### Создание продвинутого приложения (интерактивный режим)

```bash
# Интерактивный режим с wizard
autogen --interactive

# Wizard проведет через:
# 1. Имя: articles
# 2. Уровень: Advanced
# 3. Поля модели: title, content, published_at
# 4. API настройки: /articles, tags=["Articles"]
# 5. Функции: search, filters, pagination
# 6. Тесты: покрытие 85%

# Результат:
# - src/apps/articles/ - приложение с расширенными возможностями
# - tests/apps/articles/ - полный набор тестов включая поиск/фильтрацию
# - Красивые исключения с rich traceback
```

### Создание корпоративного приложения (с override шаблонов)

```bash
# Кастомные шаблоны Enterprise уровня
autogen initapp customers --level Enterprise --template-dir ./custom-templates/

# Или с полной кастомизацией
autogen startapp customers
# Редактируем app_config.toml:
# level = "Enterprise"
# enable_caching = true
# enable_events = true
# enable_monitoring = true

autogen initapp customers --overwrite

# Результат:
# - src/apps/customers/ - корпоративное приложение
# - Unit of Work + DI контейнер
# - tests/apps/customers/ - тесты UoW, кэширования, событий
# - Rich исключения с typing.Protocol
# - Автоматические Alembic миграции
```

---

## 🔍 Дополнительные функции

### 1. Валидация

- Проверка существования модели
- Валидация названий (snake_case)
- Проверка конфликтов имен

### 2. Интеграция

- Автоматическая регистрация routes
- Создание миграций
- Обновление зависимостей

### 3. Шаблонизация

- Jinja2 шаблоны для гибкой генерации
- Настраиваемые параметры
- Переиспользуемые компоненты

---

## 📊 Таблица сравнения уровней

| Функция              | BasicCRUD | Advanced | Enterprise |
| -------------------- | --------- | -------- | ---------- |
| **CRUD & Data**      |           |          |            |
| CRUD операции        | ✅        | ✅       | ✅         |
| Простые фильтры      | ✅        | ✅       | ✅         |
| Расширенные фильтры  | ❌        | ✅       | ✅         |
| Полнотекстовый поиск | ❌        | ✅       | ✅         |
| Агрегации            | ❌        | ✅       | ✅         |
| Курсорная пагинация  | ❌        | ✅       | ✅         |
| **Enterprise Features** |        |          |            |
| Кэширование          | ❌        | ❌       | ✅         |
| Bulk операции        | ❌        | ❌       | ✅         |
| События              | ❌        | ❌       | ✅         |
| Мониторинг           | ❌        | ❌       | ✅         |
| **Unit of Work**     | ❌        | ❌       | ✅         |
| **Architecture**     |           |          |            |
| **Dependency Injection** | FastAPI Depends | Auto-register | DI Container + UoW |
| **Rich Exceptions**  | ✅        | ✅       | ✅         |
| **typing.Protocol**  | ❌        | ✅       | ✅         |
| Исключения           | 5         | 10       | 15         |
| Интерфейсы           | ❌        | ✅       | ✅         |
| **Testing**          |           |          |            |
| Тесты                | 7 файлов  | 9 файлов | 11 файлов  |
| Фабрики тестов       | ✅        | ✅       | ✅         |
| E2E тесты            | ✅        | ✅       | ✅         |
| Фикстуры             | ✅        | ✅       | ✅         |
| **Tooling**          |           |          |            |
| **Alembic миграции** | ✅ Авто   | ✅ Авто  | ✅ Авто    |
| **CLI (typer)**      | ✅        | ✅       | ✅         |
| **Dry-run режим**    | ✅        | ✅       | ✅         |
| **Interactive режим** | ✅        | ✅       | ✅         |
| **Custom templates** | ✅        | ✅       | ✅         |

---

## 🎯 Итоговые изменения плана

### ✅ Профессиональный CLI с typer
- **autogen** как отдельный CLI-пакет с rich UI и интерактивным режимом
- **Структурированные команды**: `autogen startapp`, `autogen initapp`, `autogen --interactive`
- **Гибкие опции**: `--dry-run`, `--overwrite`, `--level`, `--template-dir`
- **Jinja2 шаблоны** с наследованием и возможностью override

### ✅ Умная система миграций
- **Автоматические Alembic миграции** при `autogen initapp`
- **Четкое разделение ответственности**: Alembic для схемы, ручные для данных
- **Интеграция с pyproject.toml** для метаданных приложений

### ✅ Rich система исключений
- **typing.Protocol** для строгой типизации интерфейсов исключений
- **Rich traceback** с beautiful terminal output и контекстом
- **Детальный контекст**: SQL запросы, entity_id, фильтры, security context
- **Уникальные коды ошибок** для каждого типа исключения

### ✅ Умный DI по уровням сложности
- **BasicCRUD**: простой FastAPI Depends без магии
- **Advanced**: автоматическая регистрация через декораторы
- **Enterprise**: полный DI контейнер + Unit of Work паттерн
- **Тестируемость**: легкое мокирование на всех уровнях

### ✅ Продакшен-готовая система шаблонов
- **Версионирование шаблонов**: каждая версия autogen имеет совместимые шаблоны
- **Безопасные изменения**: merge стратегии для защиты пользовательских правок
- **Валидация кастомных шаблонов**: строгое API для override без поломок
- **Автоматическая интеграция**: протоколы исключений + логирование + мониторинг

### ✅ Профессиональный CLI пакет autogen
- **Typer-based CLI** с интерактивным режимом и rich UI
- **Гибкие шаблоны** с возможностью override в autogen/templates/custom/
- **Dry-run режим** для предварительного просмотра изменений
- **Автоматические миграции** через Alembic integration
- **Умный DI** от базового FastAPI Depends до Enterprise UoW+DI

### ✅ Установка и настройка

**pyproject.toml обновления:**
```toml
[project.scripts]
autogen = "autogen.cli.main:app"

[dependency-groups]
dev = [
    # ... existing deps ...
    "typer[all]>=0.12.0",  # CLI framework
    "rich>=13.0.0",        # Beautiful terminal output
    "jinja2>=3.1.0",       # Template engine
]

# Метаданные autogen приложений
[autogen]
# Будет заполняться автоматически при создании приложений
# products = { level = "BasicCRUD", api_prefix = "/products", ... }
# articles = { level = "Advanced", api_prefix = "/articles", ... }
```

**Установка в dev режиме:**
```bash
pip install -e .  # Установка в editable режиме
autogen --help     # Проверка работы CLI
```

## 🎯 Критические улучшения для продакшена

### ✅ **Версионирование и миграции решены**
```bash
autogen check products                    # Проверка совместимости
autogen migrate products --to v2.0        # Безопасная миграция
# Метаданные в pyproject.toml отслеживают версии шаблонов
```

### ✅ **Защита пользовательских правок**
```bash
autogen initapp products --overwrite --strategy safe --backup
# Автоматическое слияние + конфликты для ручного разрешения
# autogen:skip-start/end блоки для защиты кода
```

### ✅ **Bulletproof кастомные шаблоны**
```bash
autogen validate-template ./my-templates/  # Строгая валидация
# Проверка файлов, переменных, Jinja2 синтаксиса
# Четкое API с REQUIRED_FILES_BY_LEVEL
```

### ✅ **Автоматическая интеграция исключений**
- **Логирование**: автоматический structlog с контекстом
- **Мониторинг**: Prometheus метрики + Sentry/DataDog
- **Middleware**: автогенерированный перехват исключений
- **Rich traceback**: красивые ошибки из коробки

### ✅ **Production-ready DI контейнер**
- **Async-first**: полная поддержка FastAPI async
- **Циклические зависимости**: автоматическое обнаружение с четкими ошибками
- **Скоупы**: TRANSIENT/SCOPED/SINGLETON с автоочисткой
- **Performance**: контекстные менеджеры для ресурсов

## 🚀 **Теперь это enterprise-grade система!**

**Ключевые отличия от типичных генераторов:**
- 🛡️ **Безопасность**: версионирование + merge стратегии защищают продакшн
- 🔧 **Надежность**: валидация кастомных шаблонов предотвращает поломки
- 📊 **Наблюдаемость**: автоматическая интеграция с мониторингом/логированием
- ⚡ **Производительность**: async-first DI с правильным lifecycle management
- 🎯 **Практичность**: 95% функций работают автоматически, без ручной реализации

Начинаем реализацию? CLI пакет `autogen/` с typer → шаблоны → core логика?
````
