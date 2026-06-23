from .schemas import *
from ...database.repositories.user.feed import FeedRepository
from ...database.models import UserProfile
from ...files.service import FileService
import math
import os
from fastapi import Depends, HTTPException, status
from ...database.core import get_db
from sqlalchemy.orm import Session
from ...users.auth.service.utils import verify_token

AVATAR_URL_EXPIRY = 86400  # 24 часа


def get_user_feed_service(
        db: Session = Depends(get_db),
        user_id: int = Depends(verify_token)
) -> "FeedService":
    feed_repo = FeedRepository(session=db)
    file_service = FileService(session=db)

    return FeedService(
        feed_repo=feed_repo,
        file_service=file_service,
        user_id=user_id
    )


class FeedService:
    def __init__(
            self,
            feed_repo: FeedRepository,
            file_service: FileService,
            user_id: int
    ):
        self.feed_repo = feed_repo
        self.file_service = file_service
        self.user_id = user_id

    async def _get_avatar_url(self, profile: UserProfile) -> Optional[str]:
        """
        Получение presigned URL для аватарки пользователя через FileService
        """
        if not profile.avatar_file:
            return None

        try:
            url = await self.file_service.get_file_url(
                file_id=profile.avatar_file.id,
                user_id=self.user_id,
                expires_in=AVATAR_URL_EXPIRY
            )
            return url
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            print(f"Error generating avatar URL for user {profile.user_id}: {e}")
            return None

    async def _get_avatar_urls_batch(self, profiles: List[UserProfile]) -> dict:
        """
        Массовое получение presigned URL для аватарок пользователей
        """
        if not profiles:
            return {}

        # Собираем ID всех аватаров
        avatar_file_ids = [p.avatar_file.id for p in profiles if p.avatar_file]

        if not avatar_file_ids:
            return {}

        # Получаем все URL одним batch-запросом
        return await self.file_service.get_file_urls_batch(
            file_ids=avatar_file_ids,
            user_id=self.user_id,
            expires_in=AVATAR_URL_EXPIRY
        )

    async def _build_profile_response(self, profile: UserProfile, avatar_urls: dict = None) -> FeedUserProfile:
        """
        Сборка ответа для профиля с presigned URL аватарки
        """
        avatar_url = None

        if profile.avatar_file:
            if avatar_urls is not None:
                avatar_url = avatar_urls.get(profile.avatar_file.id)
            else:
                avatar_url = await self._get_avatar_url(profile)

        return FeedUserProfile(
            user_id=profile.user_id,
            name=profile.name,
            lastname=profile.lastname,
            username=profile.username,
            birth_date=profile.birth_date,
            university=profile.university,
            faculty=profile.faculty,
            course=profile.course,
            info=profile.info,
            interests=profile.interests,
            skills=profile.skills,
            links=profile.links,
            avatar_url=avatar_url
        )

    async def _build_profile_responses_batch(
            self,
            profiles: List[UserProfile]
    ) -> List[FeedUserProfile]:
        """
        Массовая сборка ответов для профилей с batch-запросом URL аватарок
        """
        if not profiles:
            return []

        # Получаем все URL аватарок одним запросом
        avatar_urls = await self._get_avatar_urls_batch(profiles)

        # Строим ответы
        responses = []
        for profile in profiles:
            avatar_url = None
            if profile.avatar_file:
                avatar_url = avatar_urls.get(profile.avatar_file.id)

            responses.append(FeedUserProfile(
                user_id=profile.user_id,
                name=profile.name,
                lastname=profile.lastname,
                username=profile.username,
                birth_date=profile.birth_date,
                university=profile.university,
                faculty=profile.faculty,
                course=profile.course,
                info=profile.info,
                interests=profile.interests,
                skills=profile.skills,
                links=profile.links,
                avatar_url=avatar_url
            ))

        return responses

    async def get_user_feed(self, query: UserFeedQuery) -> UserFeedResponse:
        """Получить ленту пользователей"""
        profiles, total_count = self.feed_repo.get_user_feed(query)

        # Преобразуем в Pydantic модели с batch-запросом URL аватарок
        profile_responses = await self._build_profile_responses_batch(profiles)

        # Рассчитываем общее количество страниц
        total_pages = math.ceil(total_count / query.page_size) if total_count > 0 else 1

        return UserFeedResponse(
            profiles=profile_responses,
            total_count=total_count,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages
        )

    async def search_users(self, query: SearchUsersQuery) -> UserFeedResponse:
        """Поиск пользователей"""
        profiles, total_count = self.feed_repo.search_users(
            search_query=query.query,
            page=query.page,
            page_size=query.page_size
        )

        # Преобразуем в Pydantic модели с batch-запросом URL аватарок
        profile_responses = await self._build_profile_responses_batch(profiles)

        # Рассчитываем общее количество страниц
        total_pages = math.ceil(total_count / query.page_size) if total_count > 0 else 1

        return UserFeedResponse(
            profiles=profile_responses,
            total_count=total_count,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages
        )