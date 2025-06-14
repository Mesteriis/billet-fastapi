"""
Комплексные тесты для UserRepository с высоким покрытием.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User
from apps.users.repository import UserRepository
from apps.users.schemas import UserCreate, UserUpdate


@pytest.mark.unit
@pytest.mark.integration
class TestUserRepositoryBasicMethods:
    """Тесты базовых методов UserRepository."""

    @pytest.fixture
    def repository(self):
        """Фикстура репозитория."""
        return UserRepository()

    @pytest.fixture
    async def sample_user_data(self):
        """Данные для создания пользователя."""
        return UserCreate(
            email="test@example.com", username="testuser", full_name="Test User", password="test_password"
        )

    async def test_get_by_email_found(self, repository, async_session, user_factory):
        """Тест получения пользователя по email."""
        # Создаем пользователя через фабрику
        user_data = user_factory()

        # Создаем пользователя в БД
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            password_hash="hashed_password",
            is_active=True,
        )

        async_session.add(db_user)
        await async_session.commit()
        await async_session.refresh(db_user)

        # Ищем пользователя
        result = await repository.get_by_email(async_session, email=user_data.email)

        assert result is not None
        assert result.email == user_data.email
        assert result.username == user_data.username

    async def test_get_by_email_not_found(self, repository, async_session):
        """Тест получения несуществующего пользователя по email."""
        result = await repository.get_by_email(async_session, email="nonexistent@example.com")
        assert result is None

    async def test_get_by_email_case_insensitive(self, repository, async_session, user_factory):
        """Тест получения пользователя по email без учета регистра."""
        user_data = user_factory()

        db_user = User(
            email=user_data.email.lower(),
            username=user_data.username,
            full_name=user_data.full_name,
            password_hash="hashed_password",
            is_active=True,
        )

        async_session.add(db_user)
        await async_session.commit()

        # Ищем с разным регистром
        result = await repository.get_by_email(async_session, email=user_data.email.upper())

        assert result is not None
        assert result.email == user_data.email.lower()

    async def test_get_by_username_found(self, repository, async_session, user_factory):
        """Тест получения пользователя по username."""
        user_data = user_factory()

        db_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            password_hash="hashed_password",
            is_active=True,
        )

        async_session.add(db_user)
        await async_session.commit()
        await async_session.refresh(db_user)

        result = await repository.get_by_username(async_session, username=user_data.username)

        assert result is not None
        assert result.username == user_data.username
        assert result.email == user_data.email

    async def test_get_by_username_not_found(self, repository, async_session):
        """Тест получения несуществующего пользователя по username."""
        result = await repository.get_by_username(async_session, username="nonexistent")
        assert result is None

    async def test_get_by_username_case_insensitive(self, repository, async_session, user_factory):
        """Тест получения пользователя по username без учета регистра."""
        user_data = user_factory()

        db_user = User(
            email=user_data.email,
            username=user_data.username.lower(),
            full_name=user_data.full_name,
            password_hash="hashed_password",
            is_active=True,
        )

        async_session.add(db_user)
        await async_session.commit()

        result = await repository.get_by_username(async_session, username=user_data.username.upper())

        assert result is not None
        assert result.username == user_data.username.lower()


@pytest.mark.unit
@pytest.mark.integration
class TestUserRepositoryListMethods:
    """Тесты методов получения списков пользователей."""

    @pytest.fixture
    def repository(self):
        """Фикстура репозитория."""
        return UserRepository()

    @pytest.fixture
    async def create_test_users(self, async_session, multiple_users):
        """Создает тестовых пользователей в БД."""
        db_users = []

        for i, user_data in enumerate(multiple_users):
            db_user = User(
                email=user_data.email,
                username=user_data.username,
                full_name=user_data.full_name,
                password_hash="hashed_password",
                is_active=i < 3,  # Первые 3 активные, остальные неактивные
                is_superuser=i == 0,  # Первый суперпользователь
            )
            db_users.append(db_user)
            async_session.add(db_user)

        await async_session.commit()

        for db_user in db_users:
            await async_session.refresh(db_user)

        return db_users

    async def test_get_active_users(self, repository, async_session, create_test_users):
        """Тест получения активных пользователей."""
        users = await repository.get_active_users(async_session, skip=0, limit=10)

        assert len(users) == 3  # Только активные пользователи
        assert all(user.is_active for user in users)

    async def test_get_active_users_pagination(self, repository, async_session, create_test_users):
        """Тест пагинации активных пользователей."""
        users = await repository.get_active_users(async_session, skip=1, limit=2)

        assert len(users) == 2
        assert all(user.is_active for user in users)

    async def test_get_superusers(self, repository, async_session, create_test_users):
        """Тест получения суперпользователей."""
        users = await repository.get_superusers(async_session, skip=0, limit=10)

        assert len(users) == 1  # Только один суперпользователь
        assert users[0].is_superuser is True

    async def test_get_superusers_empty(self, repository, async_session):
        """Тест получения суперпользователей когда их нет."""
        users = await repository.get_superusers(async_session)
        assert len(users) == 0

    async def test_search_users_by_email(self, repository, async_session, create_test_users):
        """Тест поиска пользователей по email."""
        search_query = "example.com"
        users = await repository.search_users(async_session, query_text=search_query)

        assert len(users) > 0
        assert all("example.com" in user.email for user in users)

    async def test_search_users_by_username(self, repository, async_session, create_test_users):
        """Тест поиска пользователей по username."""
        search_query = "user"
        users = await repository.search_users(async_session, query_text=search_query)

        assert len(users) > 0
        assert all("user" in user.username.lower() for user in users)

    async def test_search_users_by_full_name(self, repository, async_session, user_factory):
        """Тест поиска пользователей по полному имени."""
        user_data = user_factory(full_name="John Doe")

        db_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name="John Doe",
            password_hash="hashed_password",
            is_active=True,
        )

        async_session.add(db_user)
        await async_session.commit()

        users = await repository.search_users(async_session, query_text="john")

        assert len(users) >= 1
        assert any("john" in user.full_name.lower() for user in users)

    async def test_search_users_no_results(self, repository, async_session, create_test_users):
        """Тест поиска пользователей без результатов."""
        users = await repository.search_users(async_session, query_text="nonexistent_query_xyz")
        assert len(users) == 0

    async def test_search_users_pagination(self, repository, async_session, create_test_users):
        """Тест пагинации поиска пользователей."""
        users = await repository.search_users(async_session, query_text="user", skip=1, limit=2)

        assert len(users) <= 2


@pytest.mark.unit
@pytest.mark.integration
class TestUserRepositoryValidationMethods:
    """Тесты методов валидации UserRepository."""

    @pytest.fixture
    def repository(self):
        """Фикстура репозитория."""
        return UserRepository()

    @pytest.fixture
    async def existing_user(self, async_session, user_factory):
        """Создает существующего пользователя в БД."""
        user_data = user_factory()

        db_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            password_hash="hashed_password",
            is_active=True,
        )

        async_session.add(db_user)
        await async_session.commit()
        await async_session.refresh(db_user)

        return db_user

    async def test_is_email_taken_true(self, repository, async_session, existing_user):
        """Тест проверки занятого email."""
        is_taken = await repository.is_email_taken(async_session, email=existing_user.email)
        assert is_taken is True

    async def test_is_email_taken_false(self, repository, async_session):
        """Тест проверки свободного email."""
        is_taken = await repository.is_email_taken(async_session, email="free@example.com")
        assert is_taken is False

    async def test_is_email_taken_exclude_current_user(self, repository, async_session, existing_user):
        """Тест проверки email с исключением текущего пользователя."""
        is_taken = await repository.is_email_taken(
            async_session, email=existing_user.email, exclude_user_id=str(existing_user.id)
        )
        assert is_taken is False

    async def test_is_email_taken_case_insensitive(self, repository, async_session, existing_user):
        """Тест проверки email без учета регистра."""
        is_taken = await repository.is_email_taken(async_session, email=existing_user.email.upper())
        assert is_taken is True

    async def test_is_username_taken_true(self, repository, async_session, existing_user):
        """Тест проверки занятого username."""
        is_taken = await repository.is_username_taken(async_session, username=existing_user.username)
        assert is_taken is True

    async def test_is_username_taken_false(self, repository, async_session):
        """Тест проверки свободного username."""
        is_taken = await repository.is_username_taken(async_session, username="free_username")
        assert is_taken is False

    async def test_is_username_taken_exclude_current_user(self, repository, async_session, existing_user):
        """Тест проверки username с исключением текущего пользователя."""
        is_taken = await repository.is_username_taken(
            async_session, username=existing_user.username, exclude_user_id=str(existing_user.id)
        )
        assert is_taken is False

    async def test_is_username_taken_case_insensitive(self, repository, async_session, existing_user):
        """Тест проверки username без учета регистра."""
        is_taken = await repository.is_username_taken(async_session, username=existing_user.username.upper())
        assert is_taken is True


@pytest.mark.unit
@pytest.mark.integration
class TestUserRepositoryDeletedRecords:
    """Тесты работы с удаленными записями."""

    @pytest.fixture
    def repository(self):
        """Фикстура репозитория."""
        return UserRepository()

    @pytest.fixture
    async def deleted_user(self, async_session, user_factory):
        """Создает мягко удаленного пользователя."""
        from datetime import datetime

        user_data = user_factory()

        db_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            password_hash="hashed_password",
            is_active=True,
            deleted_at=datetime.utcnow(),  # Мягко удален
        )

        async_session.add(db_user)
        await async_session.commit()
        await async_session.refresh(db_user)

        return db_user

    async def test_get_by_email_excludes_deleted(self, repository, async_session, deleted_user):
        """Тест что get_by_email исключает удаленные записи по умолчанию."""
        result = await repository.get_by_email(async_session, email=deleted_user.email)
        assert result is None

    async def test_get_by_email_includes_deleted(self, repository, async_session, deleted_user):
        """Тест что get_by_email может включать удаленные записи."""
        result = await repository.get_by_email(async_session, email=deleted_user.email, include_deleted=True)
        assert result is not None
        assert result.id == deleted_user.id

    async def test_get_by_username_excludes_deleted(self, repository, async_session, deleted_user):
        """Тест что get_by_username исключает удаленные записи по умолчанию."""
        result = await repository.get_by_username(async_session, username=deleted_user.username)
        assert result is None

    async def test_get_by_username_includes_deleted(self, repository, async_session, deleted_user):
        """Тест что get_by_username может включать удаленные записи."""
        result = await repository.get_by_username(async_session, username=deleted_user.username, include_deleted=True)
        assert result is not None
        assert result.id == deleted_user.id

    async def test_get_active_users_excludes_deleted(self, repository, async_session, deleted_user):
        """Тест что get_active_users исключает удаленные записи."""
        users = await repository.get_active_users(async_session)
        user_ids = [user.id for user in users]
        assert deleted_user.id not in user_ids

    async def test_search_users_excludes_deleted(self, repository, async_session, deleted_user):
        """Тест что search_users исключает удаленные записи."""
        users = await repository.search_users(async_session, query_text=deleted_user.username)
        user_ids = [user.id for user in users]
        assert deleted_user.id not in user_ids


@pytest.mark.unit
@pytest.mark.integration
class TestUserRepositoryErrorHandling:
    """Тесты обработки ошибок в UserRepository."""

    @pytest.fixture
    def repository(self):
        """Фикстура репозитория."""
        return UserRepository()

    async def test_get_by_email_with_invalid_session(self, repository):
        """Тест обработки ошибки с недействительной сессией."""
        invalid_session = None

        with pytest.raises(AttributeError):
            await repository.get_by_email(invalid_session, email="test@example.com")

    async def test_search_users_with_empty_query(self, repository, async_session):
        """Тест поиска с пустым запросом."""
        users = await repository.search_users(async_session, query_text="")
        # Должен вернуть пустой список или всех пользователей в зависимости от реализации
        assert isinstance(users, list)

    async def test_get_active_users_with_negative_pagination(self, repository, async_session):
        """Тест получения активных пользователей с отрицательными параметрами пагинации."""
        users = await repository.get_active_users(async_session, skip=-1, limit=-1)
        # Должен корректно обработать отрицательные значения
        assert isinstance(users, list)

    async def test_is_email_taken_with_none_email(self, repository, async_session):
        """Тест проверки занятости email с None."""
        with pytest.raises((TypeError, AttributeError)):
            await repository.is_email_taken(async_session, email=None)

    async def test_is_username_taken_with_none_username(self, repository, async_session):
        """Тест проверки занятости username с None."""
        with pytest.raises((TypeError, AttributeError)):
            await repository.is_username_taken(async_session, username=None)
