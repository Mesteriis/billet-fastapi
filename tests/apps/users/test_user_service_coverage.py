"""
Комплексные тесты для UserService с высоким покрытием.
"""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User
from apps.users.repository import UserRepository
from apps.users.schemas import UserPasswordChange, UserResponse, UserUpdate
from apps.users.service import UserService


@pytest.mark.unit
@pytest.mark.auth
class TestUserServiceGetMethods:
    """Тесты методов получения пользователей."""

    @pytest.fixture
    def user_service(self):
        """Фикстура UserService."""
        return UserService()

    @pytest.fixture
    def mock_repository(self, monkeypatch):
        """Мокированный репозиторий."""
        mock_repo = AsyncMock(spec=UserRepository)
        monkeypatch.setattr("apps.users.service.UserRepository", lambda: mock_repo)
        return mock_repo

    @pytest.fixture
    def sample_user_db(self):
        """Пример пользователя из БД."""
        return User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )

    async def test_get_user_by_id_found(self, user_service, mock_repository, sample_user_db):
        """Тест успешного получения пользователя по ID."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id

        mock_repository.get.return_value = sample_user_db

        result = await user_service.get_user_by_id(mock_db, user_id=user_id)

        mock_repository.get.assert_called_once_with(mock_db, id=user_id)
        assert isinstance(result, UserResponse)
        assert result.id == user_id
        assert result.email == "test@example.com"

    async def test_get_user_by_id_not_found(self, user_service, mock_repository):
        """Тест получения несуществующего пользователя по ID."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = uuid.uuid4()

        mock_repository.get.return_value = None

        result = await user_service.get_user_by_id(mock_db, user_id=user_id)

        mock_repository.get.assert_called_once_with(mock_db, id=user_id)
        assert result is None

    async def test_get_user_by_email_found(self, user_service, mock_repository, sample_user_db):
        """Тест успешного получения пользователя по email."""
        mock_db = AsyncMock(spec=AsyncSession)
        email = "test@example.com"

        mock_repository.get_by_email.return_value = sample_user_db

        result = await user_service.get_user_by_email(mock_db, email=email)

        mock_repository.get_by_email.assert_called_once_with(mock_db, email=email)
        assert isinstance(result, UserResponse)
        assert result.email == email

    async def test_get_user_by_email_not_found(self, user_service, mock_repository):
        """Тест получения несуществующего пользователя по email."""
        mock_db = AsyncMock(spec=AsyncSession)
        email = "nonexistent@example.com"

        mock_repository.get_by_email.return_value = None

        result = await user_service.get_user_by_email(mock_db, email=email)

        mock_repository.get_by_email.assert_called_once_with(mock_db, email=email)
        assert result is None

    async def test_get_user_by_username_found(self, user_service, mock_repository, sample_user_db):
        """Тест успешного получения пользователя по username."""
        mock_db = AsyncMock(spec=AsyncSession)
        username = "testuser"

        mock_repository.get_by_username.return_value = sample_user_db

        result = await user_service.get_user_by_username(mock_db, username=username)

        mock_repository.get_by_username.assert_called_once_with(mock_db, username=username)
        assert isinstance(result, UserResponse)
        assert result.username == username

    async def test_get_user_by_username_not_found(self, user_service, mock_repository):
        """Тест получения несуществующего пользователя по username."""
        mock_db = AsyncMock(spec=AsyncSession)
        username = "nonexistent"

        mock_repository.get_by_username.return_value = None

        result = await user_service.get_user_by_username(mock_db, username=username)

        mock_repository.get_by_username.assert_called_once_with(mock_db, username=username)
        assert result is None


