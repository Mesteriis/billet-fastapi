"""
Application layer для управления пользователями.

Содержит use cases и координирует между доменным слоем и инфраструктурой.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from apps.base.contracts import (
    AlreadyExistsError,
    ForbiddenError,
    IEventPublisher,
    IUserRepository,
    NotFoundError,
    ValidationException,
)
from apps.users.domain import (
    Email,
    Password,
    UserDomain,
    UserDomainService,
    UserLoginEvent,
    Username,
    UserRegisteredEvent,
    UserRole,
    UserVerifiedEvent,
)
from tools.pydantic import BaseModel


# Application DTOs
class CreateUserRequest(BaseModel):
    """Запрос на создание пользователя."""

    email: str
    username: str
    password: str
    password_confirm: str
    full_name: str
    phone: str | None = None


class UpdateUserRequest(BaseModel):
    """Запрос на обновление пользователя."""

    full_name: str | None = None
    phone: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


class ChangeRoleRequest(BaseModel):
    """Запрос на изменение роли пользователя."""

    user_id: uuid.UUID
    new_role: UserRole
    reason: str | None = None


class UserResponse(BaseModel):
    """Ответ с данными пользователя."""

    id: uuid.UUID
    email: str
    username: str
    full_name: str
    status: str
    role: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    phone: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    created_at: str
    updated_at: str
    last_login_at: str | None = None


class UserListResponse(BaseModel):
    """Ответ со списком пользователей."""

    users: list[UserResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# Application Services
class UserApplicationService:
    """Application сервис для управления пользователями."""

    def __init__(
        self,
        user_repository: IUserRepository,
        event_publisher: IEventPublisher,
    ):
        self._user_repository = user_repository
        self._event_publisher = event_publisher

    async def create_user(
        self, db_session: Any, request: CreateUserRequest, created_by_admin: bool = False
    ) -> UserResponse:
        """Создать нового пользователя."""
        # Валидация пароля
        if request.password != request.password_confirm:
            raise ValidationException("Passwords do not match", field="password_confirm")

        # Создание доменных объектов-значений с валидацией
        try:
            email = Email(request.email)
            username = Username(request.username)
            password = Password(request.password)
        except ValidationException:
            raise

        # Проверка уникальности
        existing_user = await self._user_repository.get_by_email(db_session, email=email.value)
        if existing_user:
            raise AlreadyExistsError("User", field="email", value=email.value)

        existing_user = await self._user_repository.get_by_username(db_session, username=username.value)
        if existing_user:
            raise AlreadyExistsError("User", field="username", value=username.value)

        # Создание доменной сущности
        user_domain = UserDomain(
            id=uuid.uuid4(),
            email=email,
            username=username,
            full_name=request.full_name.strip(),
            phone=request.phone,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Если создается админом, сразу верифицируем
        if created_by_admin:
            user_domain.verify_email()

        # Сохранение в репозитории
        db_user = await self._user_repository.create(db_session, obj_in=user_domain)

        # Публикация события
        event = UserRegisteredEvent(
            user_id=user_domain.id,
            email=email.value,
            username=username.value,
        )
        await self._event_publisher.publish_event("user_registered", event.dict())

        return self._map_to_response(user_domain)

    async def get_user(self, db_session: Any, user_id: uuid.UUID) -> UserResponse:
        """Получить пользователя по ID."""
        db_user = await self._user_repository.get(db_session, id=user_id)
        if not db_user:
            raise NotFoundError("User", user_id)

        user_domain = self._map_to_domain(db_user)
        return self._map_to_response(user_domain)

    async def get_users(
        self,
        db_session: Any,
        *,
        skip: int = 0,
        limit: int = 100,
        status_filter: str | None = None,
        role_filter: str | None = None,
        search: str | None = None,
    ) -> UserListResponse:
        """Получить список пользователей с фильтрацией."""
        filters = {}

        if status_filter:
            filters["status"] = status_filter
        if role_filter:
            filters["role"] = role_filter
        if search:
            # Поиск по email, username или full_name
            filters["search"] = search

        db_users = await self._user_repository.get_multi(
            db_session,
            skip=skip,
            limit=limit + 1,  # +1 для проверки has_next
            filters=filters,
        )

        has_next = len(db_users) > limit
        if has_next:
            db_users = db_users[:limit]

        users = [self._map_to_response(self._map_to_domain(db_user)) for db_user in db_users]

        total = await self._user_repository.count(db_session, filters=filters)

        return UserListResponse(
            users=users,
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            page_size=limit,
            has_next=has_next,
        )

    async def update_user(
        self, db_session: Any, user_id: uuid.UUID, request: UpdateUserRequest, updated_by_user_id: uuid.UUID
    ) -> UserResponse:
        """Обновить пользователя."""
        db_user = await self._user_repository.get(db_session, id=user_id)
        if not db_user:
            raise NotFoundError("User", user_id)

        user_domain = self._map_to_domain(db_user)

        # Проверка прав (пользователь может обновлять только себя, админ - любого)
        if user_id != updated_by_user_id:
            updater = await self._user_repository.get(db_session, id=updated_by_user_id)
            if not updater or not await self._user_repository.is_superuser(updater):
                raise ForbiddenError("Cannot update other user's profile")

        # Применение обновлений через доменную логику
        user_domain.update_profile(
            full_name=request.full_name,
            phone=request.phone,
            bio=request.bio,
            avatar_url=request.avatar_url,
        )

        # Сохранение в репозитории
        updated_user = await self._user_repository.update(db_session, db_obj=db_user, obj_in=user_domain.dict())

        return self._map_to_response(self._map_to_domain(updated_user))

    async def change_user_role(
        self, db_session: Any, request: ChangeRoleRequest, changed_by_user_id: uuid.UUID
    ) -> UserResponse:
        """Изменить роль пользователя."""
        # Проверка прав
        admin_user = await self._user_repository.get(db_session, id=changed_by_user_id)
        if not admin_user or not await self._user_repository.is_superuser(admin_user):
            raise ForbiddenError("Only superusers can change user roles")

        # Получение пользователя
        db_user = await self._user_repository.get(db_session, id=request.user_id)
        if not db_user:
            raise NotFoundError("User", request.user_id)

        user_domain = self._map_to_domain(db_user)

        # Проверка возможности повышения через доменный сервис
        if not UserDomainService.can_user_be_promoted(user_domain, request.new_role):
            raise ValidationException(f"User cannot be promoted to {request.new_role}")

        # Изменение роли через доменную логику
        user_domain.change_role(request.new_role)

        # Сохранение
        updated_user = await self._user_repository.update(db_session, db_obj=db_user, obj_in=user_domain.dict())

        return self._map_to_response(self._map_to_domain(updated_user))

    async def activate_user(self, db_session: Any, user_id: uuid.UUID, activated_by_user_id: uuid.UUID) -> UserResponse:
        """Активировать пользователя."""
        # Проверка прав
        admin_user = await self._user_repository.get(db_session, id=activated_by_user_id)
        if not admin_user or not await self._user_repository.is_superuser(admin_user):
            raise ForbiddenError("Only superusers can activate users")

        db_user = await self._user_repository.get(db_session, id=user_id)
        if not db_user:
            raise NotFoundError("User", user_id)

        user_domain = self._map_to_domain(db_user)
        user_domain.activate()

        updated_user = await self._user_repository.update(db_session, db_obj=db_user, obj_in=user_domain.dict())

        return self._map_to_response(self._map_to_domain(updated_user))

    async def deactivate_user(
        self, db_session: Any, user_id: uuid.UUID, deactivated_by_user_id: uuid.UUID, reason: str | None = None
    ) -> UserResponse:
        """Деактивировать пользователя."""
        # Проверка прав
        admin_user = await self._user_repository.get(db_session, id=deactivated_by_user_id)
        if not admin_user or not await self._user_repository.is_superuser(admin_user):
            raise ForbiddenError("Only superusers can deactivate users")

        db_user = await self._user_repository.get(db_session, id=user_id)
        if not db_user:
            raise NotFoundError("User", user_id)

        user_domain = self._map_to_domain(db_user)
        user_domain.deactivate()

        updated_user = await self._user_repository.update(db_session, db_obj=db_user, obj_in=user_domain.dict())

        return self._map_to_response(self._map_to_domain(updated_user))

    async def verify_user_email(self, db_session: Any, user_id: uuid.UUID) -> UserResponse:
        """Подтвердить email пользователя."""
        db_user = await self._user_repository.get(db_session, id=user_id)
        if not db_user:
            raise NotFoundError("User", user_id)

        user_domain = self._map_to_domain(db_user)

        if user_domain.is_verified:
            return self._map_to_response(user_domain)

        user_domain.verify_email()

        updated_user = await self._user_repository.update(db_session, db_obj=db_user, obj_in=user_domain.dict())

        # Публикация события
        event = UserVerifiedEvent(user_id=user_domain.id)
        await self._event_publisher.publish_event("user_verified", event.dict())

        return self._map_to_response(self._map_to_domain(updated_user))

    async def suggest_usernames(self, db_session: Any, base_username: str) -> list[str]:
        """Предложить варианты имен пользователей."""
        # Получить существующие имена пользователей
        existing_users = await self._user_repository.get_multi(
            db_session,
            skip=0,
            limit=1000,  # Ограничение для производительности
            filters={"username_like": base_username[:10]},  # Частичное совпадение
        )

        existing_usernames = [getattr(user, "username", "") for user in existing_users]

        return UserDomainService.generate_username_suggestions(base_username, existing_usernames)

    def _map_to_domain(self, db_user: Any) -> UserDomain:
        """Преобразовать DB модель в доменную сущность."""
        return UserDomain(
            id=db_user.id,
            email=Email(db_user.email),
            username=Username(db_user.username),
            full_name=db_user.full_name,
            status=db_user.status,
            role=db_user.role,
            is_active=db_user.is_active,
            is_verified=db_user.is_verified,
            is_superuser=db_user.is_superuser,
            phone=db_user.phone,
            avatar_url=db_user.avatar_url,
            bio=db_user.bio,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            last_login_at=db_user.last_login_at,
        )

    def _map_to_response(self, user_domain: UserDomain) -> UserResponse:
        """Преобразовать доменную сущность в ответ API."""
        return UserResponse(
            id=user_domain.id,
            email=user_domain.email.value,
            username=user_domain.username.value,
            full_name=user_domain.full_name,
            status=user_domain.status,
            role=user_domain.role,
            is_active=user_domain.is_active,
            is_verified=user_domain.is_verified,
            is_superuser=user_domain.is_superuser,
            phone=user_domain.phone,
            avatar_url=user_domain.avatar_url,
            bio=user_domain.bio,
            created_at=user_domain.created_at.isoformat(),
            updated_at=user_domain.updated_at.isoformat(),
            last_login_at=user_domain.last_login_at.isoformat() if user_domain.last_login_at else None,
        )
