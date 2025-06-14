# Автоматическое создание базы данных

## Обзор

Система автоматического создания базы данных обеспечивает бесшовную работу с проектом, автоматически создавая БД если она не существует. Это особенно полезно для:

- Первоначальной настройки проекта
- CI/CD процессов
- Разработки и тестирования
- Развертывания в новых средах

## Компоненты

### DatabaseManager

Основной класс для управления базой данных:

```python
from core.migrations import DatabaseManager

db_manager = DatabaseManager()

# Проверка/создание БД
await db_manager.ensure_database_exists()

# Получение информации о БД
info = await db_manager.get_database_info()
```

### Поддерживаемые СУБД

#### PostgreSQL

- Автоматическое создание БД через подключение к `postgres`
- Проверка существования через `pg_database`
- Получение размера и количества таблиц

#### SQLite

- Создание файла БД при первом подключении
- Проверка существования файла
- Поддержка in-memory БД (`:memory:`)

## CLI команды

### Информация о БД

```bash
# Через CLI
python scripts/migration_cli.py db-info

# Через Make
make db-info
```

### Создание БД

```bash
# Интерактивное создание
python scripts/migration_cli.py db-create

# Принудительное создание
python scripts/migration_cli.py db-create --force

# Через Make
make db-create
```

### Проверка/создание БД

```bash
# Автоматическая проверка и создание при необходимости
python scripts/migration_cli.py db-ensure

# Через Make
make db-ensure
```

### Тестирование подключения

```bash
# Тест подключения к БД
python scripts/migration_cli.py db-test

# Через Make
make db-test
```

### Удаление БД

```bash
# Интерактивное удаление (с подтверждениями)
python scripts/migration_cli.py db-drop

# Принудительное удаление
python scripts/migration_cli.py db-drop --force

# Через Make
make db-drop
```

## Интеграция с миграциями

### Автоматическое создание в safe-migrate

Команда `safe-migrate` теперь автоматически проверяет и создает БД:

```bash
# Безопасная миграция с автосозданием БД
python scripts/migration_cli.py safe-migrate

# Через Make
make migrate-safe
```

### Последовательность операций

1. **Проверка существования БД** - `database_exists()`
2. **Создание БД при необходимости** - `create_database()`
3. **Тестирование подключения** - `test_connection()`
4. **Валидация миграций** - `MigrationValidator`
5. **Создание бэкапа** - `MigrationBackup` (опционально)
6. **Применение миграций** - `alembic upgrade`

## Примеры использования

### Программное использование

```python
from core.migrations import DatabaseManager

async def setup_database():
    """Настройка базы данных для приложения."""
    db_manager = DatabaseManager()

    # Автоматическая проверка/создание
    if await db_manager.ensure_database_exists():
        print("✅ База данных готова")

        # Получаем информацию
        info = await db_manager.get_database_info()
        print(f"Тип БД: {info['database_type']}")
        print(f"Размер: {info['size']}")
        print(f"Таблиц: {info['tables_count']}")
    else:
        print("❌ Проблемы с базой данных")
```

### Использование с разными БД

```python
# PostgreSQL
db_url = "postgresql+asyncpg://user:pass@localhost/myapp"
await db_manager.ensure_database_exists(db_url)

# SQLite
db_url = "sqlite+aiosqlite:///./data/app.db"
await db_manager.ensure_database_exists(db_url)

# In-memory SQLite (для тестов)
db_url = "sqlite+aiosqlite:///:memory:"
await db_manager.ensure_database_exists(db_url)
```

### CI/CD интеграция

```yaml
# GitHub Actions пример
- name: Setup Database
  run: |
    export SQLALCHEMY_DATABASE_URI="postgresql://postgres:postgres@localhost/test_db"
    make db-ensure
    make migrate-safe
```

## Конфигурация

### Переменные окружения

```bash
# Основная строка подключения
SQLALCHEMY_DATABASE_URI="postgresql+asyncpg://user:pass@host:port/dbname"

# Для SQLite
SQLALCHEMY_DATABASE_URI="sqlite+aiosqlite:///path/to/database.db"
```

### Настройки в core/config.py

```python
class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URI: str = "sqlite+aiosqlite:///./app.db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    # ... другие настройки
```

## Безопасность

### Подтверждения для критических операций

- **Удаление БД**: Двойное подтверждение
- **Создание БД**: Подтверждение (можно отключить через `--force`)
- **Восстановление из бэкапа**: Предупреждение о потере данных

### Логирование

Все операции логируются с соответствующими уровнями:

```python
logger.info("✅ База данных успешно создана")
logger.warning("🗑️ Удаление базы данных: myapp")
logger.error("❌ Ошибка подключения к БД")
```

## Обработка ошибок

### Типы исключений

```python
from core.migrations import MigrationError

try:
    await db_manager.create_database(db_url)
except MigrationError as e:
    print(f"Ошибка создания БД: {e}")
```

### Автоматическое восстановление

При ошибках система пытается:

1. Переподключиться к БД
2. Создать БД если она не существует
3. Предложить восстановление из бэкапа

## Мониторинг

### Информация о БД

```bash
# Детальная информация
make db-info

# Вывод:
# ┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
# ┃ Параметр          ┃ Значение            ┃
# ┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
# │ Имя БД            │ myapp               │
# │ Тип БД            │ postgresql          │
# │ Существует        │ ✅ Да               │
# │ Подключение       │ ✅ OK               │
# │ Размер            │ 15.2 MB             │
# │ Количество таблиц │ 8                   │
# └───────────────────┴─────────────────────┘
```

### Интеграция с мониторингом миграций

```bash
# Комплексный мониторинг
make migrate-monitor

# Показывает:
# - Статус БД
# - Текущую версию миграций
# - Ожидающие миграции
# - Последние изменения
```

## Лучшие практики

### Разработка

1. **Используйте `db-ensure`** перед началом работы
2. **Проверяйте подключение** через `db-test`
3. **Создавайте бэкапы** перед критическими изменениями

### Продакшен

1. **Всегда используйте `safe-migrate`** вместо прямых команд alembic
2. **Настройте автоматические бэкапы**
3. **Мониторьте размер и производительность БД**

### CI/CD

1. **Автоматизируйте создание тестовых БД**
2. **Используйте изолированные БД для каждого теста**
3. **Очищайте временные БД после тестов**

## Устранение неполадок

### Частые проблемы

#### PostgreSQL не запущен

```bash
# Проверка статуса
brew services list | grep postgresql

# Запуск
brew services start postgresql
```

#### Права доступа к SQLite

```bash
# Проверка прав на директорию
ls -la $(dirname $SQLALCHEMY_DATABASE_URI)

# Создание директории
mkdir -p $(dirname $SQLALCHEMY_DATABASE_URI)
```

#### Проблемы с подключением

```bash
# Тест подключения
make db-test

# Детальная диагностика
python scripts/migration_cli.py db-info
```

### Отладка

Включите подробное логирование:

```bash
export DB_ECHO=true
export LOG_LEVEL=DEBUG
make db-ensure
```

## Заключение

Система автоматического создания БД значительно упрощает работу с проектом, обеспечивая:

- **Простоту настройки** - одна команда для готовой БД
- **Надежность** - автоматические проверки и восстановление
- **Гибкость** - поддержка PostgreSQL и SQLite
- **Безопасность** - подтверждения и бэкапы
- **Мониторинг** - детальная информация о состоянии

Используйте `make db-ensure` для быстрой настройки и `make migrate-safe` для безопасного применения миграций.
