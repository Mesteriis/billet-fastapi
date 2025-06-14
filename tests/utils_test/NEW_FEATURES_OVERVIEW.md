# Обзор новых функций AsyncApiTestClient

## 🚀 Введение

AsyncApiTestClient был значительно расширен четырьмя ключевыми возможностями для enterprise-уровня тестирования API:

1. **WebSocket поддержка** - полноценное тестирование real-time функций
2. **AI-powered генерация тестов** - автоматическое создание тестов из OpenAPI схем
3. **Тестирование безопасности** - автоматические проверки на уязвимости OWASP Top 10
4. **Нагрузочное тестирование** - интегрированные инструменты для performance тестирования

## 🔌 WebSocket Testing

### Основные возможности

```python
async with AsyncApiTestClient(app=app) as client:
    # Подключение к WebSocket
    async with client.websocket_test_session("/ws/chat") as connection_id:
        # Отправка сообщений
        await client.websocket_send(connection_id, {"type": "message", "data": "test"})

        # Получение ответов
        response = await client.websocket_receive(connection_id, timeout=5.0)

        # Ping/Pong тестирование
        ping_time = await client.websocket_ping(connection_id)

        # Получение метрик сессии
        session = client.get_websocket_session(connection_id)
        print(f"Сообщений: {len(session.messages)}")
```

### Поддерживаемые события

- `CONNECT` - событие подключения
- `DISCONNECT` - событие отключения
- `MESSAGE` - передача сообщений
- `ERROR` - обработка ошибок
- `PING/PONG` - проверка соединения

### Практические применения

- Тестирование чат-приложений
- Real-time уведомления
- Live обновления данных
- Мультиплеерные игры
- Collaborative editing

## 🔒 Security Testing

### Автоматические проверки безопасности

```python
async with AsyncApiTestClient(app=app) as client:
    # Комплексное сканирование
    results = await client.run_security_scan()

    # Анализ уязвимостей по уровню риска
    critical = client.get_vulnerabilities_by_risk("HIGH")
    medium = client.get_vulnerabilities_by_risk("MEDIUM")

    # Генерация отчета
    report = client.generate_security_report()
    print(f"Security Score: {report['security_score']}/100")
```

### Поддерживаемые типы тестов

| Тип                 | Описание                 | CWE     |
| ------------------- | ------------------------ | ------- |
| SQL Injection       | Проверка на SQL инъекции | CWE-89  |
| XSS                 | Cross-Site Scripting     | CWE-79  |
| Directory Traversal | Обход директорий         | CWE-22  |
| Rate Limiting       | Проверка ограничений     | CWE-770 |
| Auth Bypass         | Обход авторизации        | CWE-306 |
| Header Security     | Security заголовки       | CWE-693 |
| Input Validation    | Валидация входных данных | CWE-20  |

### Автоматическая детекция

- **SQL Injection**: анализ ошибок БД в ответах
- **XSS**: проверка отражения payload в HTML
- **Directory Traversal**: поиск системных файлов в ответах
- **Rate Limiting**: проверка кодов 429 при массовых запросах
- **Auth Bypass**: тестирование без токенов и с невалидными токенами

## ⚡ Load Testing

### Паттерны нагрузочного тестирования

```python
# Постоянная нагрузка
config = LoadTestConfig(
    pattern=LoadTestPattern.CONSTANT_LOAD,
    duration_seconds=60,
    concurrent_users=50,
    endpoints=["/api/users", "/api/posts"]
)

# Нарастающая нагрузка
config = LoadTestConfig(
    pattern=LoadTestPattern.RAMP_UP,
    duration_seconds=300,
    concurrent_users=100,
    ramp_up_time=60
)

# Spike тестирование
config = LoadTestConfig(
    pattern=LoadTestPattern.SPIKE,
    duration_seconds=180,
    concurrent_users=200
)

# Стресс тестирование
config = LoadTestConfig(
    pattern=LoadTestPattern.STRESS,
    duration_seconds=600,
    concurrent_users=500
)

# Запуск теста
result = await client.run_load_test(config)
```

### Метрики производительности

- **Response Time**: среднее, мин, макс время ответа
- **Throughput**: запросов в секунду (RPS)
- **Percentiles**: 95-й и 99-й перцентили
- **Success Rate**: процент успешных запросов
- **Error Analysis**: детальный анализ ошибок

### Генераторы тестовых данных

```python
config = LoadTestConfig(
    pattern=LoadTestPattern.CONSTANT_LOAD,
    duration_seconds=60,
    concurrent_users=20,
    test_data_generators={
        "/api/posts": lambda: {
            "title": f"Post {random.randint(1, 1000)}",
            "content": "Test content for load testing"
        },
        "/api/users": lambda: {
            "email": f"user{random.randint(1, 10000)}@test.com",
            "name": f"User {random.randint(1, 1000)}"
        }
    }
)
```

