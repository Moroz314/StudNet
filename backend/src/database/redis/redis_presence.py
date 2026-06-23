from .base_redis import RedisInit
from enum import Enum
from datetime import datetime, UTC
from typing import Optional, Dict
import json


class UserStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    TYPING = "typing"


class RedisPresence(RedisInit):
    USER_STATUS_KEY = "user_status:{user_id}"
    CONNECTION_META_KEY = "connection_meta:{connection_id}"

    async def user_connected(self, user_id: int, connection_id: str, device_info: dict = None):
        """Пользователь подключился - обновляем статус"""
        device_info = device_info or {}

        # Сохраняем метаинформацию о подключении
        connection_data = {
            "user_id": str(user_id),
            "device_info": json.dumps(device_info),
            "connected_at": datetime.now(UTC).isoformat(),
        }

        await self.redis.hset(
            self.CONNECTION_META_KEY.format(connection_id=connection_id),
            mapping=connection_data
        )

        # Обновляем статус пользователя
        await self.redis.hset(
            self.USER_STATUS_KEY.format(user_id=user_id),
            mapping={
                "status": UserStatus.ONLINE.value,
                "last_seen": datetime.now(UTC).isoformat(),
                "last_device": device_info.get("device_type", "unknown"),
            }
        )

    async def user_disconnected(self, connection_id: str):
        """Пользователь отключился - удаляем информацию о соединении"""
        # Удаляем запись о соединении
        await self.redis.delete(
            self.CONNECTION_META_KEY.format(connection_id=connection_id)
        )

    async def set_user_offline(self, user_id: int):
        """Явно устанавливаем статус offline"""
        await self.redis.hset(
            self.USER_STATUS_KEY.format(user_id=user_id),
            mapping={
                "status": UserStatus.OFFLINE.value,
                "last_seen": datetime.now(UTC).isoformat()
            }
        )

    async def set_user_status(self, user_id: int, status: UserStatus, device_type: str = None):
        """Установить статус пользователя"""
        current_time = datetime.now(UTC).isoformat()

        if status == UserStatus.OFFLINE:
            await self.set_user_offline(user_id)
            return

        status_data = {
            "status": status.value,
            "last_seen": current_time,
        }
        if device_type:
            status_data["last_device"] = device_type

        await self.redis.hset(
            self.USER_STATUS_KEY.format(user_id=user_id),
            mapping=status_data
        )


    # ========== ГЕТТЕРЫ ==========
    async def get_user_presence_data(self, user_id: int) -> Optional[Dict]:
        """Получить полные данные о присутствии пользователя"""
        status_data = await self.redis.hgetall(
            self.USER_STATUS_KEY.format(user_id=user_id)
        )

        if not status_data:
            return None

        return {
            "user_id": user_id,
            "status": status_data["status"],
            "last_seen": status_data.get("last_seen"),
            "last_device": status_data.get("last_device"),
        }

    async def get_connection_info(self, connection_id: str) -> Optional[Dict]:
        """Получить информацию о конкретном соединении"""
        data = await self.redis.hgetall(
            self.CONNECTION_META_KEY.format(connection_id=connection_id)
        )

        if not data:
            return None

        device_info = data.get("device_info")
        if device_info:
            try:
                data["device_info"] = json.loads(device_info)
            except json.JSONDecodeError:
                data["device_info"] = {}

        return data

