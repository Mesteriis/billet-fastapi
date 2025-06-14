# =============================================================================
# Multi-stage Dockerfile для FastAPI проекта
# =============================================================================

# =============================================================================
# Stage 1: Base image с системными зависимостями
# =============================================================================
FROM python:3.11-slim-bookworm as base

# Метаданные
LABEL maintainer="Alexander Mescheryakov <avm@sh-inc.ru>"
LABEL description="FastAPI Project с Messaging и Realtime системами"
LABEL version="1.0.0"

# Отключаем интерактивный режим и буферизацию
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Основные утилиты
    curl \
    wget \
    ca-certificates \
    # Зависимости для компиляции Python пакетов
    build-essential \
    pkg-config \
    # OpenCV зависимости (для WebRTC)
    libopencv-dev \
    python3-opencv \
    # Для работы с изображениями
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # Аудио/видео кодеки для WebRTC
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    # PostgreSQL клиент
    libpq-dev \
    # Очистка кэша
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# =============================================================================
# Stage 2: Сборка зависимостей (dependency compilation)
# =============================================================================
FROM base as deps-builder

# Устанавливаем uv для быстрой установки зависимостей
RUN pip install uv

# Создаем пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости в отдельную директорию
RUN uv export --no-dev --format requirements-txt > requirements.txt && \
    uv pip install --system -r requirements.txt

# =============================================================================
# Stage 3: Development stage (для локальной разработки)
# =============================================================================
FROM deps-builder as development

# Устанавливаем dev зависимости
RUN uv export --dev --format requirements-txt > requirements-dev.txt && \
    uv pip install --system -r requirements-dev.txt

# Создаем рабочую директорию
WORKDIR /app

# Копируем исходный код
COPY --chown=appuser:appuser . .

# Создаем необходимые директории
RUN mkdir -p /app/logs /app/reports /app/htmlcov /app/var && \
    chown -R appuser:appuser /app

# Переключаемся на непривилегированного пользователя
USER appuser

# Expose портов
EXPOSE 8000 8443

# Команда для разработки
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Stage 4: Production deps (оптимизированная сборка для продакшена)
# =============================================================================
FROM base as production-deps

# Устанавливаем uv
RUN pip install uv

# Создаем пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock ./

# Устанавливаем только production зависимости
RUN uv export --no-dev --format requirements-txt > requirements.txt && \
    uv pip install --system -r requirements.txt && \
    # Очистка
    rm -rf /root/.cache/pip/* && \
    rm -rf /tmp/* && \
    apt-get purge -y build-essential pkg-config && \
    apt-get autoremove -y && \
    apt-get clean

# =============================================================================
# Stage 5: Application (финальный production образ)
# =============================================================================
FROM production-deps as production

# Создаем рабочую директорию
WORKDIR /app

# Копируем только необходимые файлы приложения
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser migrations/ ./migrations/
COPY --chown=appuser:appuser templates/ ./templates/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser Makefile ./

# Создаем необходимые директории для production
RUN mkdir -p /app/logs /app/reports /app/var /app/backups && \
    chown -R appuser:appuser /app

# Переключаемся на непривилегированного пользователя
USER appuser

# Expose портов
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Команда по умолчанию для production
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# Stage 6: TaskIQ Worker (для обработки фоновых задач)
# =============================================================================
FROM production-deps as taskiq-worker

WORKDIR /app

# Копируем необходимые файлы
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser pyproject.toml ./

# Создаем директории
RUN mkdir -p /app/logs /app/var && \
    chown -R appuser:appuser /app

USER appuser

# Команда для запуска TaskIQ worker
CMD ["taskiq", "worker", "src.core.taskiq_client:broker", "--fs-discover"]

# =============================================================================
# Stage 7: Messaging Service (FastStream + RabbitMQ)
# =============================================================================
FROM production-deps as messaging-service

WORKDIR /app

# Копируем файлы для messaging
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser pyproject.toml ./

RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Команда для запуска messaging service
CMD ["faststream", "run", "src.core.messaging:app", "--workers", "2"]

# =============================================================================
# Stage 8: Migration (для запуска миграций)
# =============================================================================
FROM production-deps as migration

WORKDIR /app

# Копируем файлы миграций и конфигурации
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser migrations/ ./migrations/
COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser Makefile ./

RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Команда для миграций
CMD ["python", "-m", "alembic", "upgrade", "head"] 