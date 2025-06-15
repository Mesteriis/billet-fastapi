"""
Тесты для API роутов пользователей.
"""

import pytest


@pytest.mark.users
class TestUserProfile:
    """Тесты работы с профилем пользователя."""

    async def test_get_my_profile(self, api_client, verified_user, helpers):
        """Тест получения своего профиля."""
        await api_client.force_auth(verified_user)
        profile_url = api_client.url_for("get_my_profile")

        response = await api_client.get(profile_url)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_user_response(data, verified_user.email)
        assert data["id"] == str(verified_user.id)

    async def test_get_my_profile_unauthorized(self, api_client):
        """Тест получения профиля без авторизации."""
        profile_url = api_client.url_for("get_my_profile")

        response = await api_client.get(profile_url)

        assert response.status_code == 401

    async def test_update_my_profile(self, api_client, verified_user, helpers):
        """Тест обновления своего профиля."""
        await api_client.force_auth(verified_user)
        profile_url = api_client.url_for("update_my_profile")

        update_data = {"full_name": "Updated Name", "bio": "Updated bio"}

        response = await api_client.put(profile_url, json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["full_name"] == "Updated Name"
        assert data["bio"] == "Updated bio"

    async def test_update_my_profile_unauthorized(self, api_client):
        """Тест обновления профиля без авторизации."""
        profile_url = api_client.url_for("update_my_profile")

        update_data = {"full_name": "Updated Name"}

        response = await api_client.put(profile_url, json=update_data)

        assert response.status_code == 401

    async def test_change_my_password(self, api_client, verified_user):
        """Тест смены пароля."""
        await api_client.force_auth(verified_user)
        change_password_url = api_client.url_for("change_my_password")

        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        response = await api_client.post(change_password_url, json=password_data)

        assert response.status_code == 204

        # Проверяем, что старый пароль больше не работает
        login_url = api_client.url_for("login")
        login_data = {"email": verified_user.email, "password": "TestPassword123!"}

        login_response = await api_client.post(login_url, json=login_data)
        assert login_response.status_code == 401

        # Проверяем, что новый пароль работает
        new_login_data = {"email": verified_user.email, "password": "NewPassword123!"}

        new_login_response = await api_client.post(login_url, json=new_login_data)
        assert new_login_response.status_code == 200

    async def test_change_password_wrong_current(self, api_client, verified_user):
        """Тест смены пароля с неверным текущим паролем."""
        await api_client.force_auth(verified_user)
        change_password_url = api_client.url_for("change_my_password")

        password_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        response = await api_client.post(change_password_url, json=password_data)

        assert response.status_code == 400

    async def test_change_password_mismatch(self, api_client, verified_user):
        """Тест смены пароля с несовпадающими новыми паролями."""
        await api_client.force_auth(verified_user)
        change_password_url = api_client.url_for("change_my_password")

        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "DifferentPassword123!",
        }

        response = await api_client.post(change_password_url, json=password_data)

        assert response.status_code == 422


