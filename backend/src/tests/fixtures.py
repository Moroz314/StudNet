import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Generator, List
from .clients.extended import ExtendedAPIClient
from .config import TEST_PROJECT_FILE_PATH
import os


# ========== Базовые фикстуры для данных ==========

@pytest.fixture
def sample_links() -> list:
    """Пример ссылок для проекта (в openapi это массив строк)"""
    return [
        "https://github.com/test/project",
        "https://docs.example.com"
    ]


@pytest.fixture
def sample_github_links() -> list:
    """Пример GitHub ссылок для workspace (в openapi это массив строк)"""
    return [
        "https://github.com/test/backend",
        "https://github.com/test/frontend"
    ]


@pytest.fixture
def sample_project_data(sample_links) -> Dict[str, Any]:
    """Данные для создания проекта"""
    return {
        "name": f"Test Project {uuid.uuid4().hex[:8]}",
        "description": "Тестовый проект для автоматических тестов",
        "tags": ["test", "automation", "pytest"],
        "links": sample_links,
        "category": "technology",
        "create_chat": True
    }


@pytest.fixture
def sample_project_update_data(sample_links) -> Dict[str, Any]:
    """Данные для обновления проекта"""
    return {
        "name": f"Updated Project {uuid.uuid4().hex[:8]}",
        "description": "Обновленное описание тестового проекта",
        "links": sample_links
    }


@pytest.fixture
def sample_workspace_data(sample_links, sample_github_links) -> Dict[str, Any]:
    """Данные для создания рабочего пространства"""
    return {
        "name": f"Test Workspace {uuid.uuid4().hex[:8]}",
        "description": "Тестовое рабочее пространство",
        "links": sample_links,
        "github_links": sample_github_links,
        "create_chat": True
    }


@pytest.fixture
def sample_workspace_update_data(sample_github_links, sample_links) -> Dict[str, Any]:
    """Данные для обновления рабочего пространства"""
    return {
        "name": f"Updated Workspace {uuid.uuid4().hex[:8]}",
        "description": "Обновленное описание рабочего пространства",
        "links": sample_links,
        "github_links": sample_github_links
    }


@pytest.fixture
def sample_task_data() -> Dict[str, Any]:
    """Данные для создания обычной задачи"""
    return {
        "title": f"Test Task {uuid.uuid4().hex[:8]}",
        "description": "Тестовая задача",
        "task_type": "task",
        "priority": "medium",
        "deadline": (datetime.now() + timedelta(days=3)).isoformat(),
        "estimated_hours": 8
    }


@pytest.fixture
def sample_task_with_assignee_data() -> Dict[str, Any]:
    """Данные для создания задачи с назначенным исполнителем"""
    return {
        "title": f"Task With Assignee {uuid.uuid4().hex[:8]}",
        "description": "Задача с назначенным исполнителем",
        "task_type": "task",
        "priority": "high",
        "deadline": (datetime.now() + timedelta(days=2)).isoformat(),
        "estimated_hours": 4,
        "assignees": []  # Будет заполнено в тесте
    }


@pytest.fixture
def sample_idea_task_data() -> Dict[str, Any]:
    """Данные для создания задачи типа идея"""
    return {
        "title": f"Test Idea {uuid.uuid4().hex[:8]}",
        "description": "Тестовая идея",
        "task_type": "idea",
        "priority": "low"
    }


@pytest.fixture
def sample_urgent_task_data() -> Dict[str, Any]:
    """Данные для создания срочной задачи"""
    return {
        "title": f"Urgent Task {uuid.uuid4().hex[:8]}",
        "description": "Срочная задача",
        "task_type": "urgent_task",
        "priority": "urgent",
        "deadline": (datetime.now() + timedelta(hours=12)).isoformat(),
        "estimated_hours": 2
    }


@pytest.fixture
def sample_invitation_data() -> Dict[str, Any]:
    """Данные для создания приглашения"""
    return {
        "user_ids": [],  # Будут заполнены в тесте
        "role": "developer",
        "permission_level": "editor",
        "message": "Приглашение присоединиться к проекту",
    }


# ========== Фикстуры для создания сущностей ==========

@pytest.fixture
def project_with_owner(authenticated_client: ExtendedAPIClient, sample_project_data) -> Dict[str, Any]:
    """Создает проект, где текущий пользователь - владелец"""
    project = authenticated_client.create_project(sample_project_data)
    return project


@pytest.fixture
def project_with_different_owner(
        second_authenticated_client: ExtendedAPIClient,
        sample_project_data
) -> Dict[str, Any]:
    """Создает проект, где владелец - второй пользователь"""
    project = second_authenticated_client.create_project(sample_project_data)
    return project


