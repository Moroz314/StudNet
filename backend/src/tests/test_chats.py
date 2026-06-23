import pytest
from typing import List, Dict, Any
from .clients.extended import ExtendedAPIClient
from .fixtures import *

class TestChats:
    """Тесты для работы с чатами"""

    def test_create_group_chat(self, authenticated_client: ExtendedAPIClient, sample_chat_data):
        """Тест создания группового чата"""
        chat = authenticated_client.create_chat(sample_chat_data)

        assert chat["id"] is not None
        assert chat["name"] == sample_chat_data["data"]["name"]
        assert chat["type"] == "group"
        assert chat["created_by"] == authenticated_client.user_id
        assert "created_at" in chat
        assert "participants_count" in chat

    def test_create_private_chat(self, authenticated_client: ExtendedAPIClient, sample_private_chat_data):
        """Тест создания приватного чата"""
        chat = authenticated_client.create_chat(sample_private_chat_data)

        assert chat["id"] is not None
        assert chat["type"] == "private"
        assert chat["participants_count"] == 2  # Только создатель

    def test_get_user_chats(self, authenticated_client: ExtendedAPIClient, created_chat):
        """Тест получения списка чатов пользователя"""
        chats = authenticated_client.get_user_chats()

        assert isinstance(chats, list)
        assert len(chats) > 0

        # Проверяем, что созданный чат есть в списке
        chat_ids = [chat["id"] for chat in chats]
        assert created_chat["id"] in chat_ids

    def test_get_chat_info(self, authenticated_client: ExtendedAPIClient, created_chat):
        """Тест получения информации о чате"""
        chat_info = authenticated_client.get_chat(created_chat["id"])

        assert chat_info["id"] == created_chat["id"]
        assert chat_info["name"] == created_chat["name"]
        assert chat_info["type"] == created_chat["type"]

    def test_send_text_message(self, authenticated_client: ExtendedAPIClient, created_chat, sample_message_data):
        """Тест отправки текстового сообщения"""
        chat_id = created_chat["id"]
        message_data = sample_message_data.copy()
        message_data["chat_id"] = chat_id

        message = authenticated_client.send_text_message(chat_id, message_data)

        assert message["id"] is not None
        assert message["chat_id"] == chat_id
        assert message["user_id"] == authenticated_client.user_id
        assert message["content"] == message_data["content"]
        assert message["message_type"] == "text"
        assert message["is_edited"] is False
        assert "created_at" in message

    def test_get_chat_messages(self, authenticated_client: ExtendedAPIClient, created_chat, chat_with_messages):
        """Тест получения сообщений чата"""
        chat_id = created_chat["id"]

        messages = authenticated_client.get_chat_messages(chat_id, limit=10)

        assert isinstance(messages, list)
        assert len(messages) >= 3  # Минимум 3 сообщения из фикстуры

        # Проверяем пагинацию
        messages_page1 = authenticated_client.get_chat_messages(chat_id, limit=2, offset=0)
        assert len(messages_page1) == 2

        messages_page2 = authenticated_client.get_chat_messages(chat_id, limit=2, offset=2)
        assert len(messages_page2) >= 1

    def test_edit_message(self, authenticated_client: ExtendedAPIClient, created_chat, chat_with_messages):
        """Тест редактирования сообщения"""
        chat_id = created_chat["id"]
        original_message = chat_with_messages[0]
        new_content = f"Edited message {uuid.uuid4().hex[:8]}"

        edited_message = authenticated_client.edit_message(chat_id, original_message["id"], new_content)

        assert edited_message["id"] == original_message["id"]
        assert edited_message["content"] == new_content
        assert edited_message["is_edited"] is True

    def test_delete_message(self, authenticated_client: ExtendedAPIClient, created_chat, chat_with_messages):
        """Тест удаления сообщения"""
        chat_id = created_chat["id"]
        message_to_delete = chat_with_messages[0]

        authenticated_client.delete_message(chat_id, message_to_delete["id"])

        # Проверяем, что сообщение удалено
        messages = authenticated_client.get_chat_messages(chat_id)
        message_ids = [msg["id"] for msg in messages]
        assert message_to_delete["id"] not in message_ids

    def test_reply_to_message(self, authenticated_client: ExtendedAPIClient, created_chat, chat_with_messages,
                              sample_reply_data):
        """Тест ответа на сообщение"""
        chat_id = created_chat["id"]
        original_message = chat_with_messages[0]

        reply_data = sample_reply_data.copy()
        reply_data["chat_id"] = chat_id
        reply_data["reply_to_message_id"] = original_message["id"]

        reply = authenticated_client.send_text_message(chat_id, reply_data)

        assert reply["reply_to_message_id"] == original_message["id"]
        assert reply["reply_to"] is not None

        # Получаем ответы на исходное сообщение
        replies = authenticated_client.get_message_replies(chat_id, original_message["id"])
        assert len(replies) > 0
        assert any(r["id"] == reply["id"] for r in replies)

    def test_like_unlike_message(self, authenticated_client: ExtendedAPIClient, created_chat, chat_with_messages):
        """Тест лайков сообщений"""
        chat_id = created_chat["id"]
        message = chat_with_messages[0]

        # Ставим лайк
        authenticated_client.like_message(chat_id, message["id"])

        # Проверяем, что лайк появился
        messages = authenticated_client.get_chat_messages(chat_id)
        updated_message = next(m for m in messages if m["id"] == message["id"])
        assert updated_message["likes_count"] == message["likes_count"] + 1
        assert updated_message["is_liked_by_user"] is True

        # Убираем лайк
        authenticated_client.unlike_message(chat_id, message["id"])

        messages = authenticated_client.get_chat_messages(chat_id)
        updated_message = next(m for m in messages if m["id"] == message["id"])
        assert updated_message["likes_count"] == message["likes_count"]
        assert updated_message["is_liked_by_user"] is False

    def test_mark_as_read(self, authenticated_client: ExtendedAPIClient, created_chat, chat_with_messages):
        """Тест отметки сообщений как прочитанных"""
        chat_id = created_chat["id"]

        # Отмечаем все как прочитанные
        authenticated_client.mark_chat_as_read(chat_id, mark_all=True)

        # Отмечаем конкретное сообщение
        message = chat_with_messages[0]
        authenticated_client.mark_message_as_read(message["id"])

    def test_forward_messages(self, authenticated_client: ExtendedAPIClient, second_authenticated_client, created_chat,
                              chat_with_messages):
        """Тест пересылки сообщений"""
        chat_id = created_chat["id"]

        # Создаем еще один чат для пересылки
        second_chat_data = {
            "data": {
                "name": "Forward Target Chat",
                "type": "group"
            }
        }
        target_chat = authenticated_client.create_chat(second_chat_data)

        message_ids = [msg["id"] for msg in chat_with_messages[:2]]

        result = authenticated_client.forward_messages(
            chat_id,
            message_ids,
            [target_chat["id"]],
            include_original_info=True
        )

        assert result is not None

        # Проверяем, что сообщения пересланы
        target_messages = authenticated_client.get_chat_messages(target_chat["id"])
        assert len(target_messages) >= 2
        for msg in target_messages:
            assert msg["is_forwarded"] is True
            assert msg["original_message_id"] in message_ids

    def test_search_messages(self, authenticated_client: ExtendedAPIClient, created_chat, chat_with_messages):
        """Тест поиска сообщений"""
        chat_id = created_chat["id"]

        # Ищем сообщение
        search_results = authenticated_client.search_messages(chat_id, "Test message 1")

        assert isinstance(search_results, list)
        assert len(search_results) > 0
        assert "Test message 1" in search_results[0]["content"]

    def test_get_chat_participants(self, authenticated_client: ExtendedAPIClient, created_chat):
        """Тест получения участников чата"""
        chat_id = created_chat["id"]

        participants_data = authenticated_client.get_chat_participants(chat_id)

        assert participants_data["id"] == chat_id
        assert "participants" in participants_data
        assert len(participants_data["participants"]) > 0

        # Проверяем, что создатель есть в участниках
        creator = next(p for p in participants_data["participants"] if p["user_id"] == authenticated_client.user_id)
        assert creator is not None
        assert creator["role"] in ["owner", "admin", "member"]

    def test_send_media_message(self, authenticated_client: ExtendedAPIClient, created_chat):
        """Тест отправки медиа-сообщения"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        chat_id = created_chat["id"]
        caption = f"Media message caption {uuid.uuid4().hex[:8]}"

        message = authenticated_client.send_media_message(
            chat_id=chat_id,
            file_paths=[TEST_PROJECT_FILE_PATH],
            caption=caption
        )

        assert message["id"] is not None
        assert message["chat_id"] == chat_id
        assert message["user_id"] == authenticated_client.user_id
        assert message["content"] == caption
        assert message["message_type"] == "media"
        assert "media_urls" in message
        assert len(message["media_urls"]) == 1

        media = message["media_urls"][0]
        assert "url" in media
        assert "type" in media
        assert "filename" in media
        assert "size" in media
        print(f"✓ Отправлено медиа-сообщение: {message['id']}")

    def test_send_multiple_media_files(self, authenticated_client: ExtendedAPIClient, created_chat):
        """Тест отправки нескольких медиа-файлов в одном сообщении"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        chat_id = created_chat["id"]

        # Создаем несколько тестовых файлов
        test_files = []
        for i in range(3):
            test_path = f"test_media_{i}.txt"
            with open(test_path, "w") as f:
                f.write(f"Test media content {i}")
            test_files.append(test_path)

        try:
            caption = f"Multiple media files {uuid.uuid4().hex[:8]}"
            message = authenticated_client.send_media_message(
                chat_id=chat_id,
                file_paths=test_files,
                caption=caption
            )

            assert message["id"] is not None
            assert message["message_type"] == "media"
            assert len(message["media_urls"]) == 3

            # Проверяем, что все файлы загружены
            for i, media in enumerate(message["media_urls"]):
                assert "url" in media
                assert media["filename"] == os.path.basename(test_files[i])

            print(f"✓ Отправлено сообщение с {len(test_files)} медиа-файлами")

        finally:
            for path in test_files:
                if os.path.exists(path):
                    os.remove(path)

    def test_send_media_message_without_caption(self, authenticated_client: ExtendedAPIClient, created_chat):
        """Тест отправки медиа-сообщения без подписи"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        chat_id = created_chat["id"]

        message = authenticated_client.send_media_message(
            chat_id=chat_id,
            file_paths=[TEST_PROJECT_FILE_PATH]
        )

        assert message["id"] is not None
        assert message["content"] == ""  # Пустая подпись
        assert message["message_type"] == "media"
        assert len(message["media_urls"]) == 1

        print(f"✓ Отправлено медиа-сообщение без подписи")

    def test_send_media_message_as_reply(self, authenticated_client: ExtendedAPIClient,
                                         created_chat, chat_with_messages):
        """Тест отправки медиа-сообщения как ответа на другое сообщение"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        chat_id = created_chat["id"]
        original_message = chat_with_messages[0]

        message = authenticated_client.send_media_message(
            chat_id=chat_id,
            file_paths=[TEST_PROJECT_FILE_PATH],
            caption="Reply with media",
            reply_to_message_id=original_message["id"]
        )

        assert message["id"] is not None
        assert message["reply_to_message_id"] == original_message["id"]
        assert message["message_type"] == "reply"  # В openapi при ответе тип меняется на reply
        assert message["reply_to"] is not None
        assert message["reply_to"]["id"] == original_message["id"]

        print(f"✓ Отправлен медиа-ответ на сообщение")

    def test_get_chat_messages_with_media(self, authenticated_client: ExtendedAPIClient, created_chat):
        """Тест получения сообщений чата с медиа-файлами"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        chat_id = created_chat["id"]

        # Отправляем текстовое и медиа-сообщение
        text_msg = authenticated_client.send_text_message(
            chat_id,
            {"chat_id": chat_id, "content": "Text message"}
        )
        media_msg = authenticated_client.send_media_message(
            chat_id=chat_id,
            file_paths=[TEST_PROJECT_FILE_PATH],
            caption="Media message"
        )

        # Получаем сообщения
        messages = authenticated_client.get_chat_messages(chat_id, limit=10)

        # Находим наши сообщения
        text_found = any(m["id"] == text_msg["id"] for m in messages)
        media_found = any(m["id"] == media_msg["id"] for m in messages)

        assert text_found
        assert media_found

        # Проверяем структуру медиа-сообщения
        retrieved_media = next(m for m in messages if m["id"] == media_msg["id"])
        assert retrieved_media["message_type"] == "media"
        assert "media_urls" in retrieved_media
        assert len(retrieved_media["media_urls"]) == 1

        print(f"✓ Сообщения с медиа корректно возвращаются в списке")

    def test_send_media_message_with_invalid_file(self, authenticated_client: ExtendedAPIClient, created_chat):
        """Тест отправки медиа-сообщения с несуществующим файлом"""
        chat_id = created_chat["id"]
        fake_file_path = "/path/to/nonexistent/file.txt"

        with pytest.raises(FileNotFoundError):
            authenticated_client.send_media_message(
                chat_id=chat_id,
                file_paths=[fake_file_path]
            )

    def test_send_media_message_to_unauthorized_chat(self, second_authenticated_client: ExtendedAPIClient,
                                                     created_chat):
        """Тест: нельзя отправить медиа-сообщение в чат без доступа"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        chat_id = created_chat["id"]

        with pytest.raises(AssertionError) as exc_info:
            second_authenticated_client.send_media_message(
                chat_id=chat_id,
                file_paths=[TEST_PROJECT_FILE_PATH],
                caption="Should fail"
            )
        assert "failed" in str(exc_info.value) or "403" in str(exc_info.value)

        print(f"✓ Нельзя отправить медиа в чужой чат")