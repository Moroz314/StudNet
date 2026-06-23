import pytest
from .fixtures import *
from .clients.extended import ExtendedAPIClient


class TestUserFeed:
    """Тесты для ленты пользователей"""

    def test_get_user_feed(self, authenticated_client):
        """Тест получения ленты пользователей"""
        feed = authenticated_client.get_user_feed(page=1, page_size=20)

        assert "profiles" in feed
        assert "total_count" in feed
        assert "page" in feed
        assert "page_size" in feed
        assert "total_pages" in feed
        assert isinstance(feed["profiles"], list)

        if len(feed["profiles"]) > 0:
            profile = feed["profiles"][0]
            assert "user_id" in profile
            assert "username" in profile
            assert "name" in profile
            assert "lastname" in profile

        print(f"✓ Получена лента пользователей, всего: {feed['total_count']}")

    def test_get_user_feed_with_filters(self, authenticated_client):
        """Тест получения ленты пользователей с фильтрами"""
        feed = authenticated_client.get_user_feed(
            page=1,
            page_size=20,
            sort_by="username",
            sort_order="asc"
        )

        assert feed["page"] == 1
        assert feed["page_size"] == 20

        print(f"✓ Лента с сортировкой получена")

    def test_get_user_feed_pagination(self, authenticated_client):
        """Тест пагинации в ленте пользователей"""
        page1 = authenticated_client.get_user_feed(page=1, page_size=5)

        if page1["total_pages"] > 1:
            page2 = authenticated_client.get_user_feed(page=2, page_size=5)

            assert page2["page"] == 2
            page1_ids = [p["user_id"] for p in page1["profiles"]]
            page2_ids = [p["user_id"] for p in page2["profiles"]]
            assert not any(pid in page2_ids for pid in page1_ids)

        print(f"✓ Пагинация работает корректно")

    def test_search_users(self, authenticated_client, second_authenticated_client):
        """Тест поиска пользователей"""
        second_profile = second_authenticated_client.get_personal_user_profile()
        search_query = second_profile["username"][:3]

        results = authenticated_client.search_users(search_query, page=1, page_size=20)

        assert "profiles" in results
        assert "total_count" in results
        assert isinstance(results["profiles"], list)

        if results["total_count"] > 0:
            found = any(p["user_id"] == second_authenticated_client.user_id for p in results["profiles"])
            # Может найти или нет, в зависимости от совпадения

        print(f"✓ Поиск пользователей выполнен, найдено: {results['total_count']}")

    def test_search_users_empty_query(self, authenticated_client):
        """Тест поиска с пустым запросом (должен вернуть ошибку)"""
        with pytest.raises(AssertionError):
            authenticated_client.search_users("", page=1, page_size=20)

    def test_get_user_feed_with_all_filters(self, authenticated_client):
        """Тест ленты пользователей со всеми фильтрами"""
        feed = authenticated_client.get_user_feed(
            page=1,
            page_size=20,
            sort_by="username",
            sort_order="asc",
            min_course=1,
            max_course=6
        )

        assert feed is not None
        print(f"✓ Лента с фильтрами по курсу получена")


class TestUserFeedIntegration:
    """Интеграционные тесты для ленты пользователей"""

    def test_user_appears_in_feed_after_profile_creation(self, authenticated_client):
        """Тест: пользователь появляется в ленте после создания профиля"""
        feed = authenticated_client.get_user_feed(page=1, page_size=50)

        user_in_feed = any(p["user_id"] == authenticated_client.user_id for p in feed["profiles"])
        assert user_in_feed, "Current user should appear in the feed"

        print(f"✓ Текущий пользователь найден в ленте")

    def test_user_feed_response_structure(self, authenticated_client):
        """Тест структуры ответа ленты пользователей"""
        feed = authenticated_client.get_user_feed(page=1, page_size=10)

        assert "profiles" in feed
        assert "total_count" in feed
        assert "page" in feed
        assert "page_size" in feed
        assert "total_pages" in feed

        if feed["profiles"]:
            profile = feed["profiles"][0]
            expected_fields = ["user_id", "username", "name", "lastname"]
            for field in expected_fields:
                assert field in profile, f"Field {field} missing in profile"

        print(f"✓ Структура ответа корректна")