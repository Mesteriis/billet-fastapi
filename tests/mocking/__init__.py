"""
Модуль для мокирования внешних API и сервисов.
"""

from .external_api_mocks import (
    ExternalAPIMocker,
    mock_external_service,
    mock_notification_service,
    mock_payment_service,
)
from .telegram_mocks import TelegramBotMocker, mock_telegram_bot

__all__ = [
    "ExternalAPIMocker",
    "TelegramBotMocker",
    "mock_external_service",
    "mock_notification_service",
    "mock_payment_service",
    "mock_telegram_bot",
]
