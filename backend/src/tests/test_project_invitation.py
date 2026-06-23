import pytest
from typing import Dict, Any
from .fixtures import *


class TestProjectInvitations:
    """Тесты для работы с приглашениями в проекты"""

    def test_create_invitation(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project,
            sample_invitation_data
    ):
        """Тест создания приглашения в проект"""
        project_id = created_project["id"]

        # Получаем ID второго пользователя
        second_user_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_user_profile["user_id"]

        # Создаем приглашение
        invitation_data = sample_invitation_data.copy()
        invitation_data["user_ids"] = [second_user_id]

        invitations = authenticated_client.create_invitations(
            project_id=project_id,
            invitation_data=invitation_data
        )

        assert isinstance(invitations, list)
        assert len(invitations) == 1

        invitation = invitations[0]
        assert invitation["project_id"] == project_id
        assert invitation["invited_user_id"] == second_user_id
        assert invitation["status"] == "pending"
        assert invitation["role"] == "developer"
        assert invitation.get("permission_level") == "editor"
        assert invitation["message"] == sample_invitation_data["message"]
        assert "invited_at" in invitation

        # Проверяем данные пригласившего
        assert invitation["invited_by"] == authenticated_client.user_id
        assert invitation["inviter"]["user_id"] == authenticated_client.user_id

        # Проверяем данные приглашенного
        assert invitation["invited_user"]["user_id"] == second_user_id
        assert invitation["invited_user"]["username"] == second_user_profile["username"]

    def test_create_invitation_unauthorized(self, client, created_project, sample_invitation_data):
        """Тест создания приглашения без авторизации"""
        project_id = created_project["id"]

        invitation_data = sample_invitation_data.copy()
        invitation_data["user_ids"] = [1]  # Какой-то ID

        with pytest.raises(AssertionError) as exc_info:
            client.create_invitations(project_id, invitation_data)

        error_msg = str(exc_info.value)
        assert "401" in error_msg or "Unauthorized" in error_msg or "login" in error_msg.lower()