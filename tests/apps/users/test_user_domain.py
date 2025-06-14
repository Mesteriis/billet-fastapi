"""
Тесты для доменного слоя пользователей.
"""

import uuid
from datetime import datetime

import pytest

from apps.base.contracts import DomainException, ValidationException
from apps.users.domain import (
    Email,
    Password,
    UserDomain,
    UserDomainService,
    Username,
)


class TestEmail:
    """Тесты для объекта-значения Email."""
    
    def test_valid_email(self):
        """Тест валидного email."""
        email = Email("test@example.com")
        assert email.value == "test@example.com"
        assert str(email) == "test@example.com"
    
    def test_invalid_email_format(self):
        """Тест невалидного формата email."""
        with pytest.raises(ValidationException) as exc_info:
            Email("invalid-email")
        
        assert exc_info.value.field == "email"
        assert "Invalid email format" in exc_info.value.message
    
    def test_empty_email(self):
        """Тест пустого email."""
        with pytest.raises(ValidationException):
            Email("")
    
    def test_email_without_domain(self):
        """Тест email без домена."""
        with pytest.raises(ValidationException):
            Email("test@")


class TestUsername:
    """Тесты для объекта-значения Username."""
    
    def test_valid_username(self):
        """Тест валидного username."""
        username = Username("test_user123")
        assert username.value == "test_user123"
        assert str(username) == "test_user123"
    
    def test_short_username(self):
        """Тест слишком короткого username."""
        with pytest.raises(ValidationException) as exc_info:
            Username("ab")
        
        assert exc_info.value.field == "username"
        assert "3-30 characters" in exc_info.value.message
    
    def test_long_username(self):
        """Тест слишком длинного username."""
        long_name = "a" * 31
        with pytest.raises(ValidationException):
            Username(long_name)
    
    def test_invalid_characters(self):
        """Тест недопустимых символов в username."""
        with pytest.raises(ValidationException):
            Username("test-user")  # дефис недопустим
        
        with pytest.raises(ValidationException):
            Username("test@user")  # @ недопустим


class TestPassword:
    """Тесты для объекта-значения Password."""
    
    def test_strong_password(self):
        """Тест надежного пароля."""
        password = Password("TestPass123!")
        assert len(password.value) >= 8
        assert str(password) == "*" * len(password.value)  # Скрыт
    
    def test_weak_password_short(self):
        """Тест слишком короткого пароля."""
        with pytest.raises(ValidationException) as exc_info:
            Password("Test1!")
        
        assert exc_info.value.field == "password"
        assert "at least 8 characters" in exc_info.value.message
    
    def test_weak_password_no_uppercase(self):
        """Тест пароля без заглавных букв."""
        with pytest.raises(ValidationException):
            Password("testpass123!")
    
    def test_weak_password_no_lowercase(self):
        """Тест пароля без строчных букв."""
        with pytest.raises(ValidationException):
            Password("TESTPASS123!")
    
    def test_weak_password_no_digit(self):
        """Тест пароля без цифр."""
        with pytest.raises(ValidationException):
            Password("TestPass!")
    
    def test_weak_password_no_special(self):
        """Тест пароля без специальных символов."""
        with pytest.raises(ValidationException):
            Password("TestPass123")


