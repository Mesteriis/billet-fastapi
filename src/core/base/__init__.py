"""
Базовые компоненты для всех приложений.
"""

from .models import BaseModel

__all__ = [
    "BaseEvent",
    "BaseModel",
    "BaseRepository",
    "CreateEvent",
    "DeleteEvent",
    "UpdateEvent",
]

from .repo import BaseRepository

from .repo.events import BaseEvent, CreateEvent, DeleteEvent, UpdateEvent
