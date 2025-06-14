"""Декораторы для регистрации команд и обработчиков Telegram ботов."""

import functools
import inspect
from collections.abc import Callable
from typing import Any

from aiogram.types import CallbackQuery, Message


class CommandRegistry:
    """Реестр команд для автоматической регистрации."""

    def __init__(self) -> None:
        self.commands: dict[str, dict[str, Any]] = {}
        self.message_handlers: list[dict[str, Any]] = []
        self.callback_handlers: list[dict[str, Any]] = []
        self.middleware_handlers: list[Callable] = []

    def register_command(
        self,
        command: str,
        handler: Callable,
        description: str = "",
        admin_only: bool = False,
        allowed_users: list[int] | None = None,
        allowed_chats: list[int] | None = None,
        **kwargs,
    ) -> None:
        """Регистрация команды."""
        self.commands[command] = {
            "handler": handler,
            "command": command,
            "description": description,
            "admin_only": admin_only,
            "allowed_users": allowed_users or [],
            "allowed_chats": allowed_chats or [],
            "kwargs": kwargs,
        }

    def register_message_handler(
        self, handler: Callable, content_types: list[str] | None = None, filters: list | None = None, **kwargs
    ) -> None:
        """Регистрация обработчика сообщений."""
        self.message_handlers.append(
            {"handler": handler, "content_types": content_types or ["text"], "filters": filters or [], "kwargs": kwargs}
        )

    def register_callback_handler(
        self, handler: Callable, callback_data: str | None = None, filters: list | None = None, **kwargs
    ) -> None:
        """Регистрация обработчика callback query."""
        self.callback_handlers.append(
            {"handler": handler, "callback_data": callback_data, "filters": filters or [], "kwargs": kwargs}
        )

    def register_middleware(self, handler: Callable) -> None:
        """Регистрация middleware."""
        self.middleware_handlers.append(handler)

    def get_commands_info(self) -> list[dict[str, str]]:
        """Получить информацию о всех командах для помощи."""
        return [
            {"command": f"/{cmd}", "description": info["description"] or "Без описания"}
            for cmd, info in self.commands.items()
        ]


# Глобальный реестр команд
_registry = CommandRegistry()


def get_command_registry() -> CommandRegistry:
    """Получить глобальный реестр команд."""
    return _registry


def command(
    cmd: str,
    description: str = "",
    admin_only: bool = False,
    allowed_users: list[int] | None = None,
    allowed_chats: list[int] | None = None,
    **kwargs,
) -> Callable[[Callable], Callable]:
    """
    Декоратор для регистрации команды бота.

    Args:
        cmd: Команда (без /)
        description: Описание команды
        admin_only: Только для администраторов
        allowed_users: Список разрешенных пользователей
        allowed_chats: Список разрешенных чатов
    """

    def decorator(func: Callable) -> Callable:
        # Добавляем проверки безопасности
        @functools.wraps(func)
        async def wrapper(message: Message, *args, **func_kwargs):
            from .config import TelegramBotsConfig

            config = TelegramBotsConfig()

            user_id = message.from_user.id if message.from_user else None
            chat_id = message.chat.id

            # Базовые проверки безопасности
            if user_id is None or not config.is_user_allowed(user_id) or not config.is_chat_allowed(chat_id):
                return

            # Проверка прав администратора
            if admin_only and (user_id is None or not config.is_admin(user_id)):
                from .templates import render_template

                response = render_template("admin_only")
                if response:
                    await message.answer(response)
                return

            # Проверка конкретных разрешенных пользователей для команды
            if allowed_users and (user_id is None or user_id not in allowed_users):
                from .templates import render_template

                response = render_template("error", error_message="У вас нет прав на эту команду")
                if response:
                    await message.answer(response)
                return

            # Проверка конкретных разрешенных чатов для команды
            if allowed_chats and chat_id not in allowed_chats:
                return

            # Выполняем оригинальную функцию
            try:
                if inspect.iscoroutinefunction(func):
                    return await func(message, *args, **func_kwargs)
                else:
                    return func(message, *args, **func_kwargs)
            except Exception as e:
                from .templates import render_template

                response = render_template("error", error_message=f"Ошибка выполнения команды: {e!s}")
                if response:
                    await message.answer(response)

                # Логируем ошибку
                import logging

                logging.error(f"Ошибка в команде /{cmd}: {e}", exc_info=True)

        # Регистрируем команду
        _registry.register_command(cmd, wrapper, description, admin_only, allowed_users, allowed_chats, **kwargs)

        return wrapper

    return decorator


