from .schemas import *
from ...users.auth.service.utils import verify_token
from ...database.core import get_db
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from ..validation import require_project_access, require_project_owner
from ...database.repositories.project.feed import FeedRepository
from ...database.repositories.files import FileRepository
from ...database.repositories.project.core import ProjectRepository
from ...files.service import FileService
from ...files.schemas import FileType as GlobalFileType
from ...database.models import Project, ProjectStatus, ProjectPost
from typing import List, Optional, Dict
from uuid import UUID

FEED_URL_EXPIRY = 3600
AVATAR_URL_EXPIRY = 86400


class FeedService:
    def __init__(
            self,
            feed_repo: FeedRepository,
            file_repo: FileRepository,
            project_repo: ProjectRepository,
            file_service: FileService,
            user_id: int
    ):
        self.feed_repo = feed_repo
        self.file_repo = file_repo
        self.project_repo = project_repo
        self.file_service = file_service
        self.user_id = user_id
        self._liked_post_ids: Optional[set] = None
        self._liked_comment_ids: Optional[set] = None

    # ============ CACHE METHODS ============

    def _get_liked_post_ids(self) -> set:
        if self._liked_post_ids is None:
            self._liked_post_ids = self.feed_repo.get_user_liked_post_ids(self.user_id)
        return self._liked_post_ids

    def _invalidate_liked_cache(self):
        self._liked_post_ids = None

    def _get_liked_comment_ids(self) -> set:
        if self._liked_comment_ids is None:
            self._liked_comment_ids = self.feed_repo.get_user_liked_comment_ids(self.user_id)
        return self._liked_comment_ids

    def _invalidate_liked_comments_cache(self):
        self._liked_comment_ids = None

    # ============ FILE HELPERS ============

    async def _get_file_urls_batch(self, file_ids: List[UUID]) -> Dict[UUID, str]:
        """Batch получение URL для файлов"""
        if not file_ids:
            return {}
        return await self.file_service.get_file_urls_batch(
            file_ids=file_ids,
            user_id=self.user_id,
            expires_in=FEED_URL_EXPIRY
        )

    async def _get_file_response(self, file_metadata) -> Optional[FileResponse]:
        """Получение FileResponse для одного файла"""
        if not file_metadata:
            return None
        url = await self.file_service.get_file_url(
            file_id=file_metadata.id,
            user_id=self.user_id,
            expires_in=FEED_URL_EXPIRY
        )
        return FileResponse(
            id=file_metadata.id,
            url=url,
            original_filename=file_metadata.original_filename,
            mime_type=file_metadata.mime_type,
            size_bytes=file_metadata.size_bytes
        )

    async def _get_creator_response(self, creator) -> UserProfileBriefResponse:
        """Получение информации о создателе"""
        avatar_url = None
        if creator and creator.avatar_file:
            avatar_url = await self.file_service.get_file_url(
                file_id=creator.avatar_file.id,
                user_id=self.user_id,
                expires_in=AVATAR_URL_EXPIRY
            )
        return UserProfileBriefResponse(
            user_id=creator.user_id if creator else 0,
            name=creator.name if creator else None,
            lastname=creator.lastname if creator else None,
            username=creator.username if creator else None,
            avatar_url=avatar_url
        )

    # ============ POST BUILDERS ============

    async def _build_post_response(
            self,
            post: ProjectPost,
            is_from_friend: bool = False
    ) -> ProjectFeedResponse:
        """Построение ответа для одного поста"""
        is_liked = post.id in self._get_liked_post_ids()

        # Аватар проекта
        avatar_response = await self._get_file_response(post.project.avatar_file)

        # Медиафайлы поста
        files = self.feed_repo.get_post_files(post.id)
        file_ids = [f.id for f in files]
        urls = await self._get_file_urls_batch(file_ids)

        media_files = [
            FileResponse(
                id=f.id,
                url=urls.get(f.id, ""),
                original_filename=f.original_filename,
                mime_type=f.mime_type,
                size_bytes=f.size_bytes
            )
            for f in files
        ]

        # Создатель
        creator_response = await self._get_creator_response(post.project.creator)

        # Количество участников
        participants_count = len(post.project.project_participants) if post.project.project_participants else 0

        return ProjectFeedResponse(
            id=post.id,
            project_id=post.project_id,
            name=post.project.name,
            description=post.description or post.project.description,
            category=post.project.category,
            tags=post.project.tags,
            github_links=post.github_links,
            likes_count=post.likes_count,
            is_liked_by_user=is_liked,
            is_from_friend=is_from_friend,
            created_at=post.created_at,
            published_at=post.published_at,
            avatar=avatar_response,
            media_files=media_files,
            creator=creator_response,
            participants_count=participants_count
        )

    async def _build_post_responses_batch(
            self,
            posts: List[ProjectPost],
            friends_flags: List[bool] = None
    ) -> List[ProjectFeedResponse]:
        """Массовое построение ответов с batch-запросами URL"""
        if not posts:
            return []

        # Собираем все file_id
        all_file_ids = []
        for post in posts:
            if post.project.avatar_file:
                all_file_ids.append(post.project.avatar_file.id)
            if post.project.creator and post.project.creator.avatar_file:
                all_file_ids.append(post.project.creator.avatar_file.id)
            files = self.feed_repo.get_post_files(post.id)
            all_file_ids.extend([f.id for f in files])

        # Batch-запрос URL
        urls = await self._get_file_urls_batch(all_file_ids) if all_file_ids else {}

        liked_post_ids = self._get_liked_post_ids()
        results = []

        for idx, post in enumerate(posts):
            is_from_friend = friends_flags[idx] if friends_flags else False
            is_liked = post.id in liked_post_ids

            # Аватар
            avatar_response = None
            if post.project.avatar_file:
                avatar_response = FileResponse(
                    id=post.project.avatar_file.id,
                    url=urls.get(post.project.avatar_file.id, ""),
                    original_filename=post.project.avatar_file.original_filename,
                    mime_type=post.project.avatar_file.mime_type,
                    size_bytes=post.project.avatar_file.size_bytes
                )

            # Медиафайлы
            files = self.feed_repo.get_post_files(post.id)
            media_files = [
                FileResponse(
                    id=f.id,
                    url=urls.get(f.id, ""),
                    original_filename=f.original_filename,
                    mime_type=f.mime_type,
                    size_bytes=f.size_bytes
                )
                for f in files
            ]

            # Создатель
            creator_response = None
            if post.project.creator:
                avatar_url = None
                if post.project.creator.avatar_file:
                    avatar_url = urls.get(post.project.creator.avatar_file.id)
                creator_response = UserProfileBriefResponse(
                    user_id=post.project.creator.user_id,
                    name=post.project.creator.name,
                    lastname=post.project.creator.lastname,
                    username=post.project.creator.username,
                    avatar_url=avatar_url
                )

            participants_count = len(post.project.project_participants) if post.project.project_participants else 0

            results.append(ProjectFeedResponse(
                id=post.id,
                project_id=post.project_id,
                name=post.project.name,
                description=post.description or post.project.description,
                category=post.project.category,
                tags=post.project.tags,
                github_links=post.github_links,
                likes_count=post.likes_count,
                is_liked_by_user=is_liked,
                is_from_friend=is_from_friend,
                created_at=post.created_at,
                published_at=post.published_at,
                avatar=avatar_response,
                media_files=media_files,
                creator=creator_response,
                participants_count=participants_count
            ))

        return results

    # ============ FEED METHODS ============

    async def get_feed(
            self,
            limit: int = 20,
            offset: int = 0,
            category: Optional[str] = None
    ) -> FeedResponse:
        posts, total = self.feed_repo.get_feed_posts(
            user_id=self.user_id,
            limit=limit,
            offset=offset,
            category=category
        )

        friends_flags = [getattr(p, 'is_from_friend', False) for p in posts]
        items = await self._build_post_responses_batch(posts, friends_flags)

        return FeedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_next=(offset + limit) < total
        )

    async def get_post_by_project_id(self, project_id: UUID) -> ProjectFeedResponse:
        post = self.feed_repo.get_post_by_project_id(project_id)

        if not post or not post.published_at:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )

        items = await self._build_post_responses_batch([post])
        return items[0]

    async def like_post(self, post_id: UUID) -> LikeResponse:
        post = self.feed_repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        result = self.feed_repo.like_post(post_id, self.user_id)
        self._invalidate_liked_cache()

        updated_post = self.feed_repo.get_post_by_id(post_id)
        return LikeResponse(
            post_id=post_id,
            likes_count=updated_post.likes_count if updated_post else post.likes_count,
            is_liked=result
        )

    async def unlike_post(self, post_id: UUID) -> LikeResponse:
        post = self.feed_repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        result = self.feed_repo.unlike_post(post_id, self.user_id)
        self._invalidate_liked_cache()

        updated_post = self.feed_repo.get_post_by_id(post_id)
        return LikeResponse(
            post_id=post_id,
            likes_count=updated_post.likes_count if updated_post else post.likes_count,
            is_liked=not result
        )

    async def get_user_liked_posts(self, limit: int = 20, offset: int = 0) -> FeedResponse:
        posts, total = self.feed_repo.get_user_liked_posts(
            user_id=self.user_id,
            limit=limit,
            offset=offset
        )
        items = await self._build_post_responses_batch(posts)

        return FeedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_next=(offset + limit) < total
        )

    async def get_posts_by_creator(self, creator_id: int, limit: int = 20, offset: int = 0) -> FeedResponse:
        posts, total = self.feed_repo.get_posts_by_creator(
            creator_id=creator_id,
            limit=limit,
            offset=offset
        )
        items = await self._build_post_responses_batch(posts)

        return FeedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_next=(offset + limit) < total
        )

    async def get_trending_posts(self, days: int = 7, limit: int = 20) -> List[TrendingProjectResponse]:
        posts_with_likes = self.feed_repo.get_trending_posts(days=days, limit=limit)

        posts = [p for p, _ in posts_with_likes]
        post_responses = await self._build_post_responses_batch(posts)

        result = []
        for (post, likes_in_period), post_response in zip(posts_with_likes, post_responses):
            trend_score = (likes_in_period * 0.7) + (post.likes_count * 0.3)
            result.append(TrendingProjectResponse(
                project=post_response,
                likes_in_period=likes_in_period,
                trend_score=trend_score
            ))

        return result

    async def get_recommended_posts(self, limit: int = 20) -> FeedResponse:
        posts = self.feed_repo.get_recommended_posts(user_id=self.user_id, limit=limit)
        items = await self._build_post_responses_batch(posts)

        return FeedResponse(
            items=items,
            total=len(items),
            limit=limit,
            offset=0,
            has_next=False
        )

    async def get_categories(self) -> List[CategoryResponse]:
        categories_data = self.feed_repo.get_categories_with_counts()
        return [
            CategoryResponse(name=cat['name'], projects_count=cat['projects_count'])
            for cat in categories_data
        ]

    # ============ PUBLISH METHODS ============

    async def publish_project(
            self,
            project_id: UUID,
            request: PublishProjectRequest
    ) -> ProjectFeedResponse:
        """
        Публикация проекта: создание поста и изменение статуса проекта.
        """
        require_project_owner(self.project_repo, project_id, self.user_id)

        # Валидируем файлы
        if request.media_file_ids:
            await self.file_service.validate_files_batch(
                file_ids=request.media_file_ids,
                file_type=GlobalFileType.PROJECT_POST_FILE,
                user_id=self.user_id
            )

        try:
            # Публикуем проект
            post = self.feed_repo.publish_project(
                project_id=project_id,
                description=request.description,
                github_links=request.github_links
            )

            # Привязываем файлы
            if request.media_file_ids:
                self.feed_repo.attach_files_to_post(post.id, request.media_file_ids)

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        items = await self._build_post_responses_batch([post])
        return items[0]

    async def unpublish_project(self, project_id: UUID) -> dict:
        """
        Снятие проекта с публикации: удаление поста и изменение статуса проекта.
        """
        require_project_owner(self.project_repo, project_id, self.user_id)

        try:
            self.feed_repo.unpublish_project(project_id=project_id)
            self._invalidate_liked_cache()

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        return {"message": "Project unpublished successfully", "project_id": str(project_id)}

    async def update_post(
            self,
            project_id: UUID,
            request: PublishProjectRequest
    ) -> ProjectFeedResponse:
        """
        Обновление существующего поста (только если проект уже опубликован).
        """
        require_project_owner(self.project_repo, project_id, self.user_id)

        # Валидируем файлы
        if request.media_file_ids:
            await self.file_service.validate_files_batch(
                file_ids=request.media_file_ids,
                file_type=GlobalFileType.PROJECT_POST_FILE,
                user_id=self.user_id
            )

        post = self.feed_repo.update_post(
            project_id=project_id,
            description=request.description,
            github_links=request.github_links
        )

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found. Project may not be published."
            )

        # Обновляем файлы
        if request.media_file_ids is not None:
            self.feed_repo.attach_files_to_post(post.id, request.media_file_ids)

        items = await self._build_post_responses_batch([post])
        return items[0]

    # ============ COMMENTS METHODS ============

    async def _get_comment_user_response(self, user) -> CommentUserResponse:
        avatar_url = None
        if user and user.avatar_file:
            avatar_url = await self.file_service.get_file_url(
                file_id=user.avatar_file.id,
                user_id=self.user_id,
                expires_in=AVATAR_URL_EXPIRY
            )
        return CommentUserResponse(
            user_id=user.user_id if user else 0,
            name=user.name if user else None,
            lastname=user.lastname if user else None,
            username=user.username if user else None,
            avatar_url=avatar_url
        )

    async def _build_comment_response(
            self,
            comment,
            liked_comment_ids: Optional[set] = None
    ) -> CommentResponse:
        if liked_comment_ids is None:
            liked_comment_ids = self._get_liked_comment_ids()

        is_liked = comment.id in liked_comment_ids
        user_response = await self._get_comment_user_response(comment.user)

        return CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            content=comment.content,
            likes_count=comment.likes_count,
            replies_count=comment.replies_count,
            is_liked_by_user=is_liked,
            is_edited=comment.is_edited,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            user=user_response,
            parent_id=comment.parent_id
        )

    async def get_post_comments(
            self,
            post_id: UUID,
            limit: int = 20,
            offset: int = 0,
            parent_id: Optional[int] = None
    ) -> CommentsResponse:
        post = self.feed_repo.get_post_by_id(post_id)
        if not post or not post.published_at:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        comments, total = self.feed_repo.get_post_comments(
            post_id=post_id,
            limit=limit,
            offset=offset,
            parent_id=parent_id
        )

        liked_comment_ids = self._get_liked_comment_ids()
        items = [await self._build_comment_response(c, liked_comment_ids) for c in comments]

        return CommentsResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_next=(offset + limit) < total
        )

    async def create_comment(self, post_id: UUID, request: CommentCreateRequest) -> CommentResponse:
        post = self.feed_repo.get_post_by_id(post_id)
        if not post or not post.published_at:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        try:
            comment = self.feed_repo.create_comment(
                post_id=post_id,
                user_id=self.user_id,
                content=request.content,
                parent_id=request.parent_id
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        return await self._build_comment_response(comment)

    async def update_comment(self, comment_id: int, request: CommentUpdateRequest) -> CommentResponse:
        comment = self.feed_repo.update_comment(
            comment_id=comment_id,
            user_id=self.user_id,
            content=request.content
        )

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found or you don't have permission"
            )

        return await self._build_comment_response(comment)

    async def delete_comment(self, comment_id: int) -> dict:
        result = self.feed_repo.delete_comment(comment_id=comment_id, user_id=self.user_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found or you don't have permission"
            )

        return {"message": "Comment deleted successfully"}

    async def like_comment(self, comment_id: int) -> CommentLikeResponse:
        comment = self.feed_repo.get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        result = self.feed_repo.like_comment(comment_id, self.user_id)

        if not result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment already liked")

        self._invalidate_liked_comments_cache()
        updated_comment = self.feed_repo.get_comment_by_id(comment_id)

        return CommentLikeResponse(
            comment_id=comment_id,
            likes_count=updated_comment.likes_count if updated_comment else comment.likes_count,
            is_liked=True
        )

    async def unlike_comment(self, comment_id: int) -> CommentLikeResponse:
        comment = self.feed_repo.get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        result = self.feed_repo.unlike_comment(comment_id, self.user_id)

        if not result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment not liked")

        self._invalidate_liked_comments_cache()
        updated_comment = self.feed_repo.get_comment_by_id(comment_id)

        return CommentLikeResponse(
            comment_id=comment_id,
            likes_count=updated_comment.likes_count if updated_comment else comment.likes_count,
            is_liked=False
        )


# Dependency для получения сервиса
def get_feed_service(
        db: Session = Depends(get_db),
        user_id: int = Depends(verify_token)
) -> FeedService:
    feed_repo = FeedRepository(session=db)
    file_repo = FileRepository(session=db)
    project_repo = ProjectRepository(session=db)
    file_service = FileService(session=db)

    return FeedService(
        feed_repo=feed_repo,
        file_repo=file_repo,
        project_repo=project_repo,
        file_service=file_service,
        user_id=user_id
    )