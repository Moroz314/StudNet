import uuid
import pytest
from .fixtures import *
from .clients.extended import ExtendedAPIClient
from .config import SECOND_TEST_EMAIL, SECOND_TEST_PASSWORD


class TestTaskComments:
    """Тесты для управления комментариями к задачам"""

    def test_create_comment(self, authenticated_client, project_with_owner, created_workspace, created_task):
        """Тест создания комментария к задаче"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]
        task_id = created_task["id"]

        comment_data = {
            "content": f"Тестовый комментарий {uuid.uuid4().hex[:8]}",
            "file_ids": []
        }

        comment = authenticated_client.create_task_comment(project_id, workspace_id, task_id, comment_data)

        assert "id" in comment
        assert comment["task_id"] == task_id
        assert comment["user_id"] == authenticated_client.user_id
        assert comment["content"] == comment_data["content"]
        assert comment["is_edited"] is False

    def test_create_comment_with_files(self, authenticated_client, project_with_owner, created_workspace, created_task):
        """Тест создания комментария к задаче с файлами"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]
        task_id = created_task["id"]

        # 1. Загружаем файл
        upload_result = authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="task_attachment",
            metadata={"description": "Task attachment"}
        )
        file_id = upload_result["file_id"]
        print(f"✓ Файл загружен: {file_id}")

        # 2. Создаем комментарий с файлом
        comment_data = {
            "content": f"Комментарий с вложением {uuid.uuid4().hex[:8]}",
            "file_ids": [file_id]
        }

        comment = authenticated_client.create_task_comment(project_id, workspace_id, task_id, comment_data)

        assert comment["task_id"] == task_id
        assert len(comment["attachments"]) == 1
        assert comment["attachments"][0]["id"] == file_id

        print(f"✓ Создан комментарий с файлом: {comment['id']}")

    def test_get_task_comments(self, authenticated_client, project_with_owner, created_workspace, created_task):
        """Тест получения комментариев к задаче"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]
        task_id = created_task["id"]

        for i in range(3):
            comment_data = {"content": f"Тестовый комментарий {i}", "file_ids": []}
            authenticated_client.create_task_comment(project_id, workspace_id, task_id, comment_data)

        comments = authenticated_client.get_task_comments(project_id, workspace_id, task_id)
        print(comments)
        assert len(comments) >= 3

    def test_update_comment(self, authenticated_client, project_with_owner, created_workspace, created_task):
        """Тест обновления комментария"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]
        task_id = created_task["id"]

        comment_data = {"content": "Исходный текст", "file_ids": []}
        comment = authenticated_client.create_task_comment(project_id, workspace_id, task_id, comment_data)

        update_data = {"content": "Обновленный текст"}
        updated = authenticated_client.update_task_comment(project_id, workspace_id, comment["id"], update_data)

        assert updated["content"] == update_data["content"]
        assert updated["is_edited"] is True

    def test_delete_comment(self, authenticated_client, project_with_owner, created_workspace, created_task):
        """Тест удаления комментария"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]
        task_id = created_task["id"]

        comment_data = {"content": "Комментарий для удаления", "file_ids": []}
        comment = authenticated_client.create_task_comment(project_id, workspace_id, task_id, comment_data)

        authenticated_client.delete_task_comment(project_id, workspace_id, comment["id"])

        comments = authenticated_client.get_task_comments(project_id, workspace_id, task_id)
        assert not any(c["id"] == comment["id"] for c in comments)