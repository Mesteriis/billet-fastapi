# Руководство по E2E тестированию с Playwright

## Введение

Данное руководство описывает, как использовать систему End-to-End (E2E) тестирования с Playwright в нашем проекте. E2E тесты проверяют полный пользовательский workflow от фронтенда до бэкенда.

## Установка и настройка

### 1. Установка зависимостей

```bash
# Установка всех зависимостей
uv sync

# Установка Playwright браузеров
make install-playwright
# или
uv run playwright install chromium
```

### 2. Структура E2E тестов

```
tests/e2e/
├── __init__.py          # Модуль E2E тестов
├── conftest.py          # Конфигурация фикстур
├── utils.py             # Утилиты и хелперы
├── test_auth_flow.py    # Тесты аутентификации
├── test_user_profile.py # Тесты профиля пользователя
└── test_navigation.py   # Тесты навигации
```

## Основные компоненты

### Фикстуры

#### `browser` - Браузер для всей сессии

```python
@pytest.fixture(scope="session")
async def browser() -> AsyncGenerator[Browser, None]:
    # Создает браузер для всех тестов
```

#### `context` - Контекст браузера

```python
@pytest.fixture
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    # Создает изолированный контекст для каждого теста
```

#### `page` - Страница браузера

```python
@pytest.fixture
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    # Создает страницу для теста
```

### Хелперы

#### `PageHelper` - Базовый класс для работы со страницами

```python
page_helper = PageHelper(page, base_url)
await page_helper.goto("/login")
await page_helper.fill_form({"username": "test", "password": "123"})
await page_helper.click_button("Войти")
```

#### `AuthHelper` - Работа с аутентификацией

```python
auth_helper = AuthHelper(page, base_url)
await auth_helper.login("username", "password")
await auth_helper.register(user_data)
await auth_helper.logout()
is_logged = await auth_helper.is_logged_in()
```

#### `APIHelper` - Работа с API через браузер

```python
api_helper = APIHelper(page, api_base_url)
await api_helper.intercept_api_calls()
await api_helper.mock_api_response("/users/me", {"id": 1, "name": "Test"})
```

## Написание тестов

### Базовый тест аутентификации

```python
import pytest
from playwright.async_api import Page
from tests.e2e.utils import AuthHelper, create_test_user_data

@pytest.mark.e2e
async def test_user_login_logout(page: Page, base_url: str):
    """Тест входа и выхода пользователя."""
    auth_helper = AuthHelper(page, base_url)

    # Регистрируем пользователя
    user_data = create_test_user_data()
    await auth_helper.register(user_data)

    # Проверяем успешную авторизацию
    assert await auth_helper.is_logged_in()

    # Выходим
    await auth_helper.logout()

    # Проверяем выход
    assert not await auth_helper.is_logged_in()
```

### Тест с мокированием API

```python
@pytest.mark.e2e
async def test_profile_with_mocked_api(page: Page, base_url: str):
    """Тест профиля с замоканным API."""
    api_helper = APIHelper(page, "http://localhost:8000")
    auth_helper = AuthHelper(page, base_url)

    # Мокируем API ответ
    await api_helper.mock_api_response("/users/me", {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User"
    })

    # Логинимся и переходим в профиль
    await auth_helper.login("testuser", "password123")
    await page.goto("/profile")

    # Проверяем отображение данных
    await expect(page.locator('[data-testid="username"]')).to_have_text("testuser")
    await expect(page.locator('[data-testid="email"]')).to_have_text("test@example.com")
```

### Тест с ретраем

```python
from tests.e2e.utils import retry_on_failure

@pytest.mark.e2e
@retry_on_failure(max_attempts=3)
async def test_flaky_operation(page: Page, base_url: str):
    """Тест с возможными сбоями."""
    # Код теста, который может иногда падать
    pass
```

## Конфигурация тестов

### Настройки браузера

```python
# В conftest.py можно настроить браузер
browser = await p.chromium.launch(
    headless=False,     # Показывать браузер
    slow_mo=100,        # Замедление для отладки
    devtools=True,      # Открыть DevTools
    args=[
        "--start-maximized",
        "--disable-web-security"
    ]
)
```

### Настройки контекста

```python
context = await browser.new_context(
    viewport={"width": 1920, "height": 1080},
    locale="ru-RU",
    timezone_id="Europe/Moscow",
    permissions=["geolocation", "notifications"],
    record_video_dir="reports/videos/",
    record_har_path="reports/network.har"
)
```

## Отладка тестов

### 1. Визуальная отладка