@pytest.mark.users
class TestUserRetrieval:
    """Тесты получения данных пользователей."""

    async def test_get_user_by_id(self, api_client, verified_user, helpers):
        """Тест получения пользователя по ID."""
        await api_client.force_auth(verified_user)
        user_detail_url = api_client.url_for("get_user_by_id", user_id=verified_user.id)

        response = await api_client.get(user_detail_url)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_user_response(data, verified_user.email)
        assert data["id"] == str(verified_user.id)

    async def test_get_user_by_id_not_found(self, api_client, verified_user):
        """Тест получения несуществующего пользователя."""
        import uuid

        await api_client.force_auth(verified_user)
        fake_id = uuid.uuid4()
        user_detail_url = api_client.url_for("get_user_by_id", user_id=fake_id)

        response = await api_client.get(user_detail_url)

        assert response.status_code == 404

    async def test_get_users_list(self, api_client, admin_user, user_factory, helpers):
        """Тест получения списка пользователей."""
        await api_client.force_auth(admin_user)

        # Создаем дополнительных пользователей
        await user_factory.create_batch(3)

        users_list_url = api_client.url_for("get_users_list")
        response = await api_client.get(users_list_url)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 4  # admin_user + 3 новых пользователя

        # Проверяем структуру первого пользователя
        if data:
            helpers.assert_user_response(data[0], data[0]["email"])

    async def test_get_users_list_pagination(self, api_client, admin_user, user_factory):
        """Тест пагинации списка пользователей."""
        await api_client.force_auth(admin_user)

        # Создаем дополнительных пользователей
        await user_factory.create_batch(5)

        # Получаем первую страницу
        users_list_url = api_client.url_for("get_users_list")
        response1 = await api_client.get(f"{users_list_url}?skip=0&limit=3")

        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) == 3

        # Получаем вторую страницу
        response2 = await api_client.get(f"{users_list_url}?skip=3&limit=3")

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2) >= 1

        # Проверяем, что ID разные
        ids1 = {user["id"] for user in data1}
        ids2 = {user["id"] for user in data2}
        assert ids1.isdisjoint(ids2)

    async def test_search_users(self, api_client, admin_user, user_factory, helpers):
        """Тест поиска пользователей."""
        await api_client.force_auth(admin_user)

        # Создаем пользователя с определенным именем
        searchable_user = await user_factory.create(username="searchable_user", full_name="John Searchable")

        # Ищем по имени
        search_url = api_client.url_for("search_users")
        response = await api_client.get(f"{search_url}?q=searchable")

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        found_user = next((u for u in data if u["id"] == str(searchable_user.id)), None)
        assert found_user is not None
        helpers.assert_user_response(found_user, searchable_user.email)

    async def test_search_users_no_results(self, api_client, admin_user):
        """Тест поиска пользователей без результатов."""
        await api_client.force_auth(admin_user)

        search_url = api_client.url_for("search_users")
        response = await api_client.get(f"{search_url}?q=nonexistent_user_12345")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


