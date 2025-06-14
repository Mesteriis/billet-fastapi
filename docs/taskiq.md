# TaskIQ Клиент

Интеграция TaskIQ в проект для выполнения асинхронных задач в фоне.

## Обзор

TaskIQ - это современная библиотека для выполнения асинхронных задач в Python. В нашем проекте она используется для:

- ✅ Отправки email уведомлений
- ✅ Обработки файлов
- ✅ Получения данных из внешних API
- ✅ Обслуживания базы данных
- ✅ Генерации отчетов
- ✅ Создания резервных копий

## Архитектура

```
FastAPI App ──┐
              ├─► Redis (Broker) ──► TaskIQ Workers
FastAPI CLI ──┘                      │
                                     ▼
                                   Tasks
```

### Компоненты

1. **Брокер** - Redis (база данных 1)
2. **Результаты** - Redis (база данных 2)
3. **Воркеры** - Отдельные процессы
4. **Задачи** - Функции с декоратором `@broker.task`

## Установка и настройка

### 1. Зависимости

Зависимости уже добавлены в `pyproject.toml`:

```toml
"taskiq[redis]>=0.11.7"
"click>=8.1.7"
```

### 2. Переменные окружения

Создайте файл `.env` с настройками:

```bash
# TaskIQ настройки
TASKIQ_BROKER_URL=redis://localhost:6379/1
TASKIQ_RESULT_BACKEND_URL=redis://localhost:6379/2
TASKIQ_MAX_RETRIES=3
TASKIQ_RETRY_DELAY=5
TASKIQ_TASK_TIMEOUT=300

# Фоновые задачи
MAX_BACKGROUND_WORKERS=4
```

### 3. Запуск Redis

```bash
# Через Docker
docker run -d --name redis -p 6379:6379 redis:alpine

# Или через Homebrew на macOS
brew install redis
brew services start redis
```

## Использование

### 1. Запуск FastAPI сервера

```bash
uvicorn src.main:app --reload
```

### 2. Запуск TaskIQ воркеров

```bash
# Запуск воркеров через CLI
python src/cli.py worker --workers 4

# С дополнительными опциями
python src/cli.py worker --workers 4 --reload --max-memory 512
```

### 3. Проверка состояния

```bash
# Информация о конфигурации
python src/cli.py info

# Тестирование подключения
python src/cli.py test
```

## API Endpoints

### Запуск задач

#### Email уведомления

```http
POST /tasks/email/send
Content-Type: application/json

{
  "to": "user@example.com",
  "subject": "Тест",
  "body": "Текст сообщения",
  "priority": "normal"
}
```

#### Обработка файлов

```http
POST /tasks/files/process
Content-Type: application/json

{
  "file_path": "/path/to/file.txt",
  "operation": "analyze",
  "options": {
    "processing_time": 5,
    "file_size": "1MB"
  }
}
```

#### Получение внешних данных

```http
POST /tasks/external/fetch
Content-Type: application/json

{
  "url": "https://api.example.com/data",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer token"
  },
  "timeout": 30
}
```

#### Генерация отчетов

```http
POST /tasks/reports/generate
Content-Type: application/json

{
  "report_type": "sales",
  "date_from": "2024-01-01",
  "date_to": "2024-01-31",
  "format": "pdf",
  "email_to": ["manager@example.com"]
}
```

### Управление задачами

#### Статус задачи

```http
GET /tasks/status/{task_id}
```

#### Результат задачи

```http
GET /tasks/result/{task_id}?timeout=60
```

#### Проверка здоровья

```http
GET /tasks/health
```

#### Список доступных задач

```http
GET /tasks/
```

## Примеры использования

### 1. Через HTTP API

```bash
# Отправка email
curl -X POST "http://localhost:8000/tasks/email/send" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "test@example.com",
    "subject": "Тестовое письмо",
    "body": "Привет из TaskIQ!",
    "priority": "normal"
  }'

# Ответ: {"task_id": "abc123...", "status": "queued", "message": "..."}

# Проверка статуса
curl "http://localhost:8000/tasks/status/abc123..."

# Получение результата
curl "http://localhost:8000/tasks/result/abc123..."
```

### 2. Через Python код

```python
from core.tasks import send_email_notification
from core.taskiq_client import get_task_result

# Запуск задачи
task = await send_email_notification.kiq(
    to="user@example.com",
    subject="Уведомление",
    body="Важное сообщение",
    priority="high"
)

# Получение результата
result = await get_task_result(task.task_id, timeout=60)
print(result.return_value)
```

