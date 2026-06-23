from typing import Dict, Any
from .base import BaseAPIClient
from .auth import AuthClientMixin


class ProfileClientMixin(AuthClientMixin):
    """Миксин для работы с профилем пользователя"""

    def get_personal_user_profile(self: BaseAPIClient) -> Dict[str, Any]:
        """Получает профиль текущего пользователя
        GET /user/profile/personal
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get("/user/profile/personal", headers=headers)
        assert response.status_code == 200, f"Get profile failed: {response.text}"
        return response.json()

    def get_user_profile(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Получает профиль пользователя по ID
        GET /user/profile?user_id={user_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get("/user/profile", params={"user_id": user_id}, headers=headers)
        assert response.status_code == 200, f"Get user profile failed: {response.text}"
        return response.json()

    def update_profile(self: BaseAPIClient, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет профиль текущего пользователя
        PUT /user/profile
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.put("/user/profile", json=profile_data, headers=headers)
        assert response.status_code == 200, f"Update profile failed: {response.text}"
        return response.json()

    def delete_profile(self: BaseAPIClient) -> Dict[str, Any]:
        """Удаляет профиль текущего пользователя
        DELETE /user/profile
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete("/user/profile", headers=headers)
        assert response.status_code == 200, f"Delete profile failed: {response.text}"
        return response.json()

    def create_profile(self: BaseAPIClient, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает профиль пользователя
        POST /user/profile
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post("/user/profile", json=profile_data, headers=headers)
        assert response.status_code == 201, f"Create profile failed: {response.text}"
        return response.json()