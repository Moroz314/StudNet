from typing import Dict, List, Optional
from fastapi import WebSocket
import uuid


class ConnectionManager:
    def __init__(self):
        self.user_connections: Dict[int, Dict[str, WebSocket]] = {}
        self.connection_user_map: Dict[str, int] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()

        connection_id = str(uuid.uuid4())

        if user_id not in self.user_connections:
            self.user_connections[user_id] = {}

        self.user_connections[user_id][connection_id] = websocket
        self.connection_user_map[connection_id] = user_id

        print(f"Пользователь {user_id} подключился! Connection ID: {connection_id}")
        return connection_id

    async def disconnect(self, user_id: int, connection_id: str):
        user_connections = self.user_connections.get(user_id)

        if not user_connections:
            return False

        # Удаляем соединение
        if connection_id in user_connections:
            try:
                await user_connections[connection_id].close()
            except Exception as e:
                print(f"Error closing connection: {e}")

            del user_connections[connection_id]

        # Удаляем из connection_user_map
        if connection_id in self.connection_user_map:
            del self.connection_user_map[connection_id]

        # Если у пользователя больше нет соединений, удаляем запись
        if not user_connections:
            del self.user_connections[user_id]

        print(f"Соединение {connection_id} разорвано!")
        return True

    def get_user_connections(self, user_id: int) -> List[WebSocket]:
        user_connections = self.user_connections.get(user_id, {})
        return list(user_connections.values())

    async def send_to_user(self, user_id: int, message: dict):
        """Отправить сообщение конкретному пользователю"""
        connections = self.get_user_connections(user_id)
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")

    async def send_to_chat(self, chat_user_ids: list, message: dict, exclude_user_id: Optional[int] = None):
        """Отправить сообщение всем участникам чата"""
        for user_id in chat_user_ids:
            if user_id == exclude_user_id:
                continue
            await self.send_to_user(user_id, message)


connection_manager = ConnectionManager()