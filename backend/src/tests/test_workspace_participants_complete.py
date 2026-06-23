# tests/test_workspace_participants_complete.py

import pytest
from typing import Dict, Any, List
from .fixtures import *


class TestWorkspaceParticipantsComplete:
    """Комплексные тесты для управления участниками рабочего пространства"""

    def test_add_participant_to_workspace(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project,
            created_workspace
    ):
        """Тест добавления участника в рабочее пространство"""
        project_id = created_project["id"]
        workspace_id = created_workspace["id"]

        second_user_id = second_authenticated_client.get_personal_user_profile()["user_id"]
        second_user_profile = second_authenticated_client.get_personal_user_profile()

        # 1. СНАЧАЛА создаем приглашение в проект
        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Приглашение для добавления в workspace"
        }

        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        invitation_id = invitations[0]["id"]
        print(f"✓ Создано приглашение в проект ID: {invitation_id}")

        # 2. Принимаем приглашение (пользователь становится участником проекта)
        second_authenticated_client.respond_to_invitation(invitation_id, "accept")
        print(f"✓ Пользователь {second_user_id} принял приглашение и добавлен в проект")

        # 3. ТЕПЕРЬ добавляем пользователя в workspace
        workspace_participants_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "status": "editor"
        }

        participants = authenticated_client.add_workspace_participants(
            project_id=project_id,
            workspace_id=workspace_id,
            participants_data=workspace_participants_data
        )

        assert len(participants) == 1
        participant = participants[0]

        assert participant["user_id"] == second_user_id
        assert participant["username"] == second_user_profile["username"]
        assert participant["name"] == second_user_profile["name"]
        assert participant["lastname"] == second_user_profile["lastname"]
        assert participant["role"] == "developer"
        assert participant["status"] == "editor"
        assert participant["workspace_id"] == workspace_id
        assert participant["project_id"] == project_id
        assert "joined_at" in participant

        print(f"✓ Участник {second_user_id} добавлен в workspace")

        # Проверяем, что участник отображается в списке
        workspace_participants = authenticated_client.get_workspace_participants(
            project_id, workspace_id
        )
        assert len(workspace_participants) >= 1
        assert any(p["user_id"] == second_user_id for p in workspace_participants)

    def test_add_multiple_participants(
            self,
            authenticated_client,
            second_authenticated_client,
            third_authenticated_client,
            created_project,
            created_workspace
    ):
        """Тест добавления нескольких участников в workspace"""
        project_id = created_project["id"]
        workspace_id = created_workspace["id"]

        # Получаем ID всех пользователей
        main_user_id = authenticated_client.user_id
        second_user_id = second_authenticated_client.get_personal_user_profile()["user_id"]
        third_user_id = third_authenticated_client.get_personal_user_profile()["user_id"]

        all_user_ids = [second_user_id, third_user_id]

        # 1. СНАЧАЛА создаем приглашения для всех пользователей в проект
        for user_id in all_user_ids:
            invitation_data = {
                "user_ids": [user_id],
                "role": "developer",
                "permission_level": "editor",
                "message": "Приглашение в проект"
            }

            invitations = authenticated_client.create_invitations(project_id, invitation_data)
            invitation_id = invitations[0]["id"]

            # Принимаем приглашение соответствующим пользователем
            if user_id == second_user_id:
                second_authenticated_client.respond_to_invitation(invitation_id, "accept")
            else:
                third_authenticated_client.respond_to_invitation(invitation_id, "accept")

        print(f"✓ Пользователи {all_user_ids} добавлены в проект через приглашения")

        # 2. ТЕПЕРЬ добавляем пользователей в workspace
        workspace_participants_data = {
            "user_ids": all_user_ids,
            "role": "developer",
            "status": "editor"
        }

        participants = authenticated_client.add_workspace_participants(
            project_id=project_id,
            workspace_id=workspace_id,
            participants_data=workspace_participants_data
        )

        assert len(participants) == 2

        user_ids = [p["user_id"] for p in participants]
        assert second_user_id in user_ids
        assert third_user_id in user_ids

        # Проверяем, что у каждого участника есть основные поля
        for participant in participants:
            assert "username" in participant
            assert "name" in participant
            assert "lastname" in participant
            assert participant["workspace_id"] == workspace_id
            assert participant["project_id"] == project_id

        print(f"✓ Добавлено {len(participants)} участников в workspace")

    def test_get_workspace_participants_with_details(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project,
            created_workspace
    ):
        """Тест получения участников workspace с детальной информацией"""
        project_id = created_project["id"]
        workspace_id = created_workspace["id"]

        second_user_id = second_authenticated_client.get_personal_user_profile()["user_id"]
        second_user_profile = second_authenticated_client.get_personal_user_profile()

        # 1. СНАЧАЛА создаем приглашение в проект
        invitation_data = {
            "user_ids": [second_user_id],
            "role": "designer",
            "permission_level": "viewer",
            "message": "Приглашение дизайнера"
        }

        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        invitation_id = invitations[0]["id"]

        # 2. Принимаем приглашение
        second_authenticated_client.respond_to_invitation(invitation_id, "accept")

        # 3. ТЕПЕРЬ добавляем пользователя в workspace
        authenticated_client.add_workspace_participants(
            project_id=project_id,
            workspace_id=workspace_id,
            participants_data={
                "user_ids": [second_user_id],
                "role": "designer",
                "status": "viewer"
            }
        )

        # Получаем список участников
        participants = authenticated_client.get_workspace_participants(project_id, workspace_id)

        # Находим нашего пользователя
        participant = next(p for p in participants if p["user_id"] == second_user_id)

        # Проверяем детальную информацию (поля из схемы ParticipantResponse)
        assert participant["username"] == second_user_profile["username"]
        assert participant["name"] == second_user_profile["name"]
        assert participant["lastname"] == second_user_profile["lastname"]

        assert participant["workspace_id"] == workspace_id
        assert participant["project_id"] == project_id
        assert participant["role"] == "designer"
        assert participant["status"] == "viewer"
        assert "joined_at" in participant

        print("✓ Получена детальная информация об участниках")

    def test_remove_participant_from_workspace(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project,
            created_workspace
    ):
        """Тест удаления участника из workspace"""
        project_id = created_project["id"]
        workspace_id = created_workspace["id"]

        second_user_id = second_authenticated_client.get_personal_user_profile()["user_id"]

        # 1. СНАЧАЛА создаем приглашение в проект
        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Приглашение для теста удаления"
        }

        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        invitation_id = invitations[0]["id"]

        # 2. Принимаем приглашение
        second_authenticated_client.respond_to_invitation(invitation_id, "accept")

        # 3. ТЕПЕРЬ добавляем пользователя в workspace
        authenticated_client.add_workspace_participants(
            project_id=project_id,
            workspace_id=workspace_id,
            participants_data={
                "user_ids": [second_user_id],
                "role": "developer",
                "status": "editor"
            }
        )

        # Проверяем, что пользователь добавлен в workspace
        participants_before = authenticated_client.get_workspace_participants(project_id, workspace_id)
        assert any(p["user_id"] == second_user_id for p in participants_before)

        # Удаляем пользователя из workspace
        authenticated_client.remove_workspace_participants(
            project_id=project_id,
            workspace_id=workspace_id,
            participant_user_ids=[second_user_id]
        )

        # Проверяем, что пользователь удален из workspace
        participants_after = authenticated_client.get_workspace_participants(project_id, workspace_id)
        assert not any(p["user_id"] == second_user_id for p in participants_after)

        # Проверяем, что пользователь все еще в проекте (должен остаться)
        project_participants = authenticated_client.get_project_participants(project_id)
        assert any(p["user_id"] == second_user_id for p in project_participants)


        print(f"✓ Участник {second_user_id} удален из workspace, но остался в проекте")

    def test_participant_workspace_roles_and_permissions(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project,
            created_workspace
    ):
        """Тест различных ролей и уровней доступа участников workspace"""
        project_id = created_project["id"]
        workspace_id = created_workspace["id"]
        second_user_id = second_authenticated_client.get_personal_user_profile()["user_id"]

        test_configs = [
            {"role": "developer", "status": "editor", "desc": "Разработчик-редактор"},
            {"role": "designer", "status": "viewer", "desc": "Дизайнер-наблюдатель"},
            {"role": "project_manager", "status": "admin", "desc": "PM-админ"},
        ]

        for i, config in enumerate(test_configs):
            print(f"\nТестируем конфигурацию {i + 1}: {config['desc']}")

            # 1. СНАЧАЛА создаем приглашение в проект
            invitation_data = {
                "user_ids": [second_user_id],
                "role": config["role"],
                "permission_level": config["status"],
                "message": f"Приглашение для теста {config['desc']}"
            }

            invitations = authenticated_client.create_invitations(project_id, invitation_data)
            invitation_id = invitations[0]["id"]

            # 2. Принимаем приглашение
            second_authenticated_client.respond_to_invitation(invitation_id, "accept")

            # 3. ТЕПЕРЬ добавляем в workspace
            authenticated_client.add_workspace_participants(
                project_id=project_id,
                workspace_id=workspace_id,
                participants_data={
                    "user_ids": [second_user_id],
                    "role": config["role"],
                    "status": config["status"]
                }
            )

            # Проверяем
            participants = authenticated_client.get_workspace_participants(project_id, workspace_id)
            participant = next(p for p in participants if p["user_id"] == second_user_id)

            assert participant["role"] == config["role"]
            assert participant["status"] == config["status"]

            # Удаляем из workspace для следующего теста (но оставляем в проекте)
            authenticated_client.remove_workspace_participants(
                project_id=project_id,
                workspace_id=workspace_id,
                participant_user_ids=[second_user_id]
            )

            print(f"✓ {config['desc']} - успешно")

        # В конце удаляем пользователя из проекта
        # Используем правильный метод из openapi
        authenticated_client.remove_project_participants(
            project_id=project_id,
            participant_user_ids=[second_user_id]
        )
        print(f"✓ Пользователь {second_user_id} удален из проекта")

    def test_workspace_participant_flow_with_invitation(
            self,
            authenticated_client,
            second_authenticated_client,
            created_project,
            created_workspace
    ):
        """Полный flow: приглашение в проект -> добавление в workspace"""
        project_id = created_project["id"]
        workspace_id = created_workspace["id"]
        second_user_id = second_authenticated_client.get_personal_user_profile()["user_id"]

        # 1. Создаем приглашение в проект
        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Приглашение для полного flow"
        }

        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        invitation_id = invitations[0]["id"]
        print(f"✓ Создано приглашение ID: {invitation_id}")

        # 2. Принимаем приглашение (теперь пользователь в проекте)
        second_authenticated_client.respond_to_invitation(invitation_id, "accept")
        print("✓ Приглашение принято, пользователь добавлен в проект")

        # 3. Добавляем пользователя в workspace
        authenticated_client.add_workspace_participants(
            project_id=project_id,
            workspace_id=workspace_id,
            participants_data={
                "user_ids": [second_user_id],
                "role": "developer",
                "status": "editor"
            }
        )
        print("✓ Пользователь добавлен в workspace")

        # 4. Проверяем, что пользователь в workspace
        participants = authenticated_client.get_workspace_participants(project_id, workspace_id)
        assert any(p["user_id"] == second_user_id for p in participants)

        # 5. Проверяем, что пользователь видит workspace
        workspace_info = second_authenticated_client.get_workspace(project_id, workspace_id)
        assert workspace_info["id"] == workspace_id
        print("✓ Пользователь имеет доступ к workspace")

        print("✓ Полный flow: приглашение → добавление в workspace → доступ")