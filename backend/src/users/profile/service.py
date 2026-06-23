from ...database.repositories.user.profile import ProfileRepository
from .schemas import *
from fastapi.exceptions import HTTPException
from fastapi import status, Depends, UploadFile
from ..auth.service.utils import verify_token
from sqlalchemy.orm import Session
from ...database.core import get_db
from ...files.service import FileService, get_file_service
from ...files.schemas import FileType as GlobalFileType, FileUploadResponse
from ...database.redis.redis_presence import RedisPresence
import logging
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

AVATAR_URL_EXPIRY = 86400  # 24 часа


def get_profile_service(
        user_id: int = Depends(verify_token),
        db: Session = Depends(get_db)
) -> "ProfileService":
    profile_repo = ProfileRepository(session=db)
    file_service = FileService(session=db)
    presence_service = RedisPresence()

    return ProfileService(
        profile_repo=profile_repo,
        file_service=file_service,
        presence_service=presence_service,
        user_id=user_id
    )


class ProfileService:
    def __init__(
            self,
            profile_repo: ProfileRepository,
            file_service: FileService,
            presence_service: RedisPresence,
            user_id: int
    ):
        self.profile_repo = profile_repo
        self.file_service = file_service
        self.presence_service = presence_service
        self.user_id = user_id

    async def _get_avatar_url(self, avatar_file_id: Optional[uuid.UUID]) -> Optional[str]:
        """Получение URL аватара через FileService"""
        if not avatar_file_id:
            return None

        try:
            return await self.file_service.get_file_url(
                file_id=avatar_file_id,
                user_id=self.user_id,
                expires_in=AVATAR_URL_EXPIRY
            )
        except Exception as e:
            logger.error(f"Failed to generate avatar URL: {e}")
            return None

    async def _enrich_profile_with_avatar(self, profile: UserProfile) -> UserProfile:
        """Добавление URL аватара к профилю"""
        if profile.avatar_file_id:
            profile.avatar_url = await self._get_avatar_url(profile.avatar_file_id)
        return profile

    def check_profile_exists(self) -> None:
        """Проверяет существование профиля"""
        profile = self.profile_repo.get_profile_by_user_id(user_id=self.user_id)
        if profile:
            raise HTTPException(
                detail="Профиль c данным user_id уже существует.",
                status_code=status.HTTP_409_CONFLICT
            )

    async def create_profile(self, data: UserProfileCreate) -> UserProfile:
        """Создание профиля пользователя"""
        self.check_profile_exists()

        profile_data = dict(data)
        profile_data['user_id'] = self.user_id
        try:
            profile = self.profile_repo.create_profile(profile_data)

            profile_dto = UserProfile.model_validate(profile, from_attributes=True)

            # Добавляем URL аватарки, если она есть
            if profile.avatar_file_id:
                profile_dto.avatar_url = await self._get_avatar_url(profile.avatar_file_id)

            return profile_dto
        except Exception as e:
            logger.error(f"Error creating profile for user {self.user_id}: {e}")
            # Удаляем пользователя, если создание профиля не удалось
            from ...database.repositories.user.auth import UserRepository
            user_repo = UserRepository(self.session)
            user_repo.delete_user(self.user_id)
            raise HTTPException(
                detail="Ошибка при создании профиля. Пользователь удален.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_personal_profile(self) -> UserProfile:
        """Получение своего профиля"""
        profile = self.profile_repo.get_profile_by_user_id(user_id=self.user_id)

        if not profile:
            raise HTTPException(
                detail="Профиль не найден.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Получаем данные о присутствии
        presence_data = await self.presence_service.get_user_presence_data(self.user_id)

        profile_dto = UserProfile.model_validate(profile, from_attributes=True)
        profile_dto.presence_data = presence_data

        # Добавляем URL аватарки
        if profile.avatar_file_id:
            profile_dto.avatar_url = await self._get_avatar_url(profile.avatar_file_id)

        return profile_dto

    async def get_user_profile(self, user_id: int) -> UserProfile:
        """Получение профиля другого пользователя"""
        profile = self.profile_repo.get_profile_by_user_id(user_id)

        if not profile:
            raise HTTPException(
                detail="Профиль не найден.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Получаем данные о присутствии
        presence_data = await self.presence_service.get_user_presence_data(user_id)

        profile_dto = UserProfile.model_validate(profile, from_attributes=True)
        profile_dto.presence_data = presence_data

        # Добавляем URL аватарки
        if profile.avatar_file_id:
            profile_dto.avatar_url = await self._get_avatar_url(profile.avatar_file_id)

        return profile_dto

    async def get_user_profile_projects(
            self,
            user_id: int,
            offset: int = 0,
            limit: int = 50
    ) -> UserProfileProjectsResponse:
        """Проекты пользователя для просмотра на странице профиля"""
        profile = self.profile_repo.get_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                detail="Профиль не найден.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        items, total = self.profile_repo.get_user_profile_projects(
            user_id=user_id,
            offset=offset,
            limit=limit
        )

        return UserProfileProjectsResponse(
            items=[UserProfileProjectItem(**item) for item in items],
            total=total,
            offset=offset,
            limit=limit
        )

    async def edit_profile(self, data: UserProfileEdit) -> UserProfile:
        """Редактирование профиля"""
        data_to_edit = UserProfileEdit.model_dump(data, exclude_none=True)
        updated_profile = self.profile_repo.update_profile(
            user_id=self.user_id,
            data=data_to_edit
        )

        profile_dto = UserProfile.model_validate(updated_profile, from_attributes=True)

        # Добавляем URL аватарки
        if updated_profile.avatar_file_id:
            profile_dto.avatar_url = await self._get_avatar_url(updated_profile.avatar_file_id)

        return profile_dto

    async def delete_profile(self) -> bool:
        """Удаление профиля"""
        # Получаем текущий профиль для проверки аватара
        profile = self.profile_repo.get_profile_by_user_id(self.user_id)

        # Удаляем аватарку пользователя, если есть
        if profile and profile.avatar_file_id:
            try:
                await self.file_service.delete_file(profile.avatar_file_id)
            except Exception as e:
                logger.error(f"Failed to delete avatar file: {e}")

        # Удаляем профиль
        result = self.profile_repo.delete_profile(self.user_id)

        if not result:
            raise HTTPException(
                detail="Профиль не найден.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return result

    async def upload_avatar(
            self,
            file: UploadFile,
            description: Optional[str] = None
    ) -> AvatarResponse:
        """Загрузка/обновление аватарки"""
        # Проверяем существование профиля
        profile = self.profile_repo.get_profile_by_user_id(self.user_id)
        if not profile:
            raise HTTPException(
                detail="Профиль не найден. Сначала создайте профиль.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Получаем старую аватарку
        old_avatar = self.profile_repo.get_user_avatar(self.user_id)

        # Загружаем новую аватарку через FileService
        upload_result: FileUploadResponse = await self.file_service.upload_file(
            file=file,
            file_type=GlobalFileType.AVATAR,
            user_id=self.user_id,
            metadata={
                "description": description or "user avatar",
                "user_id": str(self.user_id)
            },
            public=True  # Аватары публичные
        )

        # Обновляем профиль с новой аватаркой
        self.profile_repo.update_user_avatar(self.user_id, upload_result.file_id)

        # Удаляем старую аватарку
        if old_avatar:
            try:
                await self.file_service.delete_file(old_avatar.id)
            except Exception as e:
                logger.error(f"Failed to delete old avatar: {e}")

        return AvatarResponse(
            file_id=upload_result.file_id,
            avatar_url=await self.file_service.get_file_url(
                upload_result.file_id,
                user_id=self.user_id,
                expires_in=AVATAR_URL_EXPIRY,
            ),
            original_filename=upload_result.original_filename,
            mime_type=upload_result.mime_type,
            size_bytes=upload_result.size_bytes
        )

    async def delete_avatar(self) -> DeleteAvatarResponse:
        """Удаление аватарки"""
        # Проверяем существование профиля
        profile = self.profile_repo.get_profile_by_user_id(self.user_id)
        if not profile:
            raise HTTPException(
                detail="Профиль не найден.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Получаем текущую аватарку
        current_avatar = self.profile_repo.get_user_avatar(self.user_id)
        deleted_file_id = current_avatar.id if current_avatar else None

        if current_avatar:
            # Удаляем файл через FileService
            try:
                await self.file_service.delete_file(current_avatar.id)
            except Exception as e:
                logger.error(f"Failed to delete avatar file: {e}")
                raise HTTPException(
                    detail="Не удалось удалить файл аватарки.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Обновляем профиль (убираем ссылку на аватар)
            self.profile_repo.update_user_avatar(self.user_id, None)

        return DeleteAvatarResponse(
            status="success",
            message="Аватарка успешно удалена.",
            deleted_file_id=deleted_file_id
        )

    async def get_avatar_url(self) -> Optional[str]:
        """Получение URL аватарки текущего пользователя"""
        profile = self.profile_repo.get_profile_by_user_id(self.user_id)
        if not profile or not profile.avatar_file_id:
            return None

        return await self._get_avatar_url(profile.avatar_file_id)
