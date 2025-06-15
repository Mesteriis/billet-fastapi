"""
Исключения для системы управления миграциями.
"""


class MigrationError(Exception):
    """Базовое исключение для ошибок миграций."""
    pass


class ValidationError(MigrationError):
    """Ошибка валидации миграции."""
    pass


class BackupError(MigrationError):
    """Ошибка создания бэкапа."""
    pass


class MonitoringError(MigrationError):
    """Ошибка мониторинга миграций."""
    pass 