@pytest.fixture
def created_workspace(authenticated_client, project_with_owner, sample_workspace_data) -> Generator[
    Dict[str, Any], None, None]:
    """Создает рабочее пространство в проекте"""
    workspace = authenticated_client.create_workspace(project_with_owner["id"], sample_workspace_data)
    yield workspace
    try:
        authenticated_client.delete_workspace(project_with_owner["id"], workspace["id"])
    except:
        pass


@pytest.fixture
def workspace_with_admin(authenticated_client, project_with_owner, second_authenticated_client, sample_workspace_data):
    """Создает workspace и добавляет второго пользователя как админа"""
    project_id = project_with_owner["id"]

    # Создаем workspace (только owner может создавать)
    workspace = authenticated_client.create_workspace(project_id, sample_workspace_data)
    workspace_id = workspace["id"]

    # Получаем ID второго пользователя
    second_profile = second_authenticated_client.get_personal_user_profile()
    second_user_id = second_profile["user_id"]

    # Добавляем второго пользователя в workspace
    authenticated_client.add_workspace_participants(
        project_id, workspace_id, [second_user_id]
    )

    # Обновляем статус второго пользователя на admin
    authenticated_client.update_participant(
        project_id,
        second_user_id,
        {"role": "admin", "status": "editor"}
    )

    yield workspace, second_user_id

    # Очистка
    try:
        authenticated_client.delete_workspace(project_id, workspace_id)
    except:
        pass


@pytest.fixture
def created_task(authenticated_client, project_with_owner, created_workspace, sample_task_data) -> Generator[
    Dict[str, Any], None, None]:
    """Создает задачу в рабочем пространстве"""
    project_id = project_with_owner["id"]
    workspace_id = created_workspace["id"]
    task = authenticated_client.create_task(project_id, workspace_id, sample_task_data)
    yield task
    try:
        authenticated_client.delete_task(project_id, workspace_id, task["id"])
    except:
        pass


@pytest.fixture
def task_with_assignee(authenticated_client, project_with_owner, created_workspace, sample_task_with_assignee_data,
                       second_authenticated_client) -> Generator[Dict[str, Any], None, None]:
    """Создает задачу с назначенным исполнителем"""
    project_id = project_with_owner["id"]
    workspace_id = created_workspace["id"]

    # Получаем ID второго пользователя
    second_profile = second_authenticated_client.get_personal_user_profile()
    assignee_id = second_profile["user_id"]

    task_data = sample_task_with_assignee_data.copy()
    task_data["assignees"] = [assignee_id]

    task = authenticated_client.create_task(project_id, workspace_id, task_data)
    yield task, assignee_id

    try:
        authenticated_client.delete_task(project_id, workspace_id, task["id"])
    except:
        pass


@pytest.fixture
def project_roles() -> List[str]:
    """Все возможные роли в проекте из openapi"""
    return [
        "seo", "developer", "designer", "project_manager",
        "content_manager", "marketer", "analyst", "tester",
        "devops", "other"
    ]


@pytest.fixture
def participant_statuses() -> List[str]:
    """Все возможные статусы/уровни доступа участников"""
    return ["owner", "admin", "editor", "viewer"]


@pytest.fixture
def invitation_statuses() -> List[str]:
    """Все возможные статусы приглашений"""
    return ["pending", "accepted", "rejected"]


# ========== Фикстуры для нескольких пользователей ==========

@pytest.fixture(scope="session")
def third_authenticated_client():
    """Фикстура для третьего аутентифицированного клиента"""
    try:
        from .config import THIRD_TEST_EMAIL, THIRD_TEST_PASSWORD
        if not THIRD_TEST_EMAIL or not THIRD_TEST_PASSWORD:
            pytest.skip("Третий пользователь не настроен")

        client = ExtendedAPIClient()
        client.login(email=THIRD_TEST_EMAIL, password=THIRD_TEST_PASSWORD)
        yield client
        client.cleanup()
    except (ImportError, AttributeError, Exception) as e:
        pytest.skip(f"Третий пользователь не настроен: {e}")


@pytest.fixture
def multiple_users(
        authenticated_client,
        second_authenticated_client,
        third_authenticated_client
) -> List[ExtendedAPIClient]:
    """Фикстура для работы с несколькими пользователями"""
    return [
        authenticated_client,
        second_authenticated_client,
        third_authenticated_client
    ]


@pytest.fixture
def multiple_user_ids(
        authenticated_client,
        second_authenticated_client,
        third_authenticated_client
) -> List[int]:
    """Фикстура для получения ID нескольких пользователей"""
    ids = []
    for client in [authenticated_client, second_authenticated_client, third_authenticated_client]:
        profile = client.get_personal_user_profile()
        ids.append(profile["user_id"])
    return ids


# ========== Фикстуры для чатов ==========

