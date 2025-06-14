"""
Примеры использования расширенных функций AsyncApiTestClient.

Этот файл демонстрирует практическое применение новых возможностей:
- WebSocket тестирование
- Тестирование безопасности
- Нагрузочное тестирование
- AI-генерация тестов из OpenAPI схем
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from tests.utils_test.api_test_client import (
    AsyncApiTestClient,
    LoadTestConfig,
    LoadTestPattern,
    SecurityTestType,
    TestScenarioType,
    WebSocketEventType,
)


class AdvancedFeaturesDemo:
    """Демонстрация расширенных возможностей тестового клиента."""

    def __init__(self, app):
        self.app = app

    async def demo_websocket_testing(self):
        """Демонстрация WebSocket тестирования."""
        print("\n=== WebSocket Testing Demo ===")

        async with AsyncApiTestClient(app=self.app) as client:
            # Тестирование WebSocket соединения
            async with client.websocket_test_session("/ws/chat") as connection_id:
                print(f"WebSocket подключен: {connection_id}")

                # Отправляем сообщение
                await client.websocket_send(connection_id, {"type": "message", "content": "Hello WebSocket!"})

                # Получаем ответ
                response = await client.websocket_receive(connection_id, timeout=5.0)
                print(f"Получен ответ: {response}")

                # Тестируем ping
                ping_time = await client.websocket_ping(connection_id)
                print(f"WebSocket ping: {ping_time:.3f}s")

                # Получаем историю сообщений
                session = client.get_websocket_session(connection_id)
                if session:
                    print(f"Всего сообщений в сессии: {len(session.messages)}")

                    for msg in session.messages:
                        print(f"  {msg.event_type.value}: {msg.data}")

    async def demo_security_testing(self):
        """Демонстрация тестирования безопасности."""
        print("\n=== Security Testing Demo ===")

        async with AsyncApiTestClient(app=self.app) as client:
            # Запускаем комплексное сканирование безопасности
            endpoints_to_test = ["/api/users", "/api/auth/login"]

            print("Запуск сканирования безопасности...")
            security_results = await client.run_security_scan(endpoints_to_test)

            print(f"Проведено {len(security_results)} тестов безопасности")

            # Генерируем отчет по безопасности
            security_report = client.generate_security_report()
            print(f"Общий счет безопасности: {security_report['security_score']}/100")

    async def demo_load_testing(self):
        """Демонстрация нагрузочного тестирования."""
        print("\n=== Load Testing Demo ===")

        async with AsyncApiTestClient(app=self.app) as client:
            # Настраиваем тестового пользователя
            await client.force_auth(is_superuser=True)

            # Конфигурация нагрузочного теста
            load_config = LoadTestConfig(
                pattern=LoadTestPattern.RAMP_UP,
                duration_seconds=30,
                concurrent_users=10,
                ramp_up_time=10,
                endpoints=["/api/users"],
            )

            print(f"Запуск нагрузочного теста: {load_config.pattern.value}")

            # Запускаем нагрузочный тест
            load_results = await client.run_load_test(load_config)

            # Анализируем результаты
            print(f"Всего запросов: {load_results.total_requests}")
            print(f"Среднее время ответа: {load_results.average_response_time:.3f}s")

    async def demo_ai_test_generation(self):
        """Демонстрация AI-генерации тестов."""
        print("\n=== AI Test Generation Demo ===")

        async with AsyncApiTestClient(app=self.app) as client:
            # Загружаем OpenAPI схему
            try:
                schema = client.load_openapi_schema()
                print(f"OpenAPI схема загружена")

                # Генерируем тесты из схемы
                generated_tests = client.generate_tests_from_schema()
                print(f"Сгенерировано {len(generated_tests)} тестов")

                # Сохраняем тесты в файлы
                output_dir = Path("generated_tests")
                client.save_generated_tests(output_dir)
                print(f"Тесты сохранены в: {output_dir}")

            except Exception as e:
                print(f"Ошибка при работе с AI генерацией: {e}")

    async def demo_comprehensive_testing_scenario(self):
        """Комплексный сценарий тестирования с использованием всех функций."""
        print("\n=== Comprehensive Testing Scenario ===")

        async with AsyncApiTestClient(app=self.app) as client:
            # Включаем трекинг производительности
            client.enable_performance_tracking()

            # Создаем тестовую сессию
            async with client.test_session(TestScenarioType.INTEGRATION) as session:
                print(f"Запущена интеграционная тестовая сессия: {session.session_id}")

                # 1. Тестируем аутентификацию
                print("\n1. Тестирование аутентификации...")
                user = await client.force_auth(email="test@example.com")
                print(f"   Пользователь создан: {user.email}")

                # 2. Базовые API тесты
                print("\n2. Базовые API тесты...")
                response = await client.get("/api/users/me")
                assert response.status_code == 200
                print(f"   GET /api/users/me: {response.status_code}")

                # 3. Быстрая проверка безопасности
                print("\n3. Экспресс-проверка безопасности...")
                security_results = await client.run_security_scan(["/api/users/me"])
                critical_vulns = client.get_vulnerabilities_by_risk("HIGH")
                if critical_vulns:
                    print(f"   ⚠️  Обнаружено {len(critical_vulns)} критических уязвимостей")
                else:
                    print("   ✅ Критических уязвимостей не найдено")

                # 4. Мини нагрузочный тест
                print("\n4. Мини нагрузочный тест...")
                mini_load_config = LoadTestConfig(
                    pattern=LoadTestPattern.CONSTANT_LOAD,
                    duration_seconds=10,
                    concurrent_users=5,
                    endpoints=["/api/users/me"],
                )

                load_results = await client.run_load_test(mini_load_config)
                print(f"   Обработано {load_results.total_requests} запросов")
                print(f"   Среднее время ответа: {load_results.average_response_time:.3f}s")

                # 5. Получаем метрики производительности
                print("\n5. Метрики производительности...")
                perf_stats = client.get_performance_stats()
                print(f"   Всего запросов: {perf_stats['total_requests']}")
                print(f"   Среднее время ответа: {perf_stats['avg_response_time']:.3f}s")
                print(f"   RPS: {perf_stats['requests_per_second']:.2f}")

                print(f"\n✅ Интеграционная сессия завершена")
                print(f"   Общее количество метрик: {len(session.metrics)}")
                print(f"   Снимков API: {len(session.snapshots)}")


async def run_all_demos(app):
    """Запуск всех демонстраций."""
    demo = AdvancedFeaturesDemo(app)

    try:
        await demo.demo_websocket_testing()
    except Exception as e:
        print(f"WebSocket demo failed: {e}")

    try:
        await demo.demo_security_testing()
    except Exception as e:
        print(f"Security demo failed: {e}")

    try:
        await demo.demo_load_testing()
    except Exception as e:
        print(f"Load testing demo failed: {e}")

    try:
        await demo.demo_ai_test_generation()
    except Exception as e:
        print(f"AI generation demo failed: {e}")

    try:
        await demo.demo_comprehensive_testing_scenario()
    except Exception as e:
        print(f"Comprehensive demo failed: {e}")


# Пример использования в тестах
async def test_advanced_websocket_chat():
    """Пример продвинутого WebSocket теста."""
    from fastapi import FastAPI

    app = FastAPI()  # Ваше приложение

    async with AsyncApiTestClient(app=app) as client:
        # Аутентифицируемся
        user1 = await client.force_auth(email="user1@test.com")
        user2 = await client.force_auth(email="user2@test.com")

        # Подключаем два WebSocket соединения
        conn1 = await client.websocket_connect("/ws/chat/room1")

        # Временно переключаемся на другого пользователя
        conn2 = await client.websocket_connect("/ws/chat/room1", headers={"Authorization": f"Bearer {user2.id}"})

        # Отправляем сообщение от первого пользователя
        await client.websocket_send(conn1, {"type": "message", "text": "Hello from user1!"})

        # Получаем сообщение на втором соединении
        message = await client.websocket_receive(conn2, timeout=5.0)

        assert message["type"] == "message"
        assert message["text"] == "Hello from user1!"
        assert message["from_user"] == user1.email

        # Закрываем соединения
        await client.websocket_close(conn1)
        await client.websocket_close(conn2)


async def test_advanced_security_audit():
    """Пример комплексного аудита безопасности."""
    from fastapi import FastAPI

    app = FastAPI()

    async with AsyncApiTestClient(app=app) as client:
        # Запускаем полное сканирование безопасности
        all_results = await client.run_security_scan()

        # Фильтруем критические уязвимости
        critical = client.get_vulnerabilities_by_risk("HIGH")
        medium = client.get_vulnerabilities_by_risk("MEDIUM")

        # Проверяем что нет критических SQL injection уязвимостей
        sql_injection_vulns = [r for r in critical if r.test_type == SecurityTestType.SQL_INJECTION]

        assert len(sql_injection_vulns) == 0, f"Found SQL injection vulnerabilities: {sql_injection_vulns}"

        # Генерируем отчет
        report = client.generate_security_report()

        # Проверяем что security score выше минимального порога
        assert report["security_score"] >= 80, f"Security score too low: {report['security_score']}"

        # Сохраняем отчет
        with open("security_audit_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)


async def test_performance_benchmarking():
    """Пример бенчмаркинга производительности."""
    from fastapi import FastAPI

    app = FastAPI()

    async with AsyncApiTestClient(app=app) as client:
        await client.force_auth()
        client.enable_performance_tracking()

        # Тест производительности различных endpoints
        endpoints_to_test = ["/api/users", "/api/posts", "/api/comments"]

        results = {}

        for endpoint in endpoints_to_test:
            # Конфигурация для каждого endpoint
            config = LoadTestConfig(
                pattern=LoadTestPattern.CONSTANT_LOAD, duration_seconds=30, concurrent_users=20, endpoints=[endpoint]
            )

            print(f"Benchmarking {endpoint}...")
            load_result = await client.run_load_test(config)

            results[endpoint] = {
                "avg_response_time": load_result.average_response_time,
                "requests_per_second": load_result.requests_per_second,
                "success_rate": load_result.successful_requests / load_result.total_requests,
                "p95": load_result.percentile_95,
                "p99": load_result.percentile_99,
            }

            # Проверяем SLA
            assert load_result.average_response_time < 0.5, f"{endpoint} too slow: {load_result.average_response_time}s"
            assert load_result.requests_per_second > 50, (
                f"{endpoint} low throughput: {load_result.requests_per_second} RPS"
            )

        # Сохраняем результаты бенчмарка
        with open("performance_benchmark.json", "w") as f:
            json.dump(results, f, indent=2)

        print("Performance benchmarking completed successfully!")


if __name__ == "__main__":
    # Пример запуска демонстрации
    from fastapi import FastAPI

    app = FastAPI()

    # Добавьте здесь ваши роуты

    asyncio.run(run_all_demos(app))
