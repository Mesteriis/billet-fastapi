"""
Тесты для API роутов пользователей.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User


@pytest.mark.users
class TestUserProfile:
    """Тесты работы с профилем пользователя."""

    @pytest.mark.asyncio
    async def test_get_my_profile(self, async_client: AsyncClient, auth_headers: dict, test_user: User, helpers):
        """Тест получения своего профиля."""
        response = await async_client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_user_response(data, test_user.email)
        assert data["id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_get_my_profile_unauthorized(self, async_client: AsyncClient):
        """Тест получения профиля без авторизации."""
        response = await async_client.get("/api/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_my_profile(
        self, async_client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession, helpers
    ):
        """Тест обновления своего профиля."""
        update_data = {"full_name": "Updated Test User", "bio": "Updated bio"}

        response = await async_client.put("/api/v1/users/me", json=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["full_name"] == "Updated Test User"
        assert data["bio"] == "Updated bio"
        helpers.assert_user_response(data, test_user.email)

    @pytest.mark.asyncio
    async def test_change_my_password(
        self, async_client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """Тест смены пароля."""
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        response = await async_client.post("/api/v1/users/me/change-password", json=password_data, headers=auth_headers)

        assert response.status_code == 204

        # Проверяем, что старый пароль больше не работает
        login_data = {"email": test_user.email, "password": "TestPassword123!"}

        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 401

        # Проверяем, что новый пароль работает
        new_login_data = {"email": test_user.email, "password": "NewPassword123!"}

        new_login_response = await async_client.post("/api/v1/auth/login", json=new_login_data)
        assert new_login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Тест смены пароля с неверным текущим паролем."""
        password_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        response = await async_client.post("/api/v1/users/me/change-password", json=password_data, headers=auth_headers)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Тест смены пароля с несовпадающими новыми паролями."""
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "DifferentPassword123!",
        }

        response = await async_client.post("/api/v1/users/me/change-password", json=password_data, headers=auth_headers)

        assert response.status_code == 422


@pytest.mark.users
class TestUserRetrieval:
    """Тесты получения данных пользователей."""

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, async_client: AsyncClient, auth_headers: dict, test_user: User, helpers):
        """Тест получения пользователя по ID."""
        response = await async_client.get(f"/api/v1/users/{test_user.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_user_response(data, test_user.email)
        assert data["id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, async_client: AsyncClient, auth_headers: dict):
        """Тест получения несуществующего пользователя."""
        import uuid

        fake_id = uuid.uuid4()

        response = await async_client.get(f"/api/v1/users/{fake_id}", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_users_list(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession, helpers
    ):
        """Тест получения списка пользователей."""
        # Создаем дополнительных пользователей
        await helpers.create_test_users(db_session, count=3)

        response = await async_client.get("/api/v1/users/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 4  # test_user + 3 новых пользователя

        # Проверяем структуру первого пользователя
        if data:
            helpers.assert_user_response(data[0], data[0]["email"])

    @pytest.mark.asyncio
    async def test_get_users_list_pagination(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Тест пагинации списка пользователей."""
        # Создаем дополнительных пользователей
        await helpers.create_test_users(db_session, count=5)

        # Получаем первую страницу
        response1 = await async_client.get("/api/v1/users/?skip=0&limit=3", headers=auth_headers)

        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) == 3

        # Получаем вторую страницу
        response2 = await async_client.get("/api/v1/users/?skip=3&limit=3", headers=auth_headers)

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2) >= 1

        # Проверяем, что ID разные
        ids1 = {user["id"] for user in data1}
        ids2 = {user["id"] for user in data2}
        assert ids1.isdisjoint(ids2)

    @pytest.mark.asyncio
    async def test_search_users(self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession, helpers):
        """Тест поиска пользователей."""
        # Создаем пользователей с определенными именами
        from apps.auth.auth_service import auth_service
        from apps.users.schemas import UserCreate

        search_user_data = UserCreate(
            email="searchable@example.com",
            username="searchable",
            full_name="John Searchable",
            password="SearchPassword123!",
            password_confirm="SearchPassword123!",
        )

        await auth_service.register_user(db_session, user_data=search_user_data, auto_verify=True)
        await db_session.commit()

        # Ищем по имени
        response = await async_client.get("/api/v1/users/search/?q=searchable", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1

        # Проверяем, что найденный пользователь содержит поисковый запрос
        found_user = next((user for user in data if "searchable" in user["username"].lower()), None)
        assert found_user is not None

    @pytest.mark.asyncio
    async def test_search_users_no_results(self, async_client: AsyncClient, auth_headers: dict):
        """Тест поиска пользователей без результатов."""
        response = await async_client.get("/api/v1/users/search/?q=nonexistentuser12345", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0


@pytest.mark.users
class TestAdminOperations:
    """Тесты административных операций."""

    @pytest.mark.asyncio
    async def test_admin_update_user(
        self, async_client: AsyncClient, admin_auth_headers: dict, test_user: User, helpers
    ):
        """Тест обновления пользователя админом."""
        update_data = {"full_name": "Admin Updated Name", "is_verified": True}

        response = await async_client.put(f"/api/v1/users/{test_user.id}", json=update_data, headers=admin_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["full_name"] == "Admin Updated Name"
        assert data["is_verified"] is True
        helpers.assert_user_response(data, test_user.email)

    @pytest.mark.asyncio
    async def test_admin_update_user_forbidden(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Тест обновления пользователя обычным пользователем."""
        update_data = {"full_name": "Forbidden Update", "is_verified": True}

        response = await async_client.put(f"/api/v1/users/{test_user.id}", json=update_data, headers=auth_headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_deactivate_user(
        self, async_client: AsyncClient, admin_auth_headers: dict, test_user: User, helpers
    ):
        """Тест деактивации пользователя админом."""
        response = await async_client.post(f"/api/v1/users/{test_user.id}/deactivate", headers=admin_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["is_active"] is False
        helpers.assert_user_response(data, test_user.email)

    @pytest.mark.asyncio
    async def test_admin_delete_user_soft(
        self, async_client: AsyncClient, admin_auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """Тест мягкого удаления пользователя."""
        response = await async_client.delete(f"/api/v1/users/{test_user.id}", headers=admin_auth_headers)

        assert response.status_code == 200

        # Проверяем, что пользователь помечен как удаленный
        from apps.users.repository import UserRepository

        repo = UserRepository()
        db_user = await repo.get(db_session, id=test_user.id)
        assert db_user.deleted_at is not None

    @pytest.mark.asyncio
    async def test_admin_delete_user_hard(
        self, async_client: AsyncClient, admin_auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """Тест полного удаления пользователя."""
        response = await async_client.delete(
            f"/api/v1/users/{test_user.id}?hard_delete=true", headers=admin_auth_headers
        )

        assert response.status_code == 200

        # Проверяем, что пользователь полностью удален
        from src.apps.users.repository import UserRepository

        repo = UserRepository()
        db_user = await repo.get(db_session, id=test_user.id)
        assert db_user is None


@pytest.mark.users
@pytest.mark.integration
class TestUserManagementFlow:
    """Интеграционные тесты управления пользователями."""

    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(
        self, async_client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, helpers
    ):
        """Тест полного жизненного цикла пользователя."""
        # 1. Создаем пользователя через регистрацию
        user_data = {
            "email": "lifecycle@example.com",
            "username": "lifecycle",
            "full_name": "Lifecycle User",
            "password": "LifecyclePassword123!",
            "password_confirm": "LifecyclePassword123!",
        }

        register_response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        user_id = register_response.json()["user"]["id"]

        # 2. Получаем пользователя
        get_response = await async_client.get(f"/api/v1/users/{user_id}", headers=admin_auth_headers)
        assert get_response.status_code == 200

        # 3. Обновляем пользователя
        update_data = {"full_name": "Updated Lifecycle User"}
        update_response = await async_client.put(
            f"/api/v1/users/{user_id}", json=update_data, headers=admin_auth_headers
        )
        assert update_response.status_code == 200
        assert update_response.json()["full_name"] == "Updated Lifecycle User"

        # 4. Деактивируем пользователя
        deactivate_response = await async_client.post(f"/api/v1/users/{user_id}/deactivate", headers=admin_auth_headers)
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["is_active"] is False

        # 5. Удаляем пользователя
        delete_response = await async_client.delete(f"/api/v1/users/{user_id}", headers=admin_auth_headers)
        assert delete_response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_profile_management(self, async_client: AsyncClient, db_session: AsyncSession, helpers):
        """Тест управления профилем пользователя."""
        # 1. Регистрируемся
        user_data = {
            "email": "profile@example.com",
            "username": "profile",
            "full_name": "Profile User",
            "password": "ProfilePassword123!",
            "password_confirm": "ProfilePassword123!",
        }

        register_response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        access_token = register_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. Получаем свой профиль
        profile_response = await async_client.get("/api/v1/users/me", headers=headers)
        assert profile_response.status_code == 200

        # 3. Обновляем профиль
        update_data = {"full_name": "Updated Profile User", "bio": "This is my updated bio"}

        update_response = await async_client.put("/api/v1/users/me", json=update_data, headers=headers)
        assert update_response.status_code == 200
        assert update_response.json()["full_name"] == "Updated Profile User"
        assert update_response.json()["bio"] == "This is my updated bio"

        # 4. Меняем пароль
        password_data = {
            "current_password": "ProfilePassword123!",
            "new_password": "NewProfilePassword123!",
            "new_password_confirm": "NewProfilePassword123!",
        }

        password_response = await async_client.post(
            "/api/v1/users/me/change-password", json=password_data, headers=headers
        )
        assert password_response.status_code == 204

        # 5. Проверяем, что новый пароль работает
        login_data = {"email": "profile@example.com", "password": "NewProfilePassword123!"}

        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
