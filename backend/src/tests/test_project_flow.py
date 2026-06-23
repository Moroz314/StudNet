import os
import uuid
import pytest
from .fixtures import *
from .config import TEST_AVATAR_PATH, TEST_PROJECT_FILE_PATH


class TestProjectFlow:
    """Тесты для flow создания проекта и загрузки файлов"""

    def test_client_authenticated(self, authenticated_client):
        """Тест, что клиент аутентифицирован"""
        assert authenticated_client.access_token is not None
        assert authenticated_client.user_id is not None

        # Проверяем, что можем получить профиль
        profile = authenticated_client.get_personal_user_profile()
        assert "user_id" in profile
        assert profile["user_id"] == authenticated_client.user_id

    def test_project_creation_with_links(self, authenticated_client, sample_project_data, sample_links):
        """Тест создания проекта со ссылками"""
        project = authenticated_client.create_project(sample_project_data)

        assert "id" in project
        assert "name" in project
        assert "status" in project
        assert project["name"] == sample_project_data["name"]
        assert project["description"] == sample_project_data["description"]
        assert project["status"] == "active"
        # В openapi links есть в ProjectCreate и ProjectResponse
        if "links" in project:
            assert project["links"] == sample_links

        # Проверяем, что проект можно получить
        retrieved_project = authenticated_client.get_project(project["id"])
        assert retrieved_project["id"] == project["id"]
        assert retrieved_project["name"] == project["name"]

    def test_project_creation_without_links(self, authenticated_client):
        """Тест создания проекта без ссылок"""
        project_data = {
            "name": f"Test Project No Links {uuid.uuid4().hex[:8]}",
            "description": "Проект без ссылок",
            "tags": ["test", "no-links"],
            "create_chat": True
        }

        project = authenticated_client.create_project(project_data)

        # В openapi links может отсутствовать в ответе или быть null
        if "links" in project:
            assert project["links"] is None or project["links"] == []

    def test_project_update_with_links(self, authenticated_client, created_project, sample_project_update_data):
        """Тест обновления проекта со ссылками"""
        project_id = created_project["id"]

        updated_project = authenticated_client.update_project(project_id, sample_project_update_data)

        assert updated_project["id"] == project_id
        assert updated_project["name"] == sample_project_update_data["name"]
        assert updated_project["description"] == sample_project_update_data["description"]
        if "links" in sample_project_update_data and "links" in updated_project:
            assert updated_project["links"] == sample_project_update_data["links"]

    def test_project_update_clear_links(self, authenticated_client, created_project):
        """Тест очистки ссылок проекта"""
        project_id = created_project["id"]

        # Обновляем проект, устанавливая links = []
        update_data = {
            "links": []
        }

        updated_project = authenticated_client.update_project(project_id, update_data)

        assert updated_project["id"] == project_id
        if "links" in updated_project:
            assert updated_project["links"] == []

    def test_workspace_creation_with_links(self, authenticated_client, created_project,
                                           sample_workspace_data, sample_links, sample_github_links):
        """Тест создания рабочего пространства со ссылками"""
        project_id = created_project["id"]
        workspace = authenticated_client.create_workspace(project_id, sample_workspace_data)

        assert "id" in workspace
        assert "name" in workspace
        assert "project_id" in workspace
        assert workspace["name"] == sample_workspace_data["name"]
        assert workspace["description"] == sample_workspace_data["description"]
        assert workspace["project_id"] == project_id
        if "links" in workspace:
            assert workspace["links"] == sample_links
        if "github_links" in workspace:
            assert workspace["github_links"] == sample_github_links

    def test_avatar_upload_and_delete(self, authenticated_client):
        """Тест загрузки и удаления аватарки"""
        if not os.path.exists(TEST_AVATAR_PATH):
            pytest.skip("Test avatar file not found")

        avatar_data = authenticated_client.upload_avatar(
            TEST_AVATAR_PATH,
            description="Тестовая аватарка"
        )

        assert "file_id" in avatar_data
        assert "avatar_url" in avatar_data
        assert "original_filename" in avatar_data
        assert "mime_type" in avatar_data
        assert "size_bytes" in avatar_data

        # Проверяем, что размер файла соответствует реальному
        file_size = os.path.getsize(TEST_AVATAR_PATH)
        assert avatar_data["size_bytes"] == file_size

        # Очищаем: удаляем аватарку
        delete_response = authenticated_client.delete_avatar()
        assert delete_response["status"] == "success"

    def test_project_file_upload(self, authenticated_client, created_project):
        """Тест загрузки файла в проект"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test project file not found")

        project_id = created_project["id"]

        file_data = authenticated_client.upload_project_file(
            project_id=project_id,
            file_path=TEST_PROJECT_FILE_PATH,
            description="Тестовый документ для проекта",
            tags="pdf,test,document"
        )

        assert "id" in file_data
        assert "original_filename" in file_data
        assert "mime_type" in file_data
        assert "size_bytes" in file_data
        assert file_data["project_id"] == project_id

        # Проверяем, что файл появился в списке файлов проекта
        files_list = authenticated_client.get_project_files(project_id)
        assert isinstance(files_list, list)
        assert any(f["id"] == file_data["id"] for f in files_list)

        # Очищаем: удаляем файл
        authenticated_client.delete_project_file(project_id, file_data["id"])