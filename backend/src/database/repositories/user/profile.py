from ....database.repositories.base_repository import BaseRepository
from ....database.models import *
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, func, text, delete
from sqlalchemy import and_, update, select
from typing import List, Dict, Optional, Tuple
import uuid


class ProfileRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def create_profile(self, profile_data: dict) -> UserProfile:
        profile = UserProfile(**profile_data)
        self.session.add(profile)
        self.session.commit()

        return profile

    def get_profile_by_user_id(self, user_id: int) -> Optional[UserProfile]:
        profile = (self.session.query(
            UserProfile, User.github_access_token
        )
        .join(User, UserProfile.user_id == User.id)
        .filter(UserProfile.user_id == user_id)
        .first()
                   )

        if profile:
            profile_data, github_access_token = profile
            # Добавляем поле github_access_token в объект профиля
            profile_data.github_access_token = github_access_token
            return profile_data

        return None

    def get_existing_users_ids(self, user_ids: list[int]) -> list[int]:
        if not user_ids:
            return []

        result = (
            self.session.scalars(
                select(UserProfile.user_id)
                .where(UserProfile.user_id.in_(user_ids))
            )
            .all()
        )
        return result

    def update_profile(self, user_id: int, data: dict) -> UserProfile:
        stmt = (update(UserProfile)
                .values(**data)
                .filter(UserProfile.user_id == user_id)
                .returning(UserProfile))

        result = self.session.execute(stmt)
        updated_profile = result.scalar_one()

        self.session.commit()
        return updated_profile

    def delete_profile(self, user_id: int) -> bool:
        profile = self.get_profile_by_user_id(user_id)
        if not profile:
            return False

        self.session.delete(profile)
        self.session.commit()
        return True

    def get_user_avatar(self, user_id: int) -> Optional[FileMetadata]:
        """Получение аватара пользователя"""
        return self.session.query(FileMetadata).join(
            UserProfile, UserProfile.avatar_file_id == FileMetadata.id
        ).filter(
            UserProfile.user_id == user_id
        ).first()

    def update_user_avatar(self, user_id: int, file_id: Optional[uuid.UUID]) -> bool:
        """Обновление аватара пользователя"""
        stmt = (update(UserProfile)
                .values(avatar_file_id=file_id)
                .filter(UserProfile.user_id == user_id))

        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount > 0

    def get_user_profile_projects(
            self,
            user_id: int,
            offset: int = 0,
            limit: int = 50
    ) -> Tuple[List[dict], int]:
        """Проекты пользователя для публичного просмотра профиля"""
        base_query = (
            select(
                Project.id.label('project_id'),
                Project.name,
                Project.description,
                Project.category,
                Project.tags,
                Project.status,
                ProjectParticipant.role,
                ProjectPost.id.label('feed_post_id'),
            )
            .join(ProjectParticipant, ProjectParticipant.project_id == Project.id)
            .outerjoin(ProjectPost, ProjectPost.project_id == Project.id)
            .where(ProjectParticipant.user_id == user_id)
            .where(Project.status != ProjectStatus.ARCHIVED.value)
            .order_by(Project.updated_at.desc())
        )

        count_query = select(func.count()).select_from(base_query.subquery())
        total = self.session.execute(count_query).scalar() or 0

        rows = self.session.execute(base_query.offset(offset).limit(limit)).all()

        items = []
        for row in rows:
            is_published = (
                row.status == ProjectStatus.PUBLISHED.value
                and row.feed_post_id is not None
            )
            items.append({
                'project_id': row.project_id,
                'name': row.name,
                'description': row.description,
                'role': row.role,
                'category': row.category,
                'tags': row.tags,
                'is_published_in_feed': is_published,
                'feed_post_id': row.feed_post_id if is_published else None,
            })

        return items, total