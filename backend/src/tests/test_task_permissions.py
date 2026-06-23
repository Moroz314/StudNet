import pytest
from .fixtures import *
from .clients.extended import ExtendedAPIClient
from .config import SECOND_TEST_EMAIL, SECOND_TEST_PASSWORD, THIRD_TEST_EMAIL, THIRD_TEST_PASSWORD


class TestTaskPermissions:
    """Тесты прав доступа к задачам"""

    def test_admin_can_create_task_in_workspace(self, authenticated_client, project_with_owner,
                                                second_authenticated_client):
        """Тест: админ может создавать задачи в workspace, в котором состоит"""
        project_id = project_with_owner["id"]

        # Создаем workspace (только owner может создавать workspace)
        workspace_data = {
            "name": "Test Workspace for Admin",
            "description": "Workspace for admin testing",
            "create_chat": True
        }
        workspace = authenticated_client.create_workspace(project_id, workspace_data)
        workspace_id = workspace["id"]

        # Добавляем второго пользователя в workspace как админа
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        authenticated_client.add_workspace_participants(
            project_id, workspace_id, {'user_ids': [second_user_id], 'role': 'developer', 'status': 'admin'}
        )

        # Обновляем статус второго пользователя на admin
        authenticated_client.update_participant(
            project_id,
            second_user_id,
            {"role": "admin", "status": "editor"}
        )

        # Админ создает задачу
        task_data = {
            "title": "Task created by admin",
            "description": "Task description",
            "task_type": "task"
        }

        task = second_authenticated_client.create_task(project_id, workspace_id, task_data)
        assert task["id"] is not None
        assert task["title"] == task_data["title"]

        # Очистка
        try:
            authenticated_client.delete_workspace(project_id, workspace_id)
        except:
            pass

    def test_non_member_cannot_create_task(self, authenticated_client, project_with_owner, third_authenticated_client):
        """Тест: не участник workspace не может создавать задачи"""
        project_id = project_with_owner["id"]

        # Создаем workspace
        workspace_data = {
            "name": "Test Workspace",
            "description": "Workspace for testing",
            "create_chat": True
        }
        workspace = authenticated_client.create_workspace(project_id, workspace_data)
        workspace_id = workspace["id"]

        task_data = {
            "title": "Task by non-member",
            "description": "Should fail",
            "task_type": "task"
        }

        # Третий пользователь не добавлен в workspace
        with pytest.raises(AssertionError):
            third_authenticated_client.create_task(project_id, workspace_id, task_data)

        # Очистка
        try:
            authenticated_client.delete_workspace(project_id, workspace_id)
        except:
            pass

    def test_admin_can_update_task(self, authenticated_client, project_with_owner, second_authenticated_client):
        """Тест: админ может обновлять задачи в workspace"""
        project_id = project_with_owner["id"]

        # Создаем workspace
        workspace_data = {
            "name": "Test Workspace for Update",
            "description": "Workspace for update testing",
            "create_chat": True
        }
        workspace = authenticated_client.create_workspace(project_id, workspace_data)
        workspace_id = workspace["id"]

        # Добавляем второго пользователя в workspace как админа
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        authenticated_client.add_workspace_participants(
            project_id, workspace_id, [second_user_id]
        )
        authenticated_client.update_participant(
            project_id,
            second_user_id,
            {"role": "admin", "status": "editor"}
        )

        # Создаем задачу (владельцем)
        task_data = {
            "title": "Original title",
            "description": "Original description",
            "task_type": "task"
        }
        task = authenticated_client.create_task(project_id, workspace_id, task_data)

        # Админ обновляет задачу
        update_data = {
            "title": "Updated by admin",
            "description": "Updated description"
        }
        updated_task = second_authenticated_client.update_task(
            project_id, workspace_id, task["id"], update_data
        )

        assert updated_task["title"] == update_data["title"]
        assert updated_task["description"] == update_data["description"]

        # Очистка
        try:
            authenticated_client.delete_workspace(project_id, workspace_id)
        except:
            pass

    def test_admin_can_delete_task(self, authenticated_client, project_with_owner, second_authenticated_client):
        """Тест: админ может удалять задачи в workspace"""
        project_id = project_with_owner["id"]

        # Создаем workspace
        workspace_data = {
            "name": "Test Workspace for Delete",
            "description": "Workspace for delete testing",
            "create_chat": True
        }
        workspace = authenticated_client.create_workspace(project_id, workspace_data)
        workspace_id = workspace["id"]

        # Добавляем второго пользователя в workspace как админа
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        authenticated_client.add_workspace_participants(
            project_id, workspace_id, [second_user_id]
        )
        authenticated_client.update_participant(
            project_id,
            second_user_id,
            {"role": "admin", "status": "editor"}
        )

        # Создаем задачу (владельцем)
        task_data = {
            "title": "Task to delete",
            "description": "Will be deleted",
            "task_type": "task"
        }
        task = authenticated_client.create_task(project_id, workspace_id, task_data)

        # Админ удаляет задачу
        second_authenticated_client.delete_task(project_id, workspace_id, task["id"])

        # Проверяем, что задача удалена
        with pytest.raises(AssertionError):
            authenticated_client.get_task(project_id, workspace_id, task["id"])

        # Очистка
        try:
            authenticated_client.delete_workspace(project_id, workspace_id)
        except:
            pass

    def test_admin_can_assign_users_to_task(self, authenticated_client, project_with_owner, second_authenticated_client,
                                            third_authenticated_client):
        """Тест: админ может назначать пользователей на задачу"""
        project_id = project_with_owner["id"]

        # Создаем workspace
        workspace_data = {
            "name": "Test Workspace for Assign",
            "description": "Workspace for assign testing",
            "create_chat": True
        }
        workspace = authenticated_client.create_workspace(project_id, workspace_data)
        workspace_id = workspace["id"]

        # Добавляем второго пользователя как админа
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        authenticated_client.add_workspace_participants(
            project_id, workspace_id, [second_user_id]
        )
        authenticated_client.update_participant(
            project_id,
            second_user_id,
            {"role": "admin", "status": "editor"}
        )

        # Добавляем третьего пользователя в workspace
        third_profile = third_authenticated_client.get_personal_user_profile()
        third_user_id = third_profile["user_id"]

        authenticated_client.add_workspace_participants(
            project_id, workspace_id, [third_user_id]
        )

        # Создаем задачу (админом)
        task_data = {
            "title": "Task with assignee",
            "description": "Will have assignee",
            "task_type": "task"
        }
        task = second_authenticated_client.create_task(project_id, workspace_id, task_data)

        # Админ назначает пользователя на задачу
        updated_task = second_authenticated_client.add_assignees_to_task(
            project_id, workspace_id, task["id"], [third_user_id]
        )

        assert third_user_id in updated_task["assignees"]

        # Очистка
        try:
            authenticated_client.delete_workspace(project_id, workspace_id)
        except:
            pass

    def test_admin_can_view_statistics(self, authenticated_client, project_with_owner, second_authenticated_client):
        """Тест: админ может просматривать статистику"""
        project_id = project_with_owner["id"]

        # Создаем workspace
        workspace_data = {
            "name": "Test Workspace for Stats",
            "description": "Workspace for statistics testing",
            "create_chat": True
        }
        workspace = authenticated_client.create_workspace(project_id, workspace_data)
        workspace_id = workspace["id"]

        # Добавляем второго пользователя как админа
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        authenticated_client.add_workspace_participants(
            project_id, workspace_id, [second_user_id]
        )
        authenticated_client.update_participant(
            project_id,
            second_user_id,
            {"role": "admin", "status": "editor"}
        )

        # Создаем несколько задач (админом)
        for i in range(3):
            task_data = {
                "title": f"Task {i}",
                "description": "For statistics",
                "task_type": "task"
            }
            second_authenticated_client.create_task(project_id, workspace_id, task_data)

        # Админ получает статистику
        statistics = second_authenticated_client.get_workspace_statistics(project_id, workspace_id)

        assert "total_tasks" in statistics
        assert statistics["total_tasks"] >= 3
        assert "status_distribution" in statistics
        assert "priority_distribution" in statistics

        # Очистка
        try:
            authenticated_client.delete_workspace(project_id, workspace_id)
        except:
            pass

    def test_non_admin_cannot_assign_users(self, authenticated_client, project_with_owner, second_authenticated_client):
        """Тест: обычный пользователь (не админ) не может назначать пользователей на задачу"""
        project_id = project_with_owner["id"]

        # Создаем workspace
        workspace_data = {
            "name": "Test Workspace",
            "description": "Workspace for testing",
            "create_chat": True
        }
        workspace = authenticated_client.create_workspace(project_id, workspace_data)
        workspace_id = workspace["id"]

        # Добавляем второго пользователя в workspace как обычного участника (не админа)
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        authenticated_client.add_workspace_participants(
            project_id, workspace_id, [second_user_id]
        )
        authenticated_client.update_participant(
            project_id,
            second_user_id,
            {"role": "other", "status": "viewer"}
        )

        # Создаем задачу
        task_data = {
            "title": "Test task",
            "description": "Test description",
            "task_type": "task"
        }
        task = authenticated_client.create_task(project_id, workspace_id, task_data)

        # Обычный пользователь пытается назначить пользователя
        with pytest.raises(AssertionError):
            second_authenticated_client.add_assignees_to_task(
                project_id, workspace_id, task["id"], [second_user_id]
            )

        # Очистка
        try:
            authenticated_client.delete_workspace(project_id, workspace_id)
        except:
            pass

    def test_owner_can_publish_project(self, authenticated_client, sample_project_data):
        """Тест: владелец может публиковать проект"""
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]
        workspace_id = project["workspaces"][0]["id"]

        # Загружаем файл
        test_file_path = "test_file.txt"
        with open(test_file_path, "w") as f:
            f.write("test content")

        try:
            file_data = authenticated_client.upload_project_file(
                project_id=project_id,
                workspace_id=workspace_id,
                file_path=test_file_path,
                description="Test file"
            )

            # Публикуем проект
            published = authenticated_client.publish_project(project_id, [file_data["id"]])
            assert published["status"] == "published"

            # Снимаем с публикации
            unpublished = authenticated_client.unpublish_project(project_id)
            assert unpublished["status"] == "active"

            # Удаляем файл
            authenticated_client.delete_project_file(project_id, file_data["id"], workspace_id)

        finally:
            import os
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
            try:
                authenticated_client.delete_project(project_id)
            except:
                pass

    def test_non_owner_cannot_publish_project(self, authenticated_client, project_with_owner,
                                              second_authenticated_client):
        """Тест: не владелец не может публиковать проект"""
        project_id = project_with_owner["id"]

        with pytest.raises(AssertionError):
            second_authenticated_client.publish_project(project_id, [])

    def test_admin_can_manage_workspace_participants(self, authenticated_client, project_with_owner,
                                                     second_authenticated_client, third_authenticated_client):
        """Тест: админ может добавлять/удалять участников из workspace"""
        project_id = project_with_owner["id"]

        # Создаем workspace
        workspace_data = {
            "name": "Test Workspace for Participant Management",
            "description": "Workspace for participant management",
            "create_chat": True
        }
        workspace = authenticated_client.create_workspace(project_id, workspace_data)
        workspace_id = workspace["id"]

        # Добавляем второго пользователя как админа
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        authenticated_client.add_workspace_participants(
            project_id, workspace_id, [second_user_id]
        )
        authenticated_client.update_participant(
            project_id,
            second_user_id,
            {"role": "admin", "status": "editor"}
        )

        # Получаем ID третьего пользователя
        third_profile = third_authenticated_client.get_personal_user_profile()
        third_user_id = third_profile["user_id"]

        # Админ добавляет участника в workspace
        second_authenticated_client.add_workspace_participants(
            project_id, workspace_id, [third_user_id]
        )

        # Проверяем, что участник добавлен
        participants = second_authenticated_client.get_workspace_participants(project_id, workspace_id)
        assert any(p["user_id"] == third_user_id for p in participants)

        # Админ удаляет участника из workspace
        second_authenticated_client.remove_workspace_participants(
            project_id, workspace_id, [third_user_id]
        )

        # Проверяем, что участник удален
        participants = second_authenticated_client.get_workspace_participants(project_id, workspace_id)
        assert not any(p["user_id"] == third_user_id for p in participants)

        # Очистка
        try:
            authenticated_client.delete_workspace(project_id, workspace_id)
        except:
            pass