from typing import Dict, Any, List, Optional
from .base import BaseAPIClient
from .auth import AuthClientMixin


class UserFeedClientMixin(AuthClientMixin):
    """Миксин для работы с лентой пользователей"""

    def get_user_feed(
            self: BaseAPIClient,
            page: int = 1,
            page_size: int = 20,
            sort_by: str = "username",
            sort_order: str = "asc",
            name: Optional[str] = None,
            lastname: Optional[str] = None,
            username: Optional[str] = None,
            university: Optional[str] = None,
            faculty: Optional[str] = None,
            course: Optional[int] = None,
            min_course: Optional[int] = None,
            max_course: Optional[int] = None,
            interests: Optional[List[str]] = None,
            skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Получить ленту пользователей с фильтрацией и сортировкой
        GET /feed/users
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        if name:
            params["name"] = name
        if lastname:
            params["lastname"] = lastname
        if username:
            params["username"] = username
        if university:
            params["university"] = university
        if faculty:
            params["faculty"] = faculty
        if course:
            params["course"] = course
        if min_course:
            params["min_course"] = min_course
        if max_course:
            params["max_course"] = max_course
        if interests:
            params["interests"] = interests
        if skills:
            params["skills"] = skills

        response = self.client.get("/feed/users", params=params, headers=headers)
        assert response.status_code == 200, f"Get user feed failed: {response.text}"
        return response.json()

    def search_users(
            self: BaseAPIClient,
            query: str,
            page: int = 1,
            page_size: int = 20
    ) -> Dict[str, Any]:
        """Поиск пользователей
        GET /search/users
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {
            "q": query,
            "page": page,
            "page_size": page_size
        }
        response = self.client.get("/search/users", params=params, headers=headers)
        assert response.status_code == 200, f"Search users failed: {response.text}"
        return response.json()