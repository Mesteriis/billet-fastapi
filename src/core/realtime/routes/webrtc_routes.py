"""WebRTC специализированные роуты."""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import Field

from core.exceptions import CoreRealtimeAPIException
from tools.pydantic import BaseModel

from ..auth import optional_auth, require_auth
from ..connection_manager import connection_manager
from ..models import WebRTCMessage, WebRTCPeerConnection, WebRTCRoom, WebRTCSignalType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/realtime/webrtc", tags=["WebRTC"])

# Хранилище комнат и соединений
webrtc_rooms: dict[str, WebRTCRoom] = {}
peer_connections: dict[str, WebRTCPeerConnection] = {}


# Pydantic модели
class CreateRoomRequest(BaseModel):
    """Запрос на создание WebRTC комнаты."""

    room_id: str | None = None
    name: str | None = None
    max_participants: int = Field(default=10, ge=2, le=50)
    settings: dict[str, Any] | None = None


class JoinRoomRequest(BaseModel):
    """Запрос на вход в комнату."""

    room_id: str


class WebRTCSignalRequest(BaseModel):
    """Запрос на отправку WebRTC сигнала."""

    signal_type: WebRTCSignalType
    target_peer_id: str
    room_id: str | None = None
    sdp: str | None = None
    ice_candidate: dict[str, Any] | None = None
    connection_state: str | None = None
    gathering_state: str | None = None
    metadata: dict[str, Any] | None = None


class UpdateRoomSettingsRequest(BaseModel):
    """Запрос на обновление настроек комнаты."""

    name: str | None = None
    max_participants: int | None = Field(None, ge=2, le=50)
    settings: dict[str, Any] | None = None


# WebRTC сигналинг через WebSocket
@router.websocket("/signaling")
async def webrtc_signaling_websocket(websocket: WebSocket, room_id: str | None = None, peer_id: str | None = None):
    """
    Специализированный WebSocket endpoint для WebRTC сигналинга.
    """
    if not peer_id:
        peer_id = f"peer_{uuid4()}"

    logger.info(f"WebRTC сигналинг подключение: peer_id={peer_id}, room_id={room_id}")

    try:
        await websocket.accept()

        # Отправляем информацию о подключении
        await websocket.send_json(
            {
                "type": "connection_info",
                "peer_id": peer_id,
                "room_id": room_id,
                "timestamp": datetime.now(tz=utc)().isoformat(),
            }
        )

        # Если указана комната, автоматически присоединяемся
        if room_id:
            await handle_join_room_websocket(websocket, peer_id, room_id)

        # Основной цикл обработки WebRTC сигналов
        while True:
            try:
                data = await websocket.receive_json()
                await handle_webrtc_signal_websocket(websocket, peer_id, data)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Ошибка обработки WebRTC сигнала: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Ошибка обработки сигнала: {e!s}",
                        "timestamp": datetime.now(tz=utc)().isoformat(),
                    }
                )

    except Exception as e:
        logger.error(f"Ошибка WebRTC сигналинг соединения: {e}")
    finally:
        # Удаляем пира из всех комнат
        await cleanup_peer(peer_id)
        logger.info(f"WebRTC сигналинг отключен: peer_id={peer_id}")


async def handle_webrtc_signal_websocket(websocket: WebSocket, peer_id: str, data: dict[str, Any]):
    """Обработка WebRTC сигналов через WebSocket."""
    signal_type = data.get("signal_type")
    target_peer_id = data.get("target_peer_id")
    room_id = data.get("room_id")

    if signal_type == "join_room":
        await handle_join_room_websocket(websocket, peer_id, data.get("room_id"))

    elif signal_type == "leave_room":
        await handle_leave_room_websocket(websocket, peer_id, data.get("room_id"))

    elif signal_type in ["offer", "answer", "ice-candidate"]:
        await handle_peer_signal_websocket(websocket, peer_id, data)

    else:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Неизвестный тип сигнала: {signal_type}",
                "timestamp": datetime.now(tz=utc)().isoformat(),
            }
        )


