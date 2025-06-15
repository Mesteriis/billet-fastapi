"""
Тесты для API роутов аутентификации.
Демонстрирует правильное использование фабрик и AsyncApiTestClient.
"""

import pytest


@pytest.mark.auth
class TestRegistration:
    """Тесты регистрации пользователей."""

    async def test_register_success(self, api_client, test_user_data, helpers):
        """Тест успешной регистрации пользователя."""
        # Получаем URL для регистрации
        register_url = api_client.url_for("register")

        # Регистрируем пользователя
        response = await api_client.post(register_url, json=test_user_data.model_dump())

        assert response.status_code == 201
        data = response.json()

        # Используем хелперы для проверки
        helpers.assert_user_response(data["user"], test_user_data.email)
        helpers.assert_token_response(data["tokens"])

    async def test_register_existing_email(self, api_client, verified_user, test_user_data):
        """Тест регистрации с существующим email."""
        register_url = api_client.url_for("register")

        # Используем email существующего пользователя
        test_user_data.email = verified_user.email

        response = await api_client.post(register_url, json=test_user_data.model_dump())

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "email" in data["detail"].lower()

    async def test_register_invalid_password(self, api_client, test_user_data):
        """Тест регистрации с невалидным паролем."""
        register_url = api_client.url_for("register")

        # Делаем пароль слабым
        test_user_data.password = "weak"
        test_user_data.password_confirm = "weak"

        response = await api_client.post(register_url, json=test_user_data.model_dump())

        assert response.status_code == 422

    async def test_register_password_mismatch(self, api_client, test_user_data):
        """Тест регистрации с несовпадающими паролями."""
        register_url = api_client.url_for("register")

        # Делаем пароли разными
        test_user_data.password_confirm = "DifferentPassword123!"

        response = await api_client.post(register_url, json=test_user_data.model_dump())

        assert response.status_code == 422


