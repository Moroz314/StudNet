import os
import uuid
import pytest
from datetime import datetime, timedelta
from .fixtures import *
from .config import TEST_PROJECT_FILE_PATH


class TestProjectPublishFlow:
    """Тесты для полного flow: создание -> загрузка файлов -> публикация -> лайки -> комментарии"""

    def test_complete_publish_flow(self, authenticated_client, sample_project_data):
        """Полный тест flow публикации проекта"""
        print("\n=== Запуск теста публикации проекта ===\n")

        # 1. Создаем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]
        workspace_id = project["workspaces"][0]["id"]  # Основной workspace
        print(f"✓ Создан проект: {project['name']} (ID: {project_id})")
        assert project["status"] == "active"

        # 2. Загружаем файлы через универсальный эндпоинт /files/upload
        media_file_ids = []
        if os.path.exists(TEST_PROJECT_FILE_PATH):
            # Загружаем первый файл (без кириллицы в metadata)
            file1 = authenticated_client.upload_file(
                file_path=TEST_PROJECT_FILE_PATH,
                file_type="project_post_file",
                metadata={"description": "Main project file"}
            )
            file1_id = file1["file_id"]
            media_file_ids.append(file1_id)
            print(f"✓ Загружен файл 1: {file1_id}")

            # Загружаем второй файл
            file2 = authenticated_client.upload_file(
                file_path=TEST_PROJECT_FILE_PATH,
                file_type="project_post_file",
                metadata={"description": "Additional file"}
            )
            file2_id = file2["file_id"]
            media_file_ids.append(file2_id)
            print(f"✓ Загружен файл 2: {file2_id}")
        else:
            pytest.skip("Test file not found")

        # 3. Публикуем проект с медиафайлами
        published_post = authenticated_client.publish_project(
            project_id=project_id,
            media_file_ids=media_file_ids,
            description="Post description for publication",
            github_links=["https://github.com/test/repo"]
        )

        assert published_post["project_id"] == project_id
        assert "published_at" in published_post
        assert published_post["published_at"] is not None
        assert len(published_post["media_files"]) == 2
        print(f"✓ Проект опубликован в ленте (post_id: {published_post['id']})")

        # 4. Проверяем, что пост появился в ленте
        feed = authenticated_client.get_feed(limit=20, offset=0)
        assert feed["total"] >= 1
        feed_post_ids = [p["id"] for p in feed["items"]]
        assert published_post["id"] in feed_post_ids
        print(f"✓ Пост отображается в ленте")

        # 5. Проверяем детали поста через проект
        post_detail = authenticated_client.get_post_by_project(project_id)
        assert post_detail["id"] == published_post["id"]
        assert post_detail["is_liked_by_user"] is False
        assert post_detail["likes_count"] == 0
        assert len(post_detail["media_files"]) == 2
        print(f"✓ Детали поста загружены")

        # 6. Ставим лайк посту
        like_response = authenticated_client.like_post(published_post["id"])
        assert like_response["post_id"] == published_post["id"]
        assert like_response["is_liked"] is True
        assert like_response["likes_count"] == 1
        print(f"✓ Поставлен лайк посту")

        # 7. Проверяем, что лайк отображается
        post_detail_after_like = authenticated_client.get_post_by_project(project_id)
        assert post_detail_after_like["is_liked_by_user"] is True
        assert post_detail_after_like["likes_count"] == 1
        print(f"✓ Лайк подтвержден")

        # 8. Добавляем комментарий к посту
        comment_content = "Great project! Very interesting idea."
        comment_response = authenticated_client.create_comment(
            published_post["id"],
            comment_content
        )

        assert comment_response["id"] is not None
        assert comment_response["post_id"] == published_post["id"]
        assert comment_response["content"] == comment_content
        assert comment_response["user"]["user_id"] == authenticated_client.user_id
        assert comment_response["likes_count"] == 0
        print(f"✓ Добавлен комментарий")

        # 9. Проверяем, что комментарий появился в списке
        comments = authenticated_client.get_post_comments(published_post["id"], limit=20)
        assert comments["total"] >= 1
        assert any(c["id"] == comment_response["id"] for c in comments["items"])
        print(f"✓ Комментарий отображается в списке")

        # 10. Добавляем ответ на комментарий
        reply_content = "Thank you! Glad you liked it."
        reply_response = authenticated_client.create_comment(
            published_post["id"],
            reply_content,
            parent_id=comment_response["id"]
        )

        assert reply_response["parent_id"] == comment_response["id"]
        print(f"✓ Добавлен ответ на комментарий")

        # 11. Ставим лайк на комментарий
        like_comment_response = authenticated_client.like_comment(comment_response["id"])
        assert like_comment_response["comment_id"] == comment_response["id"]
        assert like_comment_response["is_liked"] is True
        assert like_comment_response["likes_count"] == 1
        print(f"✓ Поставлен лайк на комментарий")

        # 12. Убираем лайк с комментария
        unlike_comment_response = authenticated_client.unlike_comment(comment_response["id"])
        assert unlike_comment_response["comment_id"] == comment_response["id"]
        assert unlike_comment_response["is_liked"] is False
        assert unlike_comment_response["likes_count"] == 0
        print(f"✓ Убран лайк с комментария")

        # 13. Убираем лайк с поста
        unlike_response = authenticated_client.unlike_post(published_post["id"])
        assert unlike_response["post_id"] == published_post["id"]
        assert unlike_response["is_liked"] is False
        assert unlike_response["likes_count"] == 0
        print(f"✓ Убран лайк с поста")

        # 14. Редактируем комментарий
        updated_content = "Great project! Very interesting idea. Looking forward to updates!"
        updated_comment = authenticated_client.update_comment(comment_response["id"], updated_content)
        assert updated_comment["id"] == comment_response["id"]
        assert updated_comment["content"] == updated_content
        assert updated_comment["is_edited"] is True
        print(f"✓ Комментарий отредактирован")

        # 15. Удаляем комментарий
        authenticated_client.delete_comment(comment_response["id"])

        # Проверяем, что комментарий удален
        comments_after = authenticated_client.get_post_comments(published_post["id"], limit=20)
        assert not any(c["id"] == comment_response["id"] for c in comments_after["items"])
        print(f"✓ Комментарий удален")

        # 16. Обновляем пост
        updated_post = authenticated_client.update_post(
            project_id=project_id,
            description="Updated post description",
            media_file_ids=[]  # Убираем все медиафайлы
        )
        assert updated_post["description"] == "Updated post description"
        assert len(updated_post["media_files"]) == 0
        print(f"✓ Пост обновлен")

        # 17. Снимаем проект с публикации
        unpublish_result = authenticated_client.unpublish_project(project_id)
        assert unpublish_result["message"] == "Project unpublished successfully"
        print(f"✓ Проект снят с публикации")

        # 18. Проверяем, что пост больше не в ленте
        feed_after = authenticated_client.get_feed(limit=20, offset=0)
        feed_post_ids_after = [p["id"] for p in feed_after["items"]]
        assert published_post["id"] not in feed_post_ids_after
        print(f"✓ Пост больше не отображается в ленте")

        # 19. Очистка: удаляем проект
        authenticated_client.delete_project(project_id)
        print(f"✓ Проект удален")

        print("\n=== Полный flow публикации успешно завершен ===\n")

    def test_publish_project_without_media(self, authenticated_client, sample_project_data):
        """Тест публикации проекта без медиа-файлов"""
        # 1. Создаем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]
        print(f"✓ Создан проект: {project_id}")

        # 2. Публикуем без медиа-файлов
        published_post = authenticated_client.publish_project(
            project_id=project_id,
            media_file_ids=[],
            description="Post without media"
        )

        assert published_post["project_id"] == project_id
        assert "media_files" in published_post
        assert published_post["media_files"] == []
        print(f"✓ Проект опубликован без медиа-файлов")

        # Очистка
        authenticated_client.delete_project(project_id)

    def test_publish_project_with_update(self, authenticated_client, sample_project_data):
        """Тест публикации и последующего обновления поста"""
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]
        print(f"✓ Создан проект: {project_id}")

        # 1. Публикуем с одним файлом
        media_file_ids = []
        if os.path.exists(TEST_PROJECT_FILE_PATH):
            file1 = authenticated_client.upload_file(
                file_path=TEST_PROJECT_FILE_PATH,
                file_type="project_post_file",
                metadata={"description": "First file"}
            )
            media_file_ids = [file1["file_id"]]

        published = authenticated_client.publish_project(
            project_id=project_id,
            media_file_ids=media_file_ids,
            description="First version of post"
        )
        assert len(published["media_files"]) == len(media_file_ids)
        print(f"✓ Пост опубликован")

        # 2. Обновляем пост - добавляем еще файлы
        if os.path.exists(TEST_PROJECT_FILE_PATH):
            file2 = authenticated_client.upload_file(
                file_path=TEST_PROJECT_FILE_PATH,
                file_type="project_post_file",
                metadata={"description": "Second file"}
            )
            file3 = authenticated_client.upload_file(
                file_path=TEST_PROJECT_FILE_PATH,
                file_type="project_post_file",
                metadata={"description": "Third file"}
            )
            new_media_ids = [file2["file_id"], file3["file_id"]]

            updated = authenticated_client.update_post(
                project_id=project_id,
                description="Updated version of post",
                media_file_ids=new_media_ids
            )
            assert updated["description"] == "Updated version of post"
            assert len(updated["media_files"]) == 2
            print(f"✓ Пост обновлен с новыми файлами")

        # Очистка
        authenticated_client.delete_project(project_id)

    def test_multiple_likes_from_different_users(
            self,
            authenticated_client,
            second_authenticated_client,
            sample_project_data
    ):
        """Тест лайков от разных пользователей"""
        # 1. Создаем и публикуем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]

        media_file_ids = []
        if os.path.exists(TEST_PROJECT_FILE_PATH):
            file_data = authenticated_client.upload_file(
                file_path=TEST_PROJECT_FILE_PATH,
                file_type="project_post_file"
            )
            media_file_ids = [file_data["file_id"]]

        published_post = authenticated_client.publish_project(project_id, media_file_ids)
        post_id = published_post["id"]
        print(f"✓ Пост опубликован: {post_id}")

        # 2. Первый пользователь ставит лайк
        authenticated_client.like_post(post_id)
        post_detail = authenticated_client.get_post_by_project(project_id)
        assert post_detail["likes_count"] == 1
        print(f"✓ Первый лайк")

        # 3. Второй пользователь ставит лайк
        second_authenticated_client.like_post(post_id)

        # Проверяем от лица первого
        post_detail = authenticated_client.get_post_by_project(project_id)
        assert post_detail["likes_count"] == 2
        print(f"✓ Второй лайк от другого пользователя")

        # 4. Второй пользователь убирает лайк
        second_authenticated_client.unlike_post(post_id)

        post_detail = authenticated_client.get_post_by_project(project_id)
        assert post_detail["likes_count"] == 1
        print(f"✓ Лайк убран")

        # Очистка
        authenticated_client.delete_project(project_id)

    def test_comments_hierarchy(self, authenticated_client, sample_project_data):
        """Тест иерархии комментариев"""
        # 1. Создаем и публикуем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]

        media_file_ids = []
        if os.path.exists(TEST_PROJECT_FILE_PATH):
            file_data = authenticated_client.upload_file(
                file_path=TEST_PROJECT_FILE_PATH,
                file_type="project_post_file"
            )
            media_file_ids = [file_data["file_id"]]

        published_post = authenticated_client.publish_project(project_id, media_file_ids)
        post_id = published_post["id"]
        print(f"✓ Пост опубликован: {post_id}")

        # 2. Создаем корневой комментарий
        root_comment = authenticated_client.create_comment(
            post_id,
            "Root comment"
        )
        root_id = root_comment["id"]
        print(f"✓ Создан корневой комментарий ID: {root_id}")

        # 3. Создаем ответы на корневой комментарий
        replies = []
        for i in range(3):
            reply = authenticated_client.create_comment(
                post_id,
                f"Reply {i + 1}",
                parent_id=root_id
            )
            replies.append(reply)
            print(f"✓ Создан ответ {i + 1}: ID {reply['id']}")

        # 4. Проверяем, что все ответы имеют правильный parent_id
        for reply in replies:
            assert reply["parent_id"] == root_id

        # 5. Получаем ответы на корневой комментарий
        comments_response = authenticated_client.get_post_comments(
            post_id,
            parent_id=root_id,
            limit=20
        )

        assert comments_response["total"] >= 3
        reply_ids = [c["id"] for c in comments_response["items"]]
        for reply in replies:
            assert reply["id"] in reply_ids
        print(f"✓ Все ответы получены через parent_id фильтр")

        # 6. Создаем ответ на ответ (второй уровень)
        deep_reply = authenticated_client.create_comment(
            post_id,
            "Reply to reply",
            parent_id=replies[0]["id"]
        )
        assert deep_reply["parent_id"] == replies[0]["id"]
        print(f"✓ Создан вложенный комментарий")

        # 7. Проверяем, что при получении корневых комментариев replies_count корректный
        root_comments = authenticated_client.get_post_comments(
            post_id,
            parent_id=None,
            limit=20
        )
        root_comment_from_list = next(
            c for c in root_comments["items"] if c["id"] == root_id
        )
        assert root_comment_from_list["replies_count"] >= 3
        print(f"✓ replies_count корректно отображает количество ответов")

        # Очистка
        authenticated_client.delete_project(project_id)

    def test_publish_with_different_file_types(self, authenticated_client, sample_project_data):
        """Тест публикации с разными типами файлов"""
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]

        media_file_ids = []

        if os.path.exists(TEST_PROJECT_FILE_PATH):
            # Загружаем файл
            file1 = authenticated_client.upload_file(
                file_path=TEST_PROJECT_FILE_PATH,
                file_type="project_post_file",
                metadata={"description": "Image for post"}
            )
            media_file_ids.append(file1["file_id"])

        published = authenticated_client.publish_project(
            project_id=project_id,
            media_file_ids=media_file_ids,
            description="Post with different file types"
        )

        assert published["project_id"] == project_id
        assert len(published["media_files"]) == len(media_file_ids)

        # Проверяем, что у всех файлов есть URL
        for media_file in published["media_files"]:
            assert "url" in media_file
            assert media_file["url"] is not None

        print(f"✓ Пост опубликован с {len(media_file_ids)} файлами")

        # Очистка
        authenticated_client.delete_project(project_id)