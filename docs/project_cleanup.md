# Очистка проекта от мусора

Система автоматической очистки проекта от временных файлов и мусора.

## Обзор

Скрипт `scripts/cleanup_project.py` безопасно удаляет только временные файлы и мусор, **НЕ ТРОГАЯ** важные файлы и директории.

## Что удаляется (безопасно)

### Директории

- `.benchmarks/` - файлы бенчмарков
- `htmlcov/` - HTML отчеты покрытия
- `.pytest_cache/` - кеш pytest
- `.mypy_cache/` - кеш mypy (включая в защищенных директориях как `src/`)
- `__pycache__/` - кеш Python (в любых директориях)
- `.tox/` - окружения tox
- `.ruff_cache/` - кеш Ruff
- `.black_cache/` - кеш Black
- `.hypothesis/` - Hypothesis кеш
- `.cache/` - общий кеш

### Файлы

- `.coverage*` - файлы покрытия
- `coverage.xml`, `coverage.json` - отчеты покрытия (в корне и reports/)
- `junit.xml`, `test-results.xml` - XML отчеты тестов (в корне и reports/)
- `*.pyc`, `*.pyo`, `*.pyd` - скомпилированные Python файлы
- `*.tmp`, `*.temp` - временные файлы
- `*.log` - лог файлы
- `.DS_Store` - файлы macOS
- `Thumbs.db` - файлы Windows
- `*.orig`, `*.rej` - файлы патчей
- `*.swp`, `*.swo`, `*~` - временные файлы редакторов

### Файлы в reports/

- `coverage.xml`, `coverage.json`
- `junit.xml`, `test-results.xml`
- `flake8-report.txt`, `mypy-report.txt`
- `bandit-report.json`
- `*.html`, `*.xml` - отчеты

## Что НЕ удаляется (защищено)

### Важные директории

- `.venv/`, `venv/`, `env/`, `.env/` - виртуальные окружения
- `node_modules/` - зависимости Node.js
- `dist/`, `build/` - артефакты сборки
- `.git/` - репозиторий Git
- `src/`, `tests/`, `docs/` - исходный код
- `examples/`, `migrations/`, `config/` - важные файлы проекта
- `scripts/`, `templates/`, `backups/` - служебные файлы

### Важные файлы

- `README.md`, `LICENSE`
- `pyproject.toml`, `requirements.txt`
- `Dockerfile`, `docker-compose.yml`
- `.gitignore`, `.pre-commit-config.yaml`
- `Makefile`

## Использование

### Команды Make

```bash
# Обычная очистка
make clean

# Предварительный просмотр (что будет удалено)
make clean-dry

# Подробная очистка с выводом всех действий
make clean-verbose

# Старый способ очистки (для сравнения)
make clean-old
```

### Прямое использование скрипта

```bash
# Обычная очистка
python scripts/cleanup_project.py

# Предварительный просмотр
python scripts/cleanup_project.py --dry-run

# Подробный вывод
python scripts/cleanup_project.py --verbose

# Комбинация
python scripts/cleanup_project.py --dry-run --verbose
```

### Pre-commit хук

Хук автоматически запускается в режиме `--dry-run` при каждом коммите:

```bash
# Ручной запуск pre-commit хука
uv run pre-commit run cleanup-project --all-files

# Установка pre-commit хуков
make pre-commit-install
```

## Примеры вывода

### Обычный режим

```
🧹 Очистка проекта: /path/to/project

📊 Результаты очистки:
   Удалено элементов: 15
   Освобождено места: 54.2 MB

✅ Очистка завершена!
```

### Режим dry-run

```
🧹 Очистка проекта: /path/to/project
🔍 Режим dry-run: файлы не будут удалены

📊 Результаты очистки:
   Удалено элементов: 15
   Освобождено места: 54.2 MB

💡 Запустите без --dry-run для фактического удаления
```

### Подробный режим