## Мониторинг

### Логи воркеров

```bash
# Просмотр логов в реальном времени
tail -f app.log

# Поиск ошибок
grep "ERROR" app.log
```

### Проверка Redis

```bash
# Подключение к Redis
redis-cli

# Просмотр очередей TaskIQ
KEYS taskiq:*

# Количество задач в очереди
LLEN taskiq:queue_name
```

### Статистика

```bash
# Проверка здоровья системы
curl http://localhost:8000/tasks/health

# Информация о TaskIQ
python src/cli.py info
```

## Разработка новых задач

### 1. Создание задачи

```python
# В файле core/tasks.py
from core.taskiq_client import broker

@broker.task(task_name="my_custom_task")
async def my_custom_task(param1: str, param2: int) -> dict:
    """Описание задачи."""
    # Логика выполнения
    result = await some_async_operation(param1, param2)

    return {
        "status": "completed",
        "result": result,
        "processed_at": datetime.now().isoformat()
    }
```

### 2. Добавление API endpoint

```python
# В файле core/routes.py
@router.post("/my-task", response_model=TaskResponse)
async def my_task_endpoint(request: MyTaskRequest) -> TaskResponse:
    """Запустить мою задачу."""
    task = await my_custom_task.kiq(
        param1=request.param1,
        param2=request.param2
    )

    return TaskResponse(
        task_id=task.task_id,
        status="queued",
        message="Task queued successfully"
    )
```

### 3. Тестирование

```python
# В tests/test_tasks.py
import pytest
from core.tasks import my_custom_task

@pytest.mark.asyncio
async def test_my_custom_task():
    result = await my_custom_task("test", 42)
    assert result["status"] == "completed"
```

## Производственное развертывание

### 1. Docker Compose

```yaml
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TASKIQ_BROKER_URL=redis://redis:6379/1
    depends_on:
      - redis

  taskiq-worker:
    build: .
    command: python src/cli.py worker --workers 4
    environment:
      - TASKIQ_BROKER_URL=redis://redis:6379/1
    depends_on:
      - redis

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### 2. Systemd сервис

```ini
# /etc/systemd/system/taskiq-worker.service
[Unit]
Description=TaskIQ Worker
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/app
ExecStart=/app/.venv/bin/python src/cli.py worker --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. Мониторинг в продакшене

- **Prometheus** - метрики задач
- **Grafana** - дашборды
- **Sentry** - отслеживание ошибок
- **ELK Stack** - централизованные логи

## Troubleshooting

### Распространенные проблемы

1. **Воркеры не запускаются**

   ```bash
   # Проверьте подключение к Redis
   redis-cli ping

   # Проверьте логи
   python src/cli.py test
   ```

2. **Задачи зависают**

   ```bash
   # Увеличьте таймаут в настройках
   TASKIQ_TASK_TIMEOUT=600
   ```

3. **Память заканчивается**
   ```bash
   # Ограничьте память воркеров
   python src/cli.py worker --max-memory 512
   ```

### Полезные команды

```bash
# Очистка очередей Redis
redis-cli FLUSHDB

# Перезапуск воркеров
killall python
python src/cli.py worker --workers 4

# Проверка конфигурации
python src/cli.py info
```

## Альтернативы и сравнение

### TaskIQ vs Celery

| Функция            | TaskIQ                | Celery              |
| ------------------ | --------------------- | ------------------- |
| Async/await        | ✅ Нативная поддержка | ⚠️ Через celery-aio |
| Типизация          | ✅ Full type hints    | ❌ Частичная        |
| Производительность | ✅ Высокая            | ✅ Высокая          |
| Экосистема         | ❌ Молодая            | ✅ Зрелая           |
| Простота           | ✅ Простая            | ⚠️ Сложная          |

### Дальнейшие улучшения

1. **Планировщик задач** - Cron-like функциональность
2. **Retry политики** - Более гибкие стратегии повторов
3. **Приоритеты** - Очереди с разными приоритетами
4. **Мониторинг** - Веб-интерфейс для управления
5. **Middleware** - Дополнительная логика обработки

## Заключение

TaskIQ клиент интегрирован и готов к использованию. Он предоставляет:

- 🔧 **Готовые задачи** для типовых операций
- 🌐 **HTTP API** для управления
- 💻 **CLI команды** для администрирования
- 📊 **Мониторинг** и логирование
- 🚀 **Масштабируемость** через множественные воркеры

Система спроектирована для легкого расширения и готова к использованию в продакшене.
