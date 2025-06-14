# Интеграция Telegram ботов с aiogram

Система поддерживает работу с несколькими Telegram ботами одновременно, как в режиме polling, так и в режиме webhook. Построена на основе aiogram 3.x.

## Возможности

- ✅ Поддержка нескольких ботов одновременно
- ✅ Режимы работы: polling и webhook
- ✅ Декораторы для удобного создания команд
- ✅ Система шаблонов сообщений с Jinja2
- ✅ Контроль доступа и безопасность
- ✅ Middleware для лимитирования запросов
- ✅ Административные команды
- ✅ Интеграция с Redis для FSM
- ✅ Автоматическая регистрация команд
- ✅ Полное покрытие тестами

## Архитектура

```
src/telegram/
├── __init__.py          # Основные экспорты
├── config.py            # Конфигурация ботов
├── manager.py           # Менеджер ботов
├── decorators.py        # Декораторы для команд
├── templates.py         # Система шаблонов
└── handlers/
    ├── __init__.py
    ├── basic.py         # Базовые команды
    └── admin.py         # Административные команды
```

## Быстрый старт

### 1. Настройка переменных окружения

```env
# Включение системы ботов
TELEGRAM_BOTS_ENABLED=true

# Основной бот (polling)
TELEGRAM_BOT_MAIN_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_BOT_MAIN_MODE=polling

# Дополнительный бот (webhook)
TELEGRAM_BOT_SECONDARY_TOKEN=789012:XYZ-GHI5678jklMn-abc90X3y2z456fg22
TELEGRAM_BOT_SECONDARY_MODE=webhook
TELEGRAM_BOT_SECONDARY_WEBHOOK_URL=https://your-domain.com
TELEGRAM_BOT_SECONDARY_WEBHOOK_PATH=/webhook/secondary

# Настройки безопасности
TELEGRAM_ADMIN_USERS=123456789,987654321
TELEGRAM_ALLOWED_USERS=123456789,987654321,555666777

# Redis для FSM (опционально)
TELEGRAM_REDIS_HOST=localhost
TELEGRAM_REDIS_PORT=6379
TELEGRAM_REDIS_DB=3
```

### 2. Создание команд

```python
# src/telegram/handlers/custom.py
from core.telegram.decorators import command, rate_limit, admin_only
from core.telegram.templates import render_template
from aiogram.types import Message


@command("hello", description="Приветствие пользователя")
@rate_limit(calls=5, period=60)
async def cmd_hello(message: Message):
    """Команда приветствия."""
    user = message.from_user
    response = render_template(
        "welcome",
        user={"first_name": user.first_name}
    )
    await message.answer(response or f"Привет, {user.first_name}!")


@command("admin_panel", description="Административная панель", admin_only=True)
async def cmd_admin_panel(message: Message):
    """Административная панель."""
    await message.answer("🔧 Добро пожаловать в админ панель!")


@command("stats", description="Статистика", allowed_users=[123456789])
async def cmd_stats(message: Message):
    """Статистика только для определенных пользователей."""
    await message.answer("📊 Статистика загружается...")
```

### 3. Создание шаблонов

Создайте файл `telegram/templates/custom_welcome.j2`:

```jinja2
{# description: Кастомное приветствие #}
{# parse_mode: HTML #}

🎉 <b>Добро пожаловать, {{ user.first_name }}!</b>

📅 Дата регистрации: {{ registration_date|default('сегодня') }}
🏆 Ваш уровень: {{ user_level|default('новичок') }}

{% if is_premium %}
⭐ У вас премиум аккаунт!
{% endif %}

Доступные команды:
{% for command in available_commands %}
• {{ command }}
{% endfor %}
```

### 4. Запуск приложения

```bash
# Установка зависимостей
uv sync

# Запуск с включенными ботами
TELEGRAM_BOTS_ENABLED=true uvicorn src.main:app --reload
```

## Конфигурация

### Основные настройки

| Параметр                 | Описание               | По умолчанию         |
| ------------------------ | ---------------------- | -------------------- |
| `TELEGRAM_BOTS_ENABLED`  | Включить систему ботов | `false`              |
| `TELEGRAM_DEBUG`         | Отладочный режим       | `false`              |
| `TELEGRAM_LOG_LEVEL`     | Уровень логирования    | `INFO`               |
| `TELEGRAM_TEMPLATES_DIR` | Директория шаблонов    | `telegram/templates` |

### Настройки безопасности

| Параметр                 | Описание                            |
| ------------------------ | ----------------------------------- |
| `TELEGRAM_ALLOWED_USERS` | Список ID разрешенных пользователей |
| `TELEGRAM_ALLOWED_CHATS` | Список ID разрешенных чатов         |
| `TELEGRAM_ADMIN_USERS`   | Список ID администраторов           |

