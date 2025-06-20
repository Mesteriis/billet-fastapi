# 📚 Интерактивная документация с Jupyter Notebooks

Добро пожаловать в интерактивную документацию проекта! Здесь вы найдете live примеры кода, которые можно запускать и изменять прямо в браузере.

## 🚀 Быстрый старт

### Установка зависимостей

```bash
# Установка Jupyter и дополнительных зависимостей
pip install notebook jupyterlab ipywidgets
# или
uv add --dev notebook jupyterlab ipywidgets

# Запуск Jupyter Lab
jupyter lab notebooks/
```

### Альтернативный запуск

```bash
# Через make команду
make jupyter

# Или напрямую
cd notebooks && jupyter notebook
```

## 📖 Доступные notebooks

### 🎯 Быстрый старт

- [`quickstart/01_project_overview.ipynb`](quickstart/01_project_overview.ipynb) - Обзор проекта и основные концепции
- [`quickstart/02_first_api.ipynb`](quickstart/02_first_api.ipynb) - Создание первого API endpoint
- [`quickstart/03_database_setup.ipynb`](quickstart/03_database_setup.ipynb) - Настройка базы данных

### 🔐 Аутентификация

- [`auth/01_user_registration.ipynb`](auth/01_user_registration.ipynb) - Регистрация пользователей
- [`auth/02_jwt_tokens.ipynb`](auth/02_jwt_tokens.ipynb) - Работа с JWT токенами
- [`auth/03_protected_endpoints.ipynb`](auth/03_protected_endpoints.ipynb) - Защищенные endpoints
- [`auth/04_role_based_access.ipynb`](auth/04_role_based_access.ipynb) - Ролевая модель доступа

### 🔄 Realtime система

- [`realtime/01_websocket_basics.ipynb`](realtime/01_websocket_basics.ipynb) - Основы WebSocket
- [`realtime/02_sse_streaming.ipynb`](realtime/02_sse_streaming.ipynb) - Server-Sent Events
- [`realtime/03_chat_application.ipynb`](realtime/03_chat_application.ipynb) - Создание чат-приложения
- [`realtime/04_webrtc_signaling.ipynb`](realtime/04_webrtc_signaling.ipynb) - WebRTC сигналинг

### 💾 База данных

- [`database/01_models_and_schemas.ipynb`](database/01_models_and_schemas.ipynb) - Модели и схемы
- [`database/02_repository_pattern.ipynb`](database/02_repository_pattern.ipynb) - Паттерн Repository
- [`database/03_migrations.ipynb`](database/03_migrations.ipynb) - Миграции Alembic
- [`database/04_bulk_operations.ipynb`](database/04_bulk_operations.ipynb) - Массовые операции

### 🧪 Тестирование

- [`testing/01_unit_tests.ipynb`](testing/01_unit_tests.ipynb) - Unit тестирование
- [`testing/02_integration_tests.ipynb`](testing/02_integration_tests.ipynb) - Интеграционные тесты
- [`testing/03_api_client.ipynb`](testing/03_api_client.ipynb) - AsyncApiTestClient
- [`testing/04_data_factories.ipynb`](testing/04_data_factories.ipynb) - Фабрики данных

### 📝 Примеры

- [`examples/01_crud_operations.ipynb`](examples/01_crud_operations.ipynb) - CRUD операции
- [`examples/02_messaging_system.ipynb`](examples/02_messaging_system.ipynb) - Система сообщений
- [`examples/03_background_tasks.ipynb`](examples/03_background_tasks.ipynb) - Фоновые задачи
- [`examples/04_telegram_bot.ipynb`](examples/04_telegram_bot.ipynb) - Telegram бот

## 🛠️ Настройка окружения

### Переменные окружения

Создайте файл `.env` в корне проекта:

```bash
# Копирование примера
cp .env.example .env

# Или создание минимального .env для notebooks
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/fastapi_db
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=fastapi_db
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
REDIS_URL=redis://localhost:6379/0
EOF
```

### Зависимости

```bash
# Основные зависимости проекта
pip install -r requirements.txt

# Дополнительные зависимости для notebooks
pip install matplotlib seaborn plotly pandas
```

## 🐳 Docker для Notebooks

### Запуск инфраструктуры

```bash
# Запуск PostgreSQL, RabbitMQ, Redis
docker-compose up -d postgres rabbitmq redis

# Проверка статуса
docker-compose ps
```

### Jupyter в Docker

