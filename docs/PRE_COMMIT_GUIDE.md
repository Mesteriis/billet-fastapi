# 🔗 Руководство по Pre-commit

Это руководство описывает настройку и использование pre-commit хуков в проекте.

## 📋 Обзор

Pre-commit автоматически запускает проверки кода перед каждым коммитом, обеспечивая:

- ✅ Качество кода
- 🔒 Безопасность
- 📏 Единообразное форматирование
- 🧪 Базовую валидацию

## 🚀 Быстрый старт

```bash
# Установка и настройка
make setup-dev

# Или пошагово:
make dev
make pre-commit-install
```

## 🔧 Установленные хуки

### 1. **Базовые проверки** (pre-commit-hooks)

- `trailing-whitespace` - удаляет пробелы в конце строк
- `end-of-file-fixer` - добавляет пустую строку в конец файла
- `check-yaml` - валидация YAML файлов
- `check-toml` - валидация TOML файлов
- `check-json` - валидация JSON файлов
- `check-added-large-files` - предотвращает коммит больших файлов (>1MB)
- `check-ast` - валидация Python синтаксиса
- `check-merge-conflict` - обнаружение конфликтов слияния
- `detect-private-key` - поиск приватных ключей
- `mixed-line-ending` - нормализация окончаний строк

### 2. **Ruff** - современный линтер и форматтер

```bash
# Что проверяет:
- pycodestyle (E, W)
- pyflakes (F)
- isort (I)
- flake8-bugbear (B)
- flake8-comprehensions (C4)
- pyupgrade (UP)
- pep8-naming (N)
- bandit security (S)
- pytest-style (PT)
- type-checking (TCH)
```

### 3. **MyPy** - проверка типов

- Статическая проверка типов
- Игнорирует `tests/` и `migrations/`
- Дополнительные типы для SQLAlchemy, Redis, requests

### 4. **Bandit** - безопасность кода

- Поиск уязвимостей безопасности
- Исключает тесты из проверки
- Конфигурируется через `pyproject.toml`

### 5. **Safety** - безопасность зависимостей

- Проверка известных уязвимостей в пакетах
- Интеграция с базой данных PyUp.io

### 6. **SQLFluff** - линтер SQL

- Проверка SQL миграций
- Форматирование и стилистика SQL

### 7. **Prettier** - форматирование файлов

- JavaScript, TypeScript, JSON, CSS, YAML, Markdown
- Исключает `docs/` и `htmlcov/`

### 8. **Локальные хуки проекта**

#### `pytest-fast` - Быстрые тесты

```bash
# Запускает тесты без маркера "slow"
uv run pytest -m "not slow" --maxfail=1 -q
```

#### `pytest-cov-changed` - Покрытие измененных файлов

```bash
# Проверяет покрытие только для измененных Python файлов
# Требует минимум 80% покрытия
```

#### `check-project-structure` - Структура проекта

```bash
# Проверяет наличие обязательных директорий и файлов
python scripts/check_structure.py
```

#### `check-todos` - TODO/FIXME комментарии

```bash
# Предупреждает о наличии TODO/FIXME в коммитах
# Можно отключить для черновых коммитов
```

#### `validate-openapi` - Валидация API схемы

```bash
# Проверяет, что FastAPI приложение генерирует корректную OpenAPI схему
```

## 📝 Использование

### Автоматический запуск

```bash
git add .
git commit -m "Мой коммит"
# Pre-commit автоматически запустится и проверит изменения
```

### Ручной запуск

```bash
# На всех файлах
make pre-commit-run

# Только на staged файлах
make pre-commit-run-staged

# Ручные проверки без pre-commit
make pre-commit-manual
```

### Пропуск хуков

```bash
# Пропустить все хуки (НЕ РЕКОМЕНДУЕТСЯ)
git commit --no-verify -m "Экстренный коммит"

# Пропустить конкретный хук
SKIP=mypy git commit -m "Коммит без проверки типов"

# Пропустить несколько хуков
SKIP=mypy,bandit git commit -m "Коммит без mypy и bandit"
```

## 🛠️ Управление

### Обновление версий

```bash
# Автоматическое обновление всех репозиториев
make pre-commit-update

# Или вручную:
uv run pre-commit autoupdate
```

### Очистка кэша

```bash
# При проблемах с кэшем
make pre-commit-clean
```

### Удаление хуков

