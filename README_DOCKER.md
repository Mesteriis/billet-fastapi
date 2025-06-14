# 🐳 Docker Configuration для FastAPI проекта

Полноценная Docker конфигурация со всеми сервисами, лучшими практиками и multistage build.

## 📋 Обзор архитектуры

### Сервисы

- **FastAPI App** - основное приложение (4 воркера в production)
- **TaskIQ Worker** - обработка фоновых задач (2-4 инстанса)
- **Messaging Service** - FastStream + RabbitMQ (2-3 инстанса)
- **PostgreSQL** - основная база данных
- **Redis** - кэширование, сессии, TaskIQ broker/результаты
- **RabbitMQ** - система сообщений
- **Nginx** - reverse proxy, load balancer
- **Jaeger** - OpenTelemetry трассировка
- **Migration** - автоматические миграции БД

### Production мониторинг

- **Prometheus** - сбор метрик
- **Grafana** - визуализация метрик
- **Loki** - сбор логов
- **Promtail** - агент логов
- **Node Exporter** - системные метрики

## 🚀 Быстрый старт

### 1. Подготовка

```bash
# Клонируем проект
git clone <repository-url>
cd blank-fastapi-projects

# Копируем конфигурацию
cp docker.env.example .env

# Редактируем переменные окружения
nano .env
```

### 2. Разработка

```bash
# Запуск всех сервисов для разработки
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Или только инфраструктура (для локальной разработки)
docker-compose up -d postgres redis rabbitmq

# Проверка логов
docker-compose logs -f app
```

### 3. Production

```bash
# Сборка и запуск production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# С мониторингом и Nginx
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile nginx up -d
```

## 📁 Структура файлов

```
.
├── Dockerfile                    # Multistage Dockerfile
├── docker-compose.yml           # Основная конфигурация
├── docker-compose.dev.yml       # Настройки разработки
├── docker-compose.prod.yml      # Production конфигурация
├── .dockerignore                # Исключения для Docker build
├── docker.env.example           # Пример переменных окружения
└── config/                      # Конфигурационные файлы
    ├── nginx/
    │   └── nginx.conf           # Nginx конфигурация
    ├── rabbitmq/
    │   ├── rabbitmq.conf        # RabbitMQ настройки
    │   └── enabled_plugins      # Включенные плагины
    └── scripts/
        └── postgres/
            └── dev-init.sql     # Инициализация PostgreSQL
```

## 🔧 Multistage Dockerfile

### Stages:

1. **base** - базовый образ с системными зависимостями
2. **deps-builder** - сборка Python зависимостей
3. **development** - режим разработки с dev зависимостями
4. **production-deps** - оптимизированные production зависимости
5. **production** - финальный production образ
6. **taskiq-worker** - специализированный воркер
7. **messaging-service** - сервис сообщений
8. **migration** - контейнер для миграций

### Оптимизации:

- ✅ Многоэтапная сборка для минимизации размера
- ✅ Непривилегированный пользователь
- ✅ Кэширование слоев Docker
- ✅ Оптимизированные зависимости
- ✅ Health checks для всех сервисов
- ✅ Правильные COPY инструкции
- ✅ Очистка временных файлов

## 🌐 Сети и volumes

### Сети:

- `fastapi-network` - основная сеть приложения
- `monitoring-network` - изолированная сеть мониторинга

### Volumes:

- `postgres_data` - данные PostgreSQL
- `redis_data` - данные Redis
- `rabbitmq_data` - данные RabbitMQ
- `app_logs` - логи приложения
- `app_reports` - отчеты тестирования
- `prometheus_data` - метрики Prometheus
- `grafana_data` - конфигурация Grafana

## 🔍 Мониторинг и логирование

### Доступные интерфейсы:

| Сервис              | URL                        | Описание             |
| ------------------- | -------------------------- | -------------------- |
| FastAPI App         | http://localhost:8000      | Основное приложение  |
| FastAPI Docs        | http://localhost:8000/docs | API документация     |
| RabbitMQ Management | http://localhost:15672     | Управление очередями |
| Prometheus          | http://localhost:9090      | Метрики              |
| Grafana             | http://localhost:3000      | Дашборды             |
| Jaeger              | http://localhost:16686     | Трассировка          |
| Adminer             | http://localhost:8080      | Управление БД        |
| Redis Commander     | http://localhost:8081      | Управление Redis     |

### Credentials по умолчанию:

- **RabbitMQ**: guest/guest
- **Grafana**: admin/admin123
- **Redis Commander**: admin/admin123

## 📊 Команды управления

### Основные команды:

```bash
# Полная сборка с нуля
docker-compose build --no-cache

# Запуск конкретного профиля
docker-compose --profile dev up -d
docker-compose --profile nginx up -d
docker-compose --profile test up -d

# Масштабирование сервисов
docker-compose up -d --scale taskiq-worker=4
docker-compose up -d --scale messaging-service=3

# Просмотр логов
docker-compose logs -f app
docker-compose logs -f --tail=100 taskiq-worker

# Выполнение команд в контейнере
docker-compose exec app bash
docker-compose exec postgres psql -U postgres -d mango_msg

# Остановка и очистка
docker-compose down
docker-compose down -v  # С удалением volumes
```

### Миграции:

```bash
# Применение миграций
docker-compose run --rm migration

# Создание новой миграции
docker-compose exec app python -m alembic revision --autogenerate -m "Description"

# Статус миграций
docker-compose exec app python -m alembic current
```

### Тестирование:

```bash
# Запуск тестов в контейнере
docker-compose --profile test run --rm test

# Запуск конкретных тестов
docker-compose exec app pytest tests/test_auth.py -v

# Генерация отчета покрытия
docker-compose exec app pytest --cov=src --cov-report=html
```

## 🔧 Конфигурация окружений

### Переменные окружения (.env):

```bash
# Основные настройки
ENVIRONMENT=production
SECRET_KEY=your-super-secret-key

# База данных
POSTGRES_PASSWORD=secure_password

# Компоненты
WEBSOCKET_ENABLED=true
SSE_ENABLED=true
TELEGRAM_BOTS_ENABLED=false
TRACING_ENABLED=true

# CORS
CORS_ORIGINS=https://yourdomain.com
```

### Примеры запуска:

```bash
# Локальная разработка
ENVIRONMENT=development docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Staging
ENVIRONMENT=staging docker-compose up -d

# Production с мониторингом
ENVIRONMENT=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 🛡️ Безопасность

### Реализованные меры:

- ✅ Непривилегированный пользователь в контейнерах
- ✅ Минимальные attack surface (alpine образы)
- ✅ Secrets через переменные окружения
- ✅ Изолированные сети
- ✅ Health checks для early detection
- ✅ Resource limits для предотвращения DoS
- ✅ Rate limiting в Nginx
- ✅ SSL/TLS поддержка

### Рекомендации:

1. Смените все пароли по умолчанию
2. Используйте Docker secrets в production
3. Настройте firewall правила
4. Регулярно обновляйте образы
5. Мониторьте логи безопасности

## 🚀 Production deployment

### 1. Подготовка сервера:

```bash
# Установка Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Настройка пользователя
sudo usermod -aG docker $USER

# Настройка логов Docker
sudo nano /etc/docker/daemon.json
```

### 2. Конфигурация production:

```bash
# Клонирование проекта
git clone <repository-url>
cd blank-fastapi-projects

# Настройка переменных
cp docker.env.example .env
nano .env  # Установите production значения

# SSL сертификаты (если используются)
mkdir -p config/nginx/ssl
# Копируйте cert.pem и key.pem
```

### 3. Запуск:

```bash
# Сборка образов
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Запуск миграций
docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm migration

# Запуск всех сервисов
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Проверка состояния
docker-compose ps
docker-compose logs app
```

## 📈 Масштабирование

### Горизонтальное масштабирование:

```bash
# Увеличение количества воркеров
docker-compose up -d --scale app=6
docker-compose up -d --scale taskiq-worker=8
docker-compose up -d --scale messaging-service=4
```

### Вертикальное масштабирование:

Отредактируйте `docker-compose.prod.yml` для увеличения лимитов ресурсов:

```yaml
deploy:
  resources:
    limits:
      cpus: "4.0"
      memory: 2G
```

## 🐛 Troubleshooting

### Общие проблемы:

1. **Контейнеры не запускаются**:

   ```bash
   docker-compose logs <service_name>
   docker-compose ps
   ```

2. **Проблемы с сетью**:

   ```bash
   docker network ls
   docker network inspect fastapi-project_fastapi-network
   ```

3. **Проблемы с volumes**:

   ```bash
   docker volume ls
   docker volume inspect fastapi-project_postgres_data
   ```

4. **Очистка и переустановка**:
   ```bash
   docker-compose down -v
   docker system prune -a
   docker-compose build --no-cache
   ```

### Производительность:

```bash
# Мониторинг ресурсов
docker stats

# Анализ образов
docker images
docker history fastapi-project_app

# Профилирование сети
docker-compose exec app netstat -an
```

## 🔄 Backup и восстановление

### PostgreSQL:

```bash
# Создание бэкапа
docker-compose exec postgres pg_dump -U postgres mango_msg > backup.sql

# Восстановление
docker-compose exec -T postgres psql -U postgres mango_msg < backup.sql
```

### Redis:

```bash
# Сохранение снапшота
docker-compose exec redis redis-cli BGSAVE

# Копирование данных
docker cp container_id:/data/dump.rdb ./redis_backup.rdb
```

## 🎯 Альтернативы и улучшения

### Возможные улучшения:

1. **Kubernetes deployment** - для enterprise масштабирования
2. **Docker Swarm** - для простой кластеризации
3. **External load balancer** - HAProxy/AWS ALB
4. **External monitoring** - DataDog/New Relic
5. **CI/CD интеграция** - GitHub Actions/GitLab CI
6. **Multi-region deployment** - для высокой доступности

### Дополнительные сервисы:

```yaml
# Возможные дополнения в docker-compose:
- ElasticSearch + Kibana (логирование)
- InfluxDB (time-series метрики)
- Consul (service discovery)
- Vault (secrets management)
- MinIO (S3-compatible storage)
```

---

**Документация актуальна на:** 2024  
**Автор:** Alexander Mescheryakov  
**Версия Docker:** 24+  
**Версия Docker Compose:** 3.8+
