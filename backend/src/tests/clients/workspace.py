from typing import Dict, Any, List, Optional
from .base import BaseAPIClient


class WorkspaceClientMixin:
    """Миксин для работы с рабочими пространствами"""

    def create_workspace(self: BaseAPIClient, project_id: str, workspace_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает рабочее пространство в проекте

        POST /projects/{project_id}/workspaces
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/projects/{project_id}/workspaces",
            json=workspace_data,
            headers=headers
        )
        assert response.status_code == 201, f"Workspace creation failed: {response.text}"
        return response.json()

    def get_project_workspaces(self: BaseAPIClient, project_id: str) -> List[Dict[str, Any]]:
        """Получает список рабочих пространств проекта

        GET /projects/{project_id}/workspaces
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces",
            headers=headers
        )
        assert response.status_code == 200, f"Get workspaces failed: {response.text}"
        return response.json()

    def get_workspace(self: BaseAPIClient, project_id: str, workspace_id: str) -> Dict[str, Any]:
        """Получает информацию о рабочем пространстве

        GET /projects/{project_id}/workspaces/{workspace_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces/{workspace_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Get workspace failed: {response.text}"
        return response.json()

    def update_workspace(self: BaseAPIClient, project_id: str, workspace_id: str, workspace_data: Dict[str, Any]) -> \
    Dict[str, Any]:
        """Обновляет рабочее пространство

        PATCH /projects/{project_id}/workspaces/{workspace_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.patch(
            f"/projects/{project_id}/workspaces/{workspace_id}",
            json=workspace_data,
            headers=headers
        )
        assert response.status_code == 200, f"Workspace update failed: {response.text}"
        return response.json()

    def delete_workspace(self: BaseAPIClient, project_id: str, workspace_id: str):
        """Удаляет рабочее пространство

        DELETE /projects/{project_id}/workspaces/{workspace_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/{project_id}/workspaces/{workspace_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Workspace deletion failed: {response.text}"
        return response.json()

    def add_workspace_participants(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            participants_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Добавляет участников в рабочее пространство

        POST /projects/{project_id}/workspaces/{workspace_id}/participants
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/projects/{project_id}/workspaces/{workspace_id}/participants",
            json=participants_data,
            headers=headers
        )
        assert response.status_code == 201, f"Add workspace participants failed: {response.text}"
        return response.json()

    def get_workspace_participants(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str
    ) -> List[Dict[str, Any]]:
        """Получает участников рабочего пространства

        GET /projects/{project_id}/workspaces/{workspace_id}/participants
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces/{workspace_id}/participants",
            headers=headers
        )
        assert response.status_code == 200, f"Get workspace participants failed: {response.text}"
        return response.json()

    def remove_workspace_participant(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            participant_user_id: int
    ) -> Dict[str, Any]:
        """Удаляет участника из рабочего пространства

        DELETE /projects/{project_id}/workspaces/{workspace_id}/participants/{participant_user_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/{project_id}/workspaces/{workspace_id}/participants/{participant_user_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Remove workspace participant failed: {response.text}"
        return response.json()