## 🤖 AI-Powered Test Generation

### Автоматическая генерация из OpenAPI

```python
async with AsyncApiTestClient(app=app) as client:
    # Загрузка схемы
    schema = client.load_openapi_schema()  # Из app
    # или
    schema = client.load_openapi_schema("openapi.json")  # Из файла

    # Генерация тестов
    tests = client.generate_tests_from_schema()

    # Сохранение в файлы
    client.save_generated_tests("generated_tests/")

    # Валидация тестов
    validation = await client.validate_generated_tests()
    print(f"Success Rate: {validation['success_rate']:.1%}")
```

### Типы генерируемых тестов

1. **Success Tests** - тесты успешного выполнения

   - Корректные данные
   - Ожидаемые статус коды
   - Confidence: 0.9

2. **Validation Tests** - тесты валидации

   - Отсутствующие обязательные параметры
   - Неверные типы данных
   - Confidence: 0.7-0.8

3. **Security Tests** - тесты безопасности

   - XSS payload в данных
   - SQL injection в параметрах
   - Confidence: 0.6

4. **Authorization Tests** - тесты авторизации
   - Запросы без токенов
   - Недействительные токены
   - Confidence: 0.8

### Структура сгенерированного теста

```python
@dataclass
class AIGeneratedTest:
    test_name: str                              # Имя теста
    endpoint: str                               # Путь endpoint
    method: str                                 # HTTP метод
    test_description: str                       # Описание теста
    test_code: str                             # Код теста
    test_data: Dict[str, Any]                  # Тестовые данные
    expected_status: int                       # Ожидаемый статус
    schema_validation: bool = True             # Валидация схемы
    security_checks: List[SecurityTestType]    # Проверки безопасности
    confidence_score: float = 0.0              # Уверенность (0.0-1.0)
```

## 🔄 Интеграция всех функций

### Комплексный сценарий тестирования

```python
async def comprehensive_api_testing():
    async with AsyncApiTestClient(app=app) as client:
        # Включаем трекинг производительности
        client.enable_performance_tracking()

        # Создаем тестовую сессию
        async with client.test_session(TestScenarioType.INTEGRATION) as session:

            # 1. Аутентификация
            await client.force_auth(email="test@example.com")

            # 2. WebSocket тестирование
            async with client.websocket_test_session("/ws/notifications") as ws_conn:
                await client.websocket_send(ws_conn, {"subscribe": "user_updates"})
                notification = await client.websocket_receive(ws_conn)

            # 3. Базовые API тесты
            response = await client.get("/api/users/me")
            assert response.status_code == 200

            # 4. Сканирование безопасности
            security_results = await client.run_security_scan(["/api/users/me"])
            critical_vulns = client.get_vulnerabilities_by_risk("HIGH")
            assert len(critical_vulns) == 0, "Critical vulnerabilities found!"

            # 5. Мини нагрузочный тест
            load_config = LoadTestConfig(
                pattern=LoadTestPattern.CONSTANT_LOAD,
                duration_seconds=10,
                concurrent_users=5,
                endpoints=["/api/users/me"]
            )
            load_results = await client.run_load_test(load_config)
            assert load_results.average_response_time < 0.5, "Performance degraded!"

            # 6. AI генерация дополнительных тестов
            generated_tests = client.generate_tests_from_schema()
            validation_results = await client.validate_generated_tests()

            # 7. Метрики производительности
            perf_stats = client.get_performance_stats()

            print(f"Integration Test Summary:")
            print(f"  Total Requests: {perf_stats['total_requests']}")
            print(f"  Avg Response Time: {perf_stats['avg_response_time']:.3f}s")
            print(f"  Security Score: {client.generate_security_report()['security_score']}/100")
            print(f"  Generated Tests: {len(generated_tests)}")
            print(f"  WebSocket Messages: {len(session.metrics)}")
```

## 📊 Отчеты и аналитика

### Security Report

```json
{
  "total_tests": 45,
  "total_vulnerabilities": 2,
  "security_score": 85,
  "risk_breakdown": {
    "HIGH": 0,
    "MEDIUM": 2,
    "LOW": 0
  },
  "test_coverage": {
    "sql_injection": 8,
    "xss": 6,
    "rate_limiting": 4,
    "auth_bypass": 8
  },
  "recommendations": ["Implement rate limiting", "Add security headers"]
}
```

### Load Test Results

```json
{
  "config": {
    "pattern": "ramp_up",
    "duration_seconds": 60,
    "concurrent_users": 50
  },
  "total_requests": 2547,
  "successful_requests": 2540,
  "failed_requests": 7,
  "average_response_time": 0.127,
  "min_response_time": 0.045,
  "max_response_time": 2.341,
  "percentile_95": 0.298,
  "percentile_99": 0.756,
  "requests_per_second": 42.45,
  "errors": ["Connection timeout", "Rate limit exceeded"]
}
```

