# Makefile для управления FastAPI + TaskIQ проектом

# ============================================================================
# КОНФИГУРАЦИЯ И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ============================================================================

# Автозагрузка env файлов если они существуют
ifneq (,$(wildcard .env))
    include .env
    export $(shell sed 's/=.*//' .env)
endif
ifneq (,$(wildcard local.env))
    include local.env  
    export $(shell sed 's/=.*//' local.env)
endif
ifneq (,$(wildcard docker.env))
    include docker.env
    export $(shell sed 's/=.*//' docker.env)
endif

# Переменные по умолчанию
WORKERS ?= 4
HOST ?= 0.0.0.0
PORT ?= 8000

# Цвета для вывода
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
BLUE=\033[0;34m
PURPLE=\033[0;35m
CYAN=\033[0;36m
NC=\033[0m

# Общие phony цели
.PHONY: help install dev clean setup

# ============================================================================
# СПРАВКА
# ============================================================================

help: ## 📋 Показать справку по всем командам
	@echo "$(YELLOW)🚀 FastAPI + TaskIQ Project Management$(NC)"
	@echo ""
	@echo "$(CYAN)📦 УСТАНОВКА И НАСТРОЙКА:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## 📦/ {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, substr($$2, 3)}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(CYAN)🏃 ЗАПУСК СЕРВИСОВ:$(NC)" 
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## 🏃/ {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, substr($$2, 3)}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(CYAN)🧪 ТЕСТИРОВАНИЕ:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## 🧪/ {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, substr($$2, 3)}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(CYAN)🗄️  БАЗА ДАННЫХ:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## 🗄️/ {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, substr($$2, 3)}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(CYAN)🔍 КАЧЕСТВО КОДА:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## 🔍/ {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, substr($$2, 3)}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(CYAN)🐳 DOCKER:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## 🐳/ {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, substr($$2, 3)}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(CYAN)🧹 УТИЛИТЫ:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## 🧹/ {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, substr($$2, 3)}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)💡 Примеры использования:$(NC)"
	@echo "  $(GREEN)make test$(NC)                    - Запустить все тесты"
	@echo "  $(GREEN)make test -m unit$(NC)           - Запустить только unit тесты"  
	@echo "  $(GREEN)make test -m auth --cov$(NC)     - Тесты auth с покрытием"
	@echo "  $(GREEN)make test -v -s$(NC)             - Подробный вывод + логи"
	@echo "  $(GREEN)make test --pdb$(NC)             - Режим отладки"
	@echo "  $(GREEN)make run HOST=127.0.0.1$(NC)     - API на localhost"
	@echo "  $(GREEN)make worker WORKERS=8$(NC)       - 8 воркеров TaskIQ"

# ============================================================================
# УСТАНОВКА И НАСТРОЙКА
# ============================================================================

install: ## 📦 Установить основные зависимости
	@echo "$(BLUE)📦 Установка основных зависимостей...$(NC)"
	@uv sync

dev: ## 📦 Установить зависимости для разработки
	@echo "$(BLUE)🔧 Установка dev зависимостей...$(NC)"
	@uv sync --group dev

setup: install ## 📦 Полная настройка проекта (зависимости + redis + тест)
	@echo "$(GREEN)🔧 Полная настройка проекта...$(NC)"
	@$(MAKE) redis-start
	@sleep 2
	@$(MAKE) taskiq-info
	@echo "$(GREEN)✅ Проект готов! Запустите:$(NC)"
	@echo "  $(YELLOW)make run$(NC)    - для API сервера"
	@echo "  $(YELLOW)make worker$(NC) - для TaskIQ воркеров"

setup-dev: dev ## 📦 Настройка среды разработки (dev + playwright + pre-commit)
	@echo "$(GREEN)🔧 Настройка среды разработки...$(NC)"
	@$(MAKE) install-playwright
	@$(MAKE) pre-commit-install  
	@$(MAKE) redis-start
	@echo "$(GREEN)✅ Среда разработки готова!$(NC)"

# ============================================================================
# ЗАПУСК СЕРВИСОВ  
# ============================================================================

run: ## 🏃 Запустить FastAPI сервер (HOST=0.0.0.0 PORT=8000)
	@echo "$(GREEN)🚀 Запуск FastAPI сервера на $(HOST):$(PORT)...$(NC)"
	@uvicorn src.main:app --reload --host $(HOST) --port $(PORT)

worker: ## 🏃 Запустить TaskIQ воркеры (WORKERS=4)
	@echo "$(GREEN)⚡ Запуск $(WORKERS) TaskIQ воркеров...$(NC)"
	@python src/cli.py worker --workers $(WORKERS)

worker-dev: ## 🏃 Запустить воркеры в dev режиме с автоперезагрузкой
	@echo "$(GREEN)🔄 Запуск TaskIQ воркеров (dev режим)...$(NC)"
	@python src/cli.py worker --workers 2 --reload

taskiq-info: ## 🏃 Показать информацию о TaskIQ
	@echo "$(BLUE)ℹ️  Информация о TaskIQ:$(NC)"
	@python src/cli.py info

# ============================================================================
# ТЕСТИРОВАНИЕ
# ============================================================================

test: ## 🧪 Универсальная команда тестирования (например: make test -m unit --cov -v)
	@echo "$(BLUE)🧪 Запуск тестов с аргументами: $(ARGS)$(NC)"
	@$(MAKE) _run-pytest

# Внутренняя команда для запуска pytest с переданными аргументами
_run-pytest:
	@if echo "$(ARGS)" | grep -q "\--cov"; then \
		mkdir -p reports htmlcov; \
		if echo "$(ARGS)" | grep -q "\-m"; then \
			MARK=$$(echo "$(ARGS)" | sed -n 's/.*-m \([a-zA-Z_]*\).*/\1/p'); \
			uv run pytest $(ARGS) --cov=src --cov-report=html:htmlcov/$$MARK --cov-report=term-missing; \
		else \
			uv run pytest $(ARGS) --cov=src --cov-report=html:htmlcov/full --cov-report=term-missing --cov-fail-under=80; \
		fi; \
	elif echo "$(ARGS)" | grep -q "\--pdb"; then \
		TEST_LOG_LEVEL=debug uv run pytest $(ARGS); \
	elif echo "$(ARGS)" | grep -q "\-q"; then \
		TEST_LOG_LEVEL=quiet uv run pytest $(ARGS); \
	elif [ -n "$(ARGS)" ]; then \
		uv run pytest $(ARGS); \
	else \
		uv run pytest -v; \
	fi

# Удобные алиасы для частых команд
test-unit: ## 🧪 Unit тесты
	@$(MAKE) test ARGS="-m unit"

test-integration: ## 🧪 Интеграционные тесты
	@$(MAKE) test ARGS="-m integration"

test-e2e: ## 🧪 E2E тесты
	@$(MAKE) test ARGS="-m e2e"

test-auth: ## 🧪 Тесты аутентификации
	@$(MAKE) test ARGS="-m auth"

test-cov: ## 🧪 Все тесты с покрытием
	@$(MAKE) test ARGS="--cov"

test-debug: ## 🧪 Тесты в режиме отладки
	@$(MAKE) test ARGS="--pdb -s"

test-parallel: ## 🧪 Параллельные тесты
	@$(MAKE) test ARGS="-n auto"

# Специальные типы тестов  
test-load: ## 🧪 Нагрузочные тесты с Locust
	@echo "$(RED)💪 Нагрузочные тесты...$(NC)"
	@mkdir -p reports
	@uv run locust -f tests/performance/load_tests.py --users 50 --spawn-rate 5 --run-time 2m --host http://localhost:8000 --headless --html reports/load_test_report.html

test-mutations: ## 🧪 Mutation тестирование
	@echo "$(RED)🧬 Mutation тестирование...$(NC)"
	@uv run mutmut run --paths-to-mutate=src/

install-playwright: ## 🧪 Установка Playwright для E2E тестов
	@echo "$(BLUE)🎭 Установка Playwright...$(NC)"
	@uv run playwright install chromium

# ============================================================================
# БАЗА ДАННЫХ И МИГРАЦИИ
# ============================================================================

migrate: ## 🗄️ Применить миграции (MSG="описание" для создания новой)
	@if [ -n "$(MSG)" ]; then \
		echo "$(BLUE)📝 Создание миграции: $(MSG)$(NC)"; \
		uv run alembic revision --autogenerate -m "$(MSG)"; \
	else \
		echo "$(BLUE)⬆️  Применение миграций...$(NC)"; \
		uv run alembic upgrade head; \
	fi

migrate-down: ## 🗄️ Откатить последнюю миграцию
	@echo "$(YELLOW)⬇️  Откат последней миграции...$(NC)"
	@uv run alembic downgrade -1

migrate-status: ## 🗄️ Статус миграций
	@echo "$(BLUE)📊 Статус миграций:$(NC)"
	@uv run alembic current
	@echo ""
	@uv run alembic history --verbose

migrate-reset: ## 🗄️ СБРОС всех миграций (ОСТОРОЖНО!)
	@echo "$(RED)🚨 ВНИМАНИЕ: Это удалит все данные из БД!$(NC)"
	@read -p "Вы уверены? Введите 'YES' для подтверждения: " confirm && [ "$$confirm" = "YES" ]
	@uv run alembic downgrade base
	@echo "$(GREEN)✅ Все миграции сброшены$(NC)"

db-info: ## 🗄️ Информация о базе данных
	@python scripts/migration_cli.py db-info

db-create: ## 🗄️ Создать базу данных
	@python scripts/migration_cli.py db-create

db-backup: ## 🗄️ Создать бэкап базы данных
	@echo "$(BLUE)💾 Создание бэкапа базы данных...$(NC)"
	@uv run python -c "import asyncio; from core.migrations import MigrationBackup; print(asyncio.run(MigrationBackup().create_backup('manual_backup')))"

# ============================================================================
# КАЧЕСТВО КОДА
# ============================================================================

lint: ## 🔍 Проверить код линтерами (ruff + mypy)
	@echo "$(BLUE)🔍 Проверка кода линтерами...$(NC)"
	@uv run ruff check src/ tests/ scripts/
	@uv run ruff format src/ tests/ scripts/ --check
	@cd src && uv run mypy . --ignore-missing-imports

format: ## 🔍 Отформатировать код
	@echo "$(GREEN)✨ Форматирование кода...$(NC)"
	@uv run ruff format src/ tests/ scripts/
	@uv run ruff check src/ tests/ scripts/ --fix

typecheck: ## 🔍 Проверка типов с отчетом
	@echo "$(BLUE)🔍 Проверка типов с mypy...$(NC)"
	@mkdir -p reports
	@cd src && uv run mypy . --html-report ../reports/mypy-html --txt-report ../reports/mypy-txt --ignore-missing-imports

quality: ## 🔍 Полная проверка качества кода
	@echo "$(GREEN)✨ Полная проверка качества кода...$(NC)"
	@$(MAKE) lint
	@$(MAKE) test-cov
	@echo "$(GREEN)✅ Проверка качества завершена!$(NC)"

pre-commit-install: ## 🔍 Установить pre-commit хуки
	@echo "$(GREEN)🔗 Установка pre-commit хуков...$(NC)"
	@uv run pre-commit install

pre-commit-run: ## 🔍 Запустить pre-commit на всех файлах
	@echo "$(YELLOW)🔍 Запуск pre-commit...$(NC)"
	@uv run pre-commit run --all-files

# ============================================================================
# DOCKER
# ============================================================================

docker-build: ## 🐳 Собрать Docker образ
	@echo "$(BLUE)🐳 Сборка Docker образа...$(NC)"
	@docker build -t taskiq-app .

docker-up: ## 🐳 Запустить все сервисы через Docker Compose
	@echo "$(GREEN)🐳 Запуск сервисов через Docker Compose...$(NC)"
	@docker-compose up -d

docker-down: ## 🐳 Остановить Docker сервисы
	@echo "$(RED)⏹️  Остановка Docker сервисов...$(NC)"
	@docker-compose down

docker-logs: ## 🐳 Показать логи Docker сервисов
	@echo "$(BLUE)📋 Логи Docker сервисов:$(NC)"
	@docker-compose logs -f

# ============================================================================
# УТИЛИТЫ
# ============================================================================

clean: ## 🧹 Очистить временные файлы проекта
	@echo "$(YELLOW)🧹 Очистка временных файлов...$(NC)"
	@python scripts/cleanup_project.py

clean-dry: ## 🧹 Показать что будет удалено при очистке
	@echo "$(BLUE)🔍 Предварительный просмотр очистки...$(NC)"
	@python scripts/cleanup_project.py --dry-run

redis-start: ## 🧹 Запустить Redis через Docker
	@echo "$(GREEN)🔴 Запуск Redis...$(NC)"
	@docker run -d --name taskiq-redis -p 6379:6379 redis:alpine || docker start taskiq-redis

redis-stop: ## 🧹 Остановить Redis
	@echo "$(RED)⏹️  Остановка Redis...$(NC)"
	@docker stop taskiq-redis || true

health: ## 🧹 Проверить состояние сервисов
	@echo "$(BLUE)🏥 Проверка состояния сервисов...$(NC)"
	@curl -s http://localhost:8000/health | jq . || echo "❌ API недоступен"
	@curl -s http://localhost:8000/tasks/health | jq . || echo "❌ TaskIQ недоступен"

update-deps: ## 🧹 Обновить зависимости
	@echo "$(GREEN)⬆️  Обновление зависимостей...$(NC)"
	@uv sync --upgrade

logs: ## 🧹 Показать логи приложения
	@echo "$(BLUE)📋 Логи приложения:$(NC)"
	@tail -f app.log 2>/dev/null || echo "Файл логов не найден"
