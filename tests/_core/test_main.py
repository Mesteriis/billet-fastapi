"""Тесты для главного модуля приложения."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


class TestMainApp:
    """Тесты для основного FastAPI приложения."""

    def test_app_creation(self):
        """Тест создания приложения."""
        assert app is not None
        assert app.title == "Mango Message"
        assert app.version == "1.0.0"

    def test_root_endpoint(self):
        """Тест корневого эндпоинта."""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()

            assert "message" in data
            assert "version" in data
            assert "endpoints" in data
            assert data["version"] == "1.0.0"
            assert "Welcome to Mango Message" in data["message"]

    def test_health_endpoint(self):
        """Тест эндпоинта проверки здоровья."""
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert data["app"] == "Mango Message"
            assert data["version"] == "1.0.0"

    def test_docs_endpoint(self):
        """Тест эндпоинта документации."""
        with TestClient(app) as client:
            response = client.get("/docs")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]

    def test_openapi_endpoint(self):
        """Тест эндпоинта OpenAPI спецификации."""
        with TestClient(app) as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            data = response.json()

            assert "openapi" in data
            assert "info" in data
            assert data["info"]["title"] == "Mango Message"

    @patch("src.main.TELEGRAM_AVAILABLE", True)
    def test_root_with_telegram_enabled(self):
        """Тест корневого эндпоинта с включенным Telegram."""
        with patch("src.main.settings") as mock_settings:
            mock_settings.TELEGRAM_BOTS_ENABLED = True

            with TestClient(app) as client:
                response = client.get("/")
                assert response.status_code == 200
                data = response.json()

                assert data["telegram_enabled"] is True

    @patch("src.main.REALTIME_AVAILABLE", True)
    def test_root_with_realtime_enabled(self):
        """Тест корневого эндпоинта с включенным Realtime."""
        with patch("src.main.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            mock_settings.SSE_ENABLED = True

            with TestClient(app) as client:
                response = client.get("/")
                assert response.status_code == 200
                data = response.json()

                assert data["websocket_enabled"] is True
                assert data["sse_enabled"] is True

    @patch("src.main.MESSAGING_AVAILABLE", True)
    def test_root_with_messaging_enabled(self):
        """Тест корневого эндпоинта с включенным Messaging."""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()

            assert data["messaging_enabled"] is True
            assert "messaging" in data["endpoints"]


class TestLifespan:
    """Тесты для управления жизненным циклом приложения."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_shutdown(self):
        """Тест запуска и остановки приложения."""
        from src.core.taskiq_client import broker
        from src.main import lifespan

        # Мокаем методы брокера
        broker.startup = AsyncMock()
        broker.shutdown = AsyncMock()

        # Тестируем lifespan
        async with lifespan(app):
            broker.startup.assert_called_once()

        broker.shutdown.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.main.TELEGRAM_AVAILABLE", True)
    async def test_lifespan_with_telegram(self):
        """Тест жизненного цикла с Telegram ботами."""
        from src.core.taskiq_client import broker
        from src.main import lifespan

        # Мокаем брокер и телеграм
        broker.startup = AsyncMock()
        broker.shutdown = AsyncMock()

        with patch("src.main.settings") as mock_settings:
            mock_settings.TELEGRAM_BOTS_ENABLED = True

            with patch("src.main.register_basic_handlers") as mock_basic:
                with patch("src.main.register_admin_handlers") as mock_admin:
                    with patch("src.main.get_bot_manager") as mock_manager:
                        mock_bot_manager = AsyncMock()
                        mock_manager.return_value = mock_bot_manager

                        async with lifespan(app):
                            mock_basic.assert_called_once()
                            mock_admin.assert_called_once()
                            mock_bot_manager.initialize_bots.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_telegram_error_handling(self):
        """Тест обработки ошибок в Telegram ботах."""
        from src.core.taskiq_client import broker
        from src.main import lifespan

        broker.startup = AsyncMock()
        broker.shutdown = AsyncMock()

        with patch("src.main.TELEGRAM_AVAILABLE", True):
            with patch("src.main.settings") as mock_settings:
                mock_settings.TELEGRAM_BOTS_ENABLED = True

                with patch("src.main.register_basic_handlers", side_effect=Exception("Test error")):
                    # Не должно падать, только логировать ошибку
                    async with lifespan(app):
                        pass

        broker.startup.assert_called_once()
        broker.shutdown.assert_called_once()


class TestAppConfiguration:
    """Тесты конфигурации приложения."""

    def test_app_title_and_description(self):
        """Тест названия и описания приложения."""
        assert app.title == "Mango Message"
        assert app.description == "API for messaging system"

    def test_app_version(self):
        """Тест версии приложения."""
        assert app.version == "1.0.0"

    def test_app_routes_inclusion(self):
        """Тест подключения роутов."""
        # Проверяем, что роуты подключены
        routes = [route.path for route in app.routes]

        assert "/" in routes
        assert "/health" in routes
        assert "/docs" in routes
        assert "/openapi.json" in routes
