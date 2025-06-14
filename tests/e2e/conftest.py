"""
Конфигурация для E2E тестов с Playwright.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from playwright.async_api import Browser, BrowserContext, Page, async_playwright


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всей сессии тестирования."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser() -> AsyncGenerator[Browser, None]:
    """Фикстура браузера для всей сессии."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Установить False для отладки
            slow_mo=50,  # Замедление для наблюдения
            args=[
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Фикстура контекста браузера."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="ru-RU",
        timezone_id="Europe/Moscow",
        permissions=["geolocation", "notifications"],
        record_video_dir="reports/videos/",
        record_video_size={"width": 1280, "height": 720},
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Фикстура страницы браузера."""
    page = await context.new_page()

    # Настройка логирования
    page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
    page.on("pageerror", lambda error: print(f"Page error: {error}"))

    yield page
    await page.close()


@pytest.fixture
def base_url() -> str:
    """Базовый URL приложения."""
    return "http://localhost:3000"  # URL фронтенда


# Маркеры для E2E тестов


def pytest_configure(config):
    """Настройка pytest маркеров."""
    config.addinivalue_line("markers", "e2e: End-to-End browser tests")
    config.addinivalue_line("markers", "smoke: Smoke tests for critical functionality")
    config.addinivalue_line("markers", "regression: Regression tests")


# Хуки для скриншотов при падении тестов


@pytest.fixture(autouse=True)
async def screenshot_on_failure(request, page: Page):
    """Автоматически делает скриншот при падении теста."""
    yield

    if request.node.rep_call.failed:
        test_name = request.node.name
        screenshot_path = f"reports/screenshots/{test_name}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved: {screenshot_path}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Хук для сохранения информации о результате теста."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