@pytest.mark.users
class TestAdminOperations:
    """Тесты административных операций с пользователями."""

    async def test_admin_update_user(self, api_client, admin_user, verified_user, helpers):
        """Тест обновления пользователя администратором."""
        await api_client.force_auth(admin_user)

        update_data = {"full_name": "Admin Updated User", "is_active": False}
        update_user_url = api_client.url_for("update_user", user_id=verified_user.id)

        response = await api_client.put(update_user_url, json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["full_name"] == "Admin Updated User"
        assert data["is_active"] is False
        helpers.assert_user_response(data, verified_user.email)

    async def test_admin_update_user_forbidden(self, api_client, verified_user, user_factory):
        """Тест запрета обновления пользователя обычным пользователем."""
        await api_client.force_auth(verified_user)

        other_user = await user_factory.create()
        update_data = {"full_name": "Forbidden Update"}
        update_user_url = api_client.url_for("update_user", user_id=other_user.id)

        response = await api_client.put(update_user_url, json=update_data)

        assert response.status_code == 403

    async def test_admin_deactivate_user(self, api_client, admin_user, verified_user, helpers):
        """Тест деактивации пользователя администратором."""
        await api_client.force_auth(admin_user)

        deactivate_data = {"is_active": False}
        update_user_url = api_client.url_for("update_user", user_id=verified_user.id)

        response = await api_client.put(update_user_url, json=deactivate_data)

        assert response.status_code == 200
        data = response.json()

        assert data["is_active"] is False
        helpers.assert_user_response(data, verified_user.email)

    async def test_admin_delete_user_soft(self, api_client, admin_user, user_factory):
        """Тест мягкого удаления пользователя."""
        await api_client.force_auth(admin_user)

        user_to_delete = await user_factory.create()
        delete_user_url = api_client.url_for("delete_user", user_id=user_to_delete.id)

        response = await api_client.delete(delete_user_url)

        assert response.status_code == 204

        # Проверяем, что пользователь больше не доступен
        get_user_url = api_client.url_for("get_user_by_id", user_id=user_to_delete.id)
        get_response = await api_client.get(get_user_url)
        assert get_response.status_code == 404

    async def test_admin_delete_user_hard(self, api_client, admin_user, user_factory):
        """Тест жесткого удаления пользователя."""
        await api_client.force_auth(admin_user)

        user_to_delete = await user_factory.create()
        delete_user_url = api_client.url_for("delete_user", user_id=user_to_delete.id)

        response = await api_client.delete(f"{delete_user_url}?hard=true")

        assert response.status_code == 204

        # Проверяем, что пользователь полностью удален
        get_user_url = api_client.url_for("get_user_by_id", user_id=user_to_delete.id)
        get_response = await api_client.get(get_user_url)
        assert get_response.status_code == 404


@pytest.mark.users
@pytest.mark.integration
class TestUserManagementFlow:
    """Интеграционные тесты полного жизненного цикла пользователя."""

    async def test_complete_user_lifecycle(self, api_client, admin_user, test_user_data, helpers):
        """Тест полного жизненного цикла пользователя от создания до удаления."""
        await api_client.force_auth(admin_user)

        # 1. Регистрация нового пользователя
        register_url = api_client.url_for("register")
        register_response = await api_client.post(register_url, json=test_user_data.model_dump())

        assert register_response.status_code == 201
        user_data = register_response.json()
        user_id = user_data["id"]

        # 2. Верификация пользователя (если требуется)
        # verify_url = api_client.url_for("verify_email")
        # verify_response = await api_client.post(verify_url, json={"token": "verification_token"})

        # 3. Вход в систему
        login_url = api_client.url_for("login")
        login_data = {"email": test_user_data.email, "password": test_user_data.password}
        login_response = await api_client.post(login_url, json=login_data)

        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens

        # 4. Получение профиля
        get_user_url = api_client.url_for("get_user_by_id", user_id=user_id)
        get_response = await api_client.get(get_user_url)

        assert get_response.status_code == 200
        helpers.assert_user_response(get_response.json(), test_user_data.email)

        # 5. Обновление профиля
        update_data = {"full_name": "Updated Lifecycle User", "bio": "Lifecycle test bio"}
        update_url = api_client.url_for("update_user", user_id=user_id)
        update_response = await api_client.put(update_url, json=update_data)

        assert update_response.status_code == 200
        updated_user = update_response.json()
        assert updated_user["full_name"] == "Updated Lifecycle User"

        # 6. Деактивация пользователя
        deactivate_data = {"is_active": False}
        deactivate_response = await api_client.put(update_url, json=deactivate_data)

        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["is_active"] is False

        # 7. Попытка входа деактивированного пользователя
        deactivated_login_response = await api_client.post(login_url, json=login_data)
        assert deactivated_login_response.status_code == 401

        # 8. Удаление пользователя
        delete_url = api_client.url_for("delete_user", user_id=user_id)
        delete_response = await api_client.delete(delete_url)

        assert delete_response.status_code == 204

        # 9. Проверка, что пользователь удален
        final_get_response = await api_client.get(get_user_url)
        assert final_get_response.status_code == 404

    async def test_user_profile_management(self, api_client, verified_user, helpers):
        """Тест управления профилем пользователя."""
        await api_client.force_auth(verified_user)

        # 1. Получение текущего профиля
        profile_url = api_client.url_for("get_my_profile")
        profile_response = await api_client.get(profile_url)

        assert profile_response.status_code == 200
        original_profile = profile_response.json()
        helpers.assert_user_response(original_profile, verified_user.email)

        # 2. Обновление профиля
        update_data = {"full_name": "Updated Profile Name", "bio": "Updated bio information"}
        update_profile_url = api_client.url_for("update_my_profile")
        update_response = await api_client.put(update_profile_url, json=update_data)

        assert update_response.status_code == 200
        updated_profile = update_response.json()

        assert updated_profile["full_name"] == "Updated Profile Name"
        assert updated_profile["bio"] == "Updated bio information"
        assert updated_profile["email"] == original_profile["email"]  # Email не изменился

        # 3. Смена пароля
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewSecurePassword123!",
            "new_password_confirm": "NewSecurePassword123!",
        }
        change_password_url = api_client.url_for("change_my_password")
        password_response = await api_client.post(change_password_url, json=password_data)

        assert password_response.status_code == 204

        # 4. Проверка, что новый пароль работает
        login_url = api_client.url_for("login")
        login_data = {"email": verified_user.email, "password": "NewSecurePassword123!"}
        login_response = await api_client.post(login_url, json=login_data)

        assert login_response.status_code == 200


