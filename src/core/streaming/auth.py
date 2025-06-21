"""Система авторизации для WebSocket и SSE."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import get_settings
from core.exceptions.core_base import CoreStreamingConnectionError


class WSAuthError(Exception):
    """Исключение авторизации WebSocket/SSE."""

    pass


class WSAuthenticator:
    """Класс для аутентификации WebSocket и SSE соединений."""

    def __init__(self):
        self.settings = get_settings()
        self.security = HTTPBearer(auto_error=False)

    def create_access_token(self, data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        """Создание JWT токена для WebSocket/SSE."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.settings.WS_JWT_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.settings.WS_JWT_SECRET_KEY, algorithm=self.settings.WS_JWT_ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> dict[str, Any]:
        """Проверка JWT токена."""
        try:
            payload = jwt.decode(token, self.settings.WS_JWT_SECRET_KEY, algorithms=[self.settings.WS_JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise WSAuthError("Токен истек")
        except jwt.PyJWTError:
            raise WSAuthError("Недействительный токен")

    def verify_api_key(self, api_key: str) -> bool:
        """Проверка API ключа."""
        if not self.settings.WS_API_KEYS:
            return False
        return api_key in self.settings.WS_API_KEYS

    async def authenticate_websocket(self, token: str | None = None, api_key: str | None = None) -> dict[str, Any]:
        """Аутентификация WebSocket соединения."""
        if not self.settings.WEBSOCKET_AUTH_REQUIRED:
            return {"authenticated": False, "user": None}

        # Проверяем API ключ
        if api_key and self.verify_api_key(api_key):
            return {"authenticated": True, "user": {"type": "api_key", "key": api_key}}

        # Проверяем JWT токен
        if token:
            try:
                payload = self.verify_token(token)
                return {"authenticated": True, "user": payload}
            except WSAuthError:
                pass

        raise CoreStreamingConnectionError("Не авторизован - требуется JWT токен или API ключ")

    async def authenticate_sse(self, token: str | None = None, api_key: str | None = None) -> dict[str, Any]:
        """Аутентификация SSE соединения."""
        if not self.settings.SSE_AUTH_REQUIRED:
            return {"authenticated": False, "user": None}

        # Проверяем API ключ
        if api_key and self.verify_api_key(api_key):
            return {"authenticated": True, "user": {"type": "api_key", "key": api_key}}

        # Проверяем JWT токен
        if token:
            try:
                payload = self.verify_token(token)
                return {"authenticated": True, "user": payload}
            except WSAuthError:
                pass

        raise CoreStreamingConnectionError("Требуется авторизация")

    async def get_current_user_http(
        self, request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))
    ) -> dict[str, Any]:
        """Получение текущего пользователя из HTTP запроса."""
        # Проверяем API ключ в заголовках
        api_key = request.headers.get(self.settings.WS_API_KEY_HEADER)
        if api_key and self.verify_api_key(api_key):
            return {"authenticated": True, "user": {"type": "api_key", "key": api_key}}

        # Проверяем JWT токен
        if credentials:
            try:
                payload = self.verify_token(credentials.credentials)
                return {"authenticated": True, "user": payload}
            except WSAuthError:
                pass

        # Если авторизация не требуется
        if not (self.settings.WEBSOCKET_AUTH_REQUIRED or self.settings.SSE_AUTH_REQUIRED):
            return {"authenticated": False, "user": None}

        raise CoreStreamingConnectionError("Не авторизован - требуется JWT токен или API ключ")


# Глобальный экземпляр аутентификатора
authenticator = WSAuthenticator()


async def get_ws_auth() -> WSAuthenticator:
    """Dependency для получения аутентификатора."""
    return authenticator


async def require_auth(user_data: dict[str, Any] = Depends(authenticator.get_current_user_http)) -> dict[str, Any]:
    """Dependency для обязательной авторизации."""
    if not user_data["authenticated"]:
        raise CoreStreamingConnectionError("Требуется авторизация")
    return user_data


async def optional_auth(user_data: dict[str, Any] = Depends(authenticator.get_current_user_http)) -> dict[str, Any]:
    """Dependency для опциональной авторизации."""
    return user_data
