"""
Комплексные тесты для системы событий BaseRepository.
"""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from pytz import utc

from core.base.repo.events import CreateEvent, DeleteEvent, UpdateEvent


@pytest.mark.asyncio
async def test_create_event_comprehensive():
    """Тестирует CreateEvent с различными данными."""

    # Тест 1: Событие с объектом с ID
    class MockEntity:
        def __init__(self, id_value):
            self.id = id_value
            self.name = "test"

    entity = MockEntity(uuid.uuid4())
    event = CreateEvent(entity_data=entity)

    assert event.event_type == "entity.created", "Тип события должен быть 'entity.created'"
    assert event.get_entity_id() == str(entity.id), "ID сущности должен совпадать"
    assert event.get_payload() == entity, "Payload должен содержать данные сущности"
    assert event.version == "1.0", "Версия по умолчанию должна быть 1.0"
    assert event.source == "system", "Источник по умолчанию должен быть 'system'"

    # Тест 2: Событие с объектом без ID
    class MockEntityNoId:
        def __init__(self):
            self.name = "test"

    entity_no_id = MockEntityNoId()
    event_no_id = CreateEvent(entity_data=entity_no_id)

    assert event_no_id.get_entity_id() == "unknown", "Объект без ID должен возвращать 'unknown'"

    # Тест 3: Событие с кастомными метаданными
    event_custom = CreateEvent(entity_data=entity, source="test_source", metadata={"custom": "data", "test": True})

    assert event_custom.source == "test_source", "Источник должен быть кастомным"
    assert event_custom.metadata["custom"] == "data", "Метаданные должны содержать кастомные поля"
    assert event_custom.metadata["test"] is True, "Метаданные должны содержать булевы значения"


@pytest.mark.asyncio
async def test_update_event_comprehensive():
    """Тестирует UpdateEvent с различными сценариями."""

    entity_id = str(uuid.uuid4())
    old_data = {"name": "old_name", "status": "draft", "count": 5}
    new_data = {"name": "new_name", "status": "published", "count": 10}
    changed_fields = ["name", "status", "count"]

    # Тест 1: Полное событие обновления
    event = UpdateEvent(entity_id=entity_id, old_data=old_data, new_data=new_data, changed_fields=changed_fields)

    assert event.event_type == "entity.updated", "Тип события должен быть 'entity.updated'"
    assert event.get_entity_id() == entity_id, "ID сущности должен совпадать"

    payload = event.get_payload()
    assert payload["old_data"] == old_data, "Payload должен содержать старые данные"
    assert payload["new_data"] == new_data, "Payload должен содержать новые данные"
    assert payload["changed_fields"] == changed_fields, "Payload должен содержать измененные поля"

    # Тест 2: Событие без измененных полей
    event_no_changes = UpdateEvent(
        entity_id=entity_id,
        old_data=old_data,
        new_data=old_data,  # Данные не изменились
        changed_fields=[],
    )

    assert event_no_changes.changed_fields == [], "Список измененных полей должен быть пустым"

    # Тест 3: Событие с частичными изменениями
    partial_new_data = {"name": "updated_name", "status": "draft", "count": 5}
    event_partial = UpdateEvent(
        entity_id=entity_id, old_data=old_data, new_data=partial_new_data, changed_fields=["name"]
    )

    assert len(event_partial.changed_fields) == 1, "Должно быть изменено только одно поле"
    assert "name" in event_partial.changed_fields, "Поле 'name' должно быть в списке изменений"