```bash
# Удалить pre-commit хуки
uv run pre-commit uninstall
```

## ⚙️ Конфигурация

### Файлы конфигурации:

#### `.pre-commit-config.yaml`

```yaml
# Основная конфигурация pre-commit
# Версии репозиториев, аргументы хуков
```

#### `pyproject.toml`

```toml
[tool.ruff]           # Настройки Ruff
[tool.bandit]         # Настройки Bandit
[tool.mypy]           # Настройки MyPy
```

### Настройка под проект

#### Добавить новый хук:

```yaml
# В .pre-commit-config.yaml
- repo: local
  hooks:
    - id: my-custom-hook
      name: My custom check
      entry: python scripts/my_check.py
      language: system
      pass_filenames: false
```

#### Исключить файлы:

```yaml
- id: mypy
  exclude: ^(tests/|migrations/|scripts/)
```

#### Изменить аргументы:

```yaml
- id: ruff
  args: ["--fix", "--exit-non-zero-on-fix", "--show-fixes"]
```

## 🚨 Решение проблем

### Типичные ошибки и решения:

#### 1. **Ruff ошибки форматирования**

```bash
# Автоматическое исправление:
uv run ruff check src/ --fix
uv run ruff format src/

# Или через make:
make format
```

#### 2. **MyPy ошибки типов**

```bash
# Игнорировать конкретную ошибку:
# type: ignore[error-code]

# Пример:
result = some_function()  # type: ignore[return-value]
```

#### 3. **Bandit ложные срабатывания**

```bash
# В коде:
# nosec: B101
assert user.is_authenticated()

# В pyproject.toml:
[tool.bandit]
skips = ["B101", "B404"]
```

#### 4. **Safety уязвимости**

```bash
# Временно игнорировать:
uv run safety check --ignore=70612

# В pre-commit:
args: ["--ignore=70612,51668"]
```

#### 5. **Медленные хуки**

```bash
# Пропустить медленные хуки для быстрых коммитов:
SKIP=mypy,safety git commit -m "Быстрый фикс"

# Или отключить конкретные хуки:
# В .pre-commit-config.yaml добавить:
# exclude: ^(tests/performance/|docs/)
```

### Отладка

#### Подробный вывод:

```bash
uv run pre-commit run --all-files --verbose
```

#### Логи:

```bash
# Логи pre-commit:
cat ~/.cache/pre-commit/pre-commit.log

# Проверка конфигурации:
uv run pre-commit validate-config
```

## 🎯 Рекомендации

### ✅ Хорошие практики:

1. **Коммитьте часто** - маленькие изменения проще проверить
2. **Исправляйте ошибки сразу** - не накапливайте технический долг
3. **Читайте сообщения об ошибках** - они часто содержат полезные советы
4. **Используйте `--fix` флаги** - многие проблемы исправляются автоматически
5. **Обновляйте версии** - новые версии содержат улучшения и исправления

### ❌ Чего избегать:

1. **Не используйте `--no-verify`** без крайней необходимости
2. **Не игнорируйте все ошибки** типов - исправляйте по мере возможности
3. **Не коммитьте DEBUG код** - используйте условные отладочные принты
4. **Не пропускайте тесты** перед коммитом важных изменений

## 🔄 CI/CD интеграция

### Pre-commit.ci

Настроена автоматическая проверка в CI через [pre-commit.ci](https://pre-commit.ci/):

- ✅ Автоматические исправления в PR
- 📅 Еженедельные обновления версий
- ⚡ Быстрая обратная связь

### GitHub Actions

```yaml
# .github/workflows/pre-commit.yml
- name: Run pre-commit
  uses: pre-commit/action@v3.0.0
```

## 📊 Метрики качества

После настройки pre-commit отслеживайте:

- 📉 Количество найденных ошибок (должно уменьшаться)
- ⏱️ Время выполнения хуков (оптимизируйте медленные)
- 🎯 Покрытие кода (стремитесь к >80%)
- 🔒 Безопасность (0 критических уязвимостей)

## 🆘 Поддержка

При проблемах с pre-commit:

1. Проверьте [документацию pre-commit](https://pre-commit.com/)
2. Изучите конфигурацию в `pyproject.toml`
3. Запустите диагностику: `make code-quality`
4. Обратитесь к команде разработки

---

**💡 Совет:** Pre-commit - это инвестиция в качество кода. Потратьте время на настройку один раз, и она будет экономить ваше время каждый день!
