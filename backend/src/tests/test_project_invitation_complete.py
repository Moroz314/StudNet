
import pytest
from typing import Dict, Any
from .fixtures import *


class TestProjectInvitationComplete:
    """Комплексные тесты для приглашений в проекты"""

    def test_complete_invitation_flow(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project
    ):
        """Полный тест flow приглашения:
        1. Создание приглашения
        2. Проверка получения приглашения
        3. Принятие приглашения
        4. Проверка, что пользователь стал участником
        """
        project_id = created_project["id"]

        # Получаем ID второго пользователя
        second_user_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_user_profile["user_id"]
        print(f"Второй пользователь: ID {second_user_id}")

        # 1. Создаем приглашение
        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Приглашаем присоединиться к проекту!"
        }

        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        assert len(invitations) == 1
        invitation = invitations[0]
        invitation_id = invitation["id"]

        print(f"Создано приглашение ID: {invitation_id}")
        assert invitation["status"] == "pending"
        assert invitation["invited_user_id"] == second_user_id
        assert invitation["role"] == "developer"
        assert invitation["permission_level"] == "editor"

        # 2. Второй пользователь проверяет свои приглашения
        my_invitations = second_authenticated_client.get_my_invitations(status="pending")
        assert len(my_invitations) >= 1

        found_invitation = next(
            (inv for inv in my_invitations if inv["id"] == invitation_id),
            None
        )
        assert found_invitation is not None
        assert found_invitation["project_id"] == project_id
        print("Приглашение найдено в списке ожидающих")

        # 3. Принимаем приглашение
        response = second_authenticated_client.respond_to_invitation(
            invitation_id=invitation_id,
            action="accept"
        )

        assert response["id"] == invitation_id
        assert response["status"] == "accepted"
        assert "responded_at" in response
        print("Приглашение принято")

        # 4. Проверяем, что пользователь стал участником проекта
        project_participants = authenticated_client.get_project_participants(project_id)
        participant_user_ids = [p["user_id"] for p in project_participants]

        assert second_user_id in participant_user_ids
        print("Пользователь добавлен в участники проекта")

        # Находим данные участника
        participant = next(p for p in project_participants if p["user_id"] == second_user_id)
        assert participant["role"] == "developer"
        assert participant["status"] == "editor"
        assert "joined_at" in participant

        print("✓ Полный flow приглашения успешно завершен")

    def test_invitation_with_different_roles(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project
    ):
        """Тест приглашений с разными ролями и уровнями доступа"""
        project_id = created_project["id"]
        second_user_id = second_authenticated_client.get_personal_user_profile()["user_id"]

        # Тестируем разные комбинации ролей и уровней доступа
        test_cases = [
            {"role": "developer", "permission_level": "editor", "desc": "Разработчик-редактор"},
            {"role": "designer", "permission_level": "viewer", "desc": "Дизайнер-наблюдатель"},
            {"role": "project_manager", "permission_level": "admin", "desc": "PM-админ"},
            {"role": "seo", "permission_level": "viewer", "desc": "SEO-наблюдатель"},
        ]

        for case in test_cases:
            # Создаем приглашение
            invitation_data = {
                "user_ids": [second_user_id],
                "role": case["role"],
                "permission_level": case["permission_level"],
                "message": f"Тест: {case['desc']}"
            }

            invitations = authenticated_client.create_invitations(project_id, invitation_data)
            invitation = invitations[0]
            invitation_id = invitation["id"]

            # Принимаем приглашение
            second_authenticated_client.respond_to_invitation(invitation_id, "accept")

            # Проверяем, что пользователь добавлен с правильными параметрами
            participants = authenticated_client.get_project_participants(project_id)
            participant = next(p for p in participants if p["user_id"] == second_user_id)

            assert participant["role"] == case["role"]
            assert participant["status"] == case["permission_level"]
            print(f"✓ {case['desc']} - успешно")

            # Удаляем пользователя из проекта для следующего теста
            authenticated_client.remove_project_participant(project_id, second_user_id)
            authenticated_client.cancel_invitation(invitation_id)

    def test_reject_invitation(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project
    ):
        """Тест отклонения приглашения"""
        project_id = created_project["id"]
        second_user_id = second_authenticated_client.get_personal_user_profile()["user_id"]

        # Создаем приглашение
        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor"
        }

        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        invitation_id = invitations[0]["id"]

        # Отклоняем приглашение
        response = second_authenticated_client.respond_to_invitation(
            invitation_id=invitation_id,
            action="reject"
        )

        assert response["status"] == "rejected"

        # Проверяем, что пользователь НЕ стал участником
        participants = authenticated_client.get_project_participants(project_id)
        participant_user_ids = [p["user_id"] for p in participants]
        assert second_user_id not in participant_user_ids

        print("✓ Приглашение отклонено, пользователь не добавлен")

    def test_cancel_invitation(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project
    ):
        """Тест отмены приглашения создателем"""
        project_id = created_project["id"]
        second_user_id = second_authenticated_client.get_personal_user_profile()["user_id"]

        # Создаем приглашение
        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor"
        }

        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        invitation_id = invitations[0]["id"]

        # Отменяем приглашение
        authenticated_client.cancel_invitation(invitation_id)

        # Проверяем, что приглашение не висит у второго пользователя
        my_invitations = second_authenticated_client.get_my_invitations(status="pending")
        invitation_ids = [inv["id"] for inv in my_invitations]
        assert invitation_id not in invitation_ids

        print("✓ Приглашение отменено")