async def handle_join_room_websocket(websocket: WebSocket, peer_id: str, room_id: str):
    """Обработка входа в комнату через WebSocket."""
    if not room_id:
        await websocket.send_json(
            {"type": "error", "message": "Не указан ID комнаты", "timestamp": datetime.now(tz=utc)().isoformat()}
        )
        return

    # Создаем комнату если не существует
    if room_id not in webrtc_rooms:
        webrtc_rooms[room_id] = WebRTCRoom(room_id=room_id, name=f"Room {room_id}", created_by=peer_id)

    room = webrtc_rooms[room_id]

    # Проверяем лимит участников
    if len(room.participants) >= room.max_participants:
        await websocket.send_json(
            {"type": "error", "message": "Комната переполнена", "timestamp": datetime.now(tz=utc)().isoformat()}
        )
        return

    # Добавляем участника
    if peer_id not in room.participants:
        room.participants.append(peer_id)

    # Отправляем подтверждение
    await websocket.send_json(
        {
            "type": "room_joined",
            "room_id": room_id,
            "peer_id": peer_id,
            "participants": room.participants,
            "room_info": room.dict(),
            "timestamp": datetime.now(tz=utc)().isoformat(),
        }
    )

    # Уведомляем других участников
    await broadcast_to_room(
        room_id,
        {
            "type": "peer_joined",
            "peer_id": peer_id,
            "room_id": room_id,
            "participants": room.participants,
            "timestamp": datetime.now(tz=utc)().isoformat(),
        },
        exclude_peer=peer_id,
    )


async def handle_leave_room_websocket(websocket: WebSocket, peer_id: str, room_id: str):
    """Обработка выхода из комнаты через WebSocket."""
    if room_id not in webrtc_rooms:
        await websocket.send_json(
            {"type": "error", "message": "Комната не найдена", "timestamp": datetime.now(tz=utc)().isoformat()}
        )
        return

    room = webrtc_rooms[room_id]

    # Удаляем участника
    if peer_id in room.participants:
        room.participants.remove(peer_id)

    # Отправляем подтверждение
    await websocket.send_json(
        {
            "type": "room_left",
            "room_id": room_id,
            "peer_id": peer_id,
            "participants": room.participants,
            "timestamp": datetime.now(tz=utc)().isoformat(),
        }
    )

    # Уведомляем других участников
    await broadcast_to_room(
        room_id,
        {
            "type": "peer_left",
            "peer_id": peer_id,
            "room_id": room_id,
            "participants": room.participants,
            "timestamp": datetime.now(tz=utc)().isoformat(),
        },
        exclude_peer=peer_id,
    )

    # Удаляем пустую комнату
    if not room.participants:
        del webrtc_rooms[room_id]


async def handle_peer_signal_websocket(websocket: WebSocket, peer_id: str, data: dict[str, Any]):
    """Обработка peer-to-peer сигналов через WebSocket."""
    target_peer_id = data.get("target_peer_id")
    if not target_peer_id:
        await websocket.send_json(
            {"type": "error", "message": "Не указан целевой пир", "timestamp": datetime.now(tz=utc)().isoformat()}
        )
        return

    # Создаем запись о соединении между пирами
    connection_key = f"{peer_id}_{target_peer_id}"
    if connection_key not in peer_connections:
        peer_connections[connection_key] = WebRTCPeerConnection(
            peer_id=peer_id, target_peer_id=target_peer_id, room_id=data.get("room_id")
        )

    # Обновляем состояние соединения
    connection = peer_connections[connection_key]
    connection.last_activity = datetime.now(tz=utc)()

    if data.get("connection_state"):
        connection.connection_state = data["connection_state"]
    if data.get("ice_gathering_state"):
        connection.ice_gathering_state = data["ice_gathering_state"]

    # Пересылаем сигнал целевому пиру
    signal_message = {
        "type": "webrtc_signal",
        "signal_type": data["signal_type"],
        "from_peer_id": peer_id,
        "to_peer_id": target_peer_id,
        "room_id": data.get("room_id"),
        "sdp": data.get("sdp"),
        "ice_candidate": data.get("ice_candidate"),
        "connection_state": data.get("connection_state"),
        "gathering_state": data.get("gathering_state"),
        "metadata": data.get("metadata"),
        "timestamp": datetime.now(tz=utc)().isoformat(),
    }

    # Находим целевого пира и отправляем сигнал
    target_connections = await connection_manager.get_user_connections(target_peer_id)
    if target_connections:
        for conn_id in target_connections:
            await connection_manager.send_to_connection(conn_id, signal_message)

        # Отправляем подтверждение отправителю
        await websocket.send_json(
            {
                "type": "signal_delivered",
                "signal_type": data["signal_type"],
                "target_peer_id": target_peer_id,
                "timestamp": datetime.now(tz=utc)().isoformat(),
            }
        )
    else:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Пир {target_peer_id} не найден",
                "timestamp": datetime.now(tz=utc)().isoformat(),
            }
        )