```python
# Включить показ браузера
browser = await p.chromium.launch(headless=False, slow_mo=1000)

# Сделать скриншот
await page.screenshot(path="debug.png")

# Пауза для осмотра
await page.pause()
```

### 2. Логирование

```python
# Логирование консоли браузера
page.on("console", lambda msg: print(f"Console: {msg.text}"))

# Логирование ошибок
page.on("pageerror", lambda error: print(f"Error: {error}"))

# Логирование сетевых запросов
page.on("request", lambda request: print(f"Request: {request.url}"))
page.on("response", lambda response: print(f"Response: {response.url} - {response.status}"))
```

### 3. Ожидание элементов

```python
# Ждать элемент
await page.wait_for_selector('[data-testid="submit-button"]')

# Ждать состояние сети
await page.wait_for_load_state("networkidle")

# Ждать URL
await page.wait_for_url("**/dashboard")

# Кастомное ожидание
await page.wait_for_function("document.readyState === 'complete'")
```

## Запуск тестов

### Команды для запуска

```bash
# Все E2E тесты
make test-e2e

# С конкретным маркером
pytest tests/e2e/ -m smoke -v

# Конкретный файл
pytest tests/e2e/test_auth_flow.py -v

# С показом браузера (для отладки)
pytest tests/e2e/ --headed -v

# С замедлением
pytest tests/e2e/ --slowmo=1000 -v
```

### Переменные окружения

```bash
# Базовый URL фронтенда
export FRONTEND_URL=http://localhost:3000

# API URL
export API_URL=http://localhost:8000

# Режим отладки
export PLAYWRIGHT_DEBUG=1
```

## Best Practices

### 1. Используйте data-testid

```html
<!-- HTML -->
<button data-testid="submit-button">Отправить</button>

<!-- В тесте -->
await page.locator('[data-testid="submit-button"]').click()
```

### 2. Page Object Model

```python
class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.username_input = page.locator('[name="username"]')
        self.password_input = page.locator('[name="password"]')
        self.submit_button = page.locator('[data-testid="login-submit"]')

    async def login(self, username: str, password: str):
        await self.username_input.fill(username)
        await self.password_input.fill(password)
        await self.submit_button.click()
```

### 3. Ожидания вместо sleep

```python
# Плохо
await asyncio.sleep(2)

# Хорошо
await page.wait_for_selector('[data-testid="result"]')
await expect(page.locator('[data-testid="result"]')).to_be_visible()
```

### 4. Независимые тесты

```python
# Каждый тест должен быть независимым
@pytest.fixture(autouse=True)
async def cleanup(page: Page):
    # Подготовка
    yield
    # Очистка после теста
    await clear_browser_data(page)
```

## Интеграция с CI/CD

### GitHub Actions

```yaml
- name: Install Playwright
  run: |
    uv run playwright install chromium

- name: Run E2E tests
  run: |
    make test-e2e
  env:
    FRONTEND_URL: http://localhost:3000
    API_URL: http://localhost:8000
```

### Docker

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Установка зависимостей
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копирование тестов
COPY tests/ tests/

# Запуск тестов
CMD ["pytest", "tests/e2e/", "-v"]
```

## Отчеты и артефакты

### Автоматические скриншоты при падении

```python
@pytest.fixture(autouse=True)
async def screenshot_on_failure(request, page: Page):
    yield

    if request.node.rep_call.failed:
        test_name = request.node.name
        screenshot_path = f"reports/screenshots/{test_name}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
```

### Запись видео

```python
context = await browser.new_context(
    record_video_dir="reports/videos/",
    record_video_size={"width": 1280, "height": 720}
)
```

### HTML отчеты

```bash
pytest tests/e2e/ --html=reports/e2e_report.html --self-contained-html
```

## Troubleshooting

### Частые проблемы

1. **Таймауты**: Увеличьте таймауты для медленных операций
2. **Flaky тесты**: Используйте `retry_on_failure` декоратор
3. **Память**: Закрывайте контексты и страницы после использования
4. **Сеть**: Проверьте доступность API и фронтенда

### Полезные команды

```bash
# Генерация кода теста
playwright codegen http://localhost:3000

# Отладка селекторов
playwright open --debug http://localhost:3000

# Трассировка
playwright show-trace trace.zip
```

## Заключение

E2E тесты с Playwright обеспечивают высокое качество пользовательского опыта. Следуйте этому руководству для эффективного тестирования вашего веб-приложения.

Для получения дополнительной информации обратитесь к [официальной документации Playwright](https://playwright.dev/python/).