### Performance Metrics

```json
{
  "total_requests": 156,
  "avg_response_time": 0.089,
  "min_response_time": 0.023,
  "max_response_time": 0.445,
  "total_time": 13.884,
  "requests_per_second": 11.24
}
```

## 🎯 Best Practices

### WebSocket Testing

1. **Используйте контекстные менеджеры** для автоматического закрытия соединений
2. **Тестируйте reconnection logic** при обрывах соединения
3. **Проверяйте ping/pong** для мониторинга здоровья соединения
4. **Логируйте все события** для отладки

### Security Testing

1. **Запускайте регулярно** в рамках CI/CD pipeline
2. **Фильтруйте по критичности** для приоритизации исправлений
3. **Документируйте исключения** для ложных срабатываний
4. **Интегрируйте с SIEM** системами для мониторинга

### Load Testing

1. **Начинайте с малых нагрузок** и постепенно увеличивайте
2. **Мониторьте ресурсы сервера** во время тестов
3. **Используйте realistic data** для точности результатов
4. **Анализируйте percentiles**, а не только средние значения

### AI Test Generation

1. **Проверяйте confidence scores** перед использованием
2. **Дополняйте ручными тестами** для сложной логики
3. **Регулярно обновляйте** при изменении API
4. **Валидируйте сгенерированные тесты** перед коммитом

## 🔧 Конфигурация и настройка

### Переменные окружения

```bash
# WebSocket
WEBSOCKET_TIMEOUT=30
WEBSOCKET_MAX_CONNECTIONS=100

# Security
SECURITY_SCAN_PARALLEL=true
SECURITY_STRICT_MODE=false

# Load Testing
LOAD_TEST_MAX_WORKERS=50
LOAD_TEST_TIMEOUT=300

# AI Generation
AI_CONFIDENCE_THRESHOLD=0.7
AI_MAX_TESTS_PER_ENDPOINT=5
```

### Кастомизация payloads

```python
# Добавление собственных security payloads
client._security_payloads[SecurityTestType.SQL_INJECTION].extend([
    "admin'; DROP TABLE sessions; --",
    "1' UNION SELECT password FROM users --"
])

# Кастомные генераторы данных для нагрузочных тестов
def generate_complex_user_data():
    return {
        "profile": {
            "name": fake.name(),
            "email": fake.email(),
            "preferences": {
                "theme": random.choice(["light", "dark"]),
                "language": random.choice(["en", "ru", "es"])
            }
        }
    }

config.test_data_generators["/api/users"] = generate_complex_user_data
```

## 📈 Metrics и мониторинг

### Интеграция с Prometheus

```python
# Экспорт метрик в Prometheus формате
def export_metrics_to_prometheus():
    perf_stats = client.get_performance_stats()
    security_report = client.generate_security_report()

    metrics = [
        f"api_response_time_avg {perf_stats['avg_response_time']}",
        f"api_requests_total {perf_stats['total_requests']}",
        f"api_security_score {security_report['security_score']}",
        f"api_vulnerabilities_total {security_report['total_vulnerabilities']}"
    ]

    with open("metrics.prom", "w") as f:
        f.write("\n".join(metrics))
```

### Интеграция с CI/CD

```yaml
# GitHub Actions example
- name: Advanced API Testing
  run: |
    python -m pytest tests/ --cov=src --security-scan --load-test --ai-generate

- name: Security Gate
  run: |
    if [ $(python -c "import json; print(json.load(open('security_report.json'))['security_score'])") -lt 80 ]; then
      echo "Security score too low"
      exit 1
    fi
```

## 🔮 Roadmap

### Планируемые улучшения

1. **GraphQL поддержка** - тестирование GraphQL endpoints
2. **gRPC интеграция** - поддержка gRPC сервисов
3. **Chaos Engineering** - injection ошибок и сбоев
4. **Machine Learning** - улучшение AI генерации через ML
5. **Visual Testing** - screenshot тестирование UI
6. **API Contract Testing** - проверка совместимости версий

### Экспериментальные функции

- **Fuzzing** - автоматическая генерация edge-case данных
- **Behavioral Testing** - анализ паттернов поведения API
- **Distributed Testing** - координация тестов между узлами
- **Real-time Analytics** - live дашборды с метриками

## 📞 Поддержка

Для вопросов и предложений:

- Создавайте Issues в репозитории
- Используйте Discussions для обсуждений
- Читайте документацию в `docs/`
- Изучайте примеры в `examples/`

---

**AsyncApiTestClient** теперь представляет собой комплексную платформу для enterprise-уровня тестирования API с современными возможностями автоматизации, безопасности и производительности.
