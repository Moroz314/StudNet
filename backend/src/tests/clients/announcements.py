from typing import Dict, Any, List, Optional
from .base import BaseAPIClient
from .auth import AuthClientMixin


class AnnouncementClientMixin(AuthClientMixin):
    """Миксин для работы с объявлениями и заявками"""

    # ========== Announcement endpoints ==========

    def create_announcement(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            title: str,
            content: str,
            questions: Optional[List[str]] = None,
            file_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Создать объявление
        POST /projects/{project_id}/workspaces/{workspace_id}/announcements
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {
            "title": title,
            "content": content,
            "questions": questions or []
        }
        if file_ids:
            data["file_ids"] = file_ids

        response = self.client.post(
            f"/projects/{project_id}/workspaces/{workspace_id}/announcements",
            json=data,
            headers=headers
        )
        assert response.status_code == 201, f"Create announcement failed: {response.text}"
        return response.json()

    def get_workspace_announcements(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            skip: int = 0,
            limit: int = 100,
            status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получить объявления рабочего пространства
        GET /projects/{project_id}/workspaces/{workspace_id}/announcements
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"skip": skip, "limit": limit}
        if status:
            params["status"] = status

        response = self.client.get(
            f"/projects/{project_id}/workspaces/{workspace_id}/announcements",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get workspace announcements failed: {response.text}"
        return response.json()

    def get_announcement(
            self: BaseAPIClient,
            announcement_id: str
    ) -> Dict[str, Any]:
        """Получить объявление по ID
        GET /announcements/{announcement_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"projects/announcements/{announcement_id}", headers=headers)
        assert response.status_code == 200, f"Get announcement failed: {response.text}"
        return response.json()

    def update_announcement(
            self: BaseAPIClient,
            announcement_id: str,
            title: Optional[str] = None,
            content: Optional[str] = None,
            questions: Optional[List[str]] = None,
            file_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Обновить объявление
        PATCH /announcements/{announcement_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {}
        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        if questions is not None:
            data["questions"] = questions
        if file_ids is not None:
            data["file_ids"] = file_ids

        response = self.client.patch(
            f"projects/announcements/{announcement_id}",
            json=data,
            headers=headers
        )
        assert response.status_code == 200, f"Update announcement failed: {response.text}"
        return response.json()

    def delete_announcement(
            self: BaseAPIClient,
            announcement_id: str
    ) -> Dict[str, Any]:
        """Удалить объявление
        DELETE /announcements/{announcement_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(f"projects/announcements/{announcement_id}", headers=headers)
        assert response.status_code == 200, f"Delete announcement failed: {response.text}"
        return response.json()

    # ========== Application endpoints ==========

    def create_application(
            self: BaseAPIClient,
            announcement_id: str,
            content: str,
            links: Optional[List[str]] = None,
            file_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Подать заявку на объявление
        POST /announcements/{announcement_id}/applications
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {"content": content, "links": links or []}
        if file_ids:
            data["file_ids"] = file_ids

        response = self.client.post(
            f"projects/announcements/{announcement_id}/applications",
            json=data,
            headers=headers
        )
        assert response.status_code == 201, f"Create application failed: {response.text}"
        return response.json()

    def get_announcement_applications(
            self: BaseAPIClient,
            announcement_id: str,
            skip: int = 0,
            limit: int = 100,
            status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получить заявки объявления
        GET /announcements/{announcement_id}/applications
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"skip": skip, "limit": limit}
        if status:
            params["status"] = status

        response = self.client.get(
            f"projects/announcements/{announcement_id}/applications",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get announcement applications failed: {response.text}"
        return response.json()

    def get_my_applications(
            self: BaseAPIClient,
            skip: int = 0,
            limit: int = 100
    ) -> Dict[str, Any]:
        """Получить мои заявки
        GET /applications/my
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"skip": skip, "limit": limit}
        response = self.client.get("/applications/my", params=params, headers=headers)
        assert response.status_code == 200, f"Get my applications failed: {response.text}"
        return response.json()

    def get_application(
            self: BaseAPIClient,
            application_id: str
    ) -> Dict[str, Any]:
        """Получить заявку по ID
        GET /applications/{application_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/applications/{application_id}", headers=headers)
        assert response.status_code == 200, f"Get application failed: {response.text}"
        return response.json()

    def update_application(
            self: BaseAPIClient,
            application_id: str,
            content: Optional[str] = None,
            links: Optional[List[str]] = None,
            file_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Обновить заявку (только владелец)
        PATCH /applications/{application_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {}
        if content is not None:
            data["content"] = content
        if links is not None:
            data["links"] = links
        if file_ids is not None:
            data["file_ids"] = file_ids

        response = self.client.patch(
            f"/applications/{application_id}",
            json=data,
            headers=headers
        )
        assert response.status_code == 200, f"Update application failed: {response.text}"
        return response.json()

    def delete_application(
            self: BaseAPIClient,
            application_id: str
    ) -> Dict[str, Any]:
        """Удалить заявку (только владелец)
        DELETE /applications/{application_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(f"/applications/{application_id}", headers=headers)
        assert response.status_code == 200, f"Delete application failed: {response.text}"
        return response.json()

    def update_application_status(
            self: BaseAPIClient,
            application_id: str,
            status: str
    ) -> Dict[str, Any]:
        """Обновить статус заявки (только админы)
        PATCH /applications/{application_id}/status
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"status": status}
        response = self.client.patch(
            f"/applications/{application_id}/status",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Update application status failed: {response.text}"
        return response.json()

    def vote_application(
            self: BaseAPIClient,
            application_id: str,
            vote_type: str
    ) -> Dict[str, Any]:
        """Голосовать за заявку (like/dislike/remove)
        POST /applications/{application_id}/vote
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {"vote_type": vote_type}
        response = self.client.post(
            f"/applications/{application_id}/vote",
            json=data,
            headers=headers
        )
        assert response.status_code == 200, f"Vote application failed: {response.text}"
        return response.json()