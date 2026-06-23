from typing import Dict, Any, Optional, List
from .base import BaseAPIClient
from .auth import AuthClientMixin


class ProjectClientMixin(AuthClientMixin):
    """Миксин для работы с проектами"""

    def create_project(self: BaseAPIClient, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает проект"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post("/projects/", json=project_data, headers=headers)
        assert response.status_code == 201, f"Project creation failed: {response.text}"
        return response.json()

    def get_project(self: BaseAPIClient, project_id: str) -> Dict[str, Any]:
        """Получает информацию о проекте"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/projects/{project_id}", headers=headers)
        assert response.status_code == 200, f"Get project failed: {response.text}"
        return response.json()

    def get_user_projects(
            self: BaseAPIClient,
            status: Optional[str] = None,
            tags: Optional[list] = None,
            search: Optional[str] = None,
            limit: int = 20,
            offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Получает список проектов пользователя"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if tags:
            params["tags"] = tags
        if search:
            params["search"] = search

        response = self.client.get("/projects/", params=params, headers=headers)
        assert response.status_code == 200, f"Get user projects failed: {response.text}"
        return response.json()

    def update_project(self: BaseAPIClient, project_id: str, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет проект
        PATCH /projects/{project_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.patch(
            f"/projects/{project_id}",
            json=project_data,
            headers=headers
        )
        assert response.status_code == 200, f"Project update failed: {response.text}"
        return response.json()

    def archive_project(self: BaseAPIClient, project_id: str) -> Dict[str, Any]:
        """Архивирует проект"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(f"/projects/{project_id}/archive", headers=headers)
        assert response.status_code == 200, f"Project archive failed: {response.text}"
        return response.json()

    def restore_project(self: BaseAPIClient, project_id: str) -> Dict[str, Any]:
        """Восстанавливает проект из архива"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(f"/projects/{project_id}/restore", headers=headers)
        assert response.status_code == 200, f"Project restore failed: {response.text}"
        return response.json()

    def delete_project(self: BaseAPIClient, project_id: str) -> Dict[str, Any]:
        """Удаляет проект"""
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/{project_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Project deletion failed: {response.text}"
        return response.json()

    # ========== Методы для работы с приглашениями ==========

    def create_invitations(
            self: BaseAPIClient,
            project_id: str,
            invitation_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Создает приглашения в проект для нескольких пользователей

        Args:
            project_id: ID проекта
            invitation_data: Данные приглашения:
                - user_ids: list[int] - IDs пользователей (обязательно)
                - role: ProjectRole - роль в проекте (seo, developer, designer, etc.)
                - permission_level: ParticipantStatus - уровень доступа (viewer, editor, admin)
                - message: str - сообщение (опционально)
                - expires_in_days: int - срок действия (опционально)

        Returns:
            Список созданных приглашений
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/projects/{project_id}/invitations",
            json=invitation_data,
            headers=headers
        )
        assert response.status_code == 201, f"Create invitations failed: {response.text}"
        return response.json()

    def get_project_invitations(
            self: BaseAPIClient,
            project_id: str,
            status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Получает все приглашения для конкретного проекта (для админов)

        Args:
            project_id: ID проекта
            status: Фильтр по статусу (pending, accepted, rejected)

        Returns:
            Список приглашений
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {}
        if status:
            params["status"] = status

        response = self.client.get(
            f"/projects/{project_id}/invitations",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get project invitations failed: {response.text}"
        return response.json()

    def get_my_invitations(
            self: BaseAPIClient,
            status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Получает все свои приглашения в проекты

        Args:
            status: Фильтр по статусу (pending, accepted, rejected)

        Returns:
            Список приглашений
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {}
        if status:
            params["status"] = status

        response = self.client.get(
            "/projects/invitations/personal",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get my invitations failed: {response.text}"
        return response.json()

    def respond_to_invitation(
            self: BaseAPIClient,
            invitation_id: int,
            action: str
    ) -> Dict[str, Any]:
        """Принимает или отклоняет приглашение

        Args:
            invitation_id: ID приглашения
            action: Действие ("accept" или "reject")

        Returns:
            Обновленные данные приглашения
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/projects/invitations/{invitation_id}/respond",
            json={"action": action},
            headers=headers
        )
        assert response.status_code == 200, f"Respond to invitation failed: {response.text}"
        return response.json()

    def cancel_invitation(
            self: BaseAPIClient,
            invitation_id: int
    ) -> Dict[str, Any]:
        """Отменяет приглашение (только для создателя приглашения или админа проекта)

        Args:
            invitation_id: ID приглашения

        Returns:
            Пустой ответ или статус операции
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/invitations/{invitation_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Cancel invitation failed: {response.text}"
        return response.json() if response.content else {"status": "success"}

    # ========== Методы для работы с участниками проекта ==========

    def get_project_participants(
            self: BaseAPIClient,
            project_id: str
    ) -> List[Dict[str, Any]]:
        """Получает участников проекта

        Args:
            project_id: ID проекта

        Returns:
            Список участников
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/participants",
            headers=headers
        )
        assert response.status_code == 200, f"Get project participants failed: {response.text}"
        return response.json()

    def remove_project_participant(
            self: BaseAPIClient,
            project_id: str,
            participant_user_id: int
    ) -> Dict[str, Any]:

        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/{project_id}/participants",
            headers=headers,
            params={'participant_user_ids': [participant_user_id]}
        )
        assert response.status_code == 200, f"Remove project participant failed: {response.text}"
        return response.json() if response.content else {"status": "success"}

    def update_participant(
            self: BaseAPIClient,
            project_id: str,
            participant_user_id: int,
            participant_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Обновляет статус или роль участника проекта

        Args:
            project_id: ID проекта
            participant_user_id: ID участника
            participant_data: Данные для обновления (status, role)

        Returns:
            Обновленные данные участника
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.patch(
            f"/projects/{project_id}/participants/{participant_user_id}",
            json=participant_data,
            headers=headers
        )
        assert response.status_code == 200, f"Update participant failed: {response.text}"
        return response.json()

    def leave_project(
            self: BaseAPIClient,
            project_id: str
    ) -> Dict[str, Any]:
        """Покидает проект

        Args:
            project_id: ID проекта

        Returns:
            Пустой ответ или статус операции
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/{project_id}/leave",
            headers=headers
        )
        assert response.status_code == 200, f"Leave project failed: {response.text}"
        return response.json() if response.content else {"status": "success"}

    # ========== Методы для работы с workspace ==========

    def create_workspace(
            self: BaseAPIClient,
            project_id: str,
            workspace_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Создает рабочее пространство в проекте

        Args:
            project_id: ID проекта
            workspace_data: Данные рабочего пространства:
                - name: str - название
                - description: str - описание (опционально)
                - links: list[str] - ссылки (опционально)
                - github_links: list[str] - GitHub ссылки (опционально)
                - create_chat: bool - создать чат (по умолчанию true)

        Returns:
            Созданное рабочее пространство
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(
            f"/projects/{project_id}/workspaces",
            json=workspace_data,
            headers=headers
        )
        assert response.status_code == 201, f"Create workspace failed: {response.text}"
        return response.json()

    def get_project_workspaces(
            self: BaseAPIClient,
            project_id: str
    ) -> List[Dict[str, Any]]:
        """Получает все рабочие пространства проекта

        Args:
            project_id: ID проекта

        Returns:
            Список рабочих пространств
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces",
            headers=headers
        )
        assert response.status_code == 200, f"Get project workspaces failed: {response.text}"
        return response.json()

    def get_workspace(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str
    ) -> Dict[str, Any]:
        """Получает информацию о рабочем пространстве

        Args:
            project_id: ID проекта
            workspace_id: ID рабочего пространства

        Returns:
            Данные рабочего пространства
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces/{workspace_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Get workspace failed: {response.text}"
        return response.json()

    def update_workspace(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            workspace_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Обновляет рабочее пространство

        Args:
            project_id: ID проекта
            workspace_id: ID рабочего пространства
            workspace_data: Данные для обновления

        Returns:
            Обновленные данные рабочего пространства
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.patch(
            f"/projects/{project_id}/workspaces/{workspace_id}",
            json=workspace_data,
            headers=headers
        )
        assert response.status_code == 200, f"Update workspace failed: {response.text}"
        return response.json()

    def delete_workspace(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str
    ) -> Dict[str, Any]:
        """Удаляет рабочее пространство

        Args:
            project_id: ID проекта
            workspace_id: ID рабочего пространства

        Returns:
            Пустой ответ или статус операции
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(
            f"/projects/{project_id}/workspaces/{workspace_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Delete workspace failed: {response.text}"
        return response.json() if response.content else {"status": "success"}

    # ========== Методы для работы с участниками workspace ==========

    def add_workspace_participants(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            participants_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Добавляет участников в рабочее пространство

        Args:
            project_id: ID проекта
            workspace_id: ID рабочего пространства
            participants_data: Данные участников:
                - user_ids: list[int] - IDs пользователей
                - role: ProjectRole - роль в проекте
                - status: ParticipantStatus - статус/уровень доступа

        Returns:
            Список добавленных участников
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

        Args:
            project_id: ID проекта
            workspace_id: ID рабочего пространства

        Returns:
            Список участников
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/projects/{project_id}/workspaces/{workspace_id}/participants",
            headers=headers
        )
        assert response.status_code == 200, f"Get workspace participants failed: {response.text}"
        return response.json()

    def remove_workspace_participants(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            participant_user_ids: List[int]
    ) -> Dict[str, Any]:
        """Удаляет участников из рабочего пространства

        Args:
            project_id: ID проекта
            workspace_id: ID рабочего пространства
            participant_user_ids: IDs пользователей для удаления

        Returns:
            Пустой ответ или статус операции
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"participant_user_ids": participant_user_ids}
        response = self.client.delete(
            f"/projects/{project_id}/workspaces/{workspace_id}/participants",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Remove workspace participants failed: {response.text}"
        return response.json() if response.content else {"status": "success"}