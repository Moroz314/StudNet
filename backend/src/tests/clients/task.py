from typing import Dict, Any, Optional, List
from .base import BaseAPIClient


class TaskClientMixin:
    """Миксин для работы с задачами"""

    def create_task(self: BaseAPIClient, project_id: str, workspace_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает задачу в рабочем пространстве

        POST /projects/{project_id}/workspaces/{workspace_id}/tasks/
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/",
            json=task_data,
            headers=headers
        )
        assert response.status_code == 201, f"Task creation failed: {response.text}"
        return response.json()

    def get_task(self: BaseAPIClient, project_id: str, workspace_id: str, task_id: str) -> Dict[str, Any]:
        """Получает задачу по ID

        GET /projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Get task failed: {response.text}"
        return response.json()

    def get_workspace_tasks(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            **params
    ) -> List[Dict[str, Any]]:
        """Получает список задач рабочего пространства с фильтрацией

        GET /projects/{project_id}/workspaces/{workspace_id}/tasks/
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get workspace tasks failed: {response.text}"
        return response.json()

    def update_task(self: BaseAPIClient, project_id: str, workspace_id: str, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет задачу

        PUT /projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.put(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}",
            json=task_data,
            headers=headers
        )
        assert response.status_code == 200, f"Task update failed: {response.text}"
        return response.json()

    def delete_task(self: BaseAPIClient, project_id: str, workspace_id: str, task_id: str):
        """Удаляет задачу

        DELETE /projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Task deletion failed: {response.text}"
        return response.json()

    def get_task_assignees(self: BaseAPIClient, project_id: str, workspace_id: str, task_id: str) -> List[int]:
        """Получает список назначенных на задачу пользователей

        GET /projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/assignees
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/assignees",
            headers=headers
        )
        assert response.status_code == 200, f"Get task assignees failed: {response.text}"
        return response.json()

    def add_assignees_to_task(self: BaseAPIClient, project_id: str, workspace_id: str, task_id: str, assignees: List[int]) -> Dict[str, Any]:
        """Добавляет пользователей в список назначенных на задачу

        POST /projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/assignees
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/assignees",
            json={"assignees": assignees},
            headers=headers
        )
        assert response.status_code == 200, f"Add assignees to task failed: {response.text}"
        return response.json()

    def set_task_assignees(self: BaseAPIClient, project_id: str, workspace_id: str, task_id: str, assignees: List[int]) -> Dict[str, Any]:
        """Устанавливает список назначенных пользователей (полная замена)

        PUT /projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/assignees
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.put(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/assignees",
            json={"assignees": assignees},
            headers=headers
        )
        assert response.status_code == 200, f"Set task assignees failed: {response.text}"
        return response.json()

    def remove_assignee_from_task(self: BaseAPIClient, project_id: str, workspace_id: str, task_id: str, assignee_id: int) -> Dict[str, Any]:
        """Удаляет пользователя из списка назначенных на задачу

        DELETE /projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/assignees/{assignee_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/{project_id}/workspaces/{workspace_id}/tasks/{task_id}/assignees/{assignee_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Remove assignee from task failed: {response.text}"
        return response.json()