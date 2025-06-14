"""
Утилиты для E2E тестов.
"""

import asyncio
from typing import Any

from playwright.async_api import Locator, Page, expect


class PageHelper:
    """Базовый класс для работе со страницами."""

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    async def goto(self, path: str = "/"):
        """Переходит на указанную страницу."""
        url = f"{self.base_url.rstrip('/')}{path}"
        await self.page.goto(url)
        await self.page.wait_for_load_state("networkidle")

    async def wait_for_element(self, selector: str, timeout: int = 5000) -> Locator:
        """Ждет появления элемента."""
        locator = self.page.locator(selector)
        await locator.wait_for(timeout=timeout)
        return locator

    async def fill_form(self, form_data: dict[str, str]):
        """Заполняет форму данными."""
        for field_name, value in form_data.items():
            field = self.page.locator(f'[name="{field_name}"]')
            await field.fill(value)

    async def click_button(self, text: str):
        """Кликает по кнопке с указанным текстом."""
        button = self.page.locator(f'button:has-text("{text}")')
        await button.click()

    async def wait_for_url(self, url_pattern: str, timeout: int = 5000):
        """Ждет изменения URL."""
        await self.page.wait_for_url(url_pattern, timeout=timeout)

    async def take_screenshot(self, name: str):
        """Делает скриншот страницы."""
        await self.page.screenshot(path=f"reports/screenshots/{name}.png")


class AuthHelper(PageHelper):
    """Хелпер для работы с аутентификацией."""

    async def login(self, username: str, password: str):
        """Выполняет вход в систему."""
        await self.goto("/login")

        # Заполняем форму логина
        await self.fill_form({"username": username, "password": password})

        # Нажимаем кнопку входа
        await self.click_button("Войти")

        # Ждем редиректа на главную страницу
        await self.wait_for_url("**/dashboard")

    async def register(self, user_data: dict[str, str]):
        """Выполняет регистрацию нового пользователя."""
        await self.goto("/register")

        # Заполняем форму регистрации
        await self.fill_form(user_data)

        # Нажимаем кнопку регистрации
        await self.click_button("Зарегистрироваться")

        # Ждем подтверждения регистрации
        success_message = await self.wait_for_element(".success-message")
        await expect(success_message).to_be_visible()

    async def logout(self):
        """Выполняет выход из системы."""
        # Кликаем по меню пользователя
        user_menu = self.page.locator('[data-testid="user-menu"]')
        await user_menu.click()

        # Кликаем по кнопке выхода
        logout_button = self.page.locator('button:has-text("Выйти")')
        await logout_button.click()

        # Ждем редиректа на страницу входа
        await self.wait_for_url("**/login")

    async def is_logged_in(self) -> bool:
        """Проверяет, авторизован ли пользователь."""
        try:
            user_menu = self.page.locator('[data-testid="user-menu"]')
            await user_menu.wait_for(timeout=2000)
            return True
        except:
            return False


class APIHelper:
    """Хелпер для работы с API через браузер."""

    def __init__(self, page: Page, api_base_url: str):
        self.page = page
        self.api_base_url = api_base_url

    async def intercept_api_calls(self):
        """Настраивает перехват API вызовов."""
        await self.page.route("**/api/**", self._handle_api_route)

    async def _handle_api_route(self, route):
        """Обработчик API запросов."""
        # Логируем все API запросы
        print(f"API Call: {route.request.method} {route.request.url}")
        await route.continue_()

    async def mock_api_response(self, endpoint: str, response_data: dict[str, Any]):
        """Мокирует ответ API."""
        url_pattern = f"**/api{endpoint}"

        await self.page.route(
            url_pattern,
            lambda route: route.fulfill(status=200, content_type="application/json", body=str(response_data)),
        )

    async def wait_for_api_call(self, endpoint: str, timeout: int = 5000):
        """Ждет вызова определенного API эндпоинта."""
        url_pattern = f"**/api{endpoint}"

        with self.page.expect_request(url_pattern, timeout=timeout) as request_info:
            pass

        return await request_info.value


