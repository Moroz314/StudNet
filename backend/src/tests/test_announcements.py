import uuid
import pytest
import os
from .fixtures import *
from .clients.extended import ExtendedAPIClient
from .config import TEST_PROJECT_FILE_PATH, SECOND_TEST_EMAIL, SECOND_TEST_PASSWORD, THIRD_TEST_EMAIL, \
    THIRD_TEST_PASSWORD


class TestAnnouncements:
    """Тесты для работы с объявлениями"""

    def test_create_announcement(self, authenticated_client, project_with_owner, created_workspace):
        """Тест создания объявления"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        title = f"Test Announcement {uuid.uuid4().hex[:8]}"
        content = "This is a test announcement content"
        questions = ["What is your experience?", "What technologies do you know?"]

        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=title,
            content=content,
            questions=questions
        )

        assert "id" in announcement
        assert announcement["title"] == title
        assert announcement["content"] == content
        assert announcement["questions"] == questions
        assert announcement["status"] == "active"
        assert announcement["project_id"] == project_id
        assert announcement["workspace_id"] == workspace_id
        assert announcement["created_by"] == authenticated_client.user_id
        assert "creator" in announcement
        assert announcement["applications_count"] == 0
        assert announcement["has_user_application"] is False

        print(f"✓ Создано объявление: {announcement['id']}")

    def test_create_announcement_with_files(self, authenticated_client, project_with_owner, created_workspace):
        """Тест создания объявления с файлами"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # 1. Загружаем файлы через универсальный эндпоинт /files/upload
        file_data1 = authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="announcement_file",
            metadata={"description": "Test file for announcement"}
        )
        file_id1 = file_data1["file_id"]
        print(f"✓ Загружен файл 1: {file_id1}")

        file_data2 = authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="announcement_file",
            metadata={"description": "Second test file"}
        )
        file_id2 = file_data2["file_id"]
        print(f"✓ Загружен файл 2: {file_id2}")

        # 2. Создаем объявление с прикрепленными файлами
        title = f"Test Announcement with Files {uuid.uuid4().hex[:8]}"
        content = "This announcement has attached files"
        questions = ["Please review the attached documents"]

        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=title,
            content=content,
            questions=questions,
            file_ids=[file_id1, file_id2]
        )

        assert "id" in announcement
        assert len(announcement["files"]) == 2

        attached_file_ids = [f["id"] for f in announcement["files"]]
        assert file_id1 in attached_file_ids
        assert file_id2 in attached_file_ids

        print(f"✓ Создано объявление с файлами: {announcement['id']}")

    def test_create_announcement_with_invalid_files(self, authenticated_client, project_with_owner, created_workspace):
        """Тест создания объявления с невалидными ID файлов (должен вернуть ошибку)"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # Несуществующий ID файла
        fake_file_id = str(uuid.uuid4())

        with pytest.raises(AssertionError) as exc_info:
            authenticated_client.create_announcement(
                project_id=project_id,
                workspace_id=workspace_id,
                title="Test with invalid files",
                content="Should fail",
                questions=[],
                file_ids=[fake_file_id]
            )
        assert "failed" in str(exc_info.value) or "400" in str(exc_info.value)

        print(f"✓ Невалидные файлы вызывают ошибку")

    def test_update_announcement_files(self, authenticated_client, project_with_owner, created_workspace):
        """Тест обновления файлов объявления"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # 1. Создаем объявление без файлов
        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=f"Update Files Test {uuid.uuid4().hex[:8]}",
            content="Initial content",
            questions=[]
        )
        announcement_id = announcement["id"]
        assert len(announcement["files"]) == 0
        print(f"✓ Создано объявление без файлов")

        # 2. Загружаем файл
        file_data = authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="announcement_file",
            metadata={"description": "File for update"}
        )
        file_id = file_data["file_id"]
        print(f"✓ Загружен файл: {file_id}")

        # 3. Обновляем объявление - добавляем файл
        updated = authenticated_client.update_announcement(
            announcement_id=announcement_id,
            file_ids=[file_id]
        )

        assert len(updated["files"]) == 1
        assert updated["files"][0]["id"] == file_id
        print(f"✓ Файл добавлен к объявлению")

        # 4. Загружаем еще один файл
        file_data2 = authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="announcement_file",
            metadata={"description": "Second file for update"}
        )
        file_id2 = file_data2["file_id"]
        print(f"✓ Загружен второй файл: {file_id2}")

        # 5. Обновляем объявление - заменяем файлы (теперь два файла)
        updated = authenticated_client.update_announcement(
            announcement_id=announcement_id,
            file_ids=[file_id, file_id2]
        )

        assert len(updated["files"]) == 2
        attached_ids = [f["id"] for f in updated["files"]]
        assert file_id in attached_ids
        assert file_id2 in attached_ids
        print(f"✓ Файлы обновлены (теперь 2 файла)")

        # 6. Обновляем объявление - убираем все файлы
        updated = authenticated_client.update_announcement(
            announcement_id=announcement_id,
            file_ids=[]
        )

        assert len(updated["files"]) == 0
        print(f"✓ Все файлы удалены из объявления")

    def test_application_with_files(self, authenticated_client, second_authenticated_client,
                                    project_with_owner, created_workspace):
        """Тест подачи заявки с файлами"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # 1. Добавляем второго пользователя в проект
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Join to apply with files"
        }
        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")
        print(f"✓ Второй пользователь добавлен в проект")

        # 2. Создаем объявление
        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=f"Application with Files Test {uuid.uuid4().hex[:8]}",
            content="Apply with your portfolio",
            questions=["Please attach your CV/portfolio"]
        )
        print(f"✓ Создано объявление: {announcement['id']}")

        # 3. Второй пользователь загружает файлы для заявки
        file_data1 = second_authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="application_file",
            metadata={"description": "My CV"}
        )
        file_id1 = file_data1["file_id"]
        print(f"✓ Загружен файл 1: {file_id1}")

        file_data2 = second_authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="application_file",
            metadata={"description": "My Portfolio"}
        )
        file_id2 = file_data2["file_id"]
        print(f"✓ Загружен файл 2: {file_id2}")

        # 4. Подаем заявку с файлами
        application = second_authenticated_client.create_application(
            announcement_id=announcement["id"],
            content="I would like to apply. Please find my documents attached.",
            links=["https://linkedin.com/in/testuser"],
            file_ids=[file_id1, file_id2]
        )

        assert "id" in application
        assert application["announcement_id"] == announcement["id"]
        assert application["user_id"] == second_user_id
        assert len(application["files"]) == 2

        attached_file_ids = [f["id"] for f in application["files"]]
        assert file_id1 in attached_file_ids
        assert file_id2 in attached_file_ids

        print(f"✓ Создана заявка с файлами: {application['id']}")

        # 5. Владелец получает заявку и видит файлы
        retrieved = authenticated_client.get_application(application["id"])
        assert len(retrieved["files"]) == 2
        for file in retrieved["files"]:
            assert "url" in file
            assert "original_filename" in file
        print(f"✓ Владелец видит файлы в заявке")

    def test_update_application_files(self, authenticated_client, second_authenticated_client,
                                      project_with_owner, created_workspace):
        """Тест обновления файлов заявки"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # 1. Добавляем второго пользователя
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor"
        }
        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # 2. Создаем объявление
        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=f"Update App Files Test {uuid.uuid4().hex[:8]}",
            content="Test",
            questions=[]
        )

        # 3. Загружаем первый файл и подаем заявку
        file_data1 = second_authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="application_file"
        )
        file_id1 = file_data1["file_id"]

        application = second_authenticated_client.create_application(
            announcement_id=announcement["id"],
            content="Initial application",
            file_ids=[file_id1]
        )
        assert len(application["files"]) == 1
        print(f"✓ Создана заявка с 1 файлом")

        # 4. Загружаем второй файл и обновляем заявку
        file_data2 = second_authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="application_file"
        )
        file_id2 = file_data2["file_id"]

        updated = second_authenticated_client.update_application(
            application_id=application["id"],
            content="Updated application with more files",
            file_ids=[file_id1, file_id2]
        )

        assert len(updated["files"]) == 2
        assert updated["content"] == "Updated application with more files"
        print(f"✓ Заявка обновлена (теперь 2 файла)")

        # 5. Убираем все файлы
        updated = second_authenticated_client.update_application(
            application_id=application["id"],
            file_ids=[]
        )

        assert len(updated["files"]) == 0
        print(f"✓ Все файлы удалены из заявки")

    def test_application_with_invalid_file_type(self, authenticated_client, second_authenticated_client,
                                                project_with_owner, created_workspace):
        """Тест подачи заявки с файлом неверного типа"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # 1. Добавляем второго пользователя
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor"
        }
        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # 2. Создаем объявление
        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=f"Invalid File Type Test {uuid.uuid4().hex[:8]}",
            content="Test",
            questions=[]
        )

        # 3. Загружаем файл с неверным типом (например, avatar вместо application_file)
        file_data = second_authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="avatar"  # Неверный тип для заявки
        )
        file_id = file_data["file_id"]

        # 4. Пытаемся подать заявку с файлом неверного типа
        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.create_application(
                announcement_id=announcement["id"],
                content="Application with wrong file type",
                file_ids=[file_id]
            )
        assert "failed" in str(exc_info.value) or "400" in str(exc_info.value)

        print(f"✓ Файл неверного типа вызывает ошибку")

    def test_get_announcement(self, authenticated_client, project_with_owner, created_workspace):
        """Тест получения объявления по ID"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # Создаем объявление
        title = f"Get Test {uuid.uuid4().hex[:8]}"
        content = "Test content for get"
        questions = ["Q1?", "Q2?"]

        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=title,
            content=content,
            questions=questions
        )
        announcement_id = announcement["id"]
        print(f"✓ Создано объявление: {announcement_id}")

        # Получаем объявление по ID
        retrieved = authenticated_client.get_announcement(announcement_id)

        # Проверяем все поля
        assert retrieved["id"] == announcement_id
        assert retrieved["title"] == title
        assert retrieved["content"] == content
        assert retrieved["questions"] == questions
        assert retrieved["status"] == "active"
        assert retrieved["project_id"] == project_id
        assert retrieved["workspace_id"] == workspace_id
        assert retrieved["created_by"] == authenticated_client.user_id
        assert "created_at" in retrieved
        assert "updated_at" in retrieved
        assert "creator" in retrieved
        assert retrieved["creator"]["user_id"] == authenticated_client.user_id
        assert retrieved["applications_count"] == 0
        assert retrieved["has_user_application"] is False
        assert retrieved["user_application_id"] is None
        assert "files" in retrieved
        assert isinstance(retrieved["files"], list)

        print(f"✓ Объявление получено по ID: {announcement_id}")

    def test_get_announcement_not_found(self, authenticated_client):
        """Тест получения несуществующего объявления"""
        fake_id = str(uuid.uuid4())

        with pytest.raises(AssertionError) as exc_info:
            authenticated_client.get_announcement(fake_id)

        assert "failed" in str(exc_info.value) or "404" in str(exc_info.value)
        print(f"✓ Несуществующее объявление возвращает 404")

    def test_get_announcement_with_files(self, authenticated_client, project_with_owner, created_workspace):
        """Тест получения объявления с файлами"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # Загружаем файлы
        file_data1 = authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="announcement_file",
            metadata={"description": "File 1"}
        )
        file_id1 = file_data1["file_id"]

        file_data2 = authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="announcement_file",
            metadata={"description": "File 2"}
        )
        file_id2 = file_data2["file_id"]

        # Создаем объявление с файлами
        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=f"Get with files {uuid.uuid4().hex[:8]}",
            content="Has files",
            questions=[],
            file_ids=[file_id1, file_id2]
        )
        announcement_id = announcement["id"]

        # Получаем объявление
        retrieved = authenticated_client.get_announcement(announcement_id)

        # Проверяем файлы
        assert len(retrieved["files"]) == 2
        retrieved_file_ids = [f["id"] for f in retrieved["files"]]
        assert file_id1 in retrieved_file_ids
        assert file_id2 in retrieved_file_ids

        # Проверяем что у файлов есть URL
        for file in retrieved["files"]:
            assert "url" in file
            assert "original_filename" in file
            assert "mime_type" in file
            assert "size_bytes" in file

        print(f"✓ Объявление с файлами получено, файлы доступны")

    def test_get_announcement_with_applications_count(self, authenticated_client, second_authenticated_client,
                                                      project_with_owner, created_workspace):
        """Тест получения объявления с количеством заявок"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        # Добавляем второго пользователя
        second_profile = second_authenticated_client.get_personal_user_profile()
        second_user_id = second_profile["user_id"]

        invitation_data = {
            "user_ids": [second_user_id],
            "role": "developer",
            "permission_level": "editor"
        }
        invitations = authenticated_client.create_invitations(project_id, invitation_data)
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # Создаем объявление
        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=f"Count test {uuid.uuid4().hex[:8]}",
            content="Test",
            questions=[]
        )
        announcement_id = announcement["id"]

        # Подаем две заявки (одну от второго пользователя)
        second_authenticated_client.create_application(
            announcement_id=announcement_id,
            content="Application 1"
        )

        # Получаем объявление
        retrieved = authenticated_client.get_announcement(announcement_id)

        assert retrieved["applications_count"] == 1
        assert retrieved["has_user_application"] is False  # Владелец не подавал

        # Второй пользователь проверяет
        retrieved_by_second = second_authenticated_client.get_announcement(announcement_id)
        assert retrieved_by_second["applications_count"] == 1
        assert retrieved_by_second["has_user_application"] is True  # Он подал заявку
        assert retrieved_by_second["user_application_id"] is not None

        print(f"✓ Количество заявок корректно отображается")

    def test_get_announcement_public_for_non_member(self, third_authenticated_client, authenticated_client,
                                                     project_with_owner, created_workspace):
        """Тест: не участник проекта может просматривать объявление из ленты"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        announcement = authenticated_client.create_announcement(
            project_id=project_id,
            workspace_id=workspace_id,
            title=f"Public feed test {uuid.uuid4().hex[:8]}",
            content="Open for everyone",
            questions=[]
        )
        announcement_id = announcement["id"]

        retrieved = third_authenticated_client.get_announcement(announcement_id)
        assert retrieved["id"] == announcement_id
        assert retrieved["title"] == announcement["title"]
        print(f"✓ Не участник может просматривать объявление из ленты")
