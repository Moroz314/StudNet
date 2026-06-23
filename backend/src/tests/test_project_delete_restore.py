import pytest
import uuid
from .fixtures import *
from .config import TEST_AVATAR_PATH, TEST_PROJECT_FILE_PATH
import os


class TestProjectDeleteRestore:
    """Тесты для удаления и восстановления проектов"""

    def test_archive_project(self, authenticated_client, sample_project_data):
        """Тест архивации проекта"""
        # 1. Создаем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]
        assert project["status"] == "active"
        print(f"✓ Создан проект: {project['name']} (ID: {project_id})")

        # 2. Архивируем проект - в openapi это DELETE /projects/{project_id}/archive
        archive_result = authenticated_client.archive_project(project_id)
        # Проверяем что ответ не пустой (в openapi ответ может быть пустым)
        assert archive_result is not None
        print(f"✓ Проект архивирован")

        # 3. Проверяем, что проект изменил статус
        archived_project = authenticated_client.get_project(project_id)
        assert archived_project["status"] == "archived"
        print(f"✓ Статус проекта изменен на 'archived'")

        # 4. Проверяем, что проект не отображается в активных проектах
        active_projects = authenticated_client.get_user_projects(status="active")
        assert not any(p["id"] == project_id for p in active_projects)
        print(f"✓ Проект отсутствует в списке активных проектов")

        # 5. Проверяем, что проект отображается в архивированных
        archived_projects = authenticated_client.get_user_projects(status="archived")
        assert any(p["id"] == project_id for p in archived_projects)
        print(f"✓ Проект присутствует в списке архивированных проектов")

    def test_restore_project(self, authenticated_client, sample_project_data):
        """Тест восстановления проекта из архива"""
        # 1. Создаем и архивируем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]
        authenticated_client.archive_project(project_id)
        print(f"✓ Создан и архивирован проект: {project_id}")

        # 2. Восстанавливаем проект - в openapi это POST /projects/{project_id}/restore
        restored_project = authenticated_client.restore_project(project_id)
        assert restored_project["id"] == project_id
        assert restored_project["status"] == "active"
        print(f"✓ Проект восстановлен из архива")

        # 3. Проверяем, что проект снова активен
        active_project = authenticated_client.get_project(project_id)
        assert active_project["status"] == "active"
        print(f"✓ Статус проекта изменен на 'active'")

        # 4. Проверяем, что проект отображается в активных проектах
        active_projects = authenticated_client.get_user_projects(status="active")
        assert any(p["id"] == project_id for p in active_projects)
        print(f"✓ Проект снова в списке активных проектов")

    def test_cannot_restore_active_project(self, authenticated_client, created_project):
        """Тест: нельзя восстановить активный проект"""
        project_id = created_project["id"]

        with pytest.raises(AssertionError) as exc_info:
            authenticated_client.restore_project(project_id)

        assert "Project restore failed" in str(exc_info.value)
        print(f"✓ Невозможно восстановить активный проект (ожидаемая ошибка)")

    def test_delete_project(self, authenticated_client, created_project):
        """Тест удаления проекта - требует подтверждения"""
        project_id = created_project["id"]

        # В openapi нет confirmation, просто DELETE /projects/{project_id}
        # Удаление должно работать только для создателя проекта
        result = authenticated_client.delete_project(project_id)
        # Проверяем, что проект удален
        with pytest.raises(AssertionError):
            authenticated_client.get_project(project_id)
        print(f"✓ Проект успешно удален")

    def test_delete_project_non_owner(self, second_authenticated_client, created_project):
        """Тест: попытка удалить проект не владельцем"""
        project_id = created_project["id"]

        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.delete_project(project_id)

        assert "Project deletion failed" in str(exc_info.value)
        assert "403" in str(exc_info.value) or "permission" in str(exc_info.value).lower()
        print(f"✓ Не-владелец не может удалить проект (ожидаемая ошибка)")

    def test_archive_already_archived_project(self, authenticated_client, sample_project_data):
        """Тест: попытка архивировать уже архивированный проект"""
        # 1. Создаем и архивируем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]
        authenticated_client.archive_project(project_id)
        print(f"✓ Создан и архивирован проект: {project_id}")

        # 2. Пытаемся архивировать снова - может вернуть ошибку или просто ничего не делать
        with pytest.raises(AssertionError):
            authenticated_client.archive_project(project_id)
        print(f"✓ Повторная архивация вызывает ошибку")

    def test_restore_already_active_project(self, authenticated_client, created_project):
        """Тест: попытка восстановить уже активный проект"""
        project_id = created_project["id"]

        with pytest.raises(AssertionError):
            authenticated_client.restore_project(project_id)

        print(f"✓ Нельзя восстановить активный проект (ожидаемая ошибка)")

    def test_delete_nonexistent_project(self, authenticated_client):
        """Тест: попытка удалить несуществующий проект"""
        fake_project_id = str(uuid.uuid4())

        with pytest.raises(AssertionError) as exc_info:
            authenticated_client.delete_project(fake_project_id)

        assert "Project deletion failed" in str(exc_info.value)
        assert "404" in str(exc_info.value)
        print(f"✓ Удаление несуществующего проекта возвращает 404")