"""Обработчики Telegram ботов."""

from .admin import *
from .basic import *

__all__ = [
    "register_admin_handlers",
    "register_basic_handlers",
]
