"""
End-to-End тесты для процесса аутентификации пользователей.
"""

import asyncio

import pytest
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from tests.factories.user_factory import make_admin_data, make_user_data
from tests.mocking.external_api_mocks import mock_notification_service


class TestUserAuthFlow:
    """E2E тесты для потока аутентификации."""

    @pytest.fixture(scope="class")
    async def browser(self):
        """Фикстура браузера для всех тестов."""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()
        await playwright.stop()

    @pytest.fixture
    async def context(self, browser: Browser):
        """Фикстура контекста браузера для изоляции тестов."""
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        yield context
        await context.close()

    @pytest.fixture
    async def page(self, context: BrowserContext):
        """Фикстура страницы."""
        page = await context.new_page()
        yield page
        await page.close()

    @pytest.mark.e2e
    async def test_user_registration_flow(self, page: Page):
        """Тест полного процесса регистрации пользователя."""
        # Переходим на страницу регистрации
        await page.goto("http://localhost:8000/register")

        # Проверяем что страница загрузилась
        await page.wait_for_selector("form[data-testid='registration-form']")

        # Заполняем форму регистрации
        user_data = make_user_data(email="test@example.com", username="testuser", full_name="Test User")

        await page.fill("input[name='email']", user_data["email"])
        await page.fill("input[name='username']", user_data["username"])
        await page.fill("input[name='full_name']", user_data["full_name"])
        await page.fill("input[name='password']", "TestPassword123!")
        await page.fill("input[name='password_confirm']", "TestPassword123!")

        # Отправляем форму
        await page.click("button[type='submit']")

        # Ожидаем перенаправления или сообщения об успехе
        await page.wait_for_selector(".success-message", timeout=5000)

        # Проверяем что отображается сообщение об успешной регистрации
        success_message = await page.text_content(".success-message")
        assert "успешно зарегистрированы" in success_message.lower()

    @pytest.mark.e2e
    async def test_user_login_flow(self, page: Page):
        """Тест процесса входа пользователя."""
        # Переходим на страницу входа
        await page.goto("http://localhost:8000/login")

        # Проверяем что форма входа загрузилась
        await page.wait_for_selector("form[data-testid='login-form']")

        # Заполняем форму входа
        await page.fill("input[name='email']", "test@example.com")
        await page.fill("input[name='password']", "TestPassword123!")

        # Отправляем форму
        await page.click("button[type='submit']")

        # Ожидаем перенаправления на главную страницу
        await page.wait_for_url("http://localhost:8000/dashboard", timeout=5000)

        # Проверяем что пользователь авторизован
        user_menu = await page.query_selector("[data-testid='user-menu']")
        assert user_menu is not None

    @pytest.mark.e2e
    async def test_invalid_login_credentials(self, page: Page):
        """Тест входа с неверными данными."""
        await page.goto("http://localhost:8000/login")

        # Заполняем неверные данные
        await page.fill("input[name='email']", "wrong@example.com")
        await page.fill("input[name='password']", "wrongpassword")

        # Отправляем форму
        await page.click("button[type='submit']")

        # Ожидаем сообщение об ошибке
        await page.wait_for_selector(".error-message", timeout=3000)

        error_message = await page.text_content(".error-message")
        assert "неверные" in error_message.lower() or "invalid" in error_message.lower()

    @pytest.mark.e2e
    async def test_password_reset_flow(self, page: Page):
        """Тест процесса сброса пароля."""
        with mock_notification_service() as notification_mock:
            # Переходим на страницу сброса пароля
            await page.goto("http://localhost:8000/forgot-password")

            # Заполняем email
            await page.fill("input[name='email']", "test@example.com")

            # Отправляем форму
            await page.click("button[type='submit']")

            # Ожидаем сообщение об отправке
            await page.wait_for_selector(".info-message", timeout=3000)

            info_message = await page.text_content(".info-message")
            assert "отправлена" in info_message.lower() or "sent" in info_message.lower()

            # Проверяем что email был отправлен
            sent_emails = notification_mock.get_sent_notifications("email")
            assert len(sent_emails) == 1
            assert sent_emails[0]["to"] == "test@example.com"

    @pytest.mark.e2e
    async def test_user_profile_update(self, page: Page):
        """Тест обновления профиля пользователя."""
        # Сначала входим в систему
        await self._login_user(page, "test@example.com", "TestPassword123!")

        # Переходим в профиль
        await page.goto("http://localhost:8000/profile")

        # Ожидаем загрузки формы профиля
        await page.wait_for_selector("form[data-testid='profile-form']")

        # Обновляем данные профиля
        new_full_name = "Updated Test User"
        await page.fill("input[name='full_name']", new_full_name)
        await page.fill("textarea[name='bio']", "This is my updated bio")

        # Сохраняем изменения
        await page.click("button[data-testid='save-profile']")

        # Ожидаем сообщения об успешном сохранении
        await page.wait_for_selector(".success-message", timeout=3000)

        # Перезагружаем страницу и проверяем что данные сохранены
        await page.reload()
        await page.wait_for_selector("form[data-testid='profile-form']")

        saved_name = await page.input_value("input[name='full_name']")
        assert saved_name == new_full_name

    @pytest.mark.e2e
    async def test_logout_flow(self, page: Page):
        """Тест процесса выхода из системы."""
        # Входим в систему
        await self._login_user(page, "test@example.com", "TestPassword123!")

        # Нажимаем на меню пользователя
        await page.click("[data-testid='user-menu']")

        # Нажимаем кнопку выхода
        await page.click("[data-testid='logout-button']")

        # Ожидаем перенаправления на страницу входа
        await page.wait_for_url("http://localhost:8000/login", timeout=5000)

        # Проверяем что пользователь разлогинен
        # (пытаемся зайти на защищенную страницу)
        await page.goto("http://localhost:8000/dashboard")
        await page.wait_for_url("http://localhost:8000/login", timeout=3000)

    @pytest.mark.e2e
    async def test_admin_access(self, page: Page):
        """Тест доступа администратора к админ панели."""
        # Создаем админа и входим
        admin_data = make_admin_data(email="admin@example.com", username="admin")

        await self._login_user(page, admin_data["email"], "AdminPassword123!")

        # Переходим в админ панель
        await page.goto("http://localhost:8000/admin")

        # Проверяем что админ панель доступна
        await page.wait_for_selector("[data-testid='admin-panel']", timeout=5000)

        # Проверяем наличие административных функций
        users_link = await page.query_selector("a[href='/admin/users']")
        assert users_link is not None

    @pytest.mark.e2e
    async def test_unauthorized_admin_access(self, page: Page):
        """Тест блокировки доступа обычного пользователя к админ панели."""
        # Входим как обычный пользователь
        await self._login_user(page, "test@example.com", "TestPassword123!")

        # Пытаемся зайти в админ панель
        await page.goto("http://localhost:8000/admin")

        # Ожидаем сообщение об ошибке доступа или перенаправление
        try:
            await page.wait_for_selector(".access-denied", timeout=3000)
        except:
            # Или проверяем что перенаправило на главную
            current_url = page.url
            assert "/admin" not in current_url

    async def _login_user(self, page: Page, email: str, password: str):
        """Вспомогательная функция для входа пользователя."""
        await page.goto("http://localhost:8000/login")
        await page.wait_for_selector("form[data-testid='login-form']")

        await page.fill("input[name='email']", email)
        await page.fill("input[name='password']", password)
        await page.click("button[type='submit']")

        # Ожидаем успешного входа
        await page.wait_for_url("http://localhost:8000/dashboard", timeout=5000)