@pytest.mark.asyncio
async def test_delete_event_comprehensive():
    """Тестирует DeleteEvent с различными типами удаления."""

    entity_id = str(uuid.uuid4())
    entity_data = {"id": entity_id, "name": "deleted_entity", "created_at": datetime.now(tz=utc).isoformat()}

    # Тест 1: Мягкое удаление
    soft_delete_event = DeleteEvent(entity_id=entity_id, entity_data=entity_data, soft_delete=True)

    assert soft_delete_event.event_type == "entity.deleted", "Тип события должен быть 'entity.deleted'"
    assert soft_delete_event.get_entity_id() == entity_id, "ID сущности должен совпадать"
    assert soft_delete_event.soft_delete is True, "Должно быть мягкое удаление"

    payload = soft_delete_event.get_payload()
    assert payload["entity_data"] == entity_data, "Payload должен содержать данные сущности"
    assert payload["soft_delete"] is True, "Payload должен указывать на мягкое удаление"

    # Тест 2: Жесткое удаление
    hard_delete_event = DeleteEvent(entity_id=entity_id, entity_data=entity_data, soft_delete=False)

    assert hard_delete_event.soft_delete is False, "Должно быть жесткое удаление"
    hard_payload = hard_delete_event.get_payload()
    assert hard_payload["soft_delete"] is False, "Payload должен указывать на жесткое удаление"

    # Тест 3: Событие с минимальными данными
    minimal_event = DeleteEvent(entity_id=entity_id, entity_data={"id": entity_id})

    assert minimal_event.soft_delete is False, "По умолчанию должно быть жесткое удаление"
    minimal_payload = minimal_event.get_payload()
    assert "entity_data" in minimal_payload, "Payload должен содержать данные сущности"


@pytest.mark.asyncio
async def test_events_emit_comprehensive():
    """Тестирует функцию emit событий с трассировкой."""

    entity_id = str(uuid.uuid4())
    entity_data = {"id": entity_id, "name": "test_entity"}

    # Тест 1: Эмит события создания с трассировкой
    with patch("core.base.repo.events.tracer.start_as_current_span") as mock_span:
        mock_context = mock_span.return_value.__enter__.return_value

        # Создаем объект с id атрибутом
        class MockEntityWithId:
            def __init__(self, id_value):
                self.id = id_value

        entity_with_id = MockEntityWithId(entity_id)
        event = CreateEvent(entity_data=entity_with_id)
        event.emit()

        # Проверяем что трассировка была вызвана
        mock_span.assert_called_once_with("event.entity.created")

        # Проверяем что атрибуты трассировки установлены
        mock_context.set_attribute.assert_any_call("event.id", event.id)
        mock_context.set_attribute.assert_any_call("event.type", "entity.created")
        mock_context.set_attribute.assert_any_call("event.entity_id", entity_id)
        mock_context.set_attribute.assert_any_call("event.source", "system")

    # Тест 2: Эмит события обновления
    with patch("core.base.repo.events.tracer.start_as_current_span") as mock_span:
        update_event = UpdateEvent(
            entity_id=entity_id, old_data={"name": "old"}, new_data={"name": "new"}, changed_fields=["name"]
        )
        update_event.emit()

        mock_span.assert_called_once_with("event.entity.updated")

    # Тест 3: Эмит события удаления
    with patch("core.base.repo.events.tracer.start_as_current_span") as mock_span:
        delete_event = DeleteEvent(entity_id=entity_id, entity_data=entity_data, soft_delete=True)
        delete_event.emit()

        mock_span.assert_called_once_with("event.entity.deleted")


@pytest.mark.asyncio
async def test_events_id_generation():
    """Тестирует генерацию ID для событий."""

    entity_data = {"name": "test"}

    # Тест 1: Уникальность ID
    event1 = CreateEvent(entity_data=entity_data)
    event2 = CreateEvent(entity_data=entity_data)

    assert event1.id != event2.id, "ID событий должны быть уникальными"
    assert len(event1.id) == 36, "ID должен быть UUID формата"  # UUID длина с дефисами

    # Тест 2: Временные метки
    import time

    event_before = CreateEvent(entity_data=entity_data)
    time.sleep(0.01)  # Небольшая задержка
    event_after = CreateEvent(entity_data=entity_data)

    assert event_before.timestamp < event_after.timestamp, "Временные метки должны увеличиваться"

    # Тест 3: Формат временной метки
    event = CreateEvent(entity_data=entity_data)

    assert event.timestamp.tzinfo == utc, "Временная метка должна быть в UTC"
    assert isinstance(event.timestamp, datetime), "Временная метка должна быть datetime объектом"


