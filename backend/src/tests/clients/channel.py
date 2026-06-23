from typing import Dict, Any, List, Optional
from .base import BaseAPIClient


class ChannelClientMixin:
    """Миксин для работы с каналами"""

    def create_channel(self, channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать канал для проекта"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post("/channels", json=channel_data, headers=headers)
        assert response.status_code == 201, f"Create channel failed: {response.text}"
        return response.json()

    def get_channel(self, channel_id: str) -> Dict[str, Any]:
        """Получить информацию о канале"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/channels/{channel_id}", headers=headers)
        assert response.status_code == 200, f"Get channel failed: {response.text}"
        return response.json()

    def update_channel(self, channel_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить канал"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.put(
            f"/channels/{channel_id}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200, f"Update channel failed: {response.text}"
        return response.json()

    def delete_channel(self, channel_id: str):
        """Удалить канал"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(f"/channels/{channel_id}", headers=headers)
        assert response.status_code == 204, f"Delete channel failed: {response.text}"

    def subscribe_to_channel(self, channel_id: str) -> Dict[str, Any]:
        """Подписаться на канал"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/channels/{channel_id}/subscribe",
            headers=headers
        )
        assert response.status_code == 200, f"Subscribe failed: {response.text}"
        return response.json()

    def unsubscribe_from_channel(self, channel_id: str):
        """Отписаться от канала"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/channels/{channel_id}/unsubscribe",
            headers=headers
        )
        assert response.status_code == 204, f"Unsubscribe failed: {response.text}"

    def get_my_channels(self) -> List[Dict[str, Any]]:
        """Получить каналы, на которые подписан пользователь"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get("/channels/my", headers=headers)
        assert response.status_code == 200, f"Get my channels failed: {response.text}"
        return response.json()

    def get_project_channel(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Получить канал проекта"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/channels/project/{project_id}", headers=headers)
        assert response.status_code == 200, f"Get project channel failed: {response.text}"
        return response.json()

    def get_channel_messages(
            self,
            channel_id: str,
            limit: int = 50,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Получить сообщения канала"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit, "offset": offset}
        response = self.client.get(
            f"/channels/{channel_id}/messages",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get channel messages failed: {response.text}"
        return response.json()

    def send_text_message_to_channel(self, channel_id: str, content: str) -> Dict[str, Any]:
        """Отправить текстовое сообщение в канал"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"content": content}
        response = self.client.post(
            f"/channels/{channel_id}/messages/text",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Send text message failed: {response.text}"
        return response.json()

    def send_media_message_to_channel(
            self,
            channel_id: str,
            file_paths: List[str],
            caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Отправить медиа-сообщение в канал"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()

        params = {}
        if caption:
            params["caption"] = caption

        files = []
        for file_path in file_paths:
            files.append(('files', open(file_path, 'rb')))

        response = self.client.post(
            f"/channels/{channel_id}/messages/media",
            params=params,
            files=files,
            headers=headers
        )

        for _, file_obj in files:
            file_obj.close()

        assert response.status_code == 200, f"Send media message failed: {response.text}"
        return response.json()

    def like_channel_message(self, channel_id: str, message_id: int):
        """Поставить лайк сообщению в канале"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/channels/{channel_id}/messages/{message_id}/like",
            headers=headers
        )
        assert response.status_code == 200, f"Like channel message failed: {response.text}"

    def unlike_channel_message(self, channel_id: str, message_id: int):
        """Убрать лайк с сообщения в канале"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/channels/{channel_id}/messages/{message_id}/unlike",
            headers=headers
        )
        assert response.status_code == 200, f"Unlike channel message failed: {response.text}"