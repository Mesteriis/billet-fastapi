"""
Примеры использования Protocol интерфейсов.

Демонстрирует как использовать интерфейсы для ослабления связности
между модулями и улучшения тестируемости.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth.interfaces import RefreshTokenData, TokenPayload
    from apps.users.interfaces import UserIdentity, UserProfileData


class MockUser:
    """
    Мок-объект пользователя для тестов.

    Реализует интерфейс UserIdentity без привязки к SQLAlchemy.
    """

    def __init__(
        self,
        id: uuid.UUID = None,
        username: str = "testuser",
        email: str = "test@example.com",
        role: str = "user",
        status: str = "active",
        is_verified: bool = True,
        is_active: bool = True,
        is_superuser: bool = False,
    ):
        self.id = id or uuid.uuid4()
        self.username = username
        self.email = email
        self.role = role
        self.status = status
        self.is_verified = is_verified
        self.is_active = is_active
        self.is_superuser = is_superuser

    def has_role(self, role: str) -> bool:
        """Проверить наличие роли."""
        role_hierarchy = {
            "user": 1,
            "moderator": 2,
            "admin": 3,
            "superuser": 4,
        }
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(role, 0)
        return user_level >= required_level

    def can_login(self) -> bool:
        """Может ли пользователь войти в систему."""
        return self.is_active and self.status == "active"

    @property
    def is_admin(self) -> bool:
        """Является ли пользователь администратором."""
        return self.role in ["admin", "superuser"] or self.is_superuser


class NotificationService:
    """
    Пример сервиса, который использует интерфейсы.

    Не зависит от конкретных моделей User или UserProfile.
    """

    def send_welcome_email(self, user: "UserIdentity") -> dict:
        """
        Отправить приветственное письмо.

        :param user: Пользователь (интерфейс)
        :return: Результат отправки
        """
        if not user.is_verified:
            return {"success": False, "reason": "User not verified"}

        # Логика отправки email
        email_data = {
            "to": user.email,
            "subject": f"Welcome, {user.username}!",
            "template": "welcome",
            "data": {
                "username": user.username,
                "is_premium": user.has_role("admin"),
            },
        }

        # Мок отправки
        return {"success": True, "email_id": str(uuid.uuid4()), "data": email_data}

    def send_profile_completion_reminder(self, user: "UserIdentity", profile: "UserProfileData") -> dict:
        """
        Напоминание о заполнении профиля.

        :param user: Пользователь (интерфейс)
        :param profile: Профиль (интерфейс)
        :return: Результат отправки
        """
        completion_score = self._calculate_profile_completion(profile)

        if completion_score >= 80:
            return {"success": False, "reason": "Profile already complete"}

        return {
            "success": True,
            "email_id": str(uuid.uuid4()),
            "completion_score": completion_score,
            "missing_fields": self._get_missing_fields(profile),
        }

    def _calculate_profile_completion(self, profile: "UserProfileData") -> int:
        """Рассчитать процент заполнения профиля."""
        fields = [
            profile.display_name,
            profile.bio,
            profile.location,
            profile.website,
            profile.avatar_url,
        ]

        filled_fields = sum(1 for field in fields if field)
        return (filled_fields / len(fields)) * 100

    def _get_missing_fields(self, profile: "UserProfileData") -> list[str]:
        """Получить список незаполненных полей."""
        missing = []

        if not profile.display_name:
            missing.append("display_name")
        if not profile.bio:
            missing.append("bio")
        if not profile.location:
            missing.append("location")
        if not profile.website:
            missing.append("website")
        if not profile.avatar_url:
            missing.append("avatar_url")

        return missing


class SecurityAuditService:
    """
    Пример сервиса безопасности, использующего auth интерфейсы.
    """

    def analyze_token_usage(self, tokens: list["RefreshTokenData"]) -> dict:
        """
        Анализ использования токенов.

        :param tokens: Список refresh токенов (интерфейсы)
        :return: Результат анализа
        """
        if not tokens:
            return {"risk_level": "low", "tokens_count": 0}

        suspicious_count = 0
        device_ips = set()

        for token in tokens:
            if token.ip_address:
                device_ips.add(token.ip_address)

            # Проверяем подозрительную активность
            if self._is_suspicious_token(token):
                suspicious_count += 1

        risk_level = "low"
        if len(device_ips) > 5:
            risk_level = "medium"
        if suspicious_count > 2:
            risk_level = "high"

        return {
            "risk_level": risk_level,
            "tokens_count": len(tokens),
            "unique_ips": len(device_ips),
            "suspicious_tokens": suspicious_count,
            "recommendations": self._get_security_recommendations(risk_level),
        }

    def _is_suspicious_token(self, token: "RefreshTokenData") -> bool:
        """Проверить токен на подозрительность."""
        # Токен без информации об устройстве
        if not token.device_info and not token.device_fingerprint:
            return True

        # Токен не использовался длительное время
        if token.last_used_at:
            days_unused = (datetime.utcnow() - token.last_used_at).days
            if days_unused > 30:
                return True

        return False

    def _get_security_recommendations(self, risk_level: str) -> list[str]:
        """Получить рекомендации по безопасности."""
        recommendations = []

        if risk_level == "medium":
            recommendations.extend(
                [
                    "Consider enabling two-factor authentication",
                    "Review active sessions regularly",
                ]
            )

        if risk_level == "high":
            recommendations.extend(
                [
                    "Immediately revoke all suspicious tokens",
                    "Enable mandatory two-factor authentication",
                    "Monitor account for unusual activity",
                    "Consider temporary account restriction",
                ]
            )

        return recommendations


# Пример использования в тестах
def test_notification_service():
    """
    Пример теста с использованием мок-объектов.

    Демонстрирует как интерфейсы упрощают тестирование.
    """
    # Создаем мок-пользователя
    user = MockUser(username="john_doe", email="john@example.com", is_verified=True)

    # Создаем сервис
    notification_service = NotificationService()

    # Тестируем функциональность
    result = notification_service.send_welcome_email(user)

    assert result["success"] is True
    assert result["data"]["to"] == "john@example.com"
    assert result["data"]["data"]["username"] == "john_doe"

    print("✅ Test passed: NotificationService works with UserIdentity interface")


def test_security_audit_service():
    """
    Пример теста сервиса безопасности.
    """

    # Создаем мок-токены
    class MockRefreshToken:
        def __init__(self, ip_address: str = None, device_info: str = None, last_used_at: datetime = None):
            self.id = uuid.uuid4()
            self.user_id = uuid.uuid4()
            self.token_hash = "mock_hash"
            self.expires_at = datetime.utcnow()
            self.is_revoked = False
            self.ip_address = ip_address
            self.device_info = device_info
            self.device_fingerprint = None
            self.last_used_at = last_used_at

        @property
        def is_valid(self):
            return not self.is_revoked

        def revoke(self):
            self.is_revoked = True

    tokens = [
        MockRefreshToken(ip_address="192.168.1.1", device_info="Chrome/Mac"),
        MockRefreshToken(ip_address="192.168.1.2", device_info="Firefox/Windows"),
        MockRefreshToken(ip_address="10.0.0.1"),  # Подозрительный - нет device_info
    ]

    audit_service = SecurityAuditService()
    result = audit_service.analyze_token_usage(tokens)

    assert result["tokens_count"] == 3
    assert result["unique_ips"] == 3
    assert result["suspicious_tokens"] == 1
    assert result["risk_level"] in ["low", "medium"]

    print("✅ Test passed: SecurityAuditService works with RefreshTokenData interface")


if __name__ == "__main__":
    test_notification_service()
    test_security_audit_service()
    print("\n🎉 All interface usage examples work correctly!")