### Настройки лимитирования

| Параметр                         | Описание          | По умолчанию |
| -------------------------------- | ----------------- | ------------ |
| `TELEGRAM_RATE_LIMIT_PER_MINUTE` | Запросов в минуту | `60`         |
| `TELEGRAM_RATE_LIMIT_PER_HOUR`   | Запросов в час    | `500`        |

### Настройки конкретного бота

Формат: `TELEGRAM_BOT_{NAME}_{PARAMETER}`

```env
# Бот с именем "support"
TELEGRAM_BOT_SUPPORT_TOKEN=your_bot_token
TELEGRAM_BOT_SUPPORT_MODE=polling
TELEGRAM_BOT_SUPPORT_POLLING_TIMEOUT=30
TELEGRAM_BOT_SUPPORT_PARSE_MODE=HTML
```

## Декораторы

### @command

Регистрирует команду бота:

```python
@command("test", description="Тестовая команда", admin_only=True)
async def cmd_test(message: Message):
    await message.answer("Тест!")
```

Параметры:

- `cmd`: имя команды (без /)
- `description`: описание для /help
- `admin_only`: только для администраторов
- `allowed_users`: список разрешенных пользователей
- `allowed_chats`: список разрешенных чатов

### @rate_limit

Ограничивает частоту вызовов:

```python
@rate_limit(calls=5, period=60)  # 5 раз в минуту
async def limited_handler(message: Message):
    pass
```

### @message_handler

Обрабатывает сообщения по типу контента:

```python
@message_handler(content_types=["photo"])
async def handle_photo(message: Message):
    await message.answer("Получена фотография!")
```

### @callback_handler

Обрабатывает нажатия inline кнопок:

```python
@callback_handler("button_data")
async def handle_button(callback: CallbackQuery):
    await callback.answer("Кнопка нажата!")
```

## Система шаблонов

### Создание шаблона

```python
from core.telegram.templates import MessageTemplate, get_template_manager

template = MessageTemplate(
    name="notification",
    template="🔔 {{ title }}\n\n{{ message }}",
    description="Шаблон уведомлений",
    variables={"title": "Уведомление"}
)

# Добавляем в менеджер
manager = get_template_manager()
manager.add_template(template)
```

### Использование в коде

```python
from core.telegram.templates import render_template

# Простой рендер
message_text = render_template("welcome", user_name="Иван")

# С дополнительными переменными
message_text = render_template(
    "notification",
    title="Важное сообщение",
    message="Система будет недоступна с 22:00 до 23:00"
)
```

### Шаблоны по умолчанию

Система создает следующие шаблоны:

- `welcome` - приветствие
- `help` - справка по командам
- `error` - сообщение об ошибке
- `success` - сообщение об успехе
- `loading` - сообщение о загрузке
- `admin_only` - доступ запрещен

## Административные команды

Доступны только пользователям из `TELEGRAM_ADMIN_USERS`:

- `/admin` - панель администратора
- `/broadcast <сообщение>` - рассылка всем админам
- `/logs` - просмотр логов
- `/restart_bots` - перезапуск ботов
- `/create_template` - создание шаблона
- `/delete_template` - удаление шаблона

## Middleware и безопасность

Система автоматически применяет проверки:

1. **Разрешенные пользователи** - проверка `TELEGRAM_ALLOWED_USERS`
2. **Разрешенные чаты** - проверка `TELEGRAM_ALLOWED_CHATS`
3. **Администраторы** - проверка `TELEGRAM_ADMIN_USERS`
4. **Лимитирование** - защита от спама
5. **Обработка ошибок** - автоматические ответы об ошибках

## Webhook vs Polling

### Polling (рекомендуется для разработки)

```env
TELEGRAM_BOT_MYBOT_TOKEN=your_token
TELEGRAM_BOT_MYBOT_MODE=polling
TELEGRAM_BOT_MYBOT_POLLING_TIMEOUT=20
```

Преимущества:

- Простая настройка
- Не требует внешнего домена
- Подходит для разработки

### Webhook (рекомендуется для продакшена)

```env
TELEGRAM_BOT_MYBOT_TOKEN=your_token
TELEGRAM_BOT_MYBOT_MODE=webhook
TELEGRAM_BOT_MYBOT_WEBHOOK_URL=https://your-domain.com
TELEGRAM_BOT_MYBOT_WEBHOOK_PATH=/webhook/mybot
TELEGRAM_BOT_MYBOT_WEBHOOK_SECRET=your_secret_key
```

Преимущества:

- Мгновенное получение сообщений
- Масштабируемость
- Меньше нагрузки на API

## Интеграция с Redis

Для FSM (машины состояний) и кеширования:

