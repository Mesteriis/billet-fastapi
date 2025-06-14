"""
Фабрики для создания тестовых данных.
"""

from .user_factory import (
    create_admin_and_users,
    create_admin_user,
    create_inactive_user,
    create_test_users,
    create_user,
    create_verified_user,
    make_admin_data,
    make_user_data,
)

try:
    from .message_factory import (
        make_broadcast_message,
        make_message_batch,
        make_notification,
        make_ws_command,
        make_ws_message,
        make_ws_response,
    )
except ImportError:
    # Если модули realtime/messaging не существуют
    pass

try:
    from .auth_factory import create_refresh_tokens_batch, refresh_token_factory
except ImportError:
    # Если auth_factory не существует
    pass

__all__ = [
    # User factories
    "create_user",
    "create_verified_user",
    "create_admin_user",
    "create_inactive_user",
    "create_test_users",
    "create_admin_and_users",
    "make_user_data",
    "make_admin_data",
    # Message factories (if available)
    "make_ws_message",
    "make_ws_command",
    "make_ws_response",
    "make_notification",
    "make_broadcast_message",
    "make_message_batch",
    # Auth factories (if available)
    "refresh_token_factory",
    "create_refresh_tokens_batch",
]