@pytest.mark.users
class TestUserList:
    """Тесты получения списка пользователей."""

    async def test_get_users_as_admin(self, api_client, admin_user, user_factory):
        """Тест получения списка пользователей администратором."""
        await api_client.force_auth(admin_user)

        # Создаем дополнительных пользователей
        await user_factory.create_batch(3)

        users_url = api_client.url_for("get_users_list")
        response = await api_client.get(users_url)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 4  # admin + 3 новых

        # Проверяем, что все пользователи имеют нужные поля
        for user in data:
            assert "id" in user
            assert "email" in user
            assert "username" in user
            assert "is_active" in user

    async def test_get_users_as_regular_user(self, api_client, verified_user):
        """Тест получения списка пользователей обычным пользователем."""
        await api_client.force_auth(verified_user)

        users_url = api_client.url_for("get_users_list")
        response = await api_client.get(users_url)

        # Обычные пользователи могут видеть список (зависит от бизнес-логики)
        assert response.status_code in [200, 403]

    async def test_get_users_unauthorized(self, api_client):
        """Тест получения списка пользователей без авторизации."""
        users_url = api_client.url_for("get_users_list")
        response = await api_client.get(users_url)

        assert response.status_code == 401

    async def test_get_users_with_pagination(self, api_client, admin_user, user_factory):
        """Тест пагинации списка пользователей."""
        await api_client.force_auth(admin_user)

        # Создаем много пользователей
        await user_factory.create_batch(10)

        users_url = api_client.url_for("get_users_list")

        # Первая страница
        response1 = await api_client.get(f"{users_url}?skip=0&limit=5")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) == 5

        # Вторая страница
        response2 = await api_client.get(f"{users_url}?skip=5&limit=5")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2) >= 5

        # Проверяем, что пользователи разные
        ids1 = {user["id"] for user in data1}
        ids2 = {user["id"] for user in data2}
        assert ids1.isdisjoint(ids2)


@pytest.mark.users
class TestUserDetail:
    """Тесты получения детальной информации о пользователе."""

    async def test_get_user_by_id_as_admin(self, api_client, admin_user, verified_user, helpers):
        """Тест получения пользователя по ID администратором."""
        await api_client.force_auth(admin_user)

        user_url = api_client.url_for("get_user_by_id", user_id=verified_user.id)
        response = await api_client.get(user_url)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_user_response(data, verified_user.email)
        assert data["id"] == str(verified_user.id)

    async def test_get_user_by_id_self(self, api_client, verified_user, helpers):
        """Тест получения собственного профиля по ID."""
        await api_client.force_auth(verified_user)

        user_url = api_client.url_for("get_user_by_id", user_id=verified_user.id)
        response = await api_client.get(user_url)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_user_response(data, verified_user.email)
        assert data["id"] == str(verified_user.id)

    async def test_get_user_by_id_other_user(self, api_client, verified_user, user_factory):
        """Тест получения другого пользователя обычным пользователем."""
        await api_client.force_auth(verified_user)

        other_user = await user_factory.create()
        user_url = api_client.url_for("get_user_by_id", user_id=other_user.id)
        response = await api_client.get(user_url)

        # Зависит от бизнес-логики - может быть 200 или 403
        assert response.status_code in [200, 403]

    async def test_get_user_by_id_not_found(self, api_client, admin_user):
        """Тест получения несуществующего пользователя."""
        import uuid

        await api_client.force_auth(admin_user)

        fake_id = uuid.uuid4()
        user_url = api_client.url_for("get_user_by_id", user_id=fake_id)
        response = await api_client.get(user_url)

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    async def test_get_user_unauthorized(self, api_client, verified_user):
        """Тест получения пользователя без авторизации."""
        user_url = api_client.url_for("get_user_by_id", user_id=verified_user.id)
        response = await api_client.get(user_url)

        assert response.status_code == 401