class NavigationHelper(PageHelper):
    """Хелпер для навигации по приложению."""

    async def go_to_profile(self):
        """Переходит в профиль пользователя."""
        await self.page.locator('a[href="/profile"]').click()
        await self.wait_for_url("**/profile")

    async def go_to_settings(self):
        """Переходит в настройки."""
        await self.page.locator('a[href="/settings"]').click()
        await self.wait_for_url("**/settings")

    async def search(self, query: str):
        """Выполняет поиск."""
        search_input = self.page.locator('[data-testid="search-input"]')
        await search_input.fill(query)
        await search_input.press("Enter")

        # Ждем загрузки результатов
        await self.wait_for_element('[data-testid="search-results"]')


class FormHelper:
    """Хелпер для работы с формами."""

    def __init__(self, page: Page):
        self.page = page

    async def fill_and_submit_form(self, form_selector: str, data: dict[str, str]):
        """Заполняет и отправляет форму."""
        form = self.page.locator(form_selector)

        # Заполняем поля
        for field_name, value in data.items():
            field = form.locator(f'[name="{field_name}"]')
            await field.fill(value)

        # Отправляем форму
        submit_button = form.locator('button[type="submit"]')
        await submit_button.click()

    async def validate_form_errors(self, expected_errors: dict[str, str]):
        """Проверяет ошибки валидации формы."""
        for field_name, expected_error in expected_errors.items():
            error_element = self.page.locator(f'[data-testid="{field_name}-error"]')
            await expect(error_element).to_have_text(expected_error)

    async def clear_form(self, form_selector: str):
        """Очищает все поля формы."""
        form = self.page.locator(form_selector)
        inputs = form.locator("input")

        count = await inputs.count()
        for i in range(count):
            await inputs.nth(i).clear()


# Утилиты для работы с данными


def create_test_user_data(**overrides) -> dict[str, str]:
    """Создает тестовые данные пользователя для E2E тестов."""
    import time

    defaults = {
        "email": f"e2e_test_{int(time.time())}@example.com",
        "username": f"e2e_user_{int(time.time())}",
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "full_name": "E2E Test User",
        "bio": "Created by E2E tests",
    }
    defaults.update(overrides)
    return defaults


async def wait_for_network_idle(page: Page, timeout: int = 5000):
    """Ждет когда сеть станет неактивной."""
    await page.wait_for_load_state("networkidle", timeout=timeout)


async def scroll_to_bottom(page: Page):
    """Прокручивает страницу до конца."""
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")


async def clear_browser_data(page: Page):
    """Очищает данные браузера."""
    context = page.context
    await context.clear_cookies()
    await context.clear_permissions()

    # Очищаем localStorage и sessionStorage
    await page.evaluate("""
        localStorage.clear();
        sessionStorage.clear();
    """)


# Декораторы для E2E тестов


def retry_on_failure(max_attempts: int = 3):
    """Декоратор для повтора теста при падении."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        print(f"Test failed on attempt {attempt + 1}, retrying...")
                        await asyncio.sleep(1)
                    else:
                        raise last_exception

        return wrapper

    return decorator


# Примеры использования:
"""
@pytest.mark.e2e
async def test_user_registration(page: Page, base_url: str):
    auth_helper = AuthHelper(page, base_url)

    user_data = create_test_user_data()
    await auth_helper.register(user_data)

    # Проверяем успешную регистрацию
    assert await auth_helper.is_logged_in()


@pytest.mark.e2e
@retry_on_failure(max_attempts=3)
async def test_user_login(page: Page, base_url: str):
    auth_helper = AuthHelper(page, base_url)

    await auth_helper.login("testuser", "password123")
    assert await auth_helper.is_logged_in()
"""