def message_handler(
    content_types: list[str] | None = None, filters: list | None = None, **kwargs
) -> Callable[[Callable], Callable]:
    """
    Декоратор для регистрации обработчика сообщений.

    Args:
        content_types: Типы контента (text, photo, document и т.д.)
        filters: Дополнительные фильтры
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(message: Message, *args, **func_kwargs):
            from .config import TelegramBotsConfig

            config = TelegramBotsConfig()

            user_id = message.from_user.id if message.from_user else None
            chat_id = message.chat.id

            # Базовые проверки безопасности
            if user_id is None or not config.is_user_allowed(user_id) or not config.is_chat_allowed(chat_id):
                return

            try:
                if inspect.iscoroutinefunction(func):
                    return await func(message, *args, **func_kwargs)
                else:
                    return func(message, *args, **func_kwargs)
            except Exception as e:
                from .templates import render_template

                response = render_template("error", error_message=f"Ошибка обработки сообщения: {e!s}")
                if response:
                    await message.answer(response)

                import logging

                logging.error(f"Ошибка в обработчике сообщений: {e}", exc_info=True)

        # Регистрируем обработчик
        _registry.register_message_handler(wrapper, content_types, filters, **kwargs)

        return wrapper

    return decorator


def callback_handler(
    callback_data: str | None = None, filters: list | None = None, **kwargs
) -> Callable[[Callable], Callable]:
    """
    Декоратор для регистрации обработчика callback query.

    Args:
        callback_data: Данные callback query
        filters: Дополнительные фильтры
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(callback_query: CallbackQuery, *args, **func_kwargs):
            from .config import TelegramBotsConfig

            config = TelegramBotsConfig()

            user_id = callback_query.from_user.id if callback_query.from_user else None
            chat_id = callback_query.message.chat.id if callback_query.message else None

            # Базовые проверки безопасности
            if not config.is_user_allowed(user_id) or (chat_id and not config.is_chat_allowed(chat_id)):
                await callback_query.answer("Доступ запрещен", show_alert=True)
                return

            try:
                if inspect.iscoroutinefunction(func):
                    return await func(callback_query, *args, **func_kwargs)
                else:
                    return func(callback_query, *args, **func_kwargs)
            except Exception as e:
                await callback_query.answer(f"Ошибка: {e!s}", show_alert=True)

                import logging

                logging.error(f"Ошибка в callback обработчике: {e}", exc_info=True)

        # Регистрируем обработчик
        _registry.register_callback_handler(wrapper, callback_data, filters, **kwargs)

        return wrapper

    return decorator


def middleware(func: Callable):
    """
    Декоратор для регистрации middleware.

    Middleware должен принимать (handler, event, data) и вызывать await handler(event, data)
    """
    _registry.register_middleware(func)
    return func


def rate_limit(calls: int = 1, period: int = 60):
    """
    Декоратор для ограничения частоты вызовов.

    Args:
        calls: Количество вызовов
        period: Период в секундах
    """

    def decorator(func: Callable):
        # Хранилище для отслеживания вызовов
        calls_storage: dict[int, list[float]] = {}

        @functools.wraps(func)
        async def wrapper(message_or_query: Message | CallbackQuery, *args, **kwargs):
            import time

            # Получаем ID пользователя
            if isinstance(message_or_query, Message):
                user_id = message_or_query.from_user.id if message_or_query.from_user else None
            else:  # CallbackQuery
                user_id = message_or_query.from_user.id if message_or_query.from_user else None

            if user_id is None:
                return await func(message_or_query, *args, **kwargs)

            current_time = time.time()

            # Очищаем старые записи
            if user_id in calls_storage:
                calls_storage[user_id] = [
                    call_time for call_time in calls_storage[user_id] if current_time - call_time < period
                ]
            else:
                calls_storage[user_id] = []

            # Проверяем лимит
            if len(calls_storage[user_id]) >= calls:
                from .templates import render_template

                response = render_template(
                    "error", error_message=f"Слишком много запросов. Попробуйте через {period} секунд."
                )

                if isinstance(message_or_query, Message):
                    if response:
                        await message_or_query.answer(response)
                else:  # CallbackQuery
                    await message_or_query.answer(
                        f"Слишком много запросов. Попробуйте через {period} секунд.", show_alert=True
                    )
                return

            # Добавляем текущий вызов
            calls_storage[user_id].append(current_time)

            # Выполняем функцию
            return await func(message_or_query, *args, **kwargs)

        return wrapper

    return decorator


def admin_only(func: Callable):
    """Декоратор для команд только для администраторов."""

    @functools.wraps(func)
    async def wrapper(message_or_query: Message | CallbackQuery, *args, **kwargs):
        from .config import TelegramBotsConfig

        config = TelegramBotsConfig()

        # Получаем ID пользователя
        if isinstance(message_or_query, Message):
            user_id = message_or_query.from_user.id if message_or_query.from_user else None
        else:  # CallbackQuery
            user_id = message_or_query.from_user.id if message_or_query.from_user else None

        if not config.is_admin(user_id):
            from .templates import render_template

            response = render_template("admin_only")

            if isinstance(message_or_query, Message):
                if response:
                    await message_or_query.answer(response)
            else:  # CallbackQuery
                await message_or_query.answer("Только для администраторов", show_alert=True)
            return

        return await func(message_or_query, *args, **kwargs)

    return wrapper
