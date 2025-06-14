"""
Сервис для работы с паролями.
"""

from __future__ import annotations

import secrets

from opentelemetry import trace
from passlib.context import CryptContext

tracer = trace.get_tracer(__name__)

# Настройка контекста для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordService:
    """Сервис для работы с паролями."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Хешировать пароль.

        Args:
            password: Пароль в открытом виде

        Returns:
            Хешированный пароль
        """
        with tracer.start_as_current_span("password_service.hash_password") as span:
            span.set_attribute("password.length", len(password))

            hashed = pwd_context.hash(password)

            span.set_attribute("hash.algorithm", "bcrypt")
            return hashed

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверить пароль.

        Args:
            plain_password: Пароль в открытом виде
            hashed_password: Хешированный пароль

        Returns:
            True если пароли совпадают, False если нет
        """
        with tracer.start_as_current_span("password_service.verify_password") as span:
            span.set_attribute("password.length", len(plain_password))

            try:
                is_valid = pwd_context.verify(plain_password, hashed_password)
                span.set_attribute("password.valid", is_valid)
                return is_valid
            except Exception as e:
                span.set_attribute("error", str(e))
                return False

    @staticmethod
    def generate_random_password(length: int = 12) -> str:
        """Сгенерировать случайный пароль.

        Args:
            length: Длина пароля

        Returns:
            Случайный пароль
        """
        with tracer.start_as_current_span("password_service.generate_random_password") as span:
            span.set_attribute("password.length", length)

            # Алфавит для генерации пароля
            alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
            password = "".join(secrets.choice(alphabet) for _ in range(length))

            return password

    @staticmethod
    def is_password_strong(password: str) -> tuple[bool, list[str]]:
        """Проверить силу пароля.

        Args:
            password: Пароль для проверки

        Returns:
            Tuple из булевого значения (сильный ли пароль) и списка ошибок
        """
        with tracer.start_as_current_span("password_service.is_password_strong") as span:
            span.set_attribute("password.length", len(password))

            errors = []

            # Минимальная длина
            if len(password) < 8:
                errors.append("Пароль должен содержать минимум 8 символов")

            # Максимальная длина
            if len(password) > 128:
                errors.append("Пароль не должен превышать 128 символов")

            # Проверка на наличие цифр
            if not any(char.isdigit() for char in password):
                errors.append("Пароль должен содержать хотя бы одну цифру")

            # Проверка на наличие строчных букв
            if not any(char.islower() for char in password):
                errors.append("Пароль должен содержать хотя бы одну строчную букву")

            # Проверка на наличие заглавных букв
            if not any(char.isupper() for char in password):
                errors.append("Пароль должен содержать хотя бы одну заглавную букву")

            # Проверка на наличие специальных символов
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(char in special_chars for char in password):
                errors.append("Пароль должен содержать хотя бы один специальный символ")

            is_strong = len(errors) == 0

            span.set_attribute("password.is_strong", is_strong)
            span.set_attribute("password.errors_count", len(errors))

            return is_strong, errors


# Синглтон сервиса
password_service = PasswordService()
