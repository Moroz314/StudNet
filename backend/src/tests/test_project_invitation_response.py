import pytest
from .fixtures import *


class TestProjectInvitationResponses:
    """Тесты для ответов на приглашения в проекты"""

    def test_accept_invitation(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project,
            sample_invitation_data
    ):
        """Тест принятия приглашения"""
        project_id = created_project["id"]

        # Получаем ID второго пользователя
        second_user_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_user_profile["user_id"]

        # Создаем приглашение
        invitation_data = sample_invitation_data.copy()
        invitation_data["user_ids"] = [second_user_id]

        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        invitation_id = invitations[0]["id"]

        # Второй пользователь принимает приглашение
        response = second_authenticated_client.respond_to_invitation(
            invitation_id=invitation_id,
            action="accept"
        )

        assert response["id"] == invitation_id
        assert response["status"] == "accepted"
        assert "responded_at" in response

        # Проверяем, что пользователь стал участником проекта
        project_participants = authenticated_client.get_project_participants(project_id)
        participant_user_ids = [p["user_id"] for p in project_participants]
        assert second_user_id in participant_user_ids