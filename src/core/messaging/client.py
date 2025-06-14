"""Клиент для работы с сообщениями RabbitMQ."""

# Все функции перенесены в core.py для избежания дублирования
from .core import MessageClient, get_message_client

__all__ = ["MessageClient", "get_message_client"]