@pytest.mark.users
class TestUserUpdate:
    """Тесты обновления пользователей."""

    async def test_update_own_profile(self, api_client, verified_user):
        """Тест обновления собственного профиля."""
        await api_client.force_auth(verified_user)

        update_data = {"full_name": "Self Updated Name", "bio": "Self updated bio"}
        profile_url = api_client.url_for("update_my_profile")
        response = await api_client.put(profile_url, json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["full_name"] == "Self Updated Name"
        assert data["bio"] == "Self updated bio"
        assert data["email"] == verified_user.email

    async def test_update_user_as_admin(self, api_client, admin_user, verified_user):
        """Тест обновления пользователя администратором."""
        await api_client.force_auth(admin_user)

        update_data = {"full_name": "Admin Updated Name", "is_active": False}
        user_url = api_client.url_for("update_user", user_id=verified_user.id)
        response = await api_client.put(user_url, json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["full_name"] == "Admin Updated Name"
        assert data["is_active"] is False

    async def test_update_other_user_forbidden(self, api_client, verified_user, user_factory):
        """Тест запрета обновления другого пользователя."""
        await api_client.force_auth(verified_user)

        other_user = await user_factory.create()
        update_data = {"full_name": "Forbidden Update"}
        user_url = api_client.url_for("update_user", user_id=other_user.id)
        response = await api_client.put(user_url, json=update_data)

        assert response.status_code == 403

    async def test_update_user_invalid_data(self, api_client, verified_user):
        """Тест обновления пользователя с невалидными данными."""
        await api_client.force_auth(verified_user)

        invalid_data = {"email": "invalid-email"}  # Невалидный email
        profile_url = api_client.url_for("update_my_profile")
        response = await api_client.put(profile_url, json=invalid_data)

        assert response.status_code == 422

    async def test_update_user_unauthorized(self, api_client, verified_user):
        """Тест обновления пользователя без авторизации."""
        update_data = {"full_name": "Unauthorized Update"}
        profile_url = api_client.url_for("update_my_profile")
        response = await api_client.put(profile_url, json=update_data)

        assert response.status_code == 401


@pytest.mark.users
class TestUserDelete:
    """Тесты удаления пользователей."""

    async def test_delete_user_as_admin(self, api_client, admin_user, user_factory):
        """Тест удаления пользователя администратором."""
        await api_client.force_auth(admin_user)

        user_to_delete = await user_factory.create()
        delete_url = api_client.url_for("delete_user", user_id=user_to_delete.id)
        response = await api_client.delete(delete_url)

        assert response.status_code == 204

        # Проверяем, что пользователь удален
        get_url = api_client.url_for("get_user_by_id", user_id=user_to_delete.id)
        get_response = await api_client.get(get_url)
        assert get_response.status_code == 404

    async def test_delete_self_forbidden(self, api_client, verified_user):
        """Тест запрета самоудаления."""
        await api_client.force_auth(verified_user)

        delete_url = api_client.url_for("delete_user", user_id=verified_user.id)
        response = await api_client.delete(delete_url)

        assert response.status_code == 403

    async def test_delete_user_as_regular_user(self, api_client, verified_user, user_factory):
        """Тест запрета удаления пользователя обычным пользователем."""
        await api_client.force_auth(verified_user)

        other_user = await user_factory.create()
        delete_url = api_client.url_for("delete_user", user_id=other_user.id)
        response = await api_client.delete(delete_url)

        assert response.status_code == 403

    async def test_delete_user_not_found(self, api_client, admin_user):
        """Тест удаления несуществующего пользователя."""
        import uuid

        await api_client.force_auth(admin_user)

        fake_id = uuid.uuid4()
        delete_url = api_client.url_for("delete_user", user_id=fake_id)
        response = await api_client.delete(delete_url)

        assert response.status_code == 404

    async def test_delete_user_unauthorized(self, api_client, verified_user):
        """Тест удаления пользователя без авторизации."""
        delete_url = api_client.url_for("delete_user", user_id=verified_user.id)
        response = await api_client.delete(delete_url)

        assert response.status_code == 401


@pytest.mark.users
@pytest.mark.integration
class TestUserSearch:
    """Тесты поиска пользователей."""

    async def test_search_users_by_email(self, api_client, admin_user, user_factory):
        """Тест поиска пользователей по email."""
        await api_client.force_auth(admin_user)

        # Создаем пользователя с уникальным email
        search_user = await user_factory.create(email="searchable@example.com")

        search_url = api_client.url_for("search_users")
        response = await api_client.get(f"{search_url}?q=searchable@example.com")

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        found_user = next((u for u in data if u["id"] == str(search_user.id)), None)
        assert found_user is not None
        assert found_user["email"] == "searchable@example.com"

    async def test_search_users_by_username(self, api_client, admin_user, user_factory):
        """Тест поиска пользователей по username."""
        await api_client.force_auth(admin_user)

        # Создаем пользователя с уникальным username
        search_user = await user_factory.create(username="unique_searcher")

        search_url = api_client.url_for("search_users")
        response = await api_client.get(f"{search_url}?q=unique_searcher")

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        found_user = next((u for u in data if u["id"] == str(search_user.id)), None)
        assert found_user is not None
        assert found_user["username"] == "unique_searcher"

    async def test_search_users_empty_query(self, api_client, admin_user):
        """Тест поиска с пустым запросом."""
        await api_client.force_auth(admin_user)

        search_url = api_client.url_for("search_users")
        response = await api_client.get(f"{search_url}?q=")

        assert response.status_code == 200
        data = response.json()
        # Пустой запрос может возвращать всех пользователей или пустой список
        assert isinstance(data, list)

    async def test_search_users_no_results(self, api_client, admin_user):
        """Тест поиска без результатов."""
        await api_client.force_auth(admin_user)

        search_url = api_client.url_for("search_users")
        response = await api_client.get(f"{search_url}?q=nonexistent_user_xyz_123")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


@pytest.mark.users
@pytest.mark.integration
class TestUserWorkflow:
    """Интеграционные тесты рабочих процессов пользователей."""

    async def test_complete_user_lifecycle(self, api_client, admin_user, test_user_data, helpers):
        """Тест полного жизненного цикла пользователя от создания до удаления."""
        await api_client.force_auth(admin_user)

        # 1. Регистрация нового пользователя
        register_url = api_client.url_for("register")
        register_response = await api_client.post(register_url, json=test_user_data.model_dump())

        assert register_response.status_code == 201
        user_data = register_response.json()
        user_id = user_data["id"]

        # 2. Верификация пользователя (если требуется)
        # verify_url = api_client.url_for("verify_email")
        # verify_response = await api_client.post(verify_url, json={"token": "verification_token"})

        # 3. Вход в систему
        login_url = api_client.url_for("login")
        login_data = {"email": test_user_data.email, "password": test_user_data.password}
        login_response = await api_client.post(login_url, json=login_data)

        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens

        # 4. Получение профиля
        get_user_url = api_client.url_for("get_user_by_id", user_id=user_id)
        get_response = await api_client.get(get_user_url)

        assert get_response.status_code == 200
        helpers.assert_user_response(get_response.json(), test_user_data.email)

        # 5. Обновление профиля
        update_data = {"full_name": "Updated Lifecycle User", "bio": "Lifecycle test bio"}
        update_url = api_client.url_for("update_user", user_id=user_id)
        update_response = await api_client.put(update_url, json=update_data)

        assert update_response.status_code == 200
        updated_user = update_response.json()
        assert updated_user["full_name"] == "Updated Lifecycle User"

        # 6. Деактивация пользователя
        deactivate_data = {"is_active": False}
        deactivate_response = await api_client.put(update_url, json=deactivate_data)

        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["is_active"] is False

        # 7. Попытка входа деактивированного пользователя
        deactivated_login_response = await api_client.post(login_url, json=login_data)
        assert deactivated_login_response.status_code == 401

        # 8. Удаление пользователя
        delete_url = api_client.url_for("delete_user", user_id=user_id)
        delete_response = await api_client.delete(delete_url)

        assert delete_response.status_code == 204

        # 9. Проверка, что пользователь удален
        final_get_response = await api_client.get(get_user_url)
        assert final_get_response.status_code == 404

    async def test_user_permissions_matrix(self, api_client, admin_user, verified_user, user_factory):
        """Тест матрицы разрешений пользователей."""
        # Создаем тестовых пользователей
        regular_user = await user_factory.create()
        target_user = await user_factory.create()

        # Тестируем разрешения администратора
        await api_client.force_auth(admin_user)

        # Админ может получить любого пользователя
        user_url = api_client.url_for("get_user_by_id", user_id=target_user.id)
        admin_get_response = await api_client.get(user_url)
        assert admin_get_response.status_code == 200

        # Админ может обновить любого пользователя
        update_url = api_client.url_for("update_user", user_id=target_user.id)
        admin_update_response = await api_client.put(update_url, json={"full_name": "Admin Updated"})
        assert admin_update_response.status_code == 200

        # Админ может удалить любого пользователя
        delete_url = api_client.url_for("delete_user", user_id=target_user.id)
        admin_delete_response = await api_client.delete(delete_url)
        assert admin_delete_response.status_code == 204

        # Тестируем разрешения обычного пользователя
        await api_client.force_auth(verified_user)

        # Обычный пользователь может получить свой профиль
        own_profile_url = api_client.url_for("get_my_profile")
        user_profile_response = await api_client.get(own_profile_url)
        assert user_profile_response.status_code == 200

        # Обычный пользователь может обновить свой профиль
        update_profile_url = api_client.url_for("update_my_profile")
        user_update_response = await api_client.put(update_profile_url, json={"full_name": "Self Updated"})
        assert user_update_response.status_code == 200

        # Обычный пользователь НЕ может обновить другого пользователя
        other_user_url = api_client.url_for("update_user", user_id=regular_user.id)
        forbidden_update_response = await api_client.put(other_user_url, json={"full_name": "Forbidden"})
        assert forbidden_update_response.status_code == 403

        # Обычный пользователь НЕ может удалить другого пользователя
        other_delete_url = api_client.url_for("delete_user", user_id=regular_user.id)
        forbidden_delete_response = await api_client.delete(other_delete_url)
        assert forbidden_delete_response.status_code == 403


@pytest.mark.users
@pytest.mark.performance
class TestUserPerformance:
    """Тесты производительности операций с пользователями."""

    async def test_bulk_user_operations(self, api_client, admin_user, user_factory):
        """Тест массовых операций с пользователями."""
        await api_client.force_auth(admin_user)

        # Создаем много пользователей
        users = await user_factory.create_batch(20)

        # Тестируем получение списка пользователей
        users_url = api_client.url_for("get_users_list")
        start_time = api_client.performance_tracker.start_timer()

        response = await api_client.get(users_url)

        elapsed_time = api_client.performance_tracker.end_timer(start_time)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 20

        # Проверяем, что операция выполнилась быстро (менее 1 секунды)
        assert elapsed_time < 1.0

        # Тестируем поиск среди множества пользователей
        search_url = api_client.url_for("search_users")
        search_start_time = api_client.performance_tracker.start_timer()

        search_response = await api_client.get(f"{search_url}?q={users[0].username}")

        search_elapsed_time = api_client.performance_tracker.end_timer(search_start_time)

        assert search_response.status_code == 200
        assert search_elapsed_time < 0.5  # Поиск должен быть еще быстрее

    async def test_concurrent_user_updates(self, api_client, admin_user, user_factory):
        """Тест конкурентных обновлений пользователей."""
        import asyncio

        await api_client.force_auth(admin_user)

        # Создаем пользователей для конкурентного обновления
        users = await user_factory.create_batch(5)

        async def update_user(user, suffix):
            """Обновляет пользователя с уникальным суффиксом."""
            update_url = api_client.url_for("update_user", user_id=user.id)
            update_data = {"full_name": f"Concurrent Update {suffix}"}

            response = await api_client.put(update_url, json=update_data)
            return response.status_code, response.json()

        # Запускаем конкурентные обновления
        tasks = [update_user(user, i) for i, user in enumerate(users)]
        results = await asyncio.gather(*tasks)

        # Проверяем, что все обновления прошли успешно
        for status_code, data in results:
            assert status_code == 200
            assert "Concurrent Update" in data["full_name"]

        # Проверяем, что все пользователи действительно обновились
        for i, user in enumerate(users):
            get_url = api_client.url_for("get_user_by_id", user_id=user.id)
            get_response = await api_client.get(get_url)

            assert get_response.status_code == 200
            updated_user = get_response.json()
            assert updated_user["full_name"] == f"Concurrent Update {i}"
