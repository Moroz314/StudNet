import uuid
import pytest
from .fixtures import *


class TestTaskManagement:
    """Тесты для управления задачами"""

    def test_task_creation(self, authenticated_client, project_with_owner, created_workspace, sample_task_data):
        """Тест создания обычной задачи"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        task = authenticated_client.create_task(project_id, workspace_id, sample_task_data)

        assert "id" in task
        assert task["title"] == sample_task_data["title"]
        assert task["task_type"] == sample_task_data["task_type"]
        assert task["priority"] == sample_task_data["priority"]
        assert task["workspace_id"] == workspace_id
        assert task["status"] == "todo"
        assert "assignees" in task

        retrieved_task = authenticated_client.get_task(project_id, workspace_id, task["id"])
        assert retrieved_task["id"] == task["id"]

    def test_get_workspace_tasks(self, authenticated_client, project_with_owner, created_workspace, created_task):
        """Тест получения списка задач рабочего пространства"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        tasks = authenticated_client.get_workspace_tasks(project_id, workspace_id)
        assert isinstance(tasks, list)
        assert len(tasks) >= 1
        assert any(t["id"] == created_task["id"] for t in tasks)

    def test_update_task(self, authenticated_client, project_with_owner, created_workspace, created_task):
        """Тест обновления задачи"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]
        task_id = created_task["id"]

        update_data = {
            "title": f"Updated Task {uuid.uuid4().hex[:8]}",
            "description": "Обновленное описание",
            "priority": "high",
            "status": "in_progress"
        }

        updated_task = authenticated_client.update_task(project_id, workspace_id, task_id, update_data)

        assert updated_task["id"] == task_id
        assert updated_task["title"] == update_data["title"]
        assert updated_task["priority"] == update_data["priority"]
        assert updated_task["status"] == update_data["status"]

    def test_delete_task(self, authenticated_client, project_with_owner, created_workspace, sample_task_data):
        """Тест удаления задачи"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        task = authenticated_client.create_task(project_id, workspace_id, sample_task_data)
        task_id = task["id"]

        authenticated_client.delete_task(project_id, workspace_id, task_id)

        with pytest.raises(AssertionError):
            authenticated_client.get_task(project_id, workspace_id, task_id)

    def test_task_assignees(self, authenticated_client, project_with_owner, created_workspace,
                            created_task, second_authenticated_client):
        """Тест работы с назначенными исполнителями"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]
        task_id = created_task["id"]

        second_profile = second_authenticated_client.get_personal_user_profile()
        assignee_id = second_profile["user_id"]

        # Добавляем исполнителя
        updated_task = authenticated_client.add_assignees_to_task(
            project_id, workspace_id, task_id, [assignee_id]
        )
        assert assignee_id in updated_task["assignees"]

        # Получаем список назначенных
        assignees = authenticated_client.get_task_assignees(project_id, workspace_id, task_id)
        assert assignee_id in assignees

        # Удаляем исполнителя
        updated_task = authenticated_client.remove_assignee_from_task(
            project_id, workspace_id, task_id, assignee_id
        )
        assert assignee_id not in updated_task["assignees"]

    def test_filter_tasks(self, authenticated_client, project_with_owner, created_workspace, created_task):
        """Тест фильтрации задач"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # По статусу
        tasks = authenticated_client.get_workspace_tasks(project_id, workspace_id, status="todo")
        assert any(t["id"] == created_task["id"] for t in tasks)

        tasks = authenticated_client.get_workspace_tasks(project_id, workspace_id, status="done")
        assert not any(t["id"] == created_task["id"] for t in tasks)

        # По приоритету
        tasks = authenticated_client.get_workspace_tasks(project_id, workspace_id, priority="medium")
        assert any(t["id"] == created_task["id"] for t in tasks)

    def test_search_tasks(self, authenticated_client, project_with_owner, created_workspace, created_task):
        """Тест поиска задач"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]
        search_query = created_task["title"][:10]

        tasks = authenticated_client.get_workspace_tasks(project_id, workspace_id, search=search_query)
        assert any(t["id"] == created_task["id"] for t in tasks)