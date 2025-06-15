"""
Улучшенные тесты для API роутов аутентификации.
Демонстрация продвинутых возможностей AsyncApiTestClient и правильного использования фабрик.
"""

import asyncio
import time

import pytest


@pytest.mark.auth
@pytest.mark.enhanced
class TestRegistrationEnhanced:
    """Улучшенные тесты регистрации пользователей."""

    async def test_register_success_with_metrics(self, api_client, test_user_data, helpers):
        """Тест успешной регистрации с трекингом производительности."""
        # Включаем отслеживание производительности
        api_client.enable_performance_tracking()

        register_url = api_client.url_for("register")

        # Используем сессию для группировки метрик
        async with api_client.test_session() as session:
            response = await api_client.post(register_url, json=test_user_data.model_dump())

            assert response.status_code == 201
            data = response.json()

            # Проверяем структуру ответа
            helpers.assert_user_response(data["user"], test_user_data.email)
            helpers.assert_token_response(data["tokens"])

            # Создаем снимок API для будущих регрессионных тестов
            snapshot = await api_client.create_api_snapshot(
                register_url, method="POST", json=test_user_data.model_dump()
            )

            # Получаем метрики производительности
            perf_stats = api_client.get_performance_stats()

            assert perf_stats["total_requests"] >= 1
            assert perf_stats["average_response_time"] < 2.0  # Должно быть быстро
            assert snapshot.status_code == 201

    async def test_register_multiple_users_concurrent(self, api_client, user_factory):
        """Тест параллельной регистрации нескольких пользователей."""
        # Создаем данные для нескольких пользователей
        user_data_list = []
        for _ in range(5):
            user_data = await user_factory.build()  # build не сохраняет в БД
            user_data_dict = {
                "email": user_data.email,
                "username": user_data.username,
                "full_name": user_data.full_name,
                "avatar_url": None,
                "bio": None,
                "password": "TestPassword123!",
                "password_confirm": "TestPassword123!",
            }
            user_data_list.append(user_data_dict)

        register_url = api_client.url_for("register")

        # Параллельная регистрация
        tasks = [api_client.post(register_url, json=user_data) for user_data in user_data_list]

        responses = await asyncio.gather(*tasks)

        # Все регистрации должны быть успешными
        for response in responses:
            assert response.status_code == 201
            data = response.json()
            assert "user" in data
            assert "tokens" in data

    async def test_register_with_retry_on_network_issues(self, api_client, test_user_data):
        """Тест регистрации с повторными попытками при сетевых проблемах."""
        register_url = api_client.url_for("register")

        # Используем retry механизм клиента
        response = await api_client.request_with_retry(
            method="POST",
            url=register_url,
            json=test_user_data.model_dump(),
            max_retries=3,
            retry_strategy="exponential",
            retryable_status_codes=[500, 502, 503],
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == test_user_data.email


@pytest.mark.auth
@pytest.mark.enhanced
class TestLoginEnhanced:
    """Улучшенные тесты входа в систему."""

    async def test_login_chain_scenario(self, api_client, verified_user):
        """Тест полного сценария входа через chain API."""
        # Определяем шаги цепочки
        login_chain = [
            {
                "method": "POST",
                "url": api_client.url_for("login"),
                "data": {"email": verified_user.email, "password": "TestPassword123!"},
                "expected_status": 200,
                "description": "Вход в систему",
            },
            {
                "method": "GET",
                "url": api_client.url_for("current_user"),
                "expected_status": 200,
                "description": "Получение профиля",
            },
            {
                "method": "GET",
                "url": api_client.url_for("validate"),
                "expected_status": 200,
                "description": "Валидация токена",
            },
        ]

        # Выполняем цепочку вручную с сохранением токенов
        responses = []
        access_token = None

        for step in login_chain:
            headers = {}
            if access_token and step["method"] == "GET":
                headers["Authorization"] = f"Bearer {access_token}"

            response = await api_client.request(
                method=step["method"], url=step["url"], json=step.get("data"), headers=headers
            )

            assert response.status_code == step["expected_status"], (
                f"Шаг '{step['description']}' failed: {response.status_code}"
            )

            responses.append(response)

            # Сохраняем токен после логина
            if step["method"] == "POST" and "login" in step["url"]:
                tokens = response.json()["tokens"]
                access_token = tokens["access_token"]

        assert len(responses) == 3

    async def test_login_session_management(self, api_client, verified_user):
        """Тест управления сессиями пользователя."""
        login_url = api_client.url_for("login")

        login_data = {"email": verified_user.email, "password": "TestPassword123!"}

        # Создаем несколько сессий
        sessions = []
        for i in range(3):
            response = await api_client.post(login_url, json=login_data)
            assert response.status_code == 200

            tokens = response.json()["tokens"]
            sessions.append(tokens)

        # Проверяем, что все сессии работают
        current_user_url = api_client.url_for("current_user")

        for session in sessions:
            headers = {"Authorization": f"Bearer {session['access_token']}"}
            response = await api_client.get(current_user_url, headers=headers)
            assert response.status_code == 200

        # Выходим из всех сессий
        headers = {"Authorization": f"Bearer {sessions[0]['access_token']}"}
        logout_all_url = api_client.url_for("logout_all")
        response = await api_client.post(logout_all_url, headers=headers)
        assert response.status_code == 200

        # Проверяем, что все сессии инвалидированы
        for session in sessions:
            headers = {"Authorization": f"Bearer {session['access_token']}"}
            response = await api_client.get(current_user_url, headers=headers)
            # После logout_all токены должны быть недействительны
            assert response.status_code in [401, 403]


@pytest.mark.auth
@pytest.mark.enhanced
@pytest.mark.performance
class TestAuthPerformance:
    """Тесты производительности аутентификации."""

    async def test_auth_endpoints_benchmark(self, api_client, verified_user):
        """Бенчмарк производительности эндпоинтов аутентификации."""
        # Включаем отслеживание производительности
        api_client.enable_performance_tracking()

        login_url = api_client.url_for("login")
        login_data = {"email": verified_user.email, "password": "TestPassword123!"}

        async with api_client.test_session() as session:
            # Бенчмарк входа в систему
            login_times = []

            for _ in range(5):  # 5 попыток входа
                start_time = time.time()

                response = await api_client.post(login_url, json=login_data)

                end_time = time.time()
                login_times.append(end_time - start_time)

                assert response.status_code == 200

                # Сразу выходим для следующей попытки
                tokens = response.json()["tokens"]
                logout_url = api_client.url_for("logout")
                headers = {"Authorization": f"Bearer {tokens['access_token']}"}
                await api_client.post(logout_url, headers=headers)

            # Анализируем результаты
            avg_login_time = sum(login_times) / len(login_times)
            max_login_time = max(login_times)
            min_login_time = min(login_times)

            # Проверяем производительность
            assert avg_login_time < 1.0  # Среднее время < 1 сек
            assert max_login_time < 2.0  # Максимальное время < 2 сек

            # Получаем общую статистику
            perf_stats = api_client.get_performance_stats()
            assert perf_stats["total_requests"] >= 10  # 5 логинов + 5 логаутов

    async def test_concurrent_auth_operations(self, api_client, user_factory):
        """Тест параллельных операций аутентификации."""
        # Создаем пользователей для тестирования
        users = []
        for _ in range(10):
            user = await user_factory.create(is_verified=True)
            users.append(user)

        login_url = api_client.url_for("login")

        # Параллельные логины
        tasks = []
        for user in users:
            login_data = {"email": user.email, "password": "TestPassword123!"}
            task = api_client.post(login_url, json=login_data)
            tasks.append(task)

        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time

        # Все логины должны быть успешными
        for response in responses:
            assert response.status_code == 200

        # Параллельные операции должны быть быстрее последовательных
        assert total_time < 5.0  # 10 параллельных логинов < 5 сек

        # Проверяем, что можем использовать все токены
        current_user_url = api_client.url_for("current_user")

        validation_tasks = []
        for response in responses:
            tokens = response.json()["tokens"]
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            task = api_client.get(current_user_url, headers=headers)
            validation_tasks.append(task)

        validation_responses = await asyncio.gather(*validation_tasks)

        for response in validation_responses:
            assert response.status_code == 200

    async def test_auth_load_testing(self, api_client, verified_user):
        """Нагрузочное тестирование аутентификации."""
        # Включаем отслеживание производительности
        api_client.enable_performance_tracking()

        login_url = api_client.url_for("login")
        login_data = {"email": verified_user.email, "password": "TestPassword123!"}

        # Симулируем нагрузку
        num_requests = 50
        batch_size = 10

        successful_requests = 0
        failed_requests = 0

        for batch in range(0, num_requests, batch_size):
            # Создаем батч запросов
            tasks = []
            for _ in range(min(batch_size, num_requests - batch)):
                task = api_client.post(login_url, json=login_data)
                tasks.append(task)

            # Выполняем батч
            try:
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                for response in responses:
                    if isinstance(response, Exception):
                        failed_requests += 1
                    elif response.status_code == 200:
                        successful_requests += 1
                        # Сразу выходим
                        tokens = response.json()["tokens"]
                        logout_url = api_client.url_for("logout")
                        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
                        await api_client.post(logout_url, headers=headers)
                    else:
                        failed_requests += 1

            except Exception:
                failed_requests += batch_size

            # Небольшая пауза между батчами
            await asyncio.sleep(0.1)

        # Проверяем результаты нагрузочного тестирования
        success_rate = successful_requests / (successful_requests + failed_requests)

        assert success_rate > 0.9  # Успешность > 90%
        assert successful_requests >= num_requests * 0.8  # Минимум 80% успешных

        # Получаем финальную статистику
        perf_stats = api_client.get_performance_stats()
        assert perf_stats["average_response_time"] < 1.5  # Среднее время под нагрузкой


@pytest.mark.auth
@pytest.mark.enhanced
@pytest.mark.security
class TestAuthSecurity:
    """Тесты безопасности аутентификации."""

    async def test_password_security_validation(self, api_client, test_user_data):
        """Тест валидации безопасности паролей."""
        register_url = api_client.url_for("register")

        # Тестируем слабые пароли
        weak_passwords = [
            "123",
            "password",
            "qwerty",
            "12345678",  # Только цифры
            "password123",  # Без спецсимволов
            "PASSWORD123!",  # Без строчных
            "password123!",  # Без заглавных
        ]

        for weak_password in weak_passwords:
            test_data = test_user_data.model_copy()
            test_data.password = weak_password
            test_data.password_confirm = weak_password
            test_data.email = f"weak_{weak_password[:3]}@example.com"
            test_data.username = f"weak_{weak_password[:3]}"

            response = await api_client.post(register_url, json=test_data.model_dump())

            # Слабые пароли должны отклоняться
            assert response.status_code == 422

    async def test_rate_limiting_simulation(self, api_client, verified_user):
        """Симуляция тестирования rate limiting."""
        login_url = api_client.url_for("login")

        # Делаем много запросов подряд
        rapid_requests = 20
        failed_logins = 0

        for _ in range(rapid_requests):
            login_data = {
                "email": verified_user.email,
                "password": "WrongPassword!",  # Неправильный пароль
            }

            response = await api_client.post(login_url, json=login_data)

            if response.status_code == 401:
                failed_logins += 1
            elif response.status_code == 429:  # Rate limited
                break

            await asyncio.sleep(0.01)  # Небольшая задержка

        # Должны получить отказы в авторизации
        assert failed_logins > 0

    async def test_token_security_validation(self, api_client, verified_user):
        """Тест безопасности токенов."""
        # Аутентифицируемся
        await api_client.force_auth(verified_user)

        validate_url = api_client.url_for("validate")

        # Тестируем различные невалидные токены
        invalid_tokens = [
            "invalid.token.here",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature",
            "Bearer invalid-token",
            "",
            "null",
            "undefined",
        ]

        for invalid_token in invalid_tokens:
            headers = {"Authorization": f"Bearer {invalid_token}"}
            response = await api_client.get(validate_url, headers=headers)

            # Все невалидные токены должны отклоняться
            assert response.status_code in [401, 422]

            if response.status_code == 200:
                data = response.json()
                assert data.get("valid") is False