async def broadcast_to_room(room_id: str, message: dict[str, Any], exclude_peer: str | None = None):
    """Широковещательная отправка сообщения в комнату."""
    if room_id not in webrtc_rooms:
        return

    room = webrtc_rooms[room_id]

    for participant_id in room.participants:
        if exclude_peer and participant_id == exclude_peer:
            continue

        participant_connections = await connection_manager.get_user_connections(participant_id)
        for conn_id in participant_connections:
            await connection_manager.send_to_connection(conn_id, message)


async def cleanup_peer(peer_id: str):
    """Очистка данных пира."""
    # Удаляем из всех комнат
    rooms_to_delete = []
    for room_id, room in webrtc_rooms.items():
        if peer_id in room.participants:
            room.participants.remove(peer_id)

            # Уведомляем других участников
            await broadcast_to_room(
                room_id,
                {
                    "type": "peer_disconnected",
                    "peer_id": peer_id,
                    "room_id": room_id,
                    "participants": room.participants,
                    "timestamp": datetime.now(tz=utc)().isoformat(),
                },
                exclude_peer=peer_id,
            )

            # Помечаем пустые комнаты для удаления
            if not room.participants:
                rooms_to_delete.append(room_id)

    # Удаляем пустые комнаты
    for room_id in rooms_to_delete:
        del webrtc_rooms[room_id]

    # Удаляем peer connections
    connections_to_delete = []
    for conn_key, connection in peer_connections.items():
        if connection.peer_id == peer_id or connection.target_peer_id == peer_id:
            connections_to_delete.append(conn_key)

    for conn_key in connections_to_delete:
        del peer_connections[conn_key]


# HTTP API endpoints


@router.post("/rooms", dependencies=[Depends(require_auth)])
async def create_webrtc_room(request: CreateRoomRequest, auth_data=Depends(optional_auth)):
    """Создать WebRTC комнату."""
    try:
        room_id = request.room_id or f"room_{uuid4()}"

        if room_id in webrtc_rooms:
            raise CoreRealtimeAPIException(status_code=409, detail="Комната уже существует")

        room = WebRTCRoom(
            room_id=room_id,
            name=request.name or f"Room {room_id}",
            max_participants=request.max_participants,
            created_by=auth_data.get("user_id") if auth_data else None,
            settings=request.settings,
        )

        webrtc_rooms[room_id] = room

        return {"success": True, "message": f"Комната {room_id} создана", "room": room.dict()}

    except Exception as e:
        logger.error(f"Ошибка создания WebRTC комнаты: {e}")
        raise CoreRealtimeAPIException(status_code=500, detail=str(e))


@router.get("/rooms")
async def list_webrtc_rooms():
    """Получить список WebRTC комнат."""
    return {
        "rooms": [
            {
                **room.dict(),
                "active_connections": len(
                    [
                        conn_key
                        for conn_key, conn in peer_connections.items()
                        if any(participant in [conn.peer_id, conn.target_peer_id] for participant in room.participants)
                    ]
                ),
            }
            for room in webrtc_rooms.values()
        ],
        "total": len(webrtc_rooms),
    }


@router.get("/rooms/{room_id}")
async def get_webrtc_room(room_id: str):
    """Получить информацию о WebRTC комнате."""
    if room_id not in webrtc_rooms:
        raise CoreRealtimeAPIException(status_code=404, detail="Комната не найдена")

    room = webrtc_rooms[room_id]

    # Получаем активные соединения в комнате
    active_connections = [conn.dict() for conn in peer_connections.values() if conn.room_id == room_id]

    return {"room": room.dict(), "active_connections": active_connections, "connection_count": len(active_connections)}


