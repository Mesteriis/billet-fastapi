# Миграция конфигурации Alembic в pyproject.toml

## ✅ Выполненные изменения

### 1. **Перенос конфигурации**

- Удален файл `alembic.ini`
- Конфигурация Alembic перенесена в секцию `[tool.alembic]` в `pyproject.toml`
- Обновлен `migrations/env.py` для чтения конфигурации из `pyproject.toml`

### 2. **Новая секция в pyproject.toml**

```toml
[tool.alembic]
# Путь к скриптам миграций
script_location = "migrations"
# Шаблон для имен файлов миграций
file_template = "%%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s"
# Путь для добавления в sys.path
prepend_sys_path = "src"
# Разделитель путей версий
version_path_separator = "os"
# Кодировка для файлов ревизий
output_encoding = "utf-8"
# Максимальная длина slug
truncate_slug_length = 40
```

### 3. **Обновленный migrations/env.py**

- Добавлен импорт `tomllib` для чтения TOML файлов
- Создана функция `load_alembic_config()` для загрузки конфигурации из `pyproject.toml`
- Упрощена настройка логирования (без отдельного файла конфигурации)
- Сохранена вся функциональность для асинхронных миграций

### 4. **Добавлены команды в Makefile**

```bash
make migrate-create MSG="описание"  # Создание новой миграции
make migrate-up                     # Применение миграций
make migrate-down                   # Откат последней миграции
make migrate-status                 # Статус миграций
make migrate-reset                  # Сброс всех миграций (осторожно!)
```

## 🎯 Преимущества централизации

### ✅ **Единое место конфигурации**

- Все настройки проекта в `pyproject.toml`
- Меньше файлов конфигурации
- Соответствие современным стандартам Python

### ✅ **Упрощенная поддержка**

- Легче переносить конфигурацию между проектами
- Единый формат для всех инструментов
- Версионирование конфигурации вместе с кодом

### ✅ **Гибкость настройки**

- Возможность программного изменения конфигурации
- Интеграция с другими инструментами через `pyproject.toml`
- Поддержка переменных окружения

## 🔧 Использование

### Стандартные команды Alembic работают как обычно:

```bash
# Через uv (рекомендуется)
uv run alembic revision --autogenerate -m "Add user table"
uv run alembic upgrade head
uv run alembic current
uv run alembic history

# Или через make (удобнее)
make migrate-create MSG="Add user table"
make migrate-up
make migrate-status
```

### Переменные окружения для БД:

```bash
# В .env файле или переменных окружения
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://user:password@localhost/dbname
```

## 📋 Структура файлов после миграции

```
project/
├── pyproject.toml          # ✅ Содержит [tool.alembic]
├── migrations/
│   ├── env.py             # ✅ Обновлен для чтения pyproject.toml
│   ├── script.py.mako
│   └── versions/
│       └── *.py
└── src/
    └── apps/
        └── */models.py    # Модели для автогенерации
```

## 🚨 Важные моменты

### 1. **Совместимость**

- Все существующие миграции остаются рабочими
- Команды Alembic не изменились
- Поддержка асинхронных миграций сохранена

### 2. **Логирование**

- Упрощенная настройка логирования в `env.py`
- Можно настроить через стандартный Python logging
- Убрана зависимость от отдельного файла конфигурации

### 3. **URL базы данных**

- Читается из переменных окружения через `core.config.get_settings()`
- Не хранится в `pyproject.toml` по соображениям безопасности
- Поддержка разных окружений (dev/test/prod)

## 🔄 Откат изменений (если нужно)

Если потребуется вернуться к `alembic.ini`:

1. Создать новый `alembic.ini` с нужной конфигурацией
2. Откатить изменения в `migrations/env.py`
3. Удалить секцию `[tool.alembic]` из `pyproject.toml`

## 🧪 Тестирование

```bash
# Проверка текущего состояния
make migrate-status

# Создание тестовой миграции
make migrate-create MSG="Test migration"

# Применение миграции
make migrate-up

# Откат миграции
make migrate-down
```

## 🚀 Дальнейшие улучшения

1. **CI/CD интеграция** - автоматическое применение миграций
2. **Валидация схемы** - проверка миграций перед применением
3. **Бэкапы** - автоматическое создание бэкапов перед миграциями
4. **Мониторинг** - отслеживание состояния миграций

Теперь конфигурация Alembic полностью интегрирована в `pyproject.toml`! 🎉
