#!/usr/bin/env python3
"""
Упрощенные примеры использования системы аутентификации.

Этот файл содержит практические примеры работы с:
- Регистрацией и аутентификацией пользователей
- JWT токенами и refresh токенами
- Системой ролей и разрешений
- Защищенными endpoints
- Различными типами аутентификации
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def user_registration_example():
    """Пример регистрации пользователя."""
    print("👤 Пример регистрации пользователя")

    # Данные для регистрации
    user_data = {
        "email": "john.doe@example.com",
        "username": "johndoe",
        "password": "SecurePassword123!",
        "password_confirm": "SecurePassword123!",
        "full_name": "John Doe",
    }

    try:
        print(f"📝 Регистрируем пользователя: {user_data['email']}")
        print(f"   Username: {user_data['username']}")
        print(f"   Full name: {user_data['full_name']}")

        # В реальном приложении:
        # POST /auth/register
        # {
        #   "email": "john.doe@example.com",
        #   "username": "johndoe",
        #   "password": "SecurePassword123!",
        #   "password_confirm": "SecurePassword123!",
        #   "full_name": "John Doe"
        # }

        print("✅ Пример регистрации подготовлен")
        print("   📡 Endpoint: POST /auth/register")

    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")


async def user_login_example():
    """Пример входа в систему."""
    print("\n🔐 Пример входа в систему")

    # Данные для входа
    login_data = {"email": "john.doe@example.com", "password": "SecurePassword123!"}

    try:
        print(f"🔑 Вход пользователя: {login_data['email']}")

        # В реальном приложении:
        # POST /auth/login
        # {
        #   "email": "john.doe@example.com",
        #   "password": "SecurePassword123!"
        # }

        # Имитация успешного ответа
        mock_response = {
            "user": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_active": True,
                "is_verified": True,
            },
            "tokens": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
            },
        }

        print("✅ Вход выполнен успешно")
        print(f"   Access token: {mock_response['tokens']['access_token'][:50]}...")
        print(f"   Expires in: {mock_response['tokens']['expires_in']} секунд")
        print("   📡 Endpoint: POST /auth/login")

        return mock_response

    except Exception as e:
        logger.error(f"Ошибка входа: {e}")


async def token_operations_example():
    """Пример работы с JWT токенами."""
    print("\n🎫 Пример работы с токенами")

    try:
        # Создание токенов
        user_data = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "john.doe@example.com",
            "username": "johndoe",
        }

        print("🔨 Создание токенов...")

        # Имитация токенов
        access_token = (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZW1haWwiOiJqb2huQGV4YW1wbGUuY29tIn0..."
        )
        refresh_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzIiwidHlwZSI6InJlZnJlc2gifQ..."

        print(f"✅ Access token создан: {access_token[:50]}...")
        print(f"✅ Refresh token создан: {refresh_token[:50]}...")

        # Валидация токена
        print("\n🔍 Валидация access token...")
        print("   📡 Endpoint: GET /auth/validate")
        print("   📋 Headers: Authorization: Bearer <access_token>")

        # Обновление токенов
        print("\n🔄 Обновление токенов...")
        print("   📡 Endpoint: POST /auth/refresh")
        print('   📋 Body: {"refresh_token": "<refresh_token>"}')

        print("✅ Операции с токенами завершены")

    except Exception as e:
        logger.error(f"Ошибка работы с токенами: {e}")


async def password_operations_example():
    """Пример работы с паролями."""
    print("\n🔒 Пример работы с паролями")

    try:
        passwords = ["weak", "password123", "StrongPassword123!", "VerySecurePassword123!@#"]

        for password in passwords:
            print(f"\n🔍 Проверка пароля: '{password}'")

            # Простая проверка силы пароля
            is_strong = (
                len(password) >= 8
                and any(c.isupper() for c in password)
                and any(c.islower() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)
            )

            print(f"   Сильный: {'✅' if is_strong else '❌'}")

            if is_strong:
                print(f"   Хеш: bcrypt_hash_example...")
                print(f"   Проверка: ✅")

        print("\n✅ Операции с паролями завершены")

    except Exception as e:
        logger.error(f"Ошибка работы с паролями: {e}")


async def api_key_authentication_example():
    """Пример аутентификации через API ключи."""
    print("\n🔑 Пример аутентификации через API ключи")

    try:
        # Настройка API ключей в конфигурации
        api_keys = ["api_key_12345", "mobile_app_key_67890", "service_key_abcdef"]

        print("📋 Настроенные API ключи:")
        for i, key in enumerate(api_keys, 1):
            print(f"   {i}. {key}")

        # Пример использования API ключа в заголовках
        headers_examples = [
            {"X-API-Key": "api_key_12345"},
            {"Authorization": "ApiKey api_key_12345"},
            {"X-API-Key": "invalid_key"},  # Невалидный ключ
        ]

        for headers in headers_examples:
            print(f"\n🔍 Проверка заголовков: {headers}")

            # Имитация проверки
            api_key = headers.get("X-API-Key") or headers.get("Authorization", "").replace("ApiKey ", "")
            is_valid = api_key in api_keys

            print(f"   Результат: {'✅ Валидный' if is_valid else '❌ Невалидный'}")

        print("\n📡 Примеры endpoints с API ключами:")
        print("   GET /api/data?api_key=service_key_123")
        print("   POST /api/webhook?api_key=integration_789")
        print("   Headers: X-API-Key: api_key_12345")

        print("\n✅ Примеры API ключей завершены")

    except Exception as e:
        logger.error(f"Ошибка API ключей: {e}")


async def websocket_authentication_example():
    """Пример аутентификации WebSocket соединений."""
    print("\n🌐 Пример аутентификации WebSocket")

    try:
        # Различные способы аутентификации WebSocket
        auth_methods = [
            {"type": "jwt_token", "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."},
            {"type": "api_key", "key": "api_key_12345"},
            {"type": "query_params", "token": "ws_token_xyz"},
            {"type": "no_auth", "anonymous": True},
        ]

        for method in auth_methods:
            print(f"\n🔌 Метод аутентификации: {method['type']}")

            if method["type"] == "jwt_token":
                print(f"   JWT токен: {method['token'][:30]}...")
                print("   📡 URL: ws://localhost:8000/realtime/ws")
                print("   📋 Headers: Authorization: Bearer <token>")
                print("   ✅ WebSocket соединение аутентифицировано через JWT")

            elif method["type"] == "api_key":
                print(f"   API ключ: {method['key']}")
                print("   📡 URL: ws://localhost:8000/realtime/ws")
                print("   📋 Headers: X-API-Key: <api_key>")
                print("   ✅ WebSocket соединение аутентифицировано через API ключ")

            elif method["type"] == "query_params":
                print(f"   Токен в параметрах: {method['token']}")
                print("   📡 URL: ws://localhost:8000/realtime/ws?token=ws_token_xyz")
                print("   ✅ WebSocket соединение аутентифицировано через параметры")

            elif method["type"] == "no_auth":
                print("   Анонимное соединение")
                print("   📡 URL: ws://localhost:8000/realtime/ws")
                print("   ⚠️ WebSocket соединение без аутентификации")

        print("\n✅ Примеры WebSocket аутентификации завершены")

    except Exception as e:
        logger.error(f"Ошибка WebSocket аутентификации: {e}")


async def sse_authentication_example():
    """Пример аутентификации SSE соединений."""
    print("\n📡 Пример аутентификации SSE")

    try:
        # Примеры SSE аутентификации
        sse_requests = [
            {
                "url": "/realtime/events",
                "headers": {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."},
                "description": "SSE с JWT токеном в заголовке",
            },
            {"url": "/realtime/events", "headers": {"X-API-Key": "api_key_12345"}, "description": "SSE с API ключом"},
            {"url": "/realtime/events?token=sse_token_abc", "headers": {}, "description": "SSE с токеном в параметрах"},
            {"url": "/realtime/events", "headers": {}, "description": "SSE без аутентификации"},
        ]

        for request in sse_requests:
            print(f"\n📨 {request['description']}")
            print(f"   📡 URL: {request['url']}")
            print(f"   📋 Заголовки: {request['headers']}")

            has_auth = bool(request["headers"]) or "token=" in request["url"]
            print(f"   Результат: {'✅ Аутентифицирован' if has_auth else '⚠️ Анонимный доступ'}")

        print("\n✅ Примеры SSE аутентификации завершены")

    except Exception as e:
        logger.error(f"Ошибка SSE аутентификации: {e}")


async def role_permissions_example():
    """Пример системы ролей и разрешений."""
    print("\n👑 Пример системы ролей и разрешений")

    try:
        # Определение ролей и разрешений
        roles_permissions = {
            "guest": {"permissions": ["read_public"], "description": "Гостевой доступ"},
            "user": {"permissions": ["read_public", "read_own", "write_own"], "description": "Обычный пользователь"},
            "moderator": {
                "permissions": ["read_public", "read_own", "write_own", "moderate_content"],
                "description": "Модератор контента",
            },
            "admin": {
                "permissions": ["read_public", "read_own", "write_own", "moderate_content", "manage_users"],
                "description": "Администратор",
            },
            "superuser": {
                "permissions": ["*"],  # Все разрешения
                "description": "Суперпользователь",
            },
        }

        # Примеры проверки разрешений
        test_cases = [
            {"user_role": "guest", "action": "read_public", "resource": "article"},
            {"user_role": "user", "action": "write_own", "resource": "profile"},
            {"user_role": "user", "action": "manage_users", "resource": "user_list"},
            {"user_role": "moderator", "action": "moderate_content", "resource": "comment"},
            {"user_role": "admin", "action": "manage_users", "resource": "user_account"},
            {"user_role": "superuser", "action": "delete_system", "resource": "database"},
        ]

        print("📋 Роли и разрешения:")
        for role, info in roles_permissions.items():
            print(f"   {role}: {info['description']}")
            print(f"      Разрешения: {', '.join(info['permissions'])}")

        print("\n🔍 Проверка разрешений:")
        for case in test_cases:
            role = case["user_role"]
            action = case["action"]
            resource = case["resource"]

            # Проверка разрешения
            user_permissions = roles_permissions.get(role, {}).get("permissions", [])
            has_permission = "*" in user_permissions or action in user_permissions

            status = "✅ Разрешено" if has_permission else "❌ Запрещено"
            print(f"   {role} → {action} на {resource}: {status}")

        print("\n📡 Примеры endpoints с ролевой авторизацией:")
        print("   GET /auth/profile - требует роль 'user'")
        print("   GET /auth/verified-only - требует верификацию")
        print("   GET /admin/users - требует роль 'superuser'")
        print("   POST /admin/actions - требует роль 'superuser'")

        print("\n✅ Примеры ролей и разрешений завершены")

    except Exception as e:
        logger.error(f"Ошибка ролей и разрешений: {e}")


async def optional_authentication_example():
    """Пример опциональной аутентификации."""
    print("\n🔓 Пример опциональной аутентификации")

    try:
        # Примеры запросов с опциональной аутентификацией
        requests = [
            {
                "endpoint": "/public/content",
                "headers": {"Authorization": "Bearer valid_token"},
                "description": "Аутентифицированный пользователь",
            },
            {"endpoint": "/public/content", "headers": {}, "description": "Анонимный пользователь"},
            {
                "endpoint": "/public/content",
                "headers": {"Authorization": "Bearer invalid_token"},
                "description": "Невалидный токен",
            },
        ]

        for request in requests:
            print(f"\n🌍 {request['description']}")
            print(f"   📡 Endpoint: {request['endpoint']}")

            has_token = "Authorization" in request["headers"]
            is_valid_token = has_token and "valid_token" in request["headers"]["Authorization"]

            if is_valid_token:
                print("   👤 Пользователь: john.doe@example.com")
                print("   🎯 Персонализированный контент")
                print("   📊 Расширенная аналитика")
            elif has_token:
                print("   ⚠️ Невалидный токен - игнорируется")
                print("   👤 Пользователь: Анонимный")
                print("   🌐 Общий контент")
            else:
                print("   👤 Пользователь: Анонимный")
                print("   🌐 Общий контент")

        print("\n📡 Примеры endpoints с опциональной аутентификацией:")
        print("   GET /examples/auth/public - работает для всех")
        print("   GET /examples/auth/mixed-content?include_private=true - требует токен для приватной части")

        print("\n✅ Примеры опциональной аутентификации завершены")

    except Exception as e:
        logger.error(f"Ошибка опциональной аутентификации: {e}")


async def main():
    """Запуск всех примеров."""
    print("🚀 Запуск упрощенных примеров аутентификации\n")

    # Основные операции
    await user_registration_example()
    await user_login_example()
    await token_operations_example()
    await password_operations_example()

    # Расширенные типы аутентификации
    await api_key_authentication_example()
    await websocket_authentication_example()
    await sse_authentication_example()
    await optional_authentication_example()
    await role_permissions_example()

    print("\n🎉 Все примеры завершены!")
    print("\n📚 Дополнительные ресурсы:")
    print("   📖 Документация: docs/")
    print("   🧪 Тесты: tests/apps/auth/")
    print("   🔧 Примеры endpoints: examples/auth_endpoints_examples.py")
    print("   🌐 URL примеры: docs/url_for_examples.md")


if __name__ == "__main__":
    asyncio.run(main())
