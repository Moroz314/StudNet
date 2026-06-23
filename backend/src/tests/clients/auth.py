from typing import Dict, Any, Optional
from .base import BaseAPIClient
from ..config import TEST_EMAIL, TEST_PASSWORD


class AuthClientMixin:
    """Миксин для аутентификации"""

    def login(self: BaseAPIClient, email: str = TEST_EMAIL, password: str = TEST_PASSWORD) -> str:
        """Выполняет вход и сохраняет токен"""
        login_data = {
            "email": email,
            "password": password
        }

        response = self.client.post("/user/login", json=login_data)
        assert response.status_code == 200, f"Login failed: {response.text}"

        data = response.json()
        self.access_token = data["access_token"]

        # Получаем ID пользователя
        headers = {"Authorization": f"Bearer {self.access_token}"}
        profile_response = self.client.get("/user/profile/personal", headers=headers)
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            self.user_id = profile_data["user_id"]

        return self.access_token

    def ensure_authenticated(self: BaseAPIClient):
        """Гарантирует, что клиент аутентифицирован"""
        if not self.access_token:
            self.login()

    def get_personal_user_profile(self: BaseAPIClient) -> Dict[str, Any]:
        """Получает профиль текущего пользователя"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get("/user/profile/personal", headers=headers)
        assert response.status_code == 200, f"Get profile failed: {response.text}"
        return response.json()

    def get_user_profile(self: BaseAPIClient, user_id: int) -> Dict[str, Any]:
        """Получает профиль пользователя по ID"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/user/profile", params={"user_id": user_id}, headers=headers)
        assert response.status_code == 200, f"Get user profile failed: {response.text}"
        return response.json()