```env
TELEGRAM_REDIS_HOST=localhost
TELEGRAM_REDIS_PORT=6379
TELEGRAM_REDIS_DB=3
TELEGRAM_REDIS_PASSWORD=your_password
```

Пример FSM:

```python
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()

@command("register", description="Регистрация")
async def cmd_register(message: Message, state: FSMContext):
    await message.answer("Как вас зовут?")
    await state.set_state(RegistrationStates.waiting_name)

@message_handler()
async def process_name(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == RegistrationStates.waiting_name:
        await state.update_data(name=message.text)
        await message.answer("Сколько вам лет?")
        await state.set_state(RegistrationStates.waiting_age)
```

## Мониторинг и логирование

Система автоматически логирует:

- Запуск/остановку ботов
- Ошибки обработки команд
- Нарушения лимитов
- Административные действия

Уровни логирования:

- `DEBUG` - подробная отладка
- `INFO` - основные события
- `WARNING` - предупреждения
- `ERROR` - ошибки

## Развертывание

### Docker

```dockerfile
FROM python:3.13-slim

COPY . /app
WORKDIR /app

RUN pip install uv && uv sync

ENV TELEGRAM_BOTS_ENABLED=true
EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment variables

```env
# Основные настройки
TELEGRAM_BOTS_ENABLED=true
TELEGRAM_WEBHOOK_BASE_URL=https://your-domain.com

# Боты
TELEGRAM_BOT_MAIN_TOKEN=your_main_bot_token
TELEGRAM_BOT_SUPPORT_TOKEN=your_support_bot_token

# Безопасность
TELEGRAM_ADMIN_USERS=123456789
TELEGRAM_ALLOWED_USERS=123456789,987654321

# Redis
TELEGRAM_REDIS_HOST=redis
TELEGRAM_REDIS_PORT=6379
```

## Тестирование

Запуск тестов:

```bash
# Все тесты
pytest tests/test_telegram/

# Конкретный модуль
pytest tests/test_telegram/test_config.py

# С покрытием
pytest tests/test_telegram/ --cov=src.telegram
```

## Примеры использования

### Бот поддержки

```python
@command("ticket", description="Создать заявку в поддержку")
async def cmd_create_ticket(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐛 Баг", callback_data="ticket_bug")],
        [InlineKeyboardButton(text="💡 Предложение", callback_data="ticket_feature")],
        [InlineKeyboardButton(text="❓ Вопрос", callback_data="ticket_question")]
    ])

    await message.answer(
        "🎫 Выберите тип заявки:",
        reply_markup=keyboard
    )

@callback_handler("ticket_bug")
async def handle_bug_ticket(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🐛 Опишите проблему подробно. "
        "Заявка будет отправлена в техподдержку."
    )
```

### Информационный бот

```python
@command("weather", description="Погода в городе")
async def cmd_weather(message: Message):
    # Получаем город из сообщения
    city = message.text.split(' ', 1)[1] if ' ' in message.text else "Москва"

    # Здесь бы был запрос к API погоды
    weather_info = {
        "city": city,
        "temperature": "+15°C",
        "description": "Облачно",
        "humidity": "65%"
    }

    response = render_template("weather", **weather_info)
    await message.answer(response)
```

### Уведомления

```python
from core.telegram import get_bot_manager


async def send_notification(user_id: int, message: str):
    """Отправка уведомления конкретному пользователю."""
    bot_manager = get_bot_manager()

    # Отправляем через первого доступного бота
    for bot_instance in bot_manager.bots.values():
        try:
            await bot_instance.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML"
            )
            break
        except Exception as e:
            continue
```

## Лучшие практики

1. **Безопасность**: всегда используйте `TELEGRAM_ALLOWED_USERS` в продакшене
2. **Лимитирование**: применяйте `@rate_limit` к ресурсоемким командам
3. **Шаблоны**: выносите тексты сообщений в шаблоны для удобства локализации
4. **Логирование**: используйте встроенное логирование для мониторинга
5. **Тестирование**: покрывайте тестами пользовательские команды
6. **Webhook**: используйте webhook в продакшене для лучшей производительности

## Troubleshooting

### Боты не запускаются

1. Проверьте `TELEGRAM_BOTS_ENABLED=true`
2. Убедитесь в правильности токенов
3. Проверьте логи на ошибки инициализации

### Webhook не работает

1. Проверьте доступность URL извне
2. Убедитесь в корректности `TELEGRAM_WEBHOOK_BASE_URL`
3. Проверьте SSL сертификат

### Команды не регистрируются

1. Убедитесь в правильности импортов обработчиков
2. Проверьте синтаксис декораторов
3. Посмотрите логи на ошибки регистрации

### Redis подключение

1. Проверьте доступность Redis сервера
2. Убедитесь в правильности настроек подключения
3. Проверьте права доступа к базе данных