@pytest.mark.auth
class TestLogin:
    """Тесты входа в систему."""

    async def test_login_success(self, api_client, test_user_db, helpers):
        """Тест успешного входа."""
        login_url = api_client.url_for("login")

        login_data = {"email": test_user_db.email, "password": "TestPassword123!"}

        response = await api_client.post(login_url, json=login_data)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_user_response(data["user"], test_user_db.email)
        helpers.assert_token_response(data["tokens"])

    async def test_login_invalid_email(self, api_client, user_factory):
        """Тест входа с несуществующим email."""
        login_url = api_client.url_for("login")

        # Создаем уникальный email, которого точно нет в БД
        fake_user = await user_factory.build()  # build не сохраняет в БД

        login_data = {"email": fake_user.email, "password": "TestPassword123!"}

        response = await api_client.post(login_url, json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    async def test_login_invalid_password(self, api_client, verified_user):
        """Тест входа с неверным паролем."""
        login_url = api_client.url_for("login")

        login_data = {"email": verified_user.email, "password": "WrongPassword123!"}

        response = await api_client.post(login_url, json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


@pytest.mark.auth
class TestTokenOperations:
    """Тесты операций с токенами."""

    async def test_refresh_token_success(self, api_client, verified_user, helpers):
        """Тест успешного обновления токена."""
        login_url = api_client.url_for("login")

        # Сначала входим для получения токенов
        login_data = {"email": verified_user.email, "password": "TestPassword123!"}

        login_response = await api_client.post(login_url, json=login_data)
        assert login_response.status_code == 200

        refresh_token = login_response.json()["tokens"]["refresh_token"]

        # Обновляем токен
        refresh_url = api_client.url_for("refresh")
        refresh_data = {"refresh_token": refresh_token}

        response = await api_client.post(refresh_url, json=refresh_data)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_token_response(data)

    async def test_refresh_token_invalid(self, api_client):
        """Тест обновления с невалидным токеном."""
        refresh_url = api_client.url_for("refresh")

        refresh_data = {"refresh_token": "invalid-token"}
        response = await api_client.post(refresh_url, json=refresh_data)

        assert response.status_code == 401

    async def test_validate_token_success(self, api_client, verified_user):
        """Тест валидации токена."""
        # Аутентифицируем пользователя
        await api_client.force_auth(verified_user)

        validate_url = api_client.url_for("validate")
        response = await api_client.get(validate_url)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert "user_id" in data
        assert "email" in data
        assert data["token_type"] == "access"

    async def test_validate_token_invalid(self, api_client):
        """Тест валидации невалидного токена."""
        validate_url = api_client.url_for("validate")

        # Используем невалидный токен
        headers = {"Authorization": "Bearer invalid-token"}
        response = await api_client.get(validate_url, headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False
        assert "error" in data


@pytest.mark.auth
class TestLogout:
    """Тесты выхода из системы."""

    async def test_logout_success(self, api_client, verified_user):
        """Тест успешного выхода."""
        # Аутентифицируем пользователя
        await api_client.force_auth(verified_user)

        logout_url = api_client.url_for("logout")
        response = await api_client.post(logout_url)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"

    async def test_logout_all_success(self, api_client, verified_user):
        """Тест выхода из всех сессий."""
        # Аутентифицируем пользователя
        await api_client.force_auth(verified_user)

        logout_all_url = api_client.url_for("logout_all")
        response = await api_client.post(logout_all_url)

        assert response.status_code == 200
        data = response.json()
        assert "revoked" in data
        assert data["revoked"] >= 1


@pytest.mark.auth
class TestCurrentUser:
    """Тесты получения текущего пользователя."""

    async def test_get_current_user_success(self, api_client, verified_user, helpers):
        """Тест получения информации о текущем пользователе."""
        # Аутентифицируем пользователя
        await api_client.force_auth(verified_user)

        current_user_url = api_client.url_for("current_user")
        response = await api_client.get(current_user_url)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_user_response(data, verified_user.email)

    async def test_get_current_user_unauthorized(self, api_client):
        """Тест получения информации без аутентификации."""
        current_user_url = api_client.url_for("current_user")
        response = await api_client.get(current_user_url)

        assert response.status_code == 401


@pytest.mark.auth
@pytest.mark.integration
class TestAuthenticationFlow:
    """Интеграционные тесты полного потока аутентификации."""

    async def test_complete_auth_flow(self, api_client, test_user_data, helpers):
        """Тест полного потока: регистрация -> логин -> доступ к защищенным ресурсам."""
        # 1. Регистрация
        register_url = api_client.url_for("register")
        register_response = await api_client.post(register_url, json=test_user_data.model_dump())

        assert register_response.status_code == 201
        register_data = register_response.json()

        helpers.assert_user_response(register_data["user"], test_user_data.email)
        helpers.assert_token_response(register_data["tokens"])

        # 2. Логин
        login_url = api_client.url_for("login")
        login_data = {"email": test_user_data.email, "password": test_user_data.password}

        login_response = await api_client.post(login_url, json=login_data)
        assert login_response.status_code == 200

        # 3. Доступ к защищенному ресурсу
        access_token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        current_user_url = api_client.url_for("current_user")
        protected_response = await api_client.get(current_user_url, headers=headers)

        assert protected_response.status_code == 200
        user_data = protected_response.json()
        assert user_data["email"] == test_user_data.email

    async def test_multiple_sessions(self, api_client, verified_user):
        """Тест множественных сессий одного пользователя."""
        login_url = api_client.url_for("login")

        login_data = {"email": verified_user.email, "password": "TestPassword123!"}

        # Создаем несколько сессий
        sessions = []
        for i in range(3):
            response = await api_client.post(login_url, json=login_data)
            assert response.status_code == 200

            tokens = response.json()["tokens"]
            sessions.append(tokens)

        # Проверяем, что все токены разные
        access_tokens = [session["access_token"] for session in sessions]
        refresh_tokens = [session["refresh_token"] for session in sessions]

        assert len(set(access_tokens)) == 3  # Все access токены уникальны
        assert len(set(refresh_tokens)) == 3  # Все refresh токены уникальны

        # Проверяем, что все токены работают
        current_user_url = api_client.url_for("current_user")

        for session in sessions:
            headers = {"Authorization": f"Bearer {session['access_token']}"}
            response = await api_client.get(current_user_url, headers=headers)
            assert response.status_code == 200


@pytest.mark.auth
@pytest.mark.performance
class TestAuthPerformance:
    """Тесты производительности аутентификации."""

    async def test_login_performance(self, api_client, verified_user):
        """Тест производительности логина."""
        # Включаем отслеживание производительности
        api_client.enable_performance_tracking()

        login_url = api_client.url_for("login")
        login_data = {"email": verified_user.email, "password": "TestPassword123!"}

        # Выполняем несколько логинов
        for _ in range(10):
            response = await api_client.post(login_url, json=login_data)
            assert response.status_code == 200

        # Проверяем метрики
        stats = api_client.get_performance_stats()
        assert stats["total_requests"] == 10
        assert stats["average_response_time"] < 1.0  # Логин должен быть быстрым

        api_client.disable_performance_tracking()

    async def test_concurrent_logins(self, api_client, user_factory):
        """Тест параллельных логинов."""
        # Создаем пользователей для тестирования
        users = []
        for _ in range(5):
            user = await user_factory.create(is_verified=True)
            users.append(user)

        login_url = api_client.url_for("login")

        # Параллельные логины
        import asyncio

        tasks = []

        for user in users:
            login_data = {"email": user.email, "password": "TestPassword123!"}
            task = api_client.post(login_url, json=login_data)
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # Все логины должны быть успешными
        for response in responses:
            assert response.status_code == 200