@router.put("/rooms/{room_id}", dependencies=[Depends(require_auth)])
async def update_webrtc_room(room_id: str, request: UpdateRoomSettingsRequest, auth_data=Depends(optional_auth)):
    """Обновить настройки WebRTC комнаты."""
    if room_id not in webrtc_rooms:
        raise CoreRealtimeAPIException(status_code=404, detail="Комната не найдена")

    room = webrtc_rooms[room_id]

    # Проверяем права (только создатель может изменять)
    if auth_data and room.created_by and room.created_by != auth_data.get("user_id"):
        raise CoreRealtimeAPIException(status_code=403, detail="Недостаточно прав")

    # Обновляем настройки
    if request.name is not None:
        room.name = request.name
    if request.max_participants is not None:
        room.max_participants = request.max_participants
    if request.settings is not None:
        room.settings = request.settings

    # Уведомляем участников об изменениях
    await broadcast_to_room(
        room_id,
        {
            "type": "room_updated",
            "room_id": room_id,
            "room_info": room.dict(),
            "timestamp": datetime.now(tz=utc)().isoformat(),
        },
    )

    return {"success": True, "message": f"Комната {room_id} обновлена", "room": room.dict()}


@router.delete("/rooms/{room_id}", dependencies=[Depends(require_auth)])
async def delete_webrtc_room(room_id: str, auth_data=Depends(optional_auth)):
    """Удалить WebRTC комнату."""
    if room_id not in webrtc_rooms:
        raise CoreRealtimeAPIException(status_code=404, detail="Комната не найдена")

    room = webrtc_rooms[room_id]

    # Проверяем права (только создатель может удалить)
    if auth_data and room.created_by and room.created_by != auth_data.get("user_id"):
        raise CoreRealtimeAPIException(status_code=403, detail="Недостаточно прав")

    # Уведомляем участников
    await broadcast_to_room(
        room_id, {"type": "room_deleted", "room_id": room_id, "timestamp": datetime.now(tz=utc)().isoformat()}
    )

    # Удаляем связанные peer connections
    connections_to_delete = [conn_key for conn_key, conn in peer_connections.items() if conn.room_id == room_id]

    for conn_key in connections_to_delete:
        del peer_connections[conn_key]

    del webrtc_rooms[room_id]

    return {"success": True, "message": f"Комната {room_id} удалена"}


@router.post("/signal", dependencies=[Depends(require_auth)])
async def send_webrtc_signal(request: WebRTCSignalRequest, auth_data=Depends(optional_auth)):
    """Отправить WebRTC сигнал."""
    try:
        peer_id = auth_data.get("user_id") if auth_data else f"anonymous_{uuid4()}"

        webrtc_message = WebRTCMessage(
            signal_type=request.signal_type,
            peer_id=peer_id,
            target_peer_id=request.target_peer_id,
            room_id=request.room_id,
            sdp=request.sdp,
            ice_candidate=request.ice_candidate,
            connection_state=request.connection_state,
            gathering_state=request.gathering_state,
            metadata=request.metadata,
        )

        # Отправляем сигнал целевому пиру
        target_connections = await connection_manager.get_user_connections(request.target_peer_id)
        if not target_connections:
            raise CoreRealtimeAPIException(status_code=404, detail="Целевой пир не найден")

        sent_count = 0
        for connection_id in target_connections:
            await connection_manager.send_to_connection(connection_id, webrtc_message.dict())
            sent_count += 1

        return {
            "success": True,
            "message": f"WebRTC сигнал отправлен пиру {request.target_peer_id}",
            "message_id": webrtc_message.id,
            "signal_type": request.signal_type,
            "recipients_count": sent_count,
        }

    except Exception as e:
        logger.error(f"Ошибка отправки WebRTC сигнала: {e}")
        raise CoreRealtimeAPIException(status_code=500, detail=str(e))


@router.get("/connections")
async def get_webrtc_connections():
    """Получить информацию о WebRTC соединениях."""
    return {
        "connections": [conn.dict() for conn in peer_connections.values()],
        "total": len(peer_connections),
        "by_room": {
            room_id: [conn.dict() for conn in peer_connections.values() if conn.room_id == room_id]
            for room_id in webrtc_rooms.keys()
        },
    }


@router.delete("/connections/{peer_id}", dependencies=[Depends(require_auth)])
async def disconnect_peer(peer_id: str):
    """Принудительно отключить пира."""
    await cleanup_peer(peer_id)

    return {"success": True, "message": f"Пир {peer_id} отключен"}


@router.get("/health")
async def webrtc_health():
    """Проверка состояния WebRTC сервиса."""
    return {
        "status": "healthy",
        "service": "webrtc",
        "rooms_count": len(webrtc_rooms),
        "connections_count": len(peer_connections),
        "total_participants": sum(len(room.participants) for room in webrtc_rooms.values()),
        "timestamp": datetime.now(tz=utc)().isoformat(),
    }