@pytest.fixture
def sample_chat_data() -> Dict[str, Any]:
    """Данные для создания чата"""
    return {
        "data": {
            "name": f"Test Chat {uuid.uuid4().hex[:8]}",
            "type": "group"
        },
        "members": []
    }


@pytest.fixture
def sample_private_chat_data() -> Dict[str, Any]:
    """Данные для создания приватного чата"""
    return {
        "data": {
            "name": f"Private Chat {uuid.uuid4().hex[:8]}",
            "type": "private"
        },
        "members": [4]
    }


@pytest.fixture
def sample_message_data() -> Dict[str, Any]:
    """Данные для отправки сообщения"""
    return {
        "chat_id": "",
        "content": f"Test message {uuid.uuid4().hex[:8]}",
        "message_type": "text"
    }


@pytest.fixture
def sample_reply_data() -> Dict[str, Any]:
    """Данные для ответа на сообщение"""
    return {
        "chat_id": "",
        "content": f"Test reply {uuid.uuid4().hex[:8]}",
        "message_type": "text",
        "reply_to_message_id": None
    }


@pytest.fixture
def created_chat(authenticated_client: ExtendedAPIClient, sample_chat_data) -> Generator[Dict[str, Any], None, None]:
    """Создает чат"""
    chat = authenticated_client.create_chat(sample_chat_data)
    yield chat


@pytest.fixture
def chat_with_messages(authenticated_client: ExtendedAPIClient, created_chat, sample_message_data) -> List[
    Dict[str, Any]]:
    """Создает чат с несколькими сообщениями"""
    chat_id = created_chat["id"]
    messages = []

    for i in range(3):
        msg_data = sample_message_data.copy()
        msg_data["chat_id"] = chat_id
        msg_data["content"] = f"Test message {i + 1}"
        message = authenticated_client.send_text_message(chat_id, msg_data)
        messages.append(message)

    return messages


# ========== Фикстуры для каналов ==========

@pytest.fixture
def sample_channel_data(project_with_owner) -> Dict[str, Any]:
    """Данные для создания канала в существующем проекте"""
    return {
        "name": f"Test Channel {uuid.uuid4().hex[:8]}",
        "description": "Test channel description",
        "project_id": project_with_owner["id"],
    }


@pytest.fixture
def created_channel(
        authenticated_client: ExtendedAPIClient,
        project_with_owner,
        sample_channel_data
) -> Generator[Dict[str, Any], None, None]:
    """Создает канал в проекте и удаляет его после теста"""
    channel = authenticated_client.create_channel(sample_channel_data)
    yield channel
    try:
        authenticated_client.delete_channel(channel["id"])
    except:
        pass


# ========== Фикстуры для очистки после тестов ==========

@pytest.fixture
def cleanup_project_participants(authenticated_client):
    """Фикстура для очистки участников проекта после теста"""
    participants_to_remove = []

    def _add_to_cleanup(project_id: str, user_ids: List[int]):
        participants_to_remove.append((project_id, user_ids))

    yield _add_to_cleanup

    for project_id, user_ids in participants_to_remove:
        for user_id in user_ids:
            try:
                authenticated_client.remove_project_participant(project_id, user_id)
            except:
                pass


@pytest.fixture
def cleanup_workspace_participants(authenticated_client):
    """Фикстура для очистки участников workspace после теста"""
    participants_to_remove = []

    def _add_to_cleanup(project_id: str, workspace_id: str, user_ids: List[int]):
        participants_to_remove.append((project_id, workspace_id, user_ids))

    yield _add_to_cleanup

    for project_id, workspace_id, user_ids in participants_to_remove:
        try:
            authenticated_client.remove_workspace_participants(
                project_id, workspace_id, user_ids
            )
        except:
            pass


@pytest.fixture
def sample_published_project(authenticated_client, sample_project_data):
    """Создает и публикует проект для тестов"""
    project = authenticated_client.create_project(sample_project_data)
    project_id = project["id"]

    if os.path.exists(TEST_PROJECT_FILE_PATH):
        file_data = authenticated_client.upload_project_file(
            project_id=project_id,
            workspace_id=project["workspaces"][0]["id"],  # workspace_id стал обязательным
            file_path=TEST_PROJECT_FILE_PATH,
            description="Test media for published project"
        )
        authenticated_client.publish_project(project_id, [file_data["id"]])
    else:
        authenticated_client.publish_project(project_id, [])

    yield project

    try:
        authenticated_client.delete_project(project_id)
    except:
        pass


@pytest.fixture
def sample_comment(authenticated_client, sample_published_project):
    """Создает комментарий к опубликованному проекту"""
    project_id = sample_published_project["id"]
    comment = authenticated_client.create_comment(
        project_id,
        "Тестовый комментарий для фикстуры"
    )
    yield comment
    try:
        authenticated_client.delete_comment(comment["id"])
    except:
        pass