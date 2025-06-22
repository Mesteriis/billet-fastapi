# Autogen CLI - Руководство пользователя

## 🚀 Обзор

Autogen - это enterprise-grade генератор FastAPI приложений с поддержкой трех уровней сложности. CLI предоставляет удобные команды для создания приложений от простых CRUD до сложных корпоративных систем.

## 📦 Установка и настройка

Зависимости уже включены в проект через `pyproject.toml`:

```bash
# Установка зависимостей разработки (если нужно)
uv add --dev typer jinja2 tomli-w
```

## 🎯 Основные команды

### Справка и версия

```bash
# Общая справка
python -m autogen --help

# Версия
python -m autogen --version

# Интерактивный режим
python -m autogen --interactive
```

### Создание приложения

```bash
# Создать базовую структуру
python -m autogen startapp products

# С перезаписью существующего
python -m autogen startapp products --force
```

### Генерация компонентов

```bash
# Сгенерировать все компоненты
python -m autogen initapp products

# Предварительный просмотр
python -m autogen initapp products --dry-run

# С конкретным уровнем
python -m autogen initapp products --level Enterprise

# С перезаписью файлов
python -m autogen initapp products --overwrite

# С резервным копированием
python -m autogen initapp products --backup

# Кастомные шаблоны
python -m autogen initapp products --template-dir /path/to/templates

# Стратегия слияния
python -m autogen initapp products --strategy regenerate
```

## 🏗️ Workflow создания приложения

### 1. Создание базовой структуры

```bash
python -m autogen startapp products
```

**Создается:**

- `src/apps/products/` - основная директория
- `models/products_models.py` - заготовка модели
- `app_config.toml` - конфигурация приложения
- `README.md` - инструкции по настройке
- `__init__.py` файлы

### 2. Настройка модели

Отредактируйте `src/apps/products/models/products_models.py`:

```python
class Product(BaseModel):
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
```

### 3. Конфигурация уровня

Отредактируйте `app_config.toml`:

```toml
[app]
level = "Advanced"  # или "BasicCRUD", "Enterprise"
name = "Product"
description = "Product management application"

[features]
enable_caching = false     # только для Enterprise
enable_events = false      # только для Enterprise
enable_monitoring = false  # только для Enterprise
```

### 4. Генерация компонентов

```bash
# Предварительный просмотр
python -m autogen initapp products --dry-run

# Генерация
python -m autogen initapp products
```

## 📊 Уровни приложений

### BasicCRUD

- ✅ Основные CRUD операции
- ✅ Простые фильтры (eq, ne, lt, gt, etc.)
- ✅ FastAPI Depends DI
- ✅ 5 исключений с rich traceback
- ✅ 7 тестовых файлов

### Advanced

- ✅ Все возможности BasicCRUD
- ✅ 40+ операторов фильтрации
- ✅ Полнотекстовый поиск PostgreSQL
- ✅ Курсорная пагинация
- ✅ Агрегации (SUM, AVG, MAX, MIN, COUNT)
- ✅ typing.Protocol интерфейсы
- ✅ Автоматическая регистрация DI
- ✅ 9 тестовых файлов

### Enterprise

- ✅ Все возможности Advanced
- ✅ Кэширование (Redis/Memory)
- ✅ Bulk операции с батчингом
- ✅ Система событий
- ✅ Unit of Work паттерн
- ✅ Полный DI контейнер
- ✅ Мониторинг и метрики
- ✅ 11 тестовых файлов

## 🎯 Интерактивный режим

```bash
python -m autogen --interactive
```

Интерактивный режим проведет вас через все этапы:

1. **Выбор имени приложения** с валидацией
2. **Выбор уровня** с подробным описанием
3. **Просмотр итогов** перед созданием
4. **Автоматическое создание** с правильными настройками

## 📁 Структура созданного приложения

После выполнения `initapp` создается:

```
src/apps/products/
├── __init__.py
├── models/
│   ├── __init__.py
│   └── products_models.py       # SQLAlchemy модели
├── schemas/
│   ├── __init__.py
│   └── products_schemas.py      # Pydantic схемы
├── repo/
│   ├── __init__.py
│   └── products_repo.py         # Репозиторий (уровень зависит от config)
├── services/
│   ├── __init__.py
│   ├── products_service.py      # Бизнес-логика
│   ├── products_cache_service.py    # Только Enterprise
│   └── products_event_service.py    # Только Enterprise
├── api/
│   ├── __init__.py
│   └── products_routes.py       # FastAPI routes
├── depends/
│   ├── __init__.py
│   ├── repositories.py         # DI для репозиториев
│   └── services.py             # DI для сервисов
├── exceptions.py               # Иерархия исключений (5-15 классов)
├── interfaces.py               # typing.Protocol интерфейсы
├── app_config.toml            # Конфигурация приложения
└── README.md                  # Инструкции
```

