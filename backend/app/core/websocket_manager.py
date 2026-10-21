import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        # Maps user_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Maps collaboration_id -> list of active WebSockets
        self.collaboration_rooms: Dict[str, List[WebSocket]] = {}

    async def connect_user(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect_user(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def join_room(self, websocket: WebSocket, room_id: str):
        if room_id not in self.collaboration_rooms:
            self.collaboration_rooms[room_id] = []
        if websocket not in self.collaboration_rooms[room_id]:
            self.collaboration_rooms[room_id].append(websocket)

    def leave_room(self, websocket: WebSocket, room_id: str):
        if room_id in self.collaboration_rooms:
            if websocket in self.collaboration_rooms[room_id]:
                self.collaboration_rooms[room_id].remove(websocket)
            if not self.collaboration_rooms[room_id]:
                del self.collaboration_rooms[room_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            payload = json.dumps(message)
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.warning(f"Error sending WS message to {user_id}: {e}")

    async def broadcast_to_room(self, message: dict, room_id: str):
        if room_id in self.collaboration_rooms:
            payload = json.dumps(message)
            for connection in self.collaboration_rooms[room_id]:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.warning(f"Error broadcasting WS to room {room_id}: {e}")

ws_manager = WebSocketManager()
