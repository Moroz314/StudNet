from typing import Dict, Any, List, Optional
from .base import BaseAPIClient
from .auth import AuthClientMixin


class RelationshipsClientMixin(AuthClientMixin):
    """Миксин для работы с отношениями между пользователями"""

    def send_friend_request(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Отправляет заявку в друзья"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            "/relationships/requests",
            json={"user_id": user_id},
            headers=headers
        )
        assert response.status_code == 200, f"Send friend request failed: {response.text}"
        return response.json()

    def get_pending_requests(
            self: BaseAPIClient,
            limit: int = 100,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Получает входящие и исходящие заявки"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            "/relationships/requests",
            params={"limit": limit, "offset": offset},
            headers=headers
        )
        assert response.status_code == 200, f"Get pending requests failed: {response.text}"
        return response.json()

    def accept_friend_request(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Принимает заявку в друзья"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/relationships/requests/{user_id}/accept",
            headers=headers
        )
        assert response.status_code == 200, f"Accept friend request failed: {response.text}"
        return response.json()

    def reject_friend_request(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Отклоняет заявку в друзья"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/relationships/requests/{user_id}/reject",
            headers=headers
        )
        assert response.status_code == 200, f"Reject friend request failed: {response.text}"
        return response.json()

    def cancel_friend_request(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Отменяет отправленную заявку в друзья"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/relationships/requests/{user_id}/cancel",
            headers=headers
        )
        assert response.status_code == 200, f"Cancel friend request failed: {response.text}"
        return response.json()

    def get_friends(
            self: BaseAPIClient,
            limit: int = 100,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Получает список друзей"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            "/relationships/friends",
            params={"limit": limit, "offset": offset},
            headers=headers
        )
        assert response.status_code == 200, f"Get friends failed: {response.text}"
        return response.json()

    def remove_friend(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Удаляет пользователя из друзей"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/relationships/friends/{user_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Remove friend failed: {response.text}"
        return response.json()

    def block_user(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Блокирует пользователя"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            "/relationships/block",
            json={"user_id": user_id},
            headers=headers
        )
        assert response.status_code == 200, f"Block user failed: {response.text}"
        return response.json()

    def unblock_user(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Разблокирует пользователя"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/relationships/unblock/{user_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Unblock user failed: {response.text}"
        return response.json()

    def get_blocked_users(
            self: BaseAPIClient,
            limit: int = 100,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Получает список заблокированных пользователей"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            "/relationships/blocked",
            params={"limit": limit, "offset": offset},
            headers=headers
        )
        assert response.status_code == 200, f"Get blocked users failed: {response.text}"
        return response.json()

    def get_relationship_status(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Получает статус отношений с пользователем"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/relationships/status/{user_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Get relationship status failed: {response.text}"
        return response.json()

    def get_mutual_friends(
            self: BaseAPIClient,
            user_id: int,
            limit: int = 100,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Получает общих друзей с пользователем
        GET /relationships/friends/mutual/{user_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/relationships/friends/mutual/{user_id}",
            params={"limit": limit, "offset": offset},
            headers=headers
        )
        assert response.status_code == 200, f"Get mutual friends failed: {response.text}"
        return response.json()

    def cleanup_relationships(self: BaseAPIClient, user_ids: List[int]):
        """Очищает все отношения с указанными пользователями"""
        for user_id in user_ids:
            try:
                # Пытаемся получить статус
                status_data = self.get_relationship_status(user_id)
                status = status_data.get("status")

                if status == "friend":
                    self.remove_friend(user_id)
                elif status == "pending":
                    # Проверяем, кто отправитель
                    requests = self.get_pending_requests()
                    # Если это исходящая заявка - отменяем
                    if any(req["user_id"] == user_id for req in requests["outgoing"]):
                        self.cancel_friend_request(user_id)
                elif status == "blocked":
                    self.unblock_user(user_id)
            except Exception:
                # Игнорируем ошибки при очистке
                pass