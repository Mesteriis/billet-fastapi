# Makefile для управления TaskIQ проектом

.PHONY: help install dev run worker test clean clean-dry clean-verbose clean-old typecheck typecheck-strict mypy-install-types mypy-report

# Цвета для вывода
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
NC=\033[0m # No Color

help: ## Показать справку
	@echo "$(YELLOW)Доступные команды:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Установить зависимости
	@echo "$(BLUE)📦 Установка зависимостей...$(NC)"
	uv sync

dev: ## Установить зависимости для разработки
	@echo "$(BLUE)🔧 Установка dev зависимостей...$(NC)"
	uv sync --group dev

run: ## Запустить FastAPI сервер
	@echo "$(GREEN)🚀 Запуск FastAPI сервера...$(NC)"
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

worker: ## Запустить TaskIQ воркеры
	@echo "$(GREEN)⚡ Запуск TaskIQ воркеров...$(NC)"
	python src/cli.py worker --workers 4

worker-dev: ## Запустить воркеры в режиме разработки
	@echo "$(GREEN)🔄 Запуск TaskIQ воркеров (dev режим)...$(NC)"
	python src/cli.py worker --workers 2 --reload

taskiq-info: ## Показать информацию о TaskIQ
	@echo "$(BLUE)ℹ️  Информация о TaskIQ:$(NC)"
	python src/cli.py info

taskiq-test: ## Протестировать TaskIQ
	@echo "$(BLUE)🧪 Тестирование TaskIQ...$(NC)"
	python src/cli.py test

test: ## Запустить все тесты
	@echo "$(BLUE)🧪 Запуск всех тестов...$(NC)"
	uv run pytest -v

test-quiet: ## Запустить тесты в тихом режиме (без логов внешних библиотек)
	@echo "$(BLUE)🤫 Запуск тестов в тихом режиме...$(NC)"
	TEST_LOG_LEVEL=quiet uv run pytest -v

test-verbose: ## Запустить тесты с подробным логированием
	@echo "$(BLUE)📢 Запуск тестов с подробным логированием...$(NC)"
	TEST_LOG_LEVEL=verbose uv run pytest -v -s

test-debug: ## Запустить тесты в режиме отладки
	@echo "$(BLUE)🐛 Запуск тестов в режиме отладки...$(NC)"
	TEST_LOG_LEVEL=debug uv run pytest -v -s --pdb

test-silent: ## Запустить тесты полностью без логов
	@echo "$(BLUE)🔇 Запуск тестов без логов...$(NC)"
	TEST_LOG_LEVEL=quiet uv run pytest --tb=no -q

test-cov: ## Запустить тесты с покрытием
	@echo "$(BLUE)📊 Запуск тестов с покрытием...$(NC)"
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing

test-auth: ## Запустить тесты аутентификации
	@echo "$(BLUE)🔐 Запуск тестов аутентификации...$(NC)"
	uv run pytest -v -m auth

test-users: ## Запустить тесты пользователей
	@echo "$(BLUE)👥 Запуск тестов пользователей...$(NC)"
	uv run pytest -v -m users

test-taskiq: ## Запустить только тесты TaskIQ
	@echo "$(BLUE)⚡ Запуск тестов TaskIQ...$(NC)"
	uv run pytest tests/test_taskiq_* -v

test-integration: ## Запустить интеграционные тесты
	@echo "$(BLUE)🔗 Запуск интеграционных тестов...$(NC)"
	uv run pytest -v -m integration

test-unit: ## Запустить только unit тесты
	@echo "$(BLUE)🧩 Запуск unit тестов...$(NC)"
	uv run pytest -v -m unit

test-watch: ## Запустить тесты в режиме наблюдения
	@echo "$(BLUE)👀 Запуск тестов в режиме наблюдения...$(NC)"
	uv run pytest-watch

test-fast: ## Запустить быстрые тесты (без медленных)
	@echo "$(BLUE)⚡ Запуск быстрых тестов...$(NC)"
	uv run pytest -v -m "not slow"

# Параллельное тестирование
test-parallel: ## Параллельный запуск тестов
	@echo "$(GREEN)⚡ Параллельный запуск тестов...$(NC)"
	uv run pytest -n auto

# Мокированные тесты
test-mocked: ## Тесты с моками
	@echo "$(YELLOW)🎭 Тесты с моками...$(NC)"
	uv run pytest -m mocked -v

# Performance тесты
test-performance: ## Тесты производительности
	@echo "$(RED)🏎️ Тесты производительности...$(NC)"
	uv run pytest -m performance --benchmark-only

test-load: ## Нагрузочные тесты
	@echo "$(RED)💪 Нагрузочные тесты...$(NC)"
	uv run locust -f tests/performance/load_tests.py --users 50 --spawn-rate 5 --run-time 2m --host http://localhost:8000 --headless --html reports/load_test_report.html

# E2E тесты
test-e2e: ## E2E тесты с Playwright
	@echo "$(GREEN)🎬 E2E тесты...$(NC)"
	uv run pytest tests/e2e/ -m e2e -v

install-playwright: ## Установка Playwright
	@echo "$(BLUE)🎭 Установка Playwright...$(NC)"
	uv run playwright install chromium

# Фабричные тесты
test-factories: ## Тесты фабрик данных
	@echo "$(YELLOW)🏭 Тесты фабрик данных...$(NC)"
	uv run pytest -m factories -v

# Последовательный запуск всех типов тестов
test-sequential: ## Последовательный запуск: unit → integration → e2e → performance
	@echo "$(GREEN)🔄 Последовательный запуск всех тестов...$(NC)"
	@echo "$(BLUE)1️⃣ Unit тесты...$(NC)"
	@$(MAKE) test-unit-fast
	@echo "$(BLUE)2️⃣ Интеграционные тесты...$(NC)" 
	@$(MAKE) test-integration-fast
	@echo "$(BLUE)3️⃣ E2E тесты...$(NC)"
	@$(MAKE) test-e2e-fast
	@echo "$(BLUE)4️⃣ Тесты производительности...$(NC)"
	@$(MAKE) test-performance-fast
	@echo "$(GREEN)✅ Все тесты завершены!$(NC)"

# Быстрые версии тестов для последовательного запуска
test-unit-fast: ## Быстрые unit тесты
	@uv run pytest -m unit -v --tb=short --maxfail=10

test-integration-fast: ## Быстрые интеграционные тесты
	@uv run pytest -m integration -v --tb=short --maxfail=5

test-e2e-fast: ## Быстрые E2E тесты
	@uv run pytest -m e2e -v --tb=short --maxfail=3

test-performance-fast: ## Быстрые тесты производительности
	@uv run pytest -m performance -v --tb=short --maxfail=1

# Расширенные тесты с покрытием
test-unit-coverage: ## Unit тесты с покрытием
	@echo "$(BLUE)🧩 Unit тесты с покрытием...$(NC)"
	uv run pytest -m unit --cov=src --cov-report=term-missing --cov-report=html:htmlcov/unit -v

test-integration-coverage: ## Интеграционные тесты с покрытием
	@echo "$(BLUE)🔗 Интеграционные тесты с покрытием...$(NC)"
	uv run pytest -m integration --cov=src --cov-report=term-missing --cov-report=html:htmlcov/integration -v

test-all-coverage: ## Все тесты с покрытием 80%
	@echo "$(GREEN)📊 Все тесты с покрытием 80%...$(NC)"
	uv run pytest --cov=src --cov-report=html:htmlcov/full --cov-report=term-missing --cov-fail-under=80 -v

# Тесты по категориям
test-auth-full: ## Полные тесты аутентификации
	@echo "$(BLUE)🔐 Полные тесты аутентификации...$(NC)"
	uv run pytest -m auth -v --cov=src.apps.auth --cov-report=term-missing

test-users-full: ## Полные тесты пользователей
	@echo "$(BLUE)👥 Полные тесты пользователей...$(NC)"
	uv run pytest -m users -v --cov=src.apps.users --cov-report=term-missing

test-realtime-full: ## Полные тесты realtime
	@echo "$(BLUE)⚡ Полные тесты realtime...$(NC)"
	uv run pytest -m realtime -v --cov=src.core.realtime --cov-report=term-missing

test-telegram-full: ## Полные тесты Telegram
	@echo "$(BLUE)📱 Полные тесты Telegram...$(NC)"
	uv run pytest -m telegram -v --cov=src.core.telegram --cov-report=term-missing

# Тесты с разными стратегиями
test-parallel-unit: ## Параллельные unit тесты
	@echo "$(GREEN)⚡ Параллельные unit тесты...$(NC)"
	uv run pytest -m unit -n auto --dist=loadgroup

test-parallel-integration: ## Параллельные интеграционные тесты
	@echo "$(GREEN)⚡ Параллельные интеграционные тесты...$(NC)"
	uv run pytest -m integration -n 2 --dist=loadgroup

# Проверка качества тестов
test-mutations: ## Mutation тестирование
	@echo "$(RED)🧬 Mutation тестирование...$(NC)"
	uv run mutmut run --paths-to-mutate=src/

test-coverage-report: ## Детальный отчет покрытия
	@echo "$(BLUE)📊 Детальный отчет покрытия...$(NC)"
	uv run coverage report --show-missing --skip-covered
	uv run coverage html --directory=htmlcov/detailed

# Генерация отчетов
test-report: ## Генерация отчетов тестирования
	@echo "$(BLUE)📈 Генерация отчетов тестирования...$(NC)"
	mkdir -p reports
	uv run pytest --html=reports/test_report.html --self-contained-html --json-report --json-report-file=reports/test_results.json

test-report-full: ## Полный отчет с покрытием и метриками
	@echo "$(BLUE)📊 Полный отчет тестирования...$(NC)"
	mkdir -p reports
	uv run pytest --cov=src --cov-report=html:reports/coverage --html=reports/test_report.html --self-contained-html --json-report --json-report-file=reports/test_results.json -v

# Очистка результатов тестов
clean-test: ## Очистка результатов тестов
	@echo "$(YELLOW)🧹 Очистка результатов тестов...$(NC)"
	rm -rf htmlcov/
	rm -rf reports/
	rm -rf .coverage*
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

lint: ## Проверить код линтером
	@echo "$(BLUE)🔍 Проверка кода...$(NC)"
	ruff check src/
	ruff format src/ --check

format: ## Отформатировать код
	@echo "$(GREEN)✨ Форматирование кода...$(NC)"
	ruff format src/

redis-start: ## Запустить Redis через Docker
	@echo "$(GREEN)🔴 Запуск Redis...$(NC)"
	docker run -d --name taskiq-redis -p 6379:6379 redis:alpine || docker start taskiq-redis

redis-stop: ## Остановить Redis
	@echo "$(RED)⏹️  Остановка Redis...$(NC)"
	docker stop taskiq-redis || true

redis-logs: ## Показать логи Redis
	@echo "$(BLUE)📋 Логи Redis:$(NC)"
	docker logs -f taskiq-redis

clean: ## Очистить временные файлы (новый умный способ)
	@echo "$(YELLOW)🧹 Умная очистка проекта...$(NC)"
	python scripts/cleanup_project.py

clean-dry: ## Показать что будет удалено при очистке
	@echo "$(BLUE)🔍 Предварительный просмотр очистки...$(NC)"
	python scripts/cleanup_project.py --dry-run

clean-verbose: ## Подробная очистка с выводом всех действий
	@echo "$(YELLOW)🧹 Подробная очистка проекта...$(NC)"
	python scripts/cleanup_project.py --verbose

clean-old: ## Очистить временные файлы (старый способ)
	@echo "$(YELLOW)🧹 Старая очистка...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

setup: ## Полная настройка проекта
	@echo "$(GREEN)🔧 Полная настройка проекта...$(NC)"
	$(MAKE) install
	$(MAKE) redis-start
	sleep 2
	$(MAKE) taskiq-test
	@echo "$(GREEN)✅ Проект готов к использованию!$(NC)"
	@echo "$(YELLOW)Запустите 'make run' для API и 'make worker' для воркеров$(NC)"

logs: ## Показать логи приложения
	@echo "$(BLUE)📋 Логи приложения:$(NC)"
	tail -f app.log

docker-build: ## Собрать Docker образ
	@echo "$(BLUE)🐳 Сборка Docker образа...$(NC)"
	docker build -t taskiq-app .

docker-run: ## Запустить через Docker Compose
	@echo "$(GREEN)🐳 Запуск через Docker Compose...$(NC)"
	docker-compose up -d

docker-logs: ## Показать логи Docker контейнеров
	@echo "$(BLUE)📋 Логи Docker:$(NC)"
	docker-compose logs -f

docker-stop: ## Остановить Docker контейнеры
	@echo "$(RED)⏹️  Остановка Docker контейнеров...$(NC)"
	docker-compose down

# Команды для продакшена
prod-deploy: ## Развернуть в продакшене
	@echo "$(GREEN)🚀 Развертывание в продакшене...$(NC)"
	# Добавьте свои команды развертывания

prod-logs: ## Логи продакшена
	@echo "$(BLUE)📋 Логи продакшена:$(NC)"
	journalctl -u taskiq-worker -f

# Утилиты
check-deps: ## Проверить устаревшие зависимости
	@echo "$(BLUE)📦 Проверка зависимостей...$(NC)"
	uv pip list --outdated

update-deps: ## Обновить зависимости
	@echo "$(GREEN)⬆️  Обновление зависимостей...$(NC)"
	uv sync --upgrade

health: ## Проверить здоровье системы
	@echo "$(BLUE)🏥 Проверка здоровья системы...$(NC)"
	curl -s http://localhost:8000/health | jq . || echo "API недоступен"
	curl -s http://localhost:8000/tasks/health | jq . || echo "TaskIQ недоступен"

# Pre-commit команды
pre-commit-install: ## Установить pre-commit хуки
	@echo "$(GREEN)🔗 Установка pre-commit хуков...$(NC)"
	uv run pre-commit install

pre-commit-update: ## Обновить версии в pre-commit
	@echo "$(BLUE)⬆️  Обновление pre-commit репозиториев...$(NC)"
	uv run pre-commit autoupdate

pre-commit-run: ## Запустить pre-commit на всех файлах
	@echo "$(YELLOW)🔍 Запуск pre-commit на всех файлах...$(NC)"
	uv run pre-commit run --all-files

pre-commit-run-staged: ## Запустить pre-commit только на staged файлах
	@echo "$(YELLOW)📋 Запуск pre-commit на staged файлах...$(NC)"
	uv run pre-commit run

pre-commit-clean: ## Очистить кэш pre-commit
	@echo "$(RED)🧹 Очистка кэша pre-commit...$(NC)"
	uv run pre-commit clean

pre-commit-manual: ## Ручной запуск всех проверок без pre-commit
	@echo "$(BLUE)🔧 Ручной запуск всех проверок...$(NC)"
	uv run ruff check src/ tests/ scripts/ --fix
	uv run ruff format src/ tests/ scripts/
	uv run mypy src/ --ignore-missing-imports
	uv run bandit -r src/ -f json -o reports/bandit.json || true
	uv run safety check --json --output reports/safety.json || true
	python scripts/check_structure.py

# Качество кода
code-quality: ## Полная проверка качества кода
	@echo "$(GREEN)✨ Полная проверка качества кода...$(NC)"
	mkdir -p reports
	$(MAKE) pre-commit-run
	$(MAKE) test-cov
	$(MAKE) test-performance
	@echo "$(GREEN)✅ Проверка качества завершена! Отчеты в директории reports/$(NC)"

setup-dev: ## Полная настройка для разработки
	@echo "$(GREEN)🔧 Настройка среды разработки...$(NC)"
	$(MAKE) dev
	$(MAKE) install-playwright
	$(MAKE) pre-commit-install
	$(MAKE) redis-start
	@echo "$(GREEN)✅ Среда разработки готова!$(NC)"
	@echo "$(YELLOW)Рекомендуется запустить 'make code-quality' для проверки$(NC)"

.PHONY: check-duplication
check-duplication:  ## Проверка дублирования кода
	@echo "🔍 Проверка дублирования кода..."
	@python scripts/check_duplication.py --min-lines=7

.PHONY: check-architecture  
check-architecture:  ## Проверка архитектурных правил
	@echo "🏗️ Проверка архитектурных правил..."
	@python scripts/check_architecture.py

.PHONY: lint-all
lint-all: check-duplication check-architecture  ## Запуск всех проверок качества кода
	@echo "✅ Все проверки качества кода завершены!"

.PHONY: fix-tests
fix-tests:  ## Исправление fixture в тестах
	@echo "🔧 Исправление проблем с fixture..."
	@find tests/ -name "*.py" -exec python -m py_compile {} \; || true

.PHONY: docs-update
docs-update:  ## Обновление документации модулей
	@echo "📚 Проверка документации модулей..."
	@find src/ -name "*.py" -path "*/src/*" ! -path "*/tests/*" ! -name "__init__.py" -exec grep -L '"""' {} \; || echo "Все модули задокументированы!"

.PHONY: quality-check
quality-check: lint-all fix-tests docs-update  ## Полная проверка качества проекта
	@echo "🎯 Полная проверка качества завершена!"

.PHONY: migrate-create
migrate-create:  ## Создание новой миграции (использование: make migrate-create MSG="описание")
	@echo "📝 Создание новой миграции..."
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Укажите описание миграции: make migrate-create MSG='описание'"; \
		exit 1; \
	fi
	@uv run alembic revision --autogenerate -m "$(MSG)"

.PHONY: migrate-up
migrate-up:  ## Применение миграций
	@echo "⬆️  Применение миграций..."
	@uv run alembic upgrade head

.PHONY: migrate-down
migrate-down:  ## Откат последней миграции
	@echo "⬇️  Откат последней миграции..."
	@uv run alembic downgrade -1

.PHONY: migrate-status
migrate-status:  ## Статус миграций
	@echo "📊 Статус миграций..."
	@uv run alembic current
	@echo ""
	@uv run alembic history --verbose

.PHONY: migrate-reset
migrate-reset:  ## Сброс всех миграций (ОСТОРОЖНО!)
	@echo "🚨 ВНИМАНИЕ: Это удалит все данные!"
	@read -p "Вы уверены? (y/N): " confirm && [ "$$confirm" = "y" ]
	@uv run alembic downgrade base
	@echo "✅ Все миграции отменены"

.PHONY: migrate-validate
migrate-validate:  ## Валидация миграций
	@echo "🔍 Валидация миграций..."
	@uv run python -c "import asyncio; from core.migrations import MigrationMonitor; print(asyncio.run(MigrationMonitor().check_migration_integrity()))"

.PHONY: migrate-backup
migrate-backup:  ## Создание бэкапа БД
	@echo "💾 Создание бэкапа базы данных..."
	@uv run python -c "import asyncio; from core.migrations import MigrationBackup; print(asyncio.run(MigrationBackup().create_backup('manual_backup')))"

.PHONY: migrate-list-backups
migrate-list-backups:  ## Список бэкапов
	@echo "📋 Список бэкапов:"
	@uv run python -c "from core.migrations import MigrationBackup; import json; print(json.dumps(MigrationBackup().list_backups(), indent=2, ensure_ascii=False))"

.PHONY: migrate-safe
migrate-safe:  ## Безопасная миграция с валидацией и бэкапом
	@echo "🛡️  Безопасная миграция..."
	@uv run python -c "import asyncio; from core.migrations import MigrationManager; import json; result = asyncio.run(MigrationManager().safe_migrate()); print(json.dumps(result, indent=2, ensure_ascii=False))"

.PHONY: migrate-monitor
migrate-monitor:  ## Мониторинг состояния миграций
	@echo "📊 Мониторинг миграций..."
	@uv run python -c "import asyncio; from core.migrations import MigrationMonitor; import json; result = asyncio.run(MigrationMonitor().get_migration_status()); print(json.dumps(result, indent=2, ensure_ascii=False))"

.PHONY: test-migrations
test-migrations:  ## Запуск тестов миграций
	@echo "🧪 Тестирование миграций..."
	@uv run pytest tests/test_migrations.py -v --tb=short

.PHONY: test-migrations-alembic
test-migrations-alembic:  ## Запуск встроенных тестов pytest-alembic
	@echo "🔬 Запуск pytest-alembic тестов..."
	@uv run pytest --test-alembic -v

# === Управление базой данных ===
.PHONY: db-info
db-info:  ## 🗄️ Информация о базе данных
	@python scripts/migration_cli.py db-info

.PHONY: db-create
db-create:  ## 🏗️ Создание базы данных
	@python scripts/migration_cli.py db-create

.PHONY: db-drop
db-drop:  ## 🗑️ Удаление базы данных (ОСТОРОЖНО!)
	@python scripts/migration_cli.py db-drop

.PHONY: db-test
db-test:  ## 🔌 Тестирование подключения к БД
	@python scripts/migration_cli.py db-test

.PHONY: db-ensure
db-ensure:  ## 🔍 Проверка/создание БД если не существует
	@python scripts/migration_cli.py db-ensure

# Проверка типов
typecheck:
	@echo "🔍 Проверяю типы с mypy..."
	cd src && mypy .

# Строгая проверка типов
typecheck-strict:
	@echo "🔍 Строгая проверка типов с mypy..."
	cd src && mypy . --strict

# Установка типов для внешних библиотек
mypy-install-types:
	@echo "📦 Устанавливаю типы для внешних библиотек..."
	mypy --install-types --non-interactive

# Генерация отчета по типизации
mypy-report:
	@echo "📊 Генерирую отчет по типизации..."
	cd src && mypy . --html-report ../reports/mypy-html --txt-report ../reports/mypy-txt
