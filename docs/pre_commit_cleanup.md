# 🧹 Интеграция очистки проекта с Pre-Commit

## 📋 Обзор

Проект интегрирован с [pre-commit](https://pre-commit.com/) для автоматической очистки временных файлов и артефактов перед коммитами. Это помогает поддерживать репозиторий в чистом состоянии и избегать коммитов ненужных файлов.

## 🎯 Режимы работы

### 1. Dry-Run (по умолчанию)

Запускается автоматически при каждом коммите, показывает что будет удалено без фактического удаления:

```bash
git commit -m "fix: важное исправление"
# Автоматически запустится preview очистки
```

### 2. Полная очистка

Активируется через переменную окружения для фактического удаления файлов:

```bash
# Через переменную окружения
PRECOMMIT_CLEANUP=full git commit -m "feat: новая функция"

# Или отдельно
make pre-commit-cleanup-full
```

### 3. Подробная очистка

Показывает детальную информацию о каждом удаляемом файле:

```bash
# Через переменную окружения
PRECOMMIT_CLEANUP=verbose git commit -m "docs: обновление документации"

# Или отдельно
make pre-commit-cleanup-verbose
```

## ⚙️ Настройка хуков

В `.pre-commit-config.yaml` настроены следующие хуки:

```yaml
# Быстрая очистка в режиме dry-run (по умолчанию)
- id: cleanup-project-dry
  name: Project Cleanup (Dry Run)
  entry: python scripts/cleanup_project.py
  args: ["--dry-run"]
  stages: [pre-commit]

# Полная очистка (PRECOMMIT_CLEANUP=full)
- id: cleanup-project-full
  name: Project Cleanup (Full)
  stages: [manual]

# Подробная очистка (PRECOMMIT_CLEANUP=verbose)
- id: cleanup-project-verbose
  name: Project Cleanup (Verbose)
  stages: [manual]
```

## 🚀 Команды Makefile

Для удобства добавлены специальные команды:

```bash
# Предварительный просмотр очистки через pre-commit
make pre-commit-cleanup-dry

# Полная очистка через pre-commit
make pre-commit-cleanup-full

# Подробная очистка через pre-commit
make pre-commit-cleanup-verbose

# Обычная очистка (не через pre-commit)
make clean
```

## 📊 Что очищается

Хуки используют `scripts/cleanup_project.py` и безопасно удаляют:

### ✅ Удаляется:

- `__pycache__/` - кеш Python
- `.pytest_cache/` - кеш pytest
- `.mypy_cache/` - кеш mypy
- `.ruff_cache/` - кеш Ruff
- `htmlcov/` - отчеты покрытия HTML
- `.coverage*` - файлы покрытия
- `*.pyc, *.pyo` - скомпилированные Python файлы
- `.DS_Store` - файлы macOS
- `*.tmp, *.temp` - временные файлы
- `reports/*.html` - HTML отчеты

### ❌ НЕ удаляется:

- `.venv/`, `venv/` - виртуальные окружения
- `node_modules/` - зависимости Node.js
- `src/`, `tests/` - исходный код
- `.git/` - репозиторий Git
- `migrations/` - миграции БД
- `backups/` - важные бэкапы

## 🔧 Переменные окружения

| Переменная          | Значение       | Описание                               |
| ------------------- | -------------- | -------------------------------------- |
| `PRECOMMIT_CLEANUP` | `full`         | Включает полную очистку при коммите    |
| `PRECOMMIT_CLEANUP` | `verbose`      | Включает подробную очистку при коммите |
| `PRECOMMIT_CLEANUP` | не установлена | Только dry-run режим (по умолчанию)    |

## 📝 Примеры использования

### Обычный workflow (только preview)

```bash
git add .
git commit -m "feat: новая функция"
# Вывод: 🔍 Предварительный просмотр очистки: найдено 5 файлов для удаления
```

### Коммит с полной очисткой

```bash
git add .
PRECOMMIT_CLEANUP=full git commit -m "feat: новая функция"
# Вывод: 🧹 Очистка завершена: удалено 5 файлов, освобождено 2.3 MB
```

### Проверка перед важным коммитом

```bash
# Сначала посмотрим что будет удалено
make pre-commit-cleanup-verbose

# Если всё ОК, делаем полную очистку и коммит
PRECOMMIT_CLEANUP=full git commit -m "release: v1.2.0"
```

### Отключение автоочистки для конкретного коммита

```bash
# Пропустить все хуки очистки
git commit -m "wip: временные изменения" --no-verify
```

## 🎛️ Кастомизация

### Изменение поведения по умолчанию

Если хотите, чтобы полная очистка выполнялась по умолчанию, измените в `.pre-commit-config.yaml`:

```yaml
# Было
stages: [pre-commit]  # для dry-run
stages: [manual]      # для full

# Станет
stages: [manual]      # для dry-run
stages: [pre-commit]  # для full
```

### Добавление собственных правил очистки

1. Отредактируйте `scripts/cleanup_project.py`
2. Добавьте новые паттерны в `directories_to_remove` или `file_patterns_to_remove`
3. Протестируйте с `--dry-run`

## 🚨 Меры безопасности

1. **По умолчанию только preview** - фактическое удаление требует явного указания
2. **Защищенные файлы** - важные файлы и директории защищены от удаления
3. **Логирование** - все операции логируются с детальной информацией
4. **Dry-run режим** - возможность предварительного просмотра

## 🔍 Отладка

### Проверка что будет удалено

```bash
make pre-commit-cleanup-dry
# или
python scripts/cleanup_project.py --dry-run
```

### Просмотр всех хуков

```bash
pre-commit run --all-files --verbose
```

### Запуск конкретного хука

```bash
pre-commit run cleanup-project-dry
pre-commit run cleanup-project-full --hook-stage manual
```

## 📈 Интеграция с CI/CD

В CI окружениях хуки очистки автоматически пропускаются благодаря:

1. **Обнаружению CI** - проверка переменных `CI`, `GITHUB_ACTIONS`, и др.
2. **Настройкам pre-commit.ci** - исключение в `.pre-commit-config.yaml`:

```yaml
ci:
  skip: [cleanup-project-dry, cleanup-project-full, cleanup-project-verbose]
```

## 🎯 Лучшие практики

1. **Регулярная очистка** - используйте `make clean` периодически
2. **Перед релизом** - выполняйте полную очистку с `--verbose`
3. **В команде** - договоритесь о едином подходе к очистке
4. **Мониторинг** - следите за размером репозитория

## 🔗 Связанные файлы

- `.pre-commit-config.yaml` - конфигурация хуков
- `scripts/cleanup_project.py` - скрипт очистки
- `tests/conftest.py` - автоочистка в тестах
- `Makefile` - команды управления
- `docs/project_cleanup.md` - общая документация по очистке
