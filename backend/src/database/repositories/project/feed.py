from ...repositories.base_repository import BaseRepository
from ...models import *
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, func, update, delete, case, desc
from uuid import UUID
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta


class FeedRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    # ============ POST QUERIES ============

    def get_published_posts_base_query(self):
        """Базовый запрос для опубликованных постов"""
        return self.session.query(ProjectPost).options(
            selectinload(ProjectPost.project)
            .selectinload(Project.creator)
            .selectinload(UserProfile.avatar_file),
            selectinload(ProjectPost.project)
            .selectinload(Project.avatar_file),
            selectinload(ProjectPost.project)
            .selectinload(Project.project_participants),
            selectinload(ProjectPost.files)
            .selectinload(ProjectPostFile.file),
        ).join(Project).filter(
            Project.status == ProjectStatus.PUBLISHED.value
        )

    def get_user_liked_post_ids(self, user_id: int) -> set:
        """Получение ID постов, лайкнутых пользователем"""
        likes = self.session.query(ProjectLike.post_id).filter(
            ProjectLike.user_id == user_id
        ).all()
        return {like.post_id for like in likes}

    def get_feed_posts(
            self,
            user_id: int,
            limit: int = 20,
            offset: int = 0,
            category: Optional[str] = None
    ) -> Tuple[List[ProjectPost], int]:
        """Получение ленты постов"""
        query = self.get_published_posts_base_query()

        if category:
            query = query.filter(Project.category == category)

        # Флаг "от друга"
        friends_subquery = self.session.query(
            Relationship.related_user_id
        ).filter(
            Relationship.user_id == user_id,
            Relationship.status == RelationshipStatus.FRIEND.value
        ).subquery()

        query = query.add_columns(
            case(
                (Project.created_by.in_(friends_subquery), True),
                else_=False
            ).label('is_from_friend')
        )

        total = query.count()

        query = query.order_by(
            desc('is_from_friend'),
            ProjectPost.likes_count.desc(),
            ProjectPost.published_at.desc()
        )

        posts_with_flags = query.limit(limit).offset(offset).all()
        posts = [item[0] for item in posts_with_flags]

        return posts, total

    def get_post_by_project_id(self, project_id: UUID) -> Optional[ProjectPost]:
        """Получение поста по ID проекта"""
        return self.get_published_posts_base_query().filter(
            ProjectPost.project_id == project_id
        ).first()

    def get_post_by_id(self, post_id: UUID) -> Optional[ProjectPost]:
        """Получение поста по ID"""
        return self.get_published_posts_base_query().filter(
            ProjectPost.id == post_id
        ).first()

    # ============ LIKES ============

    def like_post(self, post_id: UUID, user_id: int) -> bool:
        """Лайкнуть пост"""
        existing = self.session.query(ProjectLike).filter(
            ProjectLike.post_id == post_id,
            ProjectLike.user_id == user_id
        ).first()

        if existing:
            return False

        like = ProjectLike(post_id=post_id, user_id=user_id)
        self.session.add(like)

        self.session.execute(
            update(ProjectPost)
            .where(ProjectPost.id == post_id)
            .values(likes_count=ProjectPost.likes_count + 1)
        )

        self.session.commit()
        return True

    def unlike_post(self, post_id: UUID, user_id: int) -> bool:
        """Убрать лайк с поста"""
        result = self.session.execute(
            delete(ProjectLike).where(
                ProjectLike.post_id == post_id,
                ProjectLike.user_id == user_id
            )
        )

        if result.rowcount > 0:
            self.session.execute(
                update(ProjectPost)
                .where(ProjectPost.id == post_id)
                .values(likes_count=ProjectPost.likes_count - 1)
            )
            self.session.commit()
            return True

        return False

    def get_user_liked_posts(
            self,
            user_id: int,
            limit: int = 20,
            offset: int = 0
    ) -> Tuple[List[ProjectPost], int]:
        """Получение постов, лайкнутых пользователем"""
        query = self.get_published_posts_base_query().join(
            ProjectLike, ProjectPost.id == ProjectLike.post_id
        ).filter(
            ProjectLike.user_id == user_id
        ).order_by(
            ProjectLike.created_at.desc()
        )

        total = query.count()
        posts = query.limit(limit).offset(offset).all()
        return posts, total

    def get_posts_by_creator(
            self,
            creator_id: int,
            limit: int = 20,
            offset: int = 0
    ) -> Tuple[List[ProjectPost], int]:
        """Получение постов создателя"""
        query = self.get_published_posts_base_query().filter(
            Project.created_by == creator_id
        ).order_by(
            ProjectPost.published_at.desc()
        )

        total = query.count()
        posts = query.limit(limit).offset(offset).all()
        return posts, total

    def get_trending_posts(
            self,
            days: int = 7,
            limit: int = 20
    ) -> List[Tuple[ProjectPost, int]]:
        """Получение трендовых постов"""
        since_date = datetime.now() - timedelta(days=days)

        results = self.session.query(
            ProjectPost,
            func.count(ProjectLike.id).label('likes_in_period')
        ).options(
            selectinload(ProjectPost.project)
            .selectinload(Project.creator)
            .selectinload(UserProfile.avatar_file),
            selectinload(ProjectPost.project)
            .selectinload(Project.avatar_file),
            selectinload(ProjectPost.files)
            .selectinload(ProjectPostFile.file),
        ).join(
            ProjectLike, ProjectPost.id == ProjectLike.post_id
        ).join(Project).filter(
            Project.status == ProjectStatus.PUBLISHED.value,
            ProjectLike.created_at >= since_date
        ).group_by(ProjectPost.id).order_by(
            desc('likes_in_period'),
            ProjectPost.likes_count.desc()
        ).limit(limit).all()

        return results

    def get_recommended_posts(
            self,
            user_id: int,
            limit: int = 20
    ) -> List[ProjectPost]:
        """Получение рекомендованных постов"""
        user_profile = self.session.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()

        user_interests = user_profile.interests if user_profile else []

        friends_subquery = self.session.query(
            Relationship.related_user_id
        ).filter(
            Relationship.user_id == user_id,
            Relationship.status == RelationshipStatus.FRIEND.value
        ).subquery()

        friends_liked = self.session.query(
            ProjectLike.post_id
        ).filter(
            ProjectLike.user_id.in_(friends_subquery)
        ).subquery()

        query = self.get_published_posts_base_query()

        if user_interests:
            query = query.order_by(
                case(
                    (Project.category.in_(user_interests), 3),
                    (Project.tags.overlap(user_interests), 2),
                    (ProjectPost.id.in_(friends_liked), 1),
                    else_=0
                ).desc(),
                ProjectPost.likes_count.desc(),
                ProjectPost.published_at.desc()
            )
        else:
            query = query.order_by(
                case(
                    (ProjectPost.id.in_(friends_liked), 1),
                    else_=0
                ).desc(),
                ProjectPost.likes_count.desc(),
                ProjectPost.published_at.desc()
            )

        return query.limit(limit).all()

    def get_categories_with_counts(self) -> List[Dict[str, any]]:
        """Получение категорий с количеством постов"""
        categories = []
        for category in ProjectCategory:
            count = self.session.query(
                func.count(ProjectPost.id)
            ).join(Project).filter(
                Project.category == category.value,
                Project.status == ProjectStatus.PUBLISHED.value
            ).scalar()

            categories.append({
                'name': category.value,
                'projects_count': count or 0
            })

        return categories

    # ============ PUBLISH METHODS ============

    def publish_project(
            self,
            project_id: UUID,
            description: Optional[str] = None,
            github_links: Optional[List[str]] = None
    ) -> ProjectPost:
        """
        Публикация проекта: создание поста и изменение статуса проекта.
        Если пост уже существует - выбрасывает ошибку.
        """
        # Проверяем, не опубликован ли уже проект
        existing = self.session.query(ProjectPost).filter(
            ProjectPost.project_id == project_id
        ).first()

        if existing:
            raise ValueError("Project already published")

        # Создаем пост
        post = ProjectPost(
            project_id=project_id,
            description=description,
            github_links=github_links,
            likes_count=0,
            published_at=datetime.now()
        )
        self.session.add(post)
        self.session.flush()

        # Обновляем статус проекта
        self.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(status=ProjectStatus.PUBLISHED.value)
        )

        self.session.commit()
        return self.get_post_by_id(post.id)

    def unpublish_project(self, project_id: UUID) -> None:
        """
        Снятие проекта с публикации: удаление поста и изменение статуса проекта.
        """
        # Находим пост
        post = self.session.query(ProjectPost).filter(
            ProjectPost.project_id == project_id
        ).first()

        if not post:
            raise ValueError("Project is not published")

        # Удаляем пост (каскадно удалятся лайки, комментарии, связи с файлами)
        self.session.delete(post)

        # Обновляем статус проекта
        self.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(status=ProjectStatus.ACTIVE.value)
        )

        self.session.commit()

    def update_post(
            self,
            project_id: UUID,
            description: Optional[str] = None,
            github_links: Optional[List[str]] = None
    ) -> Optional[ProjectPost]:
        """
        Обновление существующего поста (только если проект уже опубликован).
        """
        post = self.session.query(ProjectPost).filter(
            ProjectPost.project_id == project_id
        ).first()

        if not post:
            return None

        if description is not None:
            post.description = description
        if github_links is not None:
            post.github_links = github_links

        self.session.commit()
        return self.get_post_by_id(post.id)

    def get_post_files(self, post_id: UUID) -> List[FileMetadata]:
        """Получение файлов поста"""
        return self.session.query(FileMetadata).join(
            ProjectPostFile, ProjectPostFile.file_id == FileMetadata.id
        ).filter(
            ProjectPostFile.post_id == post_id
        ).order_by(ProjectPostFile.order).all()

    def attach_files_to_post(self, post_id: UUID, file_ids: List[UUID]) -> None:
        """Привязка файлов к посту (замена всех файлов)"""
        # Удаляем старые связи
        self.session.query(ProjectPostFile).filter(
            ProjectPostFile.post_id == post_id
        ).delete()

        # Добавляем новые
        for idx, file_id in enumerate(file_ids):
            post_file = ProjectPostFile(
                post_id=post_id,
                file_id=file_id,
                order=idx
            )
            self.session.add(post_file)

        self.session.commit()

    # ============ COMMENTS METHODS ============

    def get_post_comments(
            self,
            post_id: UUID,
            limit: int = 20,
            offset: int = 0,
            parent_id: Optional[int] = None
    ) -> Tuple[List[Comment], int]:
        """Получение комментариев поста"""
        query = self.session.query(Comment).options(
            selectinload(Comment.user).selectinload(UserProfile.avatar_file)
        ).filter(
            Comment.post_id == post_id
        )

        if parent_id is not None:
            query = query.filter(Comment.parent_id == parent_id)
        else:
            query = query.filter(Comment.parent_id.is_(None))

        total = query.count()
        comments = query.order_by(
            Comment.created_at.desc()
        ).limit(limit).offset(offset).all()

        return comments, total

    def get_comment_by_id(self, comment_id: int) -> Optional[Comment]:
        """Получение комментария по ID"""
        return self.session.query(Comment).options(
            selectinload(Comment.user).selectinload(UserProfile.avatar_file)
        ).filter(
            Comment.id == comment_id
        ).first()

    def create_comment(
            self,
            post_id: UUID,
            user_id: int,
            content: str,
            parent_id: Optional[int] = None
    ) -> Comment:
        """Создание комментария"""
        if parent_id:
            parent_comment = self.get_comment_by_id(parent_id)
            if not parent_comment:
                raise ValueError("Parent comment not found")
            self.session.execute(
                update(Comment)
                .where(Comment.id == parent_id)
                .values(replies_count=Comment.replies_count + 1)
            )

        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id,
            likes={}
        )

        self.session.add(comment)
        self.session.commit()
        return self.get_comment_by_id(comment.id)

    def update_comment(
            self,
            comment_id: int,
            user_id: int,
            content: str
    ) -> Optional[Comment]:
        """Обновление комментария"""
        comment = self.get_comment_by_id(comment_id)

        if not comment or comment.user_id != user_id:
            return None

        comment.content = content
        comment.is_edited = True
        comment.updated_at = datetime.now()

        self.session.commit()
        return self.get_comment_by_id(comment_id)

    def delete_comment(self, comment_id: int, user_id: int) -> bool:
        """Удаление комментария"""
        comment = self.session.query(Comment).filter(
            Comment.id == comment_id
        ).first()

        if not comment or comment.user_id != user_id:
            return False

        if comment.parent_id:
            self.session.execute(
                update(Comment)
                .where(Comment.id == comment.parent_id)
                .values(replies_count=Comment.replies_count - 1)
            )

        # Каскадное удаление ответов
        self.session.query(Comment).filter(
            Comment.parent_id == comment_id
        ).delete(synchronize_session=False)

        self.session.delete(comment)
        self.session.commit()
        return True

    def like_comment(self, comment_id: int, user_id: int) -> bool:
        """Лайкнуть комментарий"""
        comment = self.get_comment_by_id(comment_id)
        if not comment:
            return False

        if str(user_id) in comment.likes:
            return False

        new_likes = comment.likes.copy() if comment.likes else {}
        new_likes[str(user_id)] = {"liked_at": datetime.now().isoformat()}

        self.session.execute(
            update(Comment)
            .where(Comment.id == comment_id)
            .values(
                likes=new_likes,
                likes_count=Comment.likes_count + 1
            )
        )

        self.session.commit()
        return True

    def unlike_comment(self, comment_id: int, user_id: int) -> bool:
        """Убрать лайк с комментария"""
        comment = self.get_comment_by_id(comment_id)
        if not comment or str(user_id) not in comment.likes:
            return False

        new_likes = comment.likes.copy() if comment.likes else {}
        if str(user_id) in new_likes:
            del new_likes[str(user_id)]

        self.session.execute(
            update(Comment)
            .where(Comment.id == comment_id)
            .values(
                likes=new_likes,
                likes_count=Comment.likes_count - 1
            )
        )

        self.session.commit()
        return True

    def get_user_liked_comment_ids(self, user_id: int) -> set:
        """Получение ID комментариев, лайкнутых пользователем"""
        comments = self.session.query(Comment.id).filter(
            Comment.likes.has_key(str(user_id))
        ).all()
        return {comment.id for comment in comments}