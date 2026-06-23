from typing import Dict, Any, List, Optional
from .base import BaseAPIClient
import uuid


class ChatClientMixin:
    """Миксин для работы с чатами"""

    def get_user_chats(self) -> List[Dict[str, Any]]:
        """Получить все чаты пользователя"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get("/chats", headers=headers)
        assert response.status_code == 200, f"Get user chats failed: {response.text}"
        return response.json()

    def create_chat(self, chat_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать новый чат"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post("/chat", json=chat_data, headers=headers)
        assert response.status_code == 201, f"Create chat failed: {response.text}"
        return response.json()

    def get_chat(self, chat_id: str) -> Dict[str, Any]:
        """Получить информацию о чате"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/chats/{chat_id}", headers=headers)
        assert response.status_code == 200, f"Get chat failed: {response.text}"
        return response.json()

    def send_text_message(self, chat_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Отправить текстовое сообщение"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/chats/{chat_id}/messages/text",
            json=message_data,
            headers=headers
        )
        assert response.status_code == 200, f"Send text message failed: {response.text}"
        return response.json()

    def send_media_message(
            self,
            chat_id: str,
            file_paths: List[str],
            caption: Optional[str] = None,
            reply_to_message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Отправить медиа-сообщение"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()

        params = {}
        if caption:
            params["caption"] = caption
        if reply_to_message_id:
            params["reply_to_message_id"] = reply_to_message_id

        files = []
        for file_path in file_paths:
            files.append(('files', open(file_path, 'rb')))

        response = self.client.post(
            f"/chats/{chat_id}/messages/media",
            params=params,
            files=files,
            headers=headers
        )

        for _, file_obj in files:
            file_obj.close()

        assert response.status_code == 200, f"Send media message failed: {response.text}"
        return response.json()

    def get_chat_messages(
            self,
            chat_id: str,
            limit: int = 50,
            offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Получить сообщения чата"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit, "offset": offset}
        response = self.client.get(
            f"/chats/{chat_id}/messages",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get messages failed: {response.text}"
        return response.json()

    def forward_messages(
            self,
            chat_id: str,
            message_ids: List[int],
            target_chat_ids: List[str],
            include_original_info: bool = True
    ) -> Dict[str, Any]:
        """Переслать сообщения"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {
            "message_ids": message_ids,
            "target_chat_ids": target_chat_ids,
            "include_original_info": include_original_info
        }
        response = self.client.post(
            f"/chats/{chat_id}/messages/forward",
            json=data,
            headers=headers
        )
        assert response.status_code == 200, f"Forward messages failed: {response.text}"
        return response.json()

    def edit_message(
            self,
            chat_id: str,
            message_id: int,
            content: str
    ) -> Dict[str, Any]:
        """Редактировать сообщение"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {"content": content}
        response = self.client.put(
            f"/chats/{chat_id}/messages/{message_id}",
            json=data,
            headers=headers
        )
        assert response.status_code == 200, f"Edit message failed: {response.text}"
        return response.json()

    def delete_message(self, chat_id: str, message_id: int):
        """Удалить сообщение"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/chats/{chat_id}/messages/{message_id}",
            headers=headers
        )
        assert response.status_code == 204, f"Delete message failed: {response.text}"

    def get_message_replies(
            self,
            chat_id: str,
            message_id: int,
            limit: int = 50,
            offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Получить ответы на сообщение"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit, "offset": offset}
        response = self.client.get(
            f"/chats/{chat_id}/messages/{message_id}/replies",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get replies failed: {response.text}"
        return response.json()

    def search_messages(
            self,
            chat_id: str,
            query: str,
            limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Поиск сообщений"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"query": query, "limit": limit}
        response = self.client.get(
            f"/chats/{chat_id}/messages/search",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Search messages failed: {response.text}"
        return response.json()

    def get_chat_participants(self, chat_id: str) -> Dict[str, Any]:
        """Получить участников чата"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/chats/{chat_id}/participants", headers=headers)
        assert response.status_code == 200, f"Get participants failed: {response.text}"
        return response.json()

    def add_users_to_chat(self, chat_id: str, user_ids: List[int]):
        """Добавить пользователей в чат"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"user_ids": user_ids}
        response = self.client.post(
            f"/chats/{chat_id}/users",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Add users failed: {response.text}"

    def mark_chat_as_read(
            self,
            chat_id: str,
            message_ids: Optional[List[int]] = None,
            mark_all: bool = False
    ):
        """Отметить сообщения как прочитанные"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"mark_all": mark_all}
        if message_ids:
            params["message_ids"] = message_ids
        response = self.client.post(
            f"/chats/{chat_id}/read",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Mark as read failed: {response.text}"

    def mark_message_as_read(self, message_id: int):
        """Отметить сообщение как прочитанное"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/messages/{message_id}/read",
            headers=headers
        )
        assert response.status_code == 200, f"Mark message as read failed: {response.text}"

    def like_message(self, chat_id: str, message_id: int):
        """Поставить лайк сообщению"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/chats/{chat_id}/messages/{message_id}/like",
            headers=headers
        )
        assert response.status_code == 200, f"Like message failed: {response.text}"

    def unlike_message(self, chat_id: str, message_id: int):
        """Убрать лайк с сообщения"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/chats/{chat_id}/messages/{message_id}/unlike",
            headers=headers
        )
        assert response.status_code == 200, f"Unlike message failed: {response.text}"