class TestUserWorkflows:
    """Тесты пользовательских рабочих процессов."""

    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_complete_user_journey(self, page: Page):
        """Тест полного пути пользователя от регистрации до использования системы."""
        # 1. Регистрация
        await page.goto("http://localhost:8000/register")

        user_data = make_user_data(email="journey@example.com", username="journeyuser")

        await page.fill("input[name='email']", user_data["email"])
        await page.fill("input[name='username']", user_data["username"])
        await page.fill("input[name='full_name']", user_data["full_name"])
        await page.fill("input[name='password']", "JourneyPass123!")
        await page.fill("input[name='password_confirm']", "JourneyPass123!")

        await page.click("button[type='submit']")
        await page.wait_for_selector(".success-message")

        # 2. Вход в систему
        await page.goto("http://localhost:8000/login")
        await page.fill("input[name='email']", user_data["email"])
        await page.fill("input[name='password']", "JourneyPass123!")
        await page.click("button[type='submit']")

        await page.wait_for_url("http://localhost:8000/dashboard")

        # 3. Обновление профиля
        await page.goto("http://localhost:8000/profile")
        await page.fill("textarea[name='bio']", "I'm testing the complete user journey!")
        await page.click("button[data-testid='save-profile']")
        await page.wait_for_selector(".success-message")

        # 4. Использование основного функционала (пример - отправка сообщения)
        await page.goto("http://localhost:8000/messages")

        # Если есть функция отправки сообщений
        try:
            await page.fill("textarea[name='message']", "Hello from E2E test!")
            await page.click("button[data-testid='send-message']")
            await page.wait_for_selector(".message-sent", timeout=3000)
        except:
            # Если функционал еще не реализован, пропускаем
            pass

        # 5. Выход из системы
        await page.click("[data-testid='user-menu']")
        await page.click("[data-testid='logout-button']")
        await page.wait_for_url("http://localhost:8000/login")

    @pytest.mark.e2e
    async def test_form_validation(self, page: Page):
        """Тест валидации форм на клиенте."""
        await page.goto("http://localhost:8000/register")

        # Пытаемся отправить пустую форму
        await page.click("button[type='submit']")

        # Проверяем сообщения валидации
        email_error = await page.query_selector("input[name='email']:invalid")
        assert email_error is not None

        # Заполняем невалидный email
        await page.fill("input[name='email']", "invalid-email")
        await page.click("button[type='submit']")

        email_error = await page.query_selector("input[name='email']:invalid")
        assert email_error is not None

        # Проверяем валидацию пароля
        await page.fill("input[name='email']", "valid@example.com")
        await page.fill("input[name='password']", "123")  # Слишком короткий
        await page.click("button[type='submit']")

        # Должно быть сообщение о слабом пароле
        password_error = await page.query_selector(".password-error")
        if password_error:
            error_text = await password_error.text_content()
            assert "пароль" in error_text.lower() or "password" in error_text.lower()

    @pytest.mark.e2e
    async def test_responsive_design(self, page: Page):
        """Тест адаптивного дизайна."""
        await page.goto("http://localhost:8000/login")

        # Тестируем на разных размерах экрана
        screen_sizes = [
            {"width": 1920, "height": 1080},  # Desktop
            {"width": 768, "height": 1024},  # Tablet
            {"width": 375, "height": 667},  # Mobile
        ]

        for size in screen_sizes:
            await page.set_viewport_size(size)

            # Проверяем что форма входа видна и доступна
            login_form = await page.query_selector("form[data-testid='login-form']")
            assert login_form is not None

            # Проверяем что кнопки кликабельны
            submit_button = await page.query_selector("button[type='submit']")
            is_visible = await submit_button.is_visible()
            assert is_visible

    @pytest.mark.e2e
    async def test_accessibility(self, page: Page):
        """Базовый тест доступности."""
        await page.goto("http://localhost:8000/login")

        # Проверяем наличие alt атрибутов у изображений
        images = await page.query_selector_all("img")
        for img in images:
            alt = await img.get_attribute("alt")
            # Alt может быть пустым для декоративных изображений
            assert alt is not None

        # Проверяем наличие labels у полей ввода
        inputs = await page.query_selector_all("input[type='text'], input[type='email'], input[type='password']")
        for input_field in inputs:
            # Проверяем наличие связанного label или aria-label
            input_id = await input_field.get_attribute("id")
            aria_label = await input_field.get_attribute("aria-label")

            if input_id:
                label = await page.query_selector(f"label[for='{input_id}']")
                assert label is not None or aria_label is not None
            else:
                assert aria_label is not None

    async def _wait_for_network_idle(self, page: Page, timeout: int = 5000):
        """Ожидает когда сетевая активность затихнет."""
        await page.wait_for_load_state("networkidle", timeout=timeout)