class TestUserDomain:
    """Тесты для доменной сущности пользователя."""
    
    @pytest.fixture
    def sample_user(self) -> UserDomain:
        """Создать тестового пользователя."""
        return UserDomain(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            full_name="Test User",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    
    def test_user_creation(self, sample_user):
        """Тест создания пользователя."""
        assert sample_user.email.value == "test@example.com"
        assert sample_user.username.value == "testuser"
        assert sample_user.full_name == "Test User"
        assert sample_user.status == "pending_verification"
        assert sample_user.role == "user"
        assert sample_user.is_active is True
        assert sample_user.is_verified is False
        assert sample_user.is_superuser is False
    
    def test_activate_user(self, sample_user):
        """Тест активации пользователя."""
        old_updated_at = sample_user.updated_at
        
        sample_user.activate()
        
        assert sample_user.is_active is True
        assert sample_user.status == "active"
        assert sample_user.updated_at > old_updated_at
    
    def test_deactivate_user(self, sample_user):
        """Тест деактивации пользователя."""
        sample_user.deactivate()
        
        assert sample_user.is_active is False
        assert sample_user.status == "inactive"
    
    def test_suspend_user(self, sample_user):
        """Тест блокировки пользователя."""
        sample_user.suspend("violation of terms")
        
        assert sample_user.is_active is False
        assert sample_user.status == "suspended"
    
    def test_verify_email(self, sample_user):
        """Тест подтверждения email."""
        assert sample_user.is_verified is False
        assert sample_user.status == "pending_verification"
        
        sample_user.verify_email()
        
        assert sample_user.is_verified is True
        assert sample_user.status == "active"
    
    def test_update_last_login(self, sample_user):
        """Тест обновления времени последнего входа."""
        assert sample_user.last_login_at is None
        
        old_updated_at = sample_user.updated_at
        sample_user.update_last_login()
        
        assert sample_user.last_login_at is not None
        assert sample_user.updated_at > old_updated_at
    
    def test_change_role_to_admin(self, sample_user):
        """Тест изменения роли на админа."""
        # Сначала верифицируем пользователя
        sample_user.verify_email()
        
        sample_user.change_role("admin")
        
        assert sample_user.role == "admin"
        assert sample_user.is_superuser is True
    
    def test_change_role_admin_unverified_user(self, sample_user):
        """Тест невозможности назначения админом неверифицированного пользователя."""
        with pytest.raises(DomainException) as exc_info:
            sample_user.change_role("admin")
        
        assert "Cannot assign admin role to unverified user" in str(exc_info.value)
    
    def test_update_profile_valid(self, sample_user):
        """Тест валидного обновления профиля."""
        sample_user.update_profile(
            full_name="New Full Name",
            phone="+1234567890",
            bio="Test bio",
            avatar_url="https://example.com/avatar.jpg"
        )
        
        assert sample_user.full_name == "New Full Name"
        assert sample_user.phone == "+1234567890"
        assert sample_user.bio == "Test bio"
        assert sample_user.avatar_url == "https://example.com/avatar.jpg"
    
    def test_update_profile_short_name(self, sample_user):
        """Тест обновления профиля с коротким именем."""
        with pytest.raises(ValidationException) as exc_info:
            sample_user.update_profile(full_name="A")
        
        assert exc_info.value.field == "full_name"
    
    def test_update_profile_invalid_phone(self, sample_user):
        """Тест обновления профиля с невалидным телефоном."""
        with pytest.raises(ValidationException) as exc_info:
            sample_user.update_profile(phone="invalid-phone")
        
        assert exc_info.value.field == "phone"
    
    def test_update_profile_long_bio(self, sample_user):
        """Тест обновления профиля с слишком длинной биографией."""
        long_bio = "a" * 501
        
        with pytest.raises(ValidationException) as exc_info:
            sample_user.update_profile(bio=long_bio)
        
        assert exc_info.value.field == "bio"
    
    def test_can_perform_admin_action(self, sample_user):
        """Тест проверки возможности выполнения административных действий."""
        # Неверифицированный пользователь не может
        assert sample_user.can_perform_admin_action() is False
        
        # Верифицированный обычный пользователь не может
        sample_user.verify_email()
        assert sample_user.can_perform_admin_action() is False
        
        # Админ может
        sample_user.change_role("admin")
        assert sample_user.can_perform_admin_action() is True
        
        # Деактивированный админ не может
        sample_user.deactivate()
        assert sample_user.can_perform_admin_action() is False
    
    def test_can_moderate_content(self, sample_user):
        """Тест проверки возможности модерации контента."""
        # Неверифицированный пользователь не может
        assert sample_user.can_moderate_content() is False
        
        # Верифицированный обычный пользователь не может
        sample_user.verify_email()
        assert sample_user.can_moderate_content() is False
        
        # Модератор может
        sample_user.change_role("moderator")
        assert sample_user.can_moderate_content() is True
        
        # Админ тоже может
        sample_user.change_role("admin")
        assert sample_user.can_moderate_content() is True


class TestUserDomainService:
    """Тесты для доменного сервиса пользователей."""
    
    def test_can_user_be_promoted_to_moderator(self):
        """Тест возможности повышения пользователя до модератора."""
        user = UserDomain(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            full_name="Test User",
            role="user",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        assert UserDomainService.can_user_be_promoted(user, "moderator") is True
    
    def test_can_user_be_promoted_to_admin(self):
        """Тест возможности повышения модератора до админа."""
        user = UserDomain(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            full_name="Test User",
            role="moderator",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        assert UserDomainService.can_user_be_promoted(user, "admin") is True
    
    def test_cannot_promote_unverified_user(self):
        """Тест невозможности повышения неверифицированного пользователя."""
        user = UserDomain(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            full_name="Test User",
            role="user",
            is_active=True,
            is_verified=False,  # Не верифицирован
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        assert UserDomainService.can_user_be_promoted(user, "moderator") is False
    
    def test_cannot_promote_inactive_user(self):
        """Тест невозможности повышения неактивного пользователя."""
        user = UserDomain(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            full_name="Test User",
            role="user",
            is_active=False,  # Неактивен
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        assert UserDomainService.can_user_be_promoted(user, "moderator") is False
    
    def test_cannot_skip_moderator_role(self):
        """Тест невозможности пропуска роли модератора для назначения админом."""
        user = UserDomain(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            full_name="Test User",
            role="user",  # Обычный пользователь
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        assert UserDomainService.can_user_be_promoted(user, "admin") is False
    
    def test_validate_user_for_action_active(self):
        """Тест валидации активного пользователя для действия."""
        user = UserDomain(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            full_name="Test User",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        # Не должно выбросить исключение
        UserDomainService.validate_user_for_action(user, "some_action")
    
    def test_validate_user_for_action_inactive(self):
        """Тест валидации неактивного пользователя для действия."""
        user = UserDomain(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            full_name="Test User",
            is_active=False,  # Неактивен
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        with pytest.raises(DomainException) as exc_info:
            UserDomainService.validate_user_for_action(user, "some_action")
        
        assert "User is not active" in str(exc_info.value)
    
    def test_validate_user_for_admin_action_unverified(self):
        """Тест валидации неверифицированного пользователя для админских действий."""
        user = UserDomain(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            full_name="Test User",
            is_active=True,
            is_verified=False,  # Не верифицирован
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        with pytest.raises(DomainException) as exc_info:
            UserDomainService.validate_user_for_action(user, "admin_action")
        
        assert "User is not verified" in str(exc_info.value)
    
    def test_generate_username_suggestions(self):
        """Тест генерации предложений для имени пользователя."""
        existing_usernames = ["testuser", "testuser1", "testuser2"]
        suggestions = UserDomainService.generate_username_suggestions(
            "testuser", existing_usernames
        )
        
        # Должны быть предложения, не совпадающие с существующими
        assert len(suggestions) > 0
        assert "testuser3" in suggestions
        assert "testuser" not in suggestions
        assert "testuser1" not in suggestions
    
    def test_generate_username_suggestions_special_chars(self):
        """Тест генерации предложений с очисткой специальных символов."""
        suggestions = UserDomainService.generate_username_suggestions(
            "test@user!", []
        )
        
        # Специальные символы должны быть убраны
        assert len(suggestions) > 0
        assert all("@" not in s and "!" not in s for s in suggestions)
        assert "testuser" in suggestions[0] if suggestions else True 