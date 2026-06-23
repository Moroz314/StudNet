import os
from typing import Dict, Any, Optional
from .base import BaseAPIClient
from .auth import AuthClientMixin


class AvatarClientMixin(AuthClientMixin):
    """Миксин для работы с аватарками"""

    def upload_avatar(
            self: BaseAPIClient,
            avatar_path: str,
            description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Загружает аватарку пользователя
        POST /user/avatar
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        headers.pop("Content-Type", None)

        with open(avatar_path, "rb") as f:
            files = {"avatar": (os.path.basename(avatar_path), f, self._get_mime_type(avatar_path))}
            params = {}
            if description:
                params["description"] = description

            response = self.client.post(
                "/user/avatar",
                files=files,
                params=params,
                headers=headers
            )

        assert response.status_code == 200, f"Avatar upload failed: {response.text}"
        return response.json()

    def delete_avatar(self: BaseAPIClient) -> Dict[str, Any]:
        """Удаляет аватарку пользователя
        DELETE /user/avatar
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete("/user/avatar", headers=headers)
        assert response.status_code == 200, f"Avatar deletion failed: {response.text}"
        return response.json()

    def get_avatar_url(self: BaseAPIClient) -> Dict[str, Any]:
        """Получает URL аватарки пользователя
        GET /user/avatar/url
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get("/user/avatar/url", headers=headers)
        assert response.status_code == 200, f"Get avatar URL failed: {response.text}"
        return response.json()