## 🧪 Тестовая структура

```
tests/apps/products/
├── conftest.py                 # Фикстуры приложения
├── factories.py               # Factory Boy фабрики
├── test_products_models.py     # Тесты моделей
├── test_products_repo.py       # Тесты репозитория
├── test_products_service.py    # Тесты сервиса
├── test_products_api.py        # Тесты API
├── test_products_advanced.py  # Advanced/Enterprise тесты
├── test_products_integration.py # Интеграционные тесты
├── test_products_cache.py      # Enterprise: тесты кэша
├── test_products_events.py     # Enterprise: тесты событий
└── e2e/
    └── test_products_crud_e2e.py # E2E тесты
```

## ⚙️ Файл конфигурации app_config.toml

```toml
[app]
level = "BasicCRUD"             # Уровень приложения
name = "Product"                # Имя модели (PascalCase)
description = "Product application"

[database]
table_name = "products"         # Имя таблицы в БД
schema = "public"               # Схема БД

[features]
enable_soft_delete = true       # Мягкое удаление
enable_timestamps = true        # created_at, updated_at
enable_pagination = true        # Пагинация
enable_caching = false          # Кэширование (Enterprise)
enable_events = false           # События (Enterprise)
enable_monitoring = false       # Мониторинг (Enterprise)

[exceptions]
enable_rich_traceback = true    # Rich traceback
enable_error_codes = true       # Уникальные коды ошибок
enable_detailed_context = true  # Детальный контекст
log_exceptions = true           # Логирование исключений

[api]
prefix = "/products"            # API префикс
tags = ["Product"]              # OpenAPI теги
include_in_schema = true        # Включить в схему

[testing]
generate_factories = true       # Генерировать фабрики
generate_fixtures = true        # Генерировать фикстуры
test_coverage_target = 80       # Целевое покрытие тестами
```

## 🔧 Дополнительные команды

### Управление приложениями

```bash
# Список созданных приложений
python -m autogen list

# Проверка совместимости
python -m autogen check products

# Миграция на новую версию шаблонов
python -m autogen migrate products --to latest --dry-run
python -m autogen migrate products --to 2.0

# Валидация кастомных шаблонов
python -m autogen validate-template /path/to/templates --level Enterprise
```

## 📋 Валидация имен приложений

Autogen проверяет имена приложений:

✅ **Правильные имена:**

- `products`
- `user_profiles`
- `blog_posts`
- `categories`

❌ **Неправильные имена:**

- `Product` (не PascalCase)
- `user-profiles` (не kebab-case)
- `1products` (начинается с цифры)
- `class` (зарезервированное слово)

## 🎨 Примеры использования

### Создание простого CRUD

```bash
python -m autogen startapp categories
# Отредактировать модель
python -m autogen initapp categories
```

### Создание продвинутого приложения

```bash
python -m autogen startapp articles
# В app_config.toml: level = "Advanced"
python -m autogen initapp articles
```

### Корпоративное приложение с кэшированием

```bash
python -m autogen startapp products
# В app_config.toml: level = "Enterprise", enable_caching = true
python -m autogen initapp products --backup
```

## 🚨 Устранение неполадок

### ModuleNotFoundError

```bash
# Установите зависимости
uv add --dev typer jinja2 tomli-w
```

### Ошибки валидации

- Проверьте имя приложения (lowercase, snake_case, plural)
- Убедитесь что модель существует в models/
- Проверьте синтаксис app_config.toml

### Конфликты при перезаписи

```bash
# Используйте стратегии слияния
python -m autogen initapp products --strategy safe
python -m autogen initapp products --strategy regenerate
python -m autogen initapp products --strategy interactive
```

## 📚 Дальнейшее развитие

Autogen CLI готов к расширению:

1. **Шаблоны** - добавить систему версионирования шаблонов
2. **Валидация** - улучшить проверку кастомных шаблонов
3. **Миграции** - реализовать безопасные миграции
4. **Интеграции** - добавить поддержку других ORM/фреймворков
5. **Плагины** - система расширений для кастомной логики

---

**Autogen CLI** предоставляет мощный инструмент для быстрого создания enterprise-grade FastAPI приложений с идеальной архитектурой!
