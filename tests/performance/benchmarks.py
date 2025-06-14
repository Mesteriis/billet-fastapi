"""
Бенчмарки для измерения производительности.
"""

import time
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_users_batch


@pytest.mark.performance
@pytest.mark.benchmark(group="api")
async def benchmark_api_endpoints(benchmark, async_client: AsyncClient):
    """Бенчмарк API эндпоинтов."""

    async def api_call():
        response = await async_client.get("/users/")
        return response.json()

    result = await benchmark.pedantic(api_call, rounds=10, iterations=5)
    assert result is not None


@pytest.mark.performance
@pytest.mark.benchmark(group="database")
async def benchmark_database_operations(benchmark, async_session: AsyncSession):
    """Бенчмарк операций с базой данных."""

    async def db_operations():
        # Создание пользователей
        users = await create_users_batch(async_session, count=10)

        # Поиск пользователей
        from sqlalchemy import select

        from apps.users.models import User

        query = select(User).limit(10)
        result = await async_session.execute(query)
        found_users = result.scalars().all()

        return len(found_users)

    result = await benchmark.pedantic(db_operations, rounds=5, iterations=3)
    assert result >= 0


@pytest.mark.performance
@pytest.mark.benchmark(group="auth")
async def benchmark_auth_flow(benchmark, async_client: AsyncClient):
    """Бенчмарк полного флоу аутентификации."""

    async def auth_flow():
        # Регистрация
        user_data = {
            "email": f"bench_{int(time.time())}@example.com",
            "username": f"bench_user_{int(time.time())}",
            "full_name": "Benchmark User",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
        }

        register_response = await async_client.post("/auth/register", json=user_data)

        if register_response.status_code == 201:
            # Логин
            login_response = await async_client.post(
                "/auth/login", json={"username": user_data["username"], "password": user_data["password"]}
            )

            if login_response.status_code == 200:
                token = login_response.json()["access_token"]

                # Получение профиля
                headers = {"Authorization": f"Bearer {token}"}
                profile_response = await async_client.get("/users/me", headers=headers)

                return profile_response.status_code

        return 500

    result = await benchmark.pedantic(auth_flow, rounds=5, iterations=2)
    assert result == 200


# Кастомные бенчмарки


class APIBenchmark:
    """Класс для бенчмарков API."""

    def __init__(self, client: AsyncClient):
        self.client = client
        self.results = {}

    async def measure_endpoint(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """Измеряет производительность эндпоинта."""
        times = []

        for _ in range(10):
            start_time = time.perf_counter()

            if method.upper() == "GET":
                response = await self.client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await self.client.post(url, **kwargs)
            elif method.upper() == "PUT":
                response = await self.client.put(url, **kwargs)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, **kwargs)

            end_time = time.perf_counter()
            times.append(end_time - start_time)

        return {
            "url": url,
            "method": method,
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "total_requests": len(times),
            "status_code": response.status_code,
        }

    async def run_full_benchmark(self) -> dict[str, Any]:
        """Запускает полный бенчмарк API."""
        endpoints = [
            ("GET", "/users/"),
            ("GET", "/auth/validate"),
            ("GET", "/health"),
        ]

        results = {}
        for method, url in endpoints:
            results[f"{method} {url}"] = await self.measure_endpoint(method, url)

        return results


class DatabaseBenchmark:
    """Класс для бенчмарков базы данных."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def measure_bulk_insert(self, count: int = 100) -> dict[str, Any]:
        """Измеряет производительность массовой вставки."""
        start_time = time.perf_counter()

        users = await create_users_batch(self.session, count=count)

        end_time = time.perf_counter()

        return {
            "operation": "bulk_insert",
            "count": count,
            "time": end_time - start_time,
            "ops_per_second": count / (end_time - start_time),
            "created_users": len(users),
        }

    async def measure_select_queries(self, query_count: int = 50) -> dict[str, Any]:
        """Измеряет производительность SELECT запросов."""
        from sqlalchemy import select

        from apps.users.models import User

        start_time = time.perf_counter()

        for _ in range(query_count):
            query = select(User).limit(10)
            result = await self.session.execute(query)
            result.scalars().all()

        end_time = time.perf_counter()

        return {
            "operation": "select_queries",
            "query_count": query_count,
            "time": end_time - start_time,
            "queries_per_second": query_count / (end_time - start_time),
        }


# Фикстуры для бенчмарков


@pytest.fixture
def api_benchmark(async_client: AsyncClient):
    """Фикстура API бенчмарка."""
    return APIBenchmark(async_client)


@pytest.fixture
def db_benchmark(async_session: AsyncSession):
    """Фикстура бенчмарка базы данных."""
    return DatabaseBenchmark(async_session)


# Примеры использования бенчмарков


@pytest.mark.performance
async def test_api_performance(api_benchmark: APIBenchmark):
    """Тест производительности API."""
    results = await api_benchmark.run_full_benchmark()

    for endpoint, metrics in results.items():
        print(f"{endpoint}: {metrics['avg_time']:.4f}s")
        assert metrics["avg_time"] < 1.0  # Все запросы должны быть быстрее 1 секунды


@pytest.mark.performance
async def test_database_performance(db_benchmark: DatabaseBenchmark):
    """Тест производительности базы данных."""

    # Тест массовой вставки
    insert_results = await db_benchmark.measure_bulk_insert(count=50)
    print(f"Bulk insert: {insert_results['ops_per_second']:.2f} ops/sec")
    assert insert_results["ops_per_second"] > 10  # Минимум 10 операций в секунду

    # Тест SELECT запросов
    select_results = await db_benchmark.measure_select_queries(query_count=20)
    print(f"Select queries: {select_results['queries_per_second']:.2f} queries/sec")
    assert select_results["queries_per_second"] > 50  # Минимум 50 запросов в секунду


# Утилиты для создания отчетов


def generate_performance_report(benchmark_results: list[dict[str, Any]]) -> str:
    """Генерирует отчет о производительности."""
    report = "# Performance Report\n\n"

    for result in benchmark_results:
        report += f"## {result.get('name', 'Unknown Test')}\n"
        report += f"- Average time: {result.get('avg_time', 0):.4f}s\n"
        report += f"- Min time: {result.get('min_time', 0):.4f}s\n"
        report += f"- Max time: {result.get('max_time', 0):.4f}s\n"
        report += f"- Operations per second: {result.get('ops_per_second', 0):.2f}\n\n"

    return report


# Конфигурация бенчмарков


class BenchmarkConfig:
    """Конфигурация для бенчмарков."""

    # Пороговые значения производительности
    MAX_API_RESPONSE_TIME = 1.0  # максимальное время ответа API в секундах
    MIN_DB_OPS_PER_SEC = 10  # минимальное количество операций БД в секунду
    MIN_API_OPS_PER_SEC = 50  # минимальное количество API запросов в секунду

    # Параметры тестирования
    BENCHMARK_ROUNDS = 5  # количество раундов
    BENCHMARK_ITERATIONS = 3  # количество итераций в раунде


# Примеры команд для запуска:
"""
# Запуск только бенчмарков
pytest tests/performance/benchmarks.py -m performance -v

# Запуск с выводом результатов бенчмарков
pytest tests/performance/benchmarks.py -m performance --benchmark-only --benchmark-sort=mean

# Сохранение результатов в JSON
pytest tests/performance/benchmarks.py -m performance --benchmark-json=reports/benchmark_results.json

# Сравнение с предыдущими результатами
pytest tests/performance/benchmarks.py -m performance --benchmark-compare=reports/benchmark_results.json
"""