```
🧹 Очистка проекта: /path/to/project

🗂️  Удаляем директорию: .pytest_cache (135.9 KB)
🗂️  Удаляем директорию: src/.mypy_cache (48.3 MB)
📄 Удаляем файл: .coverage (68.0 KB)
📄 Удаляем файл: reports/coverage.xml (12.5 KB)
📄 Удаляем файл: src/coverage.xml [protected dir] (14.0 KB)
📄 Удаляем файл: src/debug.log [protected dir] (8.0 KB)
📄 Удаляем файл: tests/temp.pyc [protected dir] (2.1 KB)
📂 Удаляем пустую директорию: .benchmarks

📊 Результаты очистки:
   Удалено элементов: 18
   Освобождено места: 54.4 MB

✅ Очистка завершена!
```

## Безопасность

### Защитные механизмы

1. **Проверка корня проекта** - скрипт работает только если найден `pyproject.toml`
2. **Список защищенных директорий** - важные папки никогда не удаляются
3. **Список защищенных файлов** - важные файлы никогда не удаляются
4. **Режим dry-run** - возможность предварительного просмотра
5. **Подробный вывод** - контроль над каждым действием

### Специальная логика для защищенных директорий

#### Кеш-директории

Кеш-директории (`.mypy_cache`, `__pycache__`, `.pytest_cache` и др.) удаляются даже внутри защищенных директорий:

- `src/.mypy_cache/` ✅ будет удален
- `src/__pycache__/` ✅ будет удален
- `tests/__pycache__/` ✅ будет удален

#### Мусорные файлы в защищенных директориях

Безопасные мусорные файлы удаляются даже в защищенных папках (`src/`, `tests/`, `docs/`):

**Удаляются в защищенных директориях:**

- `src/coverage.xml` ✅ отчеты покрытия
- `src/debug.log` ✅ лог файлы
- `src/temp_file.tmp` ✅ временные файлы
- `src/test.pyc` ✅ скомпилированные Python файлы
- `tests/.DS_Store` ✅ системные файлы

**НЕ удаляются в защищенных директориях:**

- `src/main.py` ❌ исходный код Python
- `src/config.py` ❌ конфигурационные файлы
- `src/core/` ❌ папки исходного кода

### Проверка перед удалением

```bash
# Всегда сначала проверяйте что будет удалено
make clean-dry

# Или с подробным выводом
python scripts/cleanup_project.py --dry-run --verbose
```

## Интеграция с CI/CD

### Pre-commit

Хук автоматически проверяет наличие мусора при каждом коммите в режиме dry-run.

### Makefile

Команды интегрированы в Makefile для удобства использования.

### Автоматизация

```bash
# В CI/CD pipeline
make clean-dry  # Проверка наличия мусора
make clean      # Очистка (если нужно)
```

## Настройка

Для изменения поведения скрипта отредактируйте `scripts/cleanup_project.py`:

- `directories_to_remove` - директории для удаления
- `file_patterns_to_remove` - паттерны файлов для удаления
- `protected_directories` - защищенные директории
- `protected_files` - защищенные файлы

## Устранение проблем

### Скрипт не запускается

```bash
# Проверьте права доступа
chmod +x scripts/cleanup_project.py

# Проверьте наличие pyproject.toml
ls pyproject.toml
```

### Неожиданное поведение

```bash
# Используйте dry-run для диагностики
python scripts/cleanup_project.py --dry-run --verbose
```

### Ошибки доступа

```bash
# Проверьте права на файлы
ls -la .pytest_cache/
```

## Заключение

Система очистки проекта обеспечивает:

- **Безопасность** - не удаляет важные файлы
- **Удобство** - интеграция с Make и pre-commit
- **Контроль** - режим dry-run и подробный вывод
- **Автоматизацию** - работа в CI/CD pipeline

Всегда используйте `--dry-run` перед фактической очисткой для проверки результатов.
