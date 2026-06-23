import pytest
import uuid
import os
from .fixtures import *
from .config import TEST_PROJECT_FILE_PATH


class TestProjectFeed:
    """Тесты для ленты постов проектов"""

    def test_get_feed(self, authenticated_client):
        """Тест получения ленты постов"""
        feed = authenticated_client.get_feed(limit=20, offset=0)

        assert "items" in feed
        assert "total" in feed
        assert "limit" in feed
        assert "offset" in feed
        assert "has_next" in feed
        assert isinstance(feed["items"], list)

        if len(feed["items"]) > 0:
            post = feed["items"][0]
            assert "id" in post
            assert "project_id" in post
            assert "name" in post
            assert "likes_count" in post
            assert "is_liked_by_user" in post
            assert "creator" in post
            assert "media_files" in post
            assert "participants_count" in post

        print(f"✓ Получена лента, всего постов: {feed['total']}")

    def test_get_feed_pagination(self, authenticated_client):
        """Тест пагинации в ленте"""
        page1 = authenticated_client.get_feed(limit=5, offset=0)

        if page1["has_next"]:
            page2 = authenticated_client.get_feed(limit=5, offset=5)
            assert len(page2["items"]) <= 5
            page1_ids = [p["id"] for p in page1["items"]]
            page2_ids = [p["id"] for p in page2["items"]]
            assert not any(pid in page2_ids for pid in page1_ids)

        print(f"✓ Пагинация работает корректно")

    def test_get_feed_by_category(self, authenticated_client):
        """Тест фильтрации ленты по категории"""
        feed = authenticated_client.get_feed(limit=10, offset=0, category="technology")
        assert "items" in feed
        print(f"✓ Получена лента по категории 'technology'")

    def test_get_trending_posts(self, authenticated_client):
        """Тест получения трендовых постов"""
        trending = authenticated_client.get_trending_posts(days=7, limit=20)

        assert isinstance(trending, list)

        if len(trending) > 0:
            item = trending[0]
            assert "project" in item
            assert "likes_in_period" in item
            assert "trend_score" in item

            post_data = item["project"]
            assert "id" in post_data
            assert "name" in post_data

        print(f"✓ Получены трендовые посты, количество: {len(trending)}")

    def test_get_recommended_posts(self, authenticated_client):
        """Тест получения рекомендуемых постов"""
        recommended = authenticated_client.get_recommended_posts(limit=20)

        assert "items" in recommended
        assert "total" in recommended
        assert isinstance(recommended["items"], list)

        print(f"✓ Получены рекомендации, всего: {recommended['total']}")

    def test_get_liked_posts(self, authenticated_client, sample_project_data):
        """Тест получения постов, на которые поставлены лайки"""
        # 1. Создаем и публикуем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]

        # Публикуем проект (создаем пост)
        post = authenticated_client.publish_project(project_id, [])
        post_id = post["id"]

        # 2. Ставим лайк
        authenticated_client.like_post(post_id)

        # 3. Получаем понравившиеся посты
        liked = authenticated_client.get_liked_posts(limit=20, offset=0)

        assert "items" in liked
        assert "total" in liked

        liked_ids = [p["id"] for p in liked["items"]]
        assert post_id in liked_ids

        our_post = next(p for p in liked["items"] if p["id"] == post_id)
        assert our_post["is_liked_by_user"] is True

        # Очистка
        authenticated_client.unlike_post(post_id)
        authenticated_client.delete_project(project_id)

        print(f"✓ Получены понравившиеся посты, всего: {liked['total']}")

    def test_get_posts_by_creator(self, authenticated_client, sample_project_data):
        """Тест получения постов по создателю"""
        project_ids = []
        post_ids = []

        for i in range(2):
            project_data = {
                "name": f"Creator Test Project {i} {uuid.uuid4().hex[:8]}",
                "description": "Тестовый проект"
            }
            project = authenticated_client.create_project(project_data)
            project_ids.append(project["id"])

            post = authenticated_client.publish_project(project["id"], [])
            post_ids.append(post["id"])

        creator_id = authenticated_client.user_id
        posts_by_creator = authenticated_client.get_posts_by_creator(
            creator_id, limit=20, offset=0
        )

        assert "items" in posts_by_creator
        returned_ids = [p["id"] for p in posts_by_creator["items"]]
        for post_id in post_ids:
            assert post_id in returned_ids

        for post in posts_by_creator["items"]:
            assert post["creator"]["user_id"] == creator_id

        for pid in project_ids:
            authenticated_client.delete_project(pid)

        print(f"✓ Получены посты создателя {creator_id}")

    def test_get_post_by_project(self, authenticated_client, sample_project_data):
        """Тест получения поста по ID проекта"""
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]

        post = authenticated_client.publish_project(project_id, [])
        post_id = post["id"]

        retrieved_post = authenticated_client.get_post_by_project(project_id)

        assert retrieved_post["id"] == post_id
        assert retrieved_post["project_id"] == project_id
        assert retrieved_post["name"] == sample_project_data["name"]

        authenticated_client.delete_project(project_id)
        print(f"✓ Получен пост по ID проекта {project_id}")

    def test_like_unlike_post(self, authenticated_client, sample_project_data):
        """Тест лайка/анлайка поста"""
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]

        post = authenticated_client.publish_project(project_id, [])
        post_id = post["id"]

        # Лайк
        like_response = authenticated_client.like_post(post_id)
        assert like_response["post_id"] == post_id
        assert like_response["is_liked"] is True
        assert like_response["likes_count"] == 1

        # Анлайк
        unlike_response = authenticated_client.unlike_post(post_id)
        assert unlike_response["post_id"] == post_id
        assert unlike_response["is_liked"] is False
        assert unlike_response["likes_count"] == 0

        authenticated_client.delete_project(project_id)
        print(f"✓ Лайк/анлайк поста работает корректно")

    def test_get_categories(self, authenticated_client):
        """Тест получения категорий"""
        categories = authenticated_client.get_categories()

        assert isinstance(categories, list)

        if len(categories) > 0:
            category = categories[0]
            assert "name" in category
            assert "projects_count" in category

        print(f"✓ Получены категории, всего: {len(categories)}")

    def test_update_post(self, authenticated_client, sample_project_data):
        """Тест обновления существующего поста"""
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]

        post = authenticated_client.publish_project(project_id, [])
        post_id = post["id"]

        updated_description = f"Updated description {uuid.uuid4().hex[:8]}"
        updated_post = authenticated_client.update_post(
            project_id,
            description=updated_description,
            media_file_ids=[]
        )

        assert updated_post["id"] == post_id
        assert updated_post["description"] == updated_description

        authenticated_client.delete_project(project_id)
        print(f"✓ Пост обновлен")

    def test_post_comments(self, authenticated_client, sample_project_data):
        """Тест комментариев к посту"""
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]

        post = authenticated_client.publish_project(project_id, [])
        post_id = post["id"]

        # Создаем комментарий
        comment = authenticated_client.create_comment(post_id, "Тестовый комментарий")
        assert comment["post_id"] == post_id
        assert comment["content"] == "Тестовый комментарий"

        # Получаем комментарии
        comments = authenticated_client.get_post_comments(post_id)
        assert comments["total"] >= 1
        assert any(c["id"] == comment["id"] for c in comments["items"])

        # Лайк комментария
        like_response = authenticated_client.like_comment(comment["id"])
        assert like_response["comment_id"] == comment["id"]
        assert like_response["is_liked"] is True

        # Анлайк комментария
        unlike_response = authenticated_client.unlike_comment(comment["id"])
        assert unlike_response["comment_id"] == comment["id"]
        assert unlike_response["is_liked"] is False

        # Обновляем комментарий
        updated = authenticated_client.update_comment(comment["id"], "Обновленный комментарий")
        assert updated["content"] == "Обновленный комментарий"
        assert updated["is_edited"] is True

        # Удаляем комментарий
        authenticated_client.delete_comment(comment["id"])

        authenticated_client.delete_project(project_id)
        print(f"✓ Комментарии к посту работают корректно")

    def test_unpublish_project(self, authenticated_client, sample_project_data):
        """Тест снятия проекта с публикации"""
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]

        post = authenticated_client.publish_project(project_id, [])
        assert post["published_at"] is not None

        result = authenticated_client.unpublish_project(project_id)
        assert result["message"] == "Project unpublished successfully"

        # Проверяем, что пост больше не доступен
        with pytest.raises(AssertionError):
            authenticated_client.get_post_by_project(project_id)

        authenticated_client.delete_project(project_id)
        print(f"✓ Проект снят с публикации")

    def test_publish_project_with_media_files(self, authenticated_client, sample_project_data):
        """Тест публикации проекта с медиафайлами"""
        if not os.path.exists(TEST_PROJECT_FILE_PATH):
            pytest.skip("Test file not found")

        # 1. Создаем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]
        print(f"✓ Создан проект: {project_id}")

        # 2. Загружаем медиафайлы через универсальный эндпоинт
        file_data1 = authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="project_post_file",
            metadata={"description": "Main media file"}
        )
        file_id1 = file_data1["file_id"]
        print(f"✓ Загружен файл 1: {file_id1}")

        file_data2 = authenticated_client.upload_file(
            file_path=TEST_PROJECT_FILE_PATH,
            file_type="project_post_file",
            metadata={"description": "Secondary media file"}
        )
        file_id2 = file_data2["file_id"]
        print(f"✓ Загружен файл 2: {file_id2}")

        # 3. Публикуем проект с медиафайлами
        published = authenticated_client.publish_project(
            project_id=project_id,
            media_file_ids=[file_id1, file_id2],
            description="Published with media files",
            github_links=["https://github.com/test/repo"]
        )

        assert published["project_id"] == project_id
        assert published["published_at"] is not None
        assert len(published["media_files"]) == 2

        media_ids = [f["id"] for f in published["media_files"]]
        assert file_id1 in media_ids
        assert file_id2 in media_ids

        print(f"✓ Проект опубликован с медиафайлами")

        # Очистка
        authenticated_client.delete_project(project_id)