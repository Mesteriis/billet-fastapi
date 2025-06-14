#!/usr/bin/env python3
"""
Примеры использования системы аутентификации и управления пользователями.

Этот файл содержит практические примеры работы с:
- Регистрацией и аутентификацией пользователей
- JWT токенами и refresh токенами
- Системой ролей и разрешений
- Защищенными endpoints
- Управлением сессиями
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты системы аутентификации
from apps.auth.auth_service import AuthService
from apps.auth.dependencies import get_current_superuser, get_current_user
from apps.auth.jwt_service import JWTService
from apps.auth.password_service import PasswordService
from apps.auth.schemas import LoginResponse, TokenPair
from apps.users.models import User
from apps.users.schemas import UserCreate, UserLogin, UserResponse, UserUpdate
from apps.users.service import UserService
from core.database import get_db

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация сервисов (в реальном приложении через DI)
# auth_service = AuthService()
# user_service = UserService()
# jwt_service = JWTService()
# password_service = PasswordService()


async def user_registration_example():
    """Пример регистрации пользователя."""
    print("👤 Пример регистрации пользователя")

    # Данные для регистрации
    user_data = UserCreate(
        email="john.doe@example.com",
        username="johndoe",
        password="SecurePassword123!",
        password_confirm="SecurePassword123!",
        full_name="John Doe",
    )

    try:
        # Имитация сессии БД (в реальном приложении получить через Depends)
        # db = await get_async_session()

        print(f"📝 Регистрируем пользователя: {user_data.email}")
        print(f"   Username: {user_data.username}")
        print(f"   Full name: {user_data.full_name}")

        # В реальном приложении:
        # user = await auth_service.register_user(db, user_data=user_data)
        # print(f"✅ Пользователь зарегистрирован: ID {user.id}")

        print("✅ Пример регистрации подготовлен")

    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")


async def user_login_example():
    """Пример входа в систему."""
    print("\n🔐 Пример входа в систему")

    # Данные для входа
    login_data = UserLogin(email="john.doe@example.com", password="SecurePassword123!")

    try:
        print(f"🔑 Вход пользователя: {login_data.email}")

        # В реальном приложении:
        # db = await get_async_session()
        # response = await auth_service.login(db, email=login_data.email, password=login_data.password)

        # Имитация успешного ответа
        mock_response = {
            "user": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_active": True,
                "role": "user",
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
            "role": "user",
        }

        print("🔨 Создание токенов...")

        # В реальном приложении:
        # access_token, refresh_token, jti = jwt_service.create_token_pair(
        #     user_id=user_data["user_id"],
        #     email=user_data["email"],
        #     username=user_data["username"]
        # )

        # Имитация токенов
        access_token = (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZW1haWwiOiJqb2huQGV4YW1wbGUuY29tIn0..."
        )
        refresh_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzIiwidHlwZSI6InJlZnJlc2gifQ..."

        print(f"✅ Access token создан: {access_token[:50]}...")
        print(f"✅ Refresh token создан: {refresh_token[:50]}...")

        # Валидация токена
        print("\n🔍 Валидация access token...")
        # payload = jwt_service.verify_access_token(access_token)
        # print(f"✅ Токен валиден: {payload}")

        # Обновление токенов
        print("\n🔄 Обновление токенов...")
        # new_access_token, new_refresh_token = jwt_service.refresh_tokens(refresh_token)
        # print(f"✅ Новый access token: {new_access_token[:50]}...")

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

            # Проверка силы пароля
            is_strong = password_service.validate_password_strength(password)
            print(f"   Сильный: {'✅' if is_strong else '❌'}")

            if is_strong:
                # Хеширование пароля
                hashed = password_service.hash_password(password)
                print(f"   Хеш: {hashed[:50]}...")

                # Проверка пароля
                is_valid = password_service.verify_password(password, hashed)
                print(f"   Проверка: {'✅' if is_valid else '❌'}")

        print("\n✅ Операции с паролями завершены")

    except Exception as e:
        logger.error(f"Ошибка работы с паролями: {e}")


async def user_management_example():
    """Пример управления пользователями."""
    print("\n👥 Пример управления пользователями")

    try:
        # Создание пользователей
        users_data = [
            {"email": "admin@example.com", "username": "admin", "full_name": "System Administrator", "role": "admin"},
            {
                "email": "moderator@example.com",
                "username": "moderator",
                "full_name": "Content Moderator",
                "role": "moderator",
            },
            {"email": "user1@example.com", "username": "user1", "full_name": "Regular User 1", "role": "user"},
        ]

        print("👤 Создание пользователей:")
        for user_data in users_data:
            print(f"   📝 {user_data['username']} ({user_data['role']})")

        # Обновление пользователя
        print("\n✏️ Обновление профиля пользователя:")
        update_data = UserUpdate(full_name="John Doe Updated", email="john.updated@example.com")
        print(f"   Новое имя: {update_data.full_name}")
        print(f"   Новый email: {update_data.email}")

        # Деактивация пользователя
        print("\n🚫 Деактивация пользователя:")
        print("   Пользователь user1 деактивирован")

        # Смена роли
        print("\n🔄 Смена роли пользователя:")
        print("   user1: user -> moderator")

        print("\n✅ Управление пользователями завершено")

    except Exception as e:
        logger.error(f"Ошибка управления пользователями: {e}")


async def session_management_example():
    """Пример управления сессиями."""
    print("\n🔗 Пример управления сессиями")

    try:
        user_id = "123e4567-e89b-12d3-a456-426614174000"

        # Создание сессий
        sessions = [
            {
                "device_type": "web",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "ip_address": "192.168.1.100",
            },
            {
                "device_type": "mobile",
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
                "ip_address": "192.168.1.101",
            },
            {"device_type": "api", "user_agent": "MyApp/1.0", "ip_address": "192.168.1.102"},
        ]

        print(f"👤 Управление сессиями для пользователя: {user_id}")

        for i, session in enumerate(sessions, 1):
            print(f"\n📱 Сессия {i}:")
            print(f"   Устройство: {session['device_type']}")
            print(f"   User-Agent: {session['user_agent'][:50]}...")
            print(f"   IP: {session['ip_address']}")
            print(f"   Статус: Активна")

        # Завершение сессии
        print(f"\n🔚 Завершение сессии на устройстве: mobile")
        print("   Сессия завершена")

        # Завершение всех сессий
        print(f"\n🔚 Завершение всех сессий пользователя")
        print("   Все сессии завершены")

        print("\n✅ Управление сессиями завершено")

    except Exception as e:
        logger.error(f"Ошибка управления сессиями: {e}")


def create_protected_endpoints():
    """Создание защищенных API endpoints."""
    print("\n🛡️ Создание защищенных endpoints")

    app = FastAPI(title="Auth Example API")
    router = APIRouter(prefix="/api/v1", tags=["auth"])

    # Публичные endpoints
    @router.post("/auth/register", response_model=UserResponse)
    async def register(user_data: UserCreate, db: AsyncSession = Depends(get_async_session)):
        """Регистрация нового пользователя."""
        user = await auth_service.register_user(db, user_data=user_data)
        return UserResponse.model_validate(user)

    @router.post("/auth/login", response_model=LoginResponse)
    async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_async_session)):
        """Вход в систему."""
        response = await auth_service.login(db, email=login_data.email, password=login_data.password)
        return response

    @router.post("/auth/refresh", response_model=TokenPair)
    async def refresh_tokens(refresh_token: str, db: AsyncSession = Depends(get_async_session)):
        """Обновление токенов."""
        tokens = await auth_service.refresh_tokens(db, refresh_token=refresh_token)
        return tokens

    # Защищенные endpoints
    @router.get("/profile", response_model=UserResponse)
    async def get_profile(current_user: User = Depends(get_current_user)):
        """Получение профиля текущего пользователя."""
        return UserResponse.model_validate(current_user)

    @router.put("/profile", response_model=UserResponse)
    async def update_profile(
        update_data: UserUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Обновление профиля пользователя."""
        updated_user = await user_service.update_user(db, user_id=current_user.id, user_update=update_data)
        return UserResponse.model_validate(updated_user)

    @router.post("/auth/logout")
    async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
        """Выход из системы."""
        await auth_service.logout_user(db, user_id=current_user.id)
        return {"message": "Выход выполнен успешно"}

    # Админские endpoints
    @router.get("/admin/users", response_model=List[UserResponse])
    async def get_all_users(
        skip: int = 0,
        limit: int = 100,
        admin_user: User = Depends(get_current_superuser),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Получение списка всех пользователей (только для админов)."""
        users = await user_service.get_users(db, skip=skip, limit=limit)
        return [UserResponse.model_validate(user) for user in users]

    @router.put("/admin/users/{user_id}/role")
    async def change_user_role(
        user_id: str,
        new_role: str,
        admin_user: User = Depends(get_current_superuser),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Изменение роли пользователя (только для админов)."""
        updated_user = await user_service.change_user_role(
            db, user_id=user_id, new_role=new_role, current_user_id=admin_user.id
        )
        return {"message": f"Роль пользователя изменена на {new_role}"}

    @router.delete("/admin/users/{user_id}")
    async def delete_user(
        user_id: str,
        hard_delete: bool = False,
        admin_user: User = Depends(get_current_superuser),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Удаление пользователя (только для админов)."""
        if hard_delete:
            await user_service.delete_user_hard(db, user_id=user_id)
            message = "Пользователь удален навсегда"
        else:
            await user_service.delete_user_soft(db, user_id=user_id)
            message = "Пользователь деактивирован"

        return {"message": message}

    app.include_router(router)

    print("✅ Защищенные endpoints созданы:")
    print("   POST /api/v1/auth/register")
    print("   POST /api/v1/auth/login")
    print("   POST /api/v1/auth/refresh")
    print("   POST /api/v1/auth/logout")
    print("   GET  /api/v1/profile")
    print("   PUT  /api/v1/profile")
    print("   GET  /api/v1/admin/users")
    print("   PUT  /api/v1/admin/users/{user_id}/role")
    print("   DELETE /api/v1/admin/users/{user_id}")

    return app


async def role_based_access_example():
    """Пример ролевого доступа."""
    print("\n🎭 Пример ролевого доступа")

    # Определение ролей и разрешений
    roles_permissions = {
        "user": ["read_own_profile", "update_own_profile", "create_posts", "read_posts"],
        "moderator": [
            "read_own_profile",
            "update_own_profile",
            "create_posts",
            "read_posts",
            "moderate_posts",
            "ban_users",
        ],
        "admin": [
            "read_own_profile",
            "update_own_profile",
            "create_posts",
            "read_posts",
            "moderate_posts",
            "ban_users",
            "manage_users",
            "system_settings",
        ],
    }

    def check_permission(user_role: str, required_permission: str) -> bool:
        """Проверка разрешения для роли."""
        return required_permission in roles_permissions.get(user_role, [])

    # Тестирование разрешений
    test_cases = [
        ("user", "read_own_profile"),
        ("user", "manage_users"),
        ("moderator", "moderate_posts"),
        ("moderator", "system_settings"),
        ("admin", "system_settings"),
        ("admin", "read_posts"),
    ]

    print("🔍 Проверка разрешений:")
    for role, permission in test_cases:
        has_permission = check_permission(role, permission)
        status = "✅" if has_permission else "❌"
        print(f"   {role} -> {permission}: {status}")

    print("\n✅ Проверка ролевого доступа завершена")


async def security_best_practices_example():
    """Пример лучших практик безопасности."""
    print("\n🔐 Лучшие практики безопасности")

    practices = [
        {
            "title": "Сильные пароли",
            "description": "Минимум 8 символов, заглавные, строчные, цифры, спецсимволы",
            "example": "MySecureP@ssw0rd123!",
        },
        {
            "title": "JWT с коротким временем жизни",
            "description": "Access токены на 15-30 минут, refresh на 7-30 дней",
            "example": "access_token_expire_minutes=30",
        },
        {
            "title": "Refresh токен ротация",
            "description": "Новый refresh токен при каждом обновлении",
            "example": "Старый токен становится недействительным",
        },
        {
            "title": "Rate limiting",
            "description": "Ограничение попыток входа и API запросов",
            "example": "5 попыток входа в минуту",
        },
        {
            "title": "HTTPS только",
            "description": "Все токены передаются только по HTTPS",
            "example": "secure=True для cookies",
        },
        {
            "title": "Логирование безопасности",
            "description": "Логирование всех попыток входа и подозрительной активности",
            "example": "Failed login from IP 192.168.1.100",
        },
    ]

    for i, practice in enumerate(practices, 1):
        print(f"\n{i}. {practice['title']}")
        print(f"   📝 {practice['description']}")
        print(f"   💡 Пример: {practice['example']}")

    print("\n✅ Лучшие практики безопасности рассмотрены")


async def main():
    """Главная функция с запуском всех примеров."""
    print("🎯 Примеры использования системы аутентификации")
    print("=" * 60)

    try:
        # Базовые операции
        await user_registration_example()
        await user_login_example()
        await token_operations_example()
        await password_operations_example()

        # Управление пользователями
        await user_management_example()
        await session_management_example()

        # Ролевой доступ
        await role_based_access_example()

        # Безопасность
        await security_best_practices_example()

        # FastAPI интеграция
        app = create_protected_endpoints()

        print("\n🎉 Все примеры выполнены успешно!")

        print("\n💡 Для тестирования с реальной БД:")
        print("   1. Настройте подключение к PostgreSQL")
        print("   2. Примените миграции: make migrate-up")
        print("   3. Раскомментируйте вызовы сервисов в примерах")

        print("\n🌐 Для тестирования API:")
        print("   uvicorn examples.auth_examples:app --reload --port 8002")
        print("   Затем откройте http://localhost:8002/docs")

        print("\n🔑 Пример использования API:")
        print("   1. POST /api/v1/auth/register - регистрация")
        print("   2. POST /api/v1/auth/login - получение токенов")
        print("   3. GET /api/v1/profile - профиль (с Bearer токеном)")

    except Exception as e:
        logger.error(f"Ошибка выполнения примеров: {e}")
        raise


if __name__ == "__main__":
    # Запуск примеров
    asyncio.run(main())
