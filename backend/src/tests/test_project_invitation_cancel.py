import pytest
from .fixtures import *


class TestProjectInvitationCancel:
    """Тесты для отмены приглашений"""

    def test_cancel_invitation(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project,
            sample_invitation_data
    ):
        """Тест отмены приглашения создателем"""
        project_id = created_project["id"]

        second_user_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_user_profile["user_id"]

        # Создаем приглашение
        invitation_data = sample_invitation_data.copy()
        invitation_data["user_ids"] = [second_user_id]

        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        invitation_id = invitations[0]["id"]

        # Отменяем приглашение
        response = authenticated_client.cancel_invitation(invitation_id)
        # Ответ может быть пустым или содержать статус
        assert response is not None

        # Проверяем, что приглашение больше не в списке ожидающих
        my_invitations = second_authenticated_client.get_my_invitations()
        invitation_ids = [inv["id"] for inv in my_invitations if inv.get("status") == "pending"]
        assert invitation_id not in invitation_ids