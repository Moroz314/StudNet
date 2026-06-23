from typing import Dict, Any, Optional, List
from .base import BaseAPIClient


class CommentClientMixin:
    """Миксин для работы с комментариями к задачам"""

    def create_task_comment(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            task_id: str,
            comment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Создает комментарий к задаче

        POST /projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/comments
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/comments",
            json=comment_data,
            headers=headers
        )
        assert response.status_code == 201, f"Comment creation failed: {response.text}"
        return response.json()

    def get_task_comments(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            task_id: str,
            limit: int = 50,
            offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Получает комментарии к задаче

        GET /projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/comments
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/comments",
            params={"limit": limit, "offset": offset},
            headers=headers
        )
        assert response.status_code == 200, f"Get comments failed: {response.text}"
        return response.json()

    def update_task_comment(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            comment_id: int,
            comment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Обновляет комментарий к задаче

        PUT /projects/{project_id}/workspaces/{workspace_id}/tasks/comments/{comment_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.put(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/comments/{comment_id}",
            json=comment_data,
            headers=headers
        )
        assert response.status_code == 200, f"Comment update failed: {response.text}"
        return response.json()

    def delete_task_comment(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            comment_id: int
    ):
        """Удаляет комментарий к задаче

        DELETE /projects/{project_id}/workspaces/{workspace_id}/tasks/comments/{comment_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/comments/{comment_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Comment deletion failed: {response.text}"
        return response.json()