```dockerfile
# Dockerfile.jupyter
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install notebook jupyterlab

COPY . .
EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--allow-root", "--no-browser"]
```

```bash
# Сборка и запуск
docker build -f Dockerfile.jupyter -t fastapi-jupyter .
docker run -p 8888:8888 -v $(pwd):/app fastapi-jupyter
```

## 🎨 Интерактивные виджеты

Notebooks используют ipywidgets для создания интерактивных элементов:

```python
import ipywidgets as widgets
from IPython.display import display

# Интерактивный выбор endpoint
endpoint_dropdown = widgets.Dropdown(
    options=['users', 'auth', 'realtime'],
    description='Endpoint:'
)

# Кнопка выполнения
run_button = widgets.Button(description='Выполнить запрос')

# Область вывода
output = widgets.Output()

display(endpoint_dropdown, run_button, output)
```

## 📊 Визуализация данных

### Графики производительности

```python
import matplotlib.pyplot as plt
import pandas as pd

# График времени ответа API
response_times = [120, 95, 110, 87, 134, 99, 105]
plt.plot(response_times)
plt.title('Время ответа API (мс)')
plt.xlabel('Запрос')
plt.ylabel('Время (мс)')
plt.show()
```

### Мониторинг соединений

```python
import plotly.graph_objects as go

# Реальная диаграмма WebSocket соединений
fig = go.Figure()
fig.add_trace(go.Scatter(x=timestamps, y=connections, name='WebSocket'))
fig.add_trace(go.Scatter(x=timestamps, y=sse_connections, name='SSE'))
fig.show()
```

## 🔧 Полезные команды

### Конвертация notebooks

```bash
# Конвертация в HTML
jupyter nbconvert --to html notebooks/quickstart/01_project_overview.ipynb

# Конвертация в Python
jupyter nbconvert --to python notebooks/auth/01_user_registration.ipynb

# Конвертация всех notebooks
find notebooks -name "*.ipynb" -exec jupyter nbconvert --to html {} \;
```

### Очистка вывода

```bash
# Очистка всех выводов
jupyter nbconvert --clear-output --inplace notebooks/**/*.ipynb

# Или через git hooks
echo "jupyter nbconvert --clear-output --inplace notebooks/**/*.ipynb" > .git/hooks/pre-commit
```

## 📚 Обучающие материалы

### Уровни сложности

- 🟢 **Начинающий** - Quickstart notebooks
- 🟡 **Средний** - Auth и Database notebooks
- 🔴 **Продвинутый** - Realtime и Testing notebooks

### Рекомендуемый порядок изучения

1. **Знакомство с проектом** → `quickstart/01_project_overview.ipynb`
2. **Первые шаги** → `quickstart/02_first_api.ipynb`
3. **База данных** → `database/01_models_and_schemas.ipynb`
4. **Аутентификация** → `auth/01_user_registration.ipynb`
5. **Тестирование** → `testing/01_unit_tests.ipynb`
6. **Realtime** → `realtime/01_websocket_basics.ipynb`

### Интерактивные туториалы

Каждый notebook содержит:

- ✅ Теоретическое введение
- 🔧 Практические примеры
- 💡 Упражнения для самостоятельной работы
- 🎯 Чек-лист для проверки понимания

## 🤝 Участие в разработке

### Создание новых notebooks

1. Скопируйте шаблон из `templates/notebook_template.ipynb`
2. Следуйте структуре: Введение → Примеры → Упражнения → Заключение
3. Добавьте интерактивные элементы
4. Протестируйте все примеры кода

### Шаблон структуры notebook

```markdown
# Заголовок урока

## 📚 Что вы изучите

- Пункт 1
- Пункт 2

## 🎯 Предварительные требования

- Знание Python
- Установленный проект

## 💡 Теория

Объяснение концепций

## 🔧 Практика

Живые примеры кода

## 🏆 Упражнения

Задания для самостоятельной работы

## ✅ Чек-лист

- [ ] Понимаю концепцию X
- [ ] Могу реализовать Y
```

## 🔗 Ссылки

- [Jupyter Documentation](https://jupyter.org/documentation)
- [IPython Widgets](https://ipywidgets.readthedocs.io/)
- [Plotly Python](https://plotly.com/python/)
- [Matplotlib](https://matplotlib.org/)

---

**Приятного обучения! 🚀**

_Если у вас есть вопросы или предложения по улучшению notebooks, создайте issue в репозитории._