@pytest.mark.unit
@pytest.mark.auth
class TestUserServiceListMethods:
    """Тесты методов получения списков пользователей."""

    @pytest.fixture
    def user_service(self):
        """Фикстура UserService."""
        return UserService()

    @pytest.fixture
    def mock_repository(self, monkeypatch):
        """Мокированный репозиторий."""
        mock_repo = AsyncMock(spec=UserRepository)
        monkeypatch.setattr("apps.users.service.UserRepository", lambda: mock_repo)
        return mock_repo

    @pytest.fixture
    def sample_users_db(self):
        """Список пользователей из БД."""
        return [
            User(
                id=uuid.uuid4(),
                email=f"user{i}@example.com",
                username=f"user{i}",
                full_name=f"User {i}",
                is_active=True,
                is_verified=True,
                is_superuser=False,
            )
            for i in range(1, 4)  # 3 пользователя
        ]

    async def test_get_users_active_only(self, user_service, mock_repository, sample_users_db):
        """Тест получения только активных пользователей."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_repository.get_active_users.return_value = sample_users_db

        result = await user_service.get_users(mock_db, skip=0, limit=10, active_only=True)

        mock_repository.get_active_users.assert_called_once_with(mock_db, skip=0, limit=10)
        assert len(result) == 3
        assert all(isinstance(user, UserResponse) for user in result)

    async def test_get_users_all(self, user_service, mock_repository, sample_users_db):
        """Тест получения всех пользователей."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_repository.get_multi.return_value = sample_users_db

        result = await user_service.get_users(mock_db, skip=0, limit=10, active_only=False)

        mock_repository.get_multi.assert_called_once_with(mock_db, skip=0, limit=10)
        assert len(result) == 3
        assert all(isinstance(user, UserResponse) for user in result)

    async def test_get_users_with_pagination(self, user_service, mock_repository, sample_users_db):
        """Тест получения пользователей с пагинацией."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_repository.get_active_users.return_value = sample_users_db[1:]  # Пропускаем первого

        result = await user_service.get_users(mock_db, skip=1, limit=2, active_only=True)

        mock_repository.get_active_users.assert_called_once_with(mock_db, skip=1, limit=2)
        assert len(result) == 2

    async def test_search_users(self, user_service, mock_repository, sample_users_db):
        """Тест поиска пользователей."""
        mock_db = AsyncMock(spec=AsyncSession)
        search_query = "user"

        mock_repository.search_users.return_value = sample_users_db

        result = await user_service.search_users(mock_db, query=search_query, skip=0, limit=10)

        mock_repository.search_users.assert_called_once_with(mock_db, query_text=search_query, skip=0, limit=10)
        assert len(result) == 3
        assert all(isinstance(user, UserResponse) for user in result)

    async def test_search_users_empty_result(self, user_service, mock_repository):
        """Тест поиска пользователей с пустым результатом."""
        mock_db = AsyncMock(spec=AsyncSession)
        search_query = "nonexistent"

        mock_repository.search_users.return_value = []

        result = await user_service.search_users(mock_db, query=search_query)

        mock_repository.search_users.assert_called_once_with(mock_db, query_text=search_query, skip=0, limit=100)
        assert len(result) == 0


@pytest.mark.unit
@pytest.mark.auth
class TestUserServiceUpdateMethods:
    """Тесты методов обновления пользователей."""

    @pytest.fixture
    def user_service(self):
        """Фикстура UserService."""
        return UserService()

    @pytest.fixture
    def mock_repository(self, monkeypatch):
        """Мокированный репозиторий."""
        mock_repo = AsyncMock(spec=UserRepository)
        monkeypatch.setattr("apps.users.service.UserRepository", lambda: mock_repo)
        return mock_repo

    @pytest.fixture
    def sample_user_db(self):
        """Пример пользователя из БД."""
        return User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )

    @pytest.fixture
    def admin_user_db(self):
        """Пример администратора из БД."""
        return User(
            id=uuid.uuid4(),
            email="admin@example.com",
            username="admin",
            full_name="Admin User",
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )

    async def test_update_user_success(self, user_service, mock_repository, sample_user_db):
        """Тест успешного обновления пользователя."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id

        update_data = UserUpdate(full_name="Updated Name", bio="New bio")
        updated_user = User(**sample_user_db.__dict__)
        updated_user.full_name = "Updated Name"
        updated_user.bio = "New bio"

        mock_repository.get.return_value = sample_user_db
        mock_repository.is_email_taken.return_value = False
        mock_repository.is_username_taken.return_value = False
        mock_repository.update.return_value = updated_user

        result = await user_service.update_user(mock_db, user_id=user_id, user_data=update_data)

        mock_repository.get.assert_called_once_with(mock_db, id=user_id)
        mock_repository.update.assert_called_once_with(mock_db, db_obj=sample_user_db, obj_in=update_data)
        mock_db.commit.assert_called_once()
        assert isinstance(result, UserResponse)
        assert result.full_name == "Updated Name"

    async def test_update_user_not_found(self, user_service, mock_repository):
        """Тест обновления несуществующего пользователя."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = uuid.uuid4()
        update_data = UserUpdate(full_name="Updated Name")

        mock_repository.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await user_service.update_user(mock_db, user_id=user_id, user_data=update_data)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Пользователь не найден" in exc_info.value.detail

    async def test_update_user_permission_denied(self, user_service, mock_repository, sample_user_db):
        """Тест обновления пользователя без прав."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        current_user_id = uuid.uuid4()  # Другой пользователь
        update_data = UserUpdate(full_name="Updated Name")

        current_user = User(
            id=current_user_id,
            email="current@example.com",
            username="current",
            full_name="Current User",
            is_active=True,
            is_verified=True,
            is_superuser=False,  # Не админ
        )

        mock_repository.get.side_effect = [sample_user_db, current_user]

        with pytest.raises(HTTPException) as exc_info:
            await user_service.update_user(
                mock_db, user_id=user_id, user_data=update_data, current_user_id=current_user_id
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Недостаточно прав" in exc_info.value.detail

    async def test_update_user_admin_can_edit_any(self, user_service, mock_repository, sample_user_db, admin_user_db):
        """Тест что админ может редактировать любого пользователя."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        current_user_id = admin_user_db.id
        update_data = UserUpdate(full_name="Updated by Admin")

        updated_user = User(**sample_user_db.__dict__)
        updated_user.full_name = "Updated by Admin"

        mock_repository.get.side_effect = [sample_user_db, admin_user_db]
        mock_repository.is_email_taken.return_value = False
        mock_repository.is_username_taken.return_value = False
        mock_repository.update.return_value = updated_user

        result = await user_service.update_user(
            mock_db, user_id=user_id, user_data=update_data, current_user_id=current_user_id
        )

        assert isinstance(result, UserResponse)
        assert result.full_name == "Updated by Admin"

    async def test_update_user_email_already_taken(self, user_service, mock_repository, sample_user_db):
        """Тест обновления с уже занятым email."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        update_data = UserUpdate(email="taken@example.com")

        mock_repository.get.return_value = sample_user_db
        mock_repository.is_email_taken.return_value = True

        with pytest.raises(HTTPException) as exc_info:
            await user_service.update_user(mock_db, user_id=user_id, user_data=update_data)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "email уже существует" in exc_info.value.detail

    async def test_update_user_username_already_taken(self, user_service, mock_repository, sample_user_db):
        """Тест обновления с уже занятым username."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        update_data = UserUpdate(username="taken_username")

        mock_repository.get.return_value = sample_user_db
        mock_repository.is_email_taken.return_value = False
        mock_repository.is_username_taken.return_value = True

        with pytest.raises(HTTPException) as exc_info:
            await user_service.update_user(mock_db, user_id=user_id, user_data=update_data)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "именем уже существует" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.auth
class TestUserServicePasswordMethods:
    """Тесты методов работы с паролями."""

    @pytest.fixture
    def user_service(self):
        """Фикстура UserService."""
        return UserService()

    @pytest.fixture
    def mock_repository(self, monkeypatch):
        """Мокированный репозиторий."""
        mock_repo = AsyncMock(spec=UserRepository)
        monkeypatch.setattr("apps.users.service.UserRepository", lambda: mock_repo)
        return mock_repo

    @pytest.fixture
    def mock_password_service(self, monkeypatch):
        """Мокированный сервис паролей."""
        mock_service = Mock()
        mock_service.verify_password.return_value = True
        mock_service.hash_password.return_value = "hashed_new_password"
        monkeypatch.setattr("apps.users.service.password_service", mock_service)
        return mock_service

    @pytest.fixture
    def sample_user_db(self):
        """Пример пользователя из БД."""
        return User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            password_hash="hashed_old_password",
            is_active=True,
        )

    async def test_change_password_success(self, user_service, mock_repository, mock_password_service, sample_user_db):
        """Тест успешной смены пароля."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        password_data = UserPasswordChange(current_password="old_password", new_password="new_password_123")

        mock_repository.get.return_value = sample_user_db

        await user_service.change_password(mock_db, user_id=user_id, password_data=password_data)

        mock_repository.get.assert_called_once_with(mock_db, id=user_id)
        mock_password_service.verify_password.assert_called_once_with("old_password", "hashed_old_password")
        mock_password_service.hash_password.assert_called_once_with("new_password_123")
        mock_db.commit.assert_called_once()

    async def test_change_password_user_not_found(self, user_service, mock_repository):
        """Тест смены пароля для несуществующего пользователя."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = uuid.uuid4()
        password_data = UserPasswordChange(current_password="old_password", new_password="new_password_123")

        mock_repository.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await user_service.change_password(mock_db, user_id=user_id, password_data=password_data)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Пользователь не найден" in exc_info.value.detail

    async def test_change_password_wrong_current_password(
        self, user_service, mock_repository, mock_password_service, sample_user_db
    ):
        """Тест смены пароля с неправильным текущим паролем."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        password_data = UserPasswordChange(current_password="wrong_password", new_password="new_password_123")

        mock_repository.get.return_value = sample_user_db
        mock_password_service.verify_password.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await user_service.change_password(mock_db, user_id=user_id, password_data=password_data)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Неверный текущий пароль" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.auth
class TestUserServiceDeactivateDelete:
    """Тесты методов деактивации и удаления пользователей."""

    @pytest.fixture
    def user_service(self):
        """Фикстура UserService."""
        return UserService()

    @pytest.fixture
    def mock_repository(self, monkeypatch):
        """Мокированный репозиторий."""
        mock_repo = AsyncMock(spec=UserRepository)
        monkeypatch.setattr("apps.users.service.UserRepository", lambda: mock_repo)
        return mock_repo

    @pytest.fixture
    def sample_user_db(self):
        """Пример пользователя из БД."""
        return User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
        )

    @pytest.fixture
    def admin_user_db(self):
        """Пример администратора из БД."""
        return User(
            id=uuid.uuid4(),
            email="admin@example.com",
            username="admin",
            full_name="Admin User",
            is_active=True,
            is_superuser=True,
        )

    async def test_deactivate_user_success(self, user_service, mock_repository, sample_user_db, admin_user_db):
        """Тест успешной деактивации пользователя."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        current_user_id = admin_user_db.id

        deactivated_user = User(**sample_user_db.__dict__)
        deactivated_user.is_active = False

        mock_repository.get.side_effect = [sample_user_db, admin_user_db]
        mock_repository.update.return_value = deactivated_user

        result = await user_service.deactivate_user(mock_db, user_id=user_id, current_user_id=current_user_id)

        assert isinstance(result, UserResponse)
        assert result.is_active is False

    async def test_deactivate_user_permission_denied(self, user_service, mock_repository, sample_user_db):
        """Тест деактивации пользователя без прав."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        current_user_id = uuid.uuid4()

        current_user = User(
            id=current_user_id,
            email="current@example.com",
            username="current",
            full_name="Current User",
            is_active=True,
            is_superuser=False,  # Не админ
        )

        mock_repository.get.side_effect = [sample_user_db, current_user]

        with pytest.raises(HTTPException) as exc_info:
            await user_service.deactivate_user(mock_db, user_id=user_id, current_user_id=current_user_id)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_user_soft_delete_success(self, user_service, mock_repository, sample_user_db, admin_user_db):
        """Тест успешного мягкого удаления пользователя."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        current_user_id = admin_user_db.id

        mock_repository.get.side_effect = [sample_user_db, admin_user_db]

        await user_service.delete_user(mock_db, user_id=user_id, current_user_id=current_user_id, soft_delete=True)

        mock_repository.soft_delete.assert_called_once_with(mock_db, id=user_id)
        mock_db.commit.assert_called_once()

    async def test_delete_user_hard_delete_success(self, user_service, mock_repository, sample_user_db, admin_user_db):
        """Тест успешного жесткого удаления пользователя."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        current_user_id = admin_user_db.id

        mock_repository.get.side_effect = [sample_user_db, admin_user_db]

        await user_service.delete_user(mock_db, user_id=user_id, current_user_id=current_user_id, soft_delete=False)

        mock_repository.remove.assert_called_once_with(mock_db, id=user_id)
        mock_db.commit.assert_called_once()

    async def test_delete_user_permission_denied(self, user_service, mock_repository, sample_user_db):
        """Тест удаления пользователя без прав."""
        mock_db = AsyncMock(spec=AsyncSession)
        user_id = sample_user_db.id
        current_user_id = uuid.uuid4()

        current_user = User(
            id=current_user_id,
            email="current@example.com",
            username="current",
            full_name="Current User",
            is_active=True,
            is_superuser=False,  # Не админ
        )

        mock_repository.get.side_effect = [sample_user_db, current_user]

        with pytest.raises(HTTPException) as exc_info:
            await user_service.delete_user(mock_db, user_id=user_id, current_user_id=current_user_id)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