@pytest.mark.asyncio
async def test_events_custom_fields():
    """Тестирует кастомизацию полей событий."""

    entity_data = {"id": "custom_id", "name": "custom_entity"}
    custom_timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=utc)

    # Тест 1: Кастомное событие создания
    event = CreateEvent(
        entity_data=entity_data,
        timestamp=custom_timestamp,
        source="custom_source",
        version="2.0",
        metadata={"operation": "bulk_import", "batch_id": "batch_123", "user_id": "user_456"},
    )

    assert event.timestamp == custom_timestamp, "Временная метка должна быть кастомной"
    assert event.source == "custom_source", "Источник должен быть кастомным"
    assert event.version == "2.0", "Версия должна быть кастомной"
    assert event.metadata["operation"] == "bulk_import", "Метаданные должны содержать operation"
    assert event.metadata["batch_id"] == "batch_123", "Метаданные должны содержать batch_id"
    assert event.metadata["user_id"] == "user_456", "Метаданные должны содержать user_id"

    # Тест 2: Кастомное событие обновления с метаданными
    update_event = UpdateEvent(
        entity_id="update_id",
        old_data={"status": "draft"},
        new_data={"status": "published"},
        changed_fields=["status"],
        metadata={"updated_by": "admin", "reason": "content_review_completed", "automated": False},
    )

    assert update_event.metadata["updated_by"] == "admin", "Метаданные должны содержать updated_by"
    assert update_event.metadata["reason"] == "content_review_completed", "Метаданные должны содержать reason"
    assert update_event.metadata["automated"] is False, "Метаданные должны содержать automated flag"

    # Тест 3: Кастомное событие удаления
    delete_event = DeleteEvent(
        entity_id="delete_id",
        entity_data=entity_data,
        soft_delete=True,
        metadata={"deleted_by": "user_123", "retention_policy": "30_days", "cascade_delete": True},
    )

    assert delete_event.metadata["deleted_by"] == "user_123", "Метаданные должны содержать deleted_by"
    assert delete_event.metadata["retention_policy"] == "30_days", "Метаданные должны содержать retention_policy"
    assert delete_event.metadata["cascade_delete"] is True, "Метаданные должны содержать cascade_delete"


@pytest.mark.asyncio
async def test_events_inheritance_and_generics():
    """Тестирует наследование и работу с generic типами."""

    # Тест 1: Создание событий с разными типами данных
    string_event = CreateEvent[str](entity_data="string_data")
    assert string_event.get_payload() == "string_data", "String payload должен работать"

    dict_event = CreateEvent[dict](entity_data={"key": "value"})
    assert dict_event.get_payload() == {"key": "value"}, "Dict payload должен работать"

    # Тест 2: Событие обновления с комплексными типами
    complex_old = {
        "user": {"id": 1, "name": "John"},
        "settings": {"theme": "dark", "notifications": True},
        "tags": ["python", "fastapi"],
    }
    complex_new = {
        "user": {"id": 1, "name": "John Doe"},
        "settings": {"theme": "light", "notifications": True},
        "tags": ["python", "fastapi", "sqlalchemy"],
    }

    complex_event = UpdateEvent(
        entity_id="complex_id",
        old_data=complex_old,
        new_data=complex_new,
        changed_fields=["user.name", "settings.theme", "tags"],
    )

    payload = complex_event.get_payload()
    assert payload["old_data"]["user"]["name"] == "John", "Старое имя должно быть John"
    assert payload["new_data"]["user"]["name"] == "John Doe", "Новое имя должно быть John Doe"
    assert len(payload["new_data"]["tags"]) == 3, "Должно быть 3 тега в новых данных"

    # Тест 3: Проверка базового класса
    event = CreateEvent(entity_data={"test": "data"})

    assert hasattr(event, "id"), "Событие должно иметь поле id"
    assert hasattr(event, "timestamp"), "Событие должно иметь поле timestamp"
    assert hasattr(event, "event_type"), "Событие должно иметь поле event_type"
    assert hasattr(event, "source"), "Событие должно иметь поле source"
    assert hasattr(event, "version"), "Событие должно иметь поле version"
    assert hasattr(event, "metadata"), "Событие должно иметь поле metadata"
