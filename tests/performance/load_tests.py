"""
Нагрузочные тесты с использованием Locust.
"""

import random

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner


class UserLoadTest(HttpUser):
    """Нагрузочное тестирование пользовательских операций."""

    wait_time = between(1, 3)  # Пауза между запросами

    def on_start(self):
        """Инициализация пользователя."""
        self.auth_token = None
        self.user_data = None
        self.login()

    def login(self):
        """Авторизация пользователя."""
        login_data = {"username": f"testuser_{random.randint(1000, 9999)}", "password": "TestPassword123!"}

        # Сначала регистрируемся
        register_response = self.client.post(
            "/auth/register",
            json={
                **login_data,
                "email": f"test_{random.randint(1000, 9999)}@example.com",
                "full_name": "Test User",
                "password_confirm": "TestPassword123!",
            },
        )

        if register_response.status_code == 201:
            # Теперь логинимся
            response = self.client.post("/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_data = data.get("user")

    def get_headers(self):
        """Возвращает заголовки с авторизацией."""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    @task(3)
    def get_profile(self):
        """Получение профиля пользователя."""
        self.client.get("/users/me", headers=self.get_headers())

    @task(2)
    def update_profile(self):
        """Обновление профиля пользователя."""
        update_data = {
            "full_name": f"Updated User {random.randint(1, 1000)}",
            "bio": f"Updated bio {random.randint(1, 1000)}",
        }
        self.client.put("/users/me", json=update_data, headers=self.get_headers())

    @task(1)
    def change_password(self):
        """Смена пароля."""
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }
        self.client.post("/users/me/change-password", json=password_data, headers=self.get_headers())

    @task(1)
    def refresh_token(self):
        """Обновление токена."""
        self.client.post("/auth/refresh", headers=self.get_headers())


class APILoadTest(HttpUser):
    """Общее нагрузочное тестирование API."""

    wait_time = between(0.5, 2)

    @task(5)
    def health_check(self):
        """Проверка здоровья API."""
        self.client.get("/health")

    @task(3)
    def get_users_list(self):
        """Получение списка пользователей."""
        self.client.get("/users/")

    @task(2)
    def search_users(self):
        """Поиск пользователей."""
        query = random.choice(["test", "user", "admin", "john"])
        self.client.get(f"/users/search/?q={query}")


class DatabaseLoadTest(HttpUser):
    """Нагрузочное тестирование операций с БД."""

    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Подготовка данных."""
        self.auth_token = self.get_admin_token()

    def get_admin_token(self):
        """Получение токена администратора."""
        admin_data = {"username": "admin", "password": "admin123"}
        response = self.client.post("/auth/login", json=admin_data)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None

    def get_headers(self):
        """Заголовки с авторизацией."""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    @task(10)
    def read_operations(self):
        """Операции чтения."""
        endpoints = ["/users/", "/users/me", f"/users/{random.randint(1, 100)}"]
        endpoint = random.choice(endpoints)
        self.client.get(endpoint, headers=self.get_headers())

    @task(3)
    def write_operations(self):
        """Операции записи."""
        user_data = {
            "email": f"load_test_{random.randint(10000, 99999)}@example.com",
            "username": f"load_user_{random.randint(10000, 99999)}",
            "full_name": "Load Test User",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
        }
        self.client.post("/auth/register", json=user_data)

    @task(1)
    def complex_operations(self):
        """Сложные операции с БД."""
        # Создание пользователя
        user_data = {
            "email": f"complex_{random.randint(10000, 99999)}@example.com",
            "username": f"complex_user_{random.randint(10000, 99999)}",
            "full_name": "Complex Test User",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
        }

        # Регистрация
        register_response = self.client.post("/auth/register", json=user_data)

        if register_response.status_code == 201:
            # Логин
            login_response = self.client.post(
                "/auth/login", json={"username": user_data["username"], "password": user_data["password"]}
            )

            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                headers = {"Authorization": f"Bearer {token}"}

                # Обновление профиля
                self.client.put(
                    "/users/me",
                    json={"full_name": "Updated Complex User", "bio": "Complex operations test"},
                    headers=headers,
                )


# Конфигурация для запуска тестов


class LoadTestConfig:
    """Конфигурация нагрузочных тестов."""

    # Параметры нагрузки
    USERS = 50  # Количество виртуальных пользователей
    SPAWN_RATE = 5  # Скорость создания пользователей в секунду
    RUN_TIME = "5m"  # Время выполнения тестов

    # Хост для тестирования
    HOST = "http://localhost:8000"

    @classmethod
    def get_command(cls, test_class: str = "UserLoadTest") -> str:
        """Возвращает команду для запуска нагрузочного теста."""
        return (
            f"locust -f tests/performance/load_tests.py "
            f"--users {cls.USERS} "
            f"--spawn-rate {cls.SPAWN_RATE} "
            f"--run-time {cls.RUN_TIME} "
            f"--host {cls.HOST} "
            f"{test_class} "
            f"--headless "
            f"--html reports/locust_report.html"
        )


# События Locust для кастомной статистики


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Обработчик событий запросов."""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Обработчик начала тестирования."""
    print("🚀 Начинаем нагрузочное тестирование!")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Обработчик окончания тестирования."""
    print("✅ Нагрузочное тестирование завершено!")

    # Можно добавить отправку результатов в систему мониторинга
    if isinstance(environment.runner, MasterRunner):
        print("📊 Статистика:")
        print(f"Общее количество запросов: {environment.runner.stats.total.num_requests}")
        print(f"Количество ошибок: {environment.runner.stats.total.num_failures}")
        print(f"Среднее время ответа: {environment.runner.stats.total.avg_response_time:.2f}ms")


# Примеры команд для запуска:
"""
# Запуск веб-интерфейса Locust
locust -f tests/performance/load_tests.py --host http://localhost:8000

# Headless режим
locust -f tests/performance/load_tests.py --users 50 --spawn-rate 5 --run-time 5m --host http://localhost:8000 --headless

# Только пользовательские тесты
locust -f tests/performance/load_tests.py --users 20 --spawn-rate 2 --run-time 2m --host http://localhost:8000 UserLoadTest --headless

# С генерацией отчета
locust -f tests/performance/load_tests.py --users 100 --spawn-rate 10 --run-time 10m --host http://localhost:8000 --headless --html reports/load_test_report.html
"""
