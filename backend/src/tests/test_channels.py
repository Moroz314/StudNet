import pytest
import uuid
from typing import Dict, Any
from .clients.extended import ExtendedAPIClient
from .fixtures import *

class TestChannels:
    """Тесты для работы с каналами (только админы/владельцы проекта могут создавать и публиковать)"""

    def test_create_channel_as_owner(
            self,
            authenticated_client: ExtendedAPIClient,
            project_with_owner,
    ):
        """Тест: владелец проекта может создать канал"""
        channel_data = {
            "name": f"Owner Channel {uuid.uuid4().hex[:8]}",
            "description": "Channel created by owner",
            "project_id": project_with_owner["id"],
        }

        channel = authenticated_client.create_channel(channel_data)

        assert channel["id"] is not None
        assert channel["name"] == channel_data["name"]
        assert channel["description"] == channel_data["description"]
        assert channel["project_id"] == project_with_owner["id"]
        assert channel["created_by"] == authenticated_client.user_id

    def test_create_channel_as_admin(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner
    ):
        """Тест: администратор проекта может создать канал"""
        # Отправляем приглашение с уровнем доступа admin
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "admin",
            "message": "Join as admin"
        }

        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        invitation_id = invitations[0]["id"]

        # Второй пользователь принимает приглашение и становится админом
        second_authenticated_client.respond_to_invitation(invitation_id, "accept")

        # Админ создает канал
        channel_data = {
            "name": f"Admin Channel {uuid.uuid4().hex[:8]}",
            "description": "Channel created by admin",
            "project_id": project_with_owner["id"],
        }

        channel = second_authenticated_client.create_channel(channel_data)

        assert channel["id"] is not None
        assert channel["name"] == channel_data["name"]
        assert channel["created_by"] == second_authenticated_client.user_id
        assert channel["project_id"] == project_with_owner["id"]

    def test_create_channel_as_regular_participant(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner
    ):
        """Тест: обычный участник НЕ может создать канал"""
        # Отправляем приглашение с уровнем доступа editor
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Join as editor"
        }

        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        invitation_id = invitations[0]["id"]

        # Второй пользователь принимает приглашение
        second_authenticated_client.respond_to_invitation(invitation_id, "accept")

        # Пытаемся создать канал как обычный участник
        channel_data = {
            "name": "Unauthorized Channel",
            "description": "Should fail",
            "project_id": project_with_owner["id"],
        }

        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.create_channel(channel_data)
        assert "failed" in str(exc_info.value)

    def test_create_channel_non_participant(
            self,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner
    ):
        """Тест: пользователь не участвующий в проекте НЕ может создать канал"""
        channel_data = {
            "name": "Unauthorized Channel",
            "description": "Should fail",
            "project_id": project_with_owner["id"],
        }

        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.create_channel(channel_data)
        assert "failed" in str(exc_info.value)

    def test_create_duplicate_channel_for_project(
            self,
            authenticated_client: ExtendedAPIClient,
            project_with_owner
    ):
        """Тест: нельзя создать второй канал для одного проекта"""
        # Создаем первый канал
        channel_data1 = {
            "name": "First Channel",
            "description": "First channel",
            "project_id": project_with_owner["id"],
        }
        authenticated_client.create_channel(channel_data1)

        # Пытаемся создать второй
        channel_data2 = {
            "name": "Second Channel",
            "description": "Should fail",
            "project_id": project_with_owner["id"],
        }

        with pytest.raises(AssertionError) as exc_info:
            authenticated_client.create_channel(channel_data2)
        assert "failed" in str(exc_info.value)

    def test_get_channel(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: любой участник проекта может просматривать канал"""
        channel_id = created_channel["id"]

        # Владелец может просматривать
        channel = authenticated_client.get_channel(channel_id)
        assert channel["id"] == channel_id
        assert channel["project_id"] == project_with_owner["id"]

        # Добавляем второго пользователя как участника
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Join my project"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # Второй пользователь тоже может просматривать
        channel_from_second = second_authenticated_client.get_channel(channel_id)
        assert channel_from_second["id"] == channel_id

    def test_get_project_channel(
            self,
            authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест получения канала по ID проекта"""
        project_channel = authenticated_client.get_project_channel(project_with_owner["id"])

        assert project_channel is not None
        assert project_channel["id"] == created_channel["id"]
        assert project_channel["project_id"] == project_with_owner["id"]

    def test_update_channel_as_owner(
            self,
            authenticated_client: ExtendedAPIClient,
            created_channel
    ):
        """Тест: владелец может обновлять канал"""
        update_data = {
            "name": "Updated Channel Name",
            "description": "Updated description"
        }

        updated_channel = authenticated_client.update_channel(created_channel["id"], update_data)

        assert updated_channel["id"] == created_channel["id"]
        assert updated_channel["name"] == update_data["name"]
        assert updated_channel["description"] == update_data["description"]

    def test_update_channel_as_admin(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: администратор может обновлять канал"""
        # Добавляем второго пользователя как админа
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "admin",
            "message": "Join as admin"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # Админ обновляет канал
        update_data = {
            "name": "Updated by Admin",
            "description": "Admin update"
        }

        updated_channel = second_authenticated_client.update_channel(created_channel["id"], update_data)
        assert updated_channel["name"] == update_data["name"]
        assert updated_channel["id"] == created_channel["id"]

    def test_update_channel_as_regular_participant(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: обычный участник НЕ может обновлять канал"""
        # Добавляем второго пользователя как обычного участника
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Join as editor"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # Пытаемся обновить канал
        update_data = {"name": "Should Fail"}

        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.update_channel(created_channel["id"], update_data)
        assert "failed" in str(exc_info.value)

    def test_subscribe_to_channel(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: любой участник проекта может подписаться на канал"""
        channel_id = created_channel["id"]

        # Добавляем второго пользователя как участника
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Join my project"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # Подписываемся
        subscription = second_authenticated_client.subscribe_to_channel(channel_id)

        assert subscription["channel_id"] == channel_id
        assert subscription["user_id"] == second_authenticated_client.user_id

        # Проверяем, что подписчик появился
        channel = authenticated_client.get_channel(channel_id)
        subscriber_ids = [s["user_id"] for s in channel["subscribers"]]
        assert second_authenticated_client.user_id in subscriber_ids

    def test_unsubscribe_from_channel(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: подписчик может отписаться от канала"""
        channel_id = created_channel["id"]

        # Добавляем участника и подписываем
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Join my project"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")
        second_authenticated_client.subscribe_to_channel(channel_id)

        # Отписываемся
        second_authenticated_client.unsubscribe_from_channel(channel_id)

        # Проверяем, что подписчик удален
        channel = authenticated_client.get_channel(channel_id)
        subscriber_ids = [s["user_id"] for s in channel["subscribers"]]
        assert second_authenticated_client.user_id not in subscriber_ids

    def test_owner_cannot_unsubscribe(
            self,
            authenticated_client: ExtendedAPIClient,
            created_channel
    ):
        """Тест: владелец канала не может отписаться"""
        with pytest.raises(AssertionError) as exc_info:
            authenticated_client.unsubscribe_from_channel(created_channel["id"])
        assert "failed" in str(exc_info.value)

    # ========== ИЗМЕНЕННЫЕ ТЕСТЫ ДЛЯ ОТПРАВКИ СООБЩЕНИЙ ==========

    def test_owner_can_send_message_to_channel(
            self,
            authenticated_client: ExtendedAPIClient,
            created_channel
    ):
        """Тест: владелец проекта может отправлять сообщения в канал"""
        channel_id = created_channel["id"]
        content = "Message from owner"

        message = authenticated_client.send_text_message_to_channel(channel_id, content)

        assert message["channel_id"] == channel_id
        assert message["user_id"] == authenticated_client.user_id
        assert message["content"] == content
        assert message["message_type"] == "text"

    def test_admin_can_send_message_to_channel(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: администратор проекта может отправлять сообщения в канал"""
        channel_id = created_channel["id"]

        # Добавляем второго пользователя как админа
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "admin",
            "message": "Join as admin"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # Админ может подписаться (опционально) и отправить сообщение
        second_authenticated_client.subscribe_to_channel(channel_id)

        content = "Message from admin"
        message = second_authenticated_client.send_text_message_to_channel(channel_id, content)

        assert message["channel_id"] == channel_id
        assert message["user_id"] == second_authenticated_client.user_id
        assert message["content"] == content

    def test_regular_participant_cannot_send_message(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: обычный участник НЕ может отправлять сообщения (только админы/владельцы)"""
        channel_id = created_channel["id"]

        # Добавляем второго пользователя как обычного участника (editor)
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Join as editor"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # Участник может подписаться, но не может отправлять сообщения
        second_authenticated_client.subscribe_to_channel(channel_id)

        # Пытаемся отправить сообщение
        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.send_text_message_to_channel(
                channel_id,
                "Should fail"
            )
        assert "failed" in str(exc_info.value)

    def test_non_participant_cannot_send_message(
            self,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: пользователь не участвующий в проекте не может отправлять сообщения"""
        channel_id = created_channel["id"]

        # Не добавляем пользователя в проект, просто пытаемся отправить сообщение
        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.send_text_message_to_channel(
                channel_id,
                "Should fail"
            )
        assert "failed" in str(exc_info.value)

    def test_subscriber_without_admin_rights_cannot_send_message(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: подписчик без прав админа/владельца не может отправлять сообщения"""
        channel_id = created_channel["id"]

        # Добавляем второго пользователя как обычного участника (viewer)
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "viewer",  # Самый низкий уровень доступа
            "message": "Join as viewer"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # Подписываемся на канал
        second_authenticated_client.subscribe_to_channel(channel_id)

        # Пытаемся отправить сообщение
        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.send_text_message_to_channel(
                channel_id,
                "Should fail"
            )
        assert "failed" in str(exc_info.value)

    def test_like_message_as_participant(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner,
            created_channel
    ):
        """Тест: любой участник может ставить лайки (лайки не требуют прав админа)"""
        channel_id = created_channel["id"]

        # Владелец отправляет сообщение
        content = "Message to like"
        message = authenticated_client.send_text_message_to_channel(channel_id, content)
        message_id = message["id"]

        # Добавляем второго пользователя как обычного участника
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "editor",
            "message": "Join as editor"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")
        second_authenticated_client.subscribe_to_channel(channel_id)

        # Участник ставит лайк
        second_authenticated_client.like_channel_message(channel_id, message_id)

        # Проверяем лайк
        messages = authenticated_client.get_channel_messages(channel_id)
        liked_message = next(m for m in messages["messages"] if m["id"] == message_id)
        assert liked_message["likes_count"] == 1

    def test_delete_channel_as_owner(
            self,
            authenticated_client: ExtendedAPIClient,
            project_with_owner
    ):
        """Тест: только владелец может удалить канал"""
        # Создаем канал
        channel_data = {
            "name": "Channel to Delete",
            "project_id": project_with_owner["id"],
        }
        channel = authenticated_client.create_channel(channel_data)

        # Удаляем как владелец
        authenticated_client.delete_channel(channel["id"])

        # Проверяем, что канал удален
        with pytest.raises(AssertionError):
            authenticated_client.get_channel(channel["id"])

    def test_delete_channel_as_admin(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner
    ):
        """Тест: администратор НЕ может удалить канал"""
        # Создаем канал как владелец
        channel_data = {
            "name": "Channel to Delete",
            "project_id": project_with_owner["id"],
        }
        channel = authenticated_client.create_channel(channel_data)

        # Добавляем админа
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "admin",
            "message": "Join as admin"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # Пытаемся удалить как админ
        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.delete_channel(channel["id"])
        assert "failed" in str(exc_info.value)

    def test_channel_lifecycle(
            self,
            authenticated_client: ExtendedAPIClient,
            second_authenticated_client: ExtendedAPIClient,
            project_with_owner
    ):
        """Тест полного жизненного цикла канала"""
        # 1. Владелец создает канал
        channel_data = {
            "name": "Lifecycle Channel",
            "description": "Testing lifecycle",
            "project_id": project_with_owner["id"],
        }
        channel = authenticated_client.create_channel(channel_data)
        channel_id = channel["id"]

        # 2. Добавляем админа
        invitation_data = {
            "user_ids": [second_authenticated_client.user_id],
            "role": "developer",
            "permission_level": "admin",
            "message": "Join as admin"
        }
        invitations = authenticated_client.create_invitations(
            project_with_owner["id"],
            invitation_data
        )
        second_authenticated_client.respond_to_invitation(invitations[0]["id"], "accept")

        # 3. Админ подписывается
        second_authenticated_client.subscribe_to_channel(channel_id)

        # 4. Админ отправляет сообщение (теперь это разрешено)
        message = second_authenticated_client.send_text_message_to_channel(
            channel_id,
            "Hello from admin"
        )
        assert message["id"] is not None

        # 5. Владелец ставит лайк
        authenticated_client.like_channel_message(channel_id, message["id"])

        # 6. Проверяем лайк
        messages = authenticated_client.get_channel_messages(channel_id)
        liked_message = next(m for m in messages["messages"] if m["id"] == message["id"])
        assert liked_message["likes_count"] == 1

        # 7. Админ отписывается
        second_authenticated_client.unsubscribe_from_channel(channel_id)

        # 8. Владелец удаляет канал
        authenticated_client.delete_channel(channel_id)

        # 9. Проверяем, что канал удален
        with pytest.raises(AssertionError):
            authenticated_client.get_channel(channel_id)