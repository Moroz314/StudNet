from typing import Dict, Any, List, Optional
from .base import BaseAPIClient
from .auth import AuthClientMixin


class ProjectFeedClientMixin(AuthClientMixin):
    """Миксин для работы с лентой постов проектов"""

    # ========== Feed endpoints ==========

    def get_feed(
            self: BaseAPIClient,
            limit: int = 20,
            offset: int = 0,
            category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получить ленту постов
        GET /feed/posts
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category
        response = self.client.get("/feed/posts", params=params, headers=headers)
        assert response.status_code == 200, f"Get feed failed: {response.text}"
        return response.json()

    def get_trending_posts(
            self: BaseAPIClient,
            days: int = 7,
            limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Получить трендовые посты
        GET /feed/posts/trending
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"days": days, "limit": limit}
        response = self.client.get("/feed/posts/trending", params=params, headers=headers)
        assert response.status_code == 200, f"Get trending posts failed: {response.text}"
        return response.json()

    def get_recommended_posts(
            self: BaseAPIClient,
            limit: int = 20
    ) -> Dict[str, Any]:
        """Получить рекомендованные посты
        GET /feed/posts/recommended
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit}
        response = self.client.get("/feed/posts/recommended", params=params, headers=headers)
        assert response.status_code == 200, f"Get recommended posts failed: {response.text}"
        return response.json()

    def get_liked_posts(
            self: BaseAPIClient,
            limit: int = 20,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Получить понравившиеся посты
        GET /feed/posts/liked
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit, "offset": offset}
        response = self.client.get("/feed/posts/liked", params=params, headers=headers)
        assert response.status_code == 200, f"Get liked posts failed: {response.text}"
        return response.json()

    def get_posts_by_creator(
            self: BaseAPIClient,
            user_id: int,
            limit: int = 20,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Получить посты по создателю
        GET /feed/posts/user/{user_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit, "offset": offset}
        response = self.client.get(f"/feed/posts/user/{user_id}", params=params, headers=headers)
        assert response.status_code == 200, f"Get posts by creator failed: {response.text}"
        return response.json()

    def get_post_by_project(
            self: BaseAPIClient,
            project_id: str
    ) -> Dict[str, Any]:
        """Получить пост по ID проекта
        GET /feed/posts/project/{project_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/feed/posts/project/{project_id}", headers=headers)
        assert response.status_code == 200, f"Get post by project failed: {response.text}"
        return response.json()

    # ========== Like endpoints ==========

    def like_post(self: BaseAPIClient, post_id: str) -> Dict[str, Any]:
        """Поставить лайк посту
        POST /feed/posts/{post_id}/like
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(f"/feed/posts/{post_id}/like", headers=headers)
        assert response.status_code == 200, f"Like post failed: {response.text}"
        return response.json()

    def unlike_post(self: BaseAPIClient, post_id: str) -> Dict[str, Any]:
        """Убрать лайк с поста
        DELETE /feed/posts/{post_id}/like
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(f"/feed/posts/{post_id}/like", headers=headers)
        assert response.status_code == 200, f"Unlike post failed: {response.text}"
        return response.json()

    # ========== Categories endpoints ==========

    def get_categories(self: BaseAPIClient) -> List[Dict[str, Any]]:
        """Получить категории проектов
        GET /feed/categories
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get("/feed/categories", headers=headers)
        assert response.status_code == 200, f"Get categories failed: {response.text}"
        return response.json()

    # ========== Publish endpoints ==========

    def publish_project(
            self: BaseAPIClient,
            project_id: str,
            media_file_ids: Optional[List[str]] = None,
            description: Optional[str] = None,
            github_links: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Опубликовать проект (создать пост)
        POST /feed/projects/{project_id}/publish
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {"media_file_ids": media_file_ids or []}
        if description:
            data["description"] = description
        if github_links:
            data["github_links"] = github_links
        response = self.client.post(
            f"/feed/projects/{project_id}/publish",
            json=data,
            headers=headers
        )
        assert response.status_code == 200, f"Publish project failed: {response.text}"
        return response.json()

    def unpublish_project(self: BaseAPIClient, project_id: str) -> Dict[str, Any]:
        """Снять проект с публикации (удалить пост)
        POST /feed/projects/{project_id}/unpublish
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(f"/feed/projects/{project_id}/unpublish", headers=headers)
        assert response.status_code == 200, f"Unpublish project failed: {response.text}"
        return response.json()

    def update_post(
            self: BaseAPIClient,
            project_id: str,
            media_file_ids: Optional[List[str]] = None,
            description: Optional[str] = None,
            github_links: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Обновить существующий пост
        PUT /feed/projects/{project_id}/post
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {}
        if media_file_ids is not None:
            data["media_file_ids"] = media_file_ids
        if description is not None:
            data["description"] = description
        if github_links is not None:
            data["github_links"] = github_links
        response = self.client.put(
            f"/feed/projects/{project_id}/post",
            json=data,
            headers=headers
        )
        assert response.status_code == 200, f"Update post failed: {response.text}"
        return response.json()

    # ========== Comments endpoints ==========

    def get_post_comments(
            self: BaseAPIClient,
            post_id: str,
            limit: int = 20,
            offset: int = 0,
            parent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Получить комментарии к посту
        GET /feed/posts/{post_id}/comments
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit, "offset": offset}
        if parent_id:
            params["parent_id"] = parent_id
        response = self.client.get(f"/feed/posts/{post_id}/comments", params=params, headers=headers)
        assert response.status_code == 200, f"Get post comments failed: {response.text}"
        return response.json()

    def create_comment(
            self: BaseAPIClient,
            post_id: str,
            content: str,
            parent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Создать комментарий к посту
        POST /feed/posts/{post_id}/comments
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {"content": content}
        if parent_id:
            data["parent_id"] = parent_id
        response = self.client.post(
            f"/feed/posts/{post_id}/comments",
            json=data,
            headers=headers
        )
        assert response.status_code == 201, f"Create comment failed: {response.text}"
        return response.json()

    def update_comment(
            self: BaseAPIClient,
            comment_id: int,
            content: str
    ) -> Dict[str, Any]:
        """Обновить комментарий
        PUT /feed/comments/{comment_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {"content": content}
        response = self.client.put(f"/feed/comments/{comment_id}", json=data, headers=headers)
        assert response.status_code == 200, f"Update comment failed: {response.text}"
        return response.json()

    def delete_comment(self: BaseAPIClient, comment_id: int) -> Dict[str, Any]:
        """Удалить комментарий
        DELETE /feed/comments/{comment_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(f"/feed/comments/{comment_id}", headers=headers)
        assert response.status_code == 200, f"Delete comment failed: {response.text}"
        return response.json()

    def like_comment(self: BaseAPIClient, comment_id: int) -> Dict[str, Any]:
        """Поставить лайк комментарию
        POST /feed/comments/{comment_id}/like
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.post(f"/feed/comments/{comment_id}/like", headers=headers)
        assert response.status_code == 200, f"Like comment failed: {response.text}"
        return response.json()

    def unlike_comment(self: BaseAPIClient, comment_id: int) -> Dict[str, Any]:
        """Убрать лайк с комментария
        DELETE /feed/comments/{comment_id}/like
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(f"/feed/comments/{comment_id}/like", headers=headers)
        assert response.status_code == 200, f"Unlike comment failed: {response.text}"
        return response.json()