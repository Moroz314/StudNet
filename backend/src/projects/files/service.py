import os
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status, UploadFile, Depends
from sqlalchemy.orm import Session

from ...users.auth.service.utils import verify_token
from ...database.core import get_db
from ...database.repositories.files import FileRepository
from ...database.repositories.project.core import ProjectRepository
from ...database.models import FileType
from ..validation import (
    require_project_admin, require_project_owner,
    require_workspace_access
)
from .schemas import *
from ...files.service import FileService
from ...files.schemas import FileType as GlobalFileType

DEFAULT_URL_EXPIRY = 3600
AVATAR_URL_EXPIRY = 86400


def get_project_files_service(
        db: Session = Depends(get_db),
        user_id: int = Depends(verify_token)
):
    file_repo = FileRepository(session=db)
    project_repo = ProjectRepository(session=db)
    file_service = FileService(session=db)

    return ProjectFilesService(
        file_repository=file_repo,
        project_repository=project_repo,
        file_service=file_service,
        user_id=user_id
    )


class ProjectFilesService:
    def __init__(
            self,
            file_repository: FileRepository,
            project_repository: ProjectRepository,
            file_service: FileService,
            user_id: int
    ):
        self.file_repo = file_repository
        self.project_repo = project_repository
        self.file_service = file_service
        self.user_id = user_id

    async def _get_file_urls_batch(
            self,
            files: List,
            expires_in: int = DEFAULT_URL_EXPIRY
    ) -> dict:
        """Получение URL для списка файлов через FileService"""
        if not files:
            return {}
        file_ids = [f.id for f in files]
        return await self.file_service.get_file_urls_batch(
            file_ids=file_ids,
            user_id=self.user_id,
            expires_in=expires_in
        )

    async def _validate_file_exists(self, file_id: UUID, expected_type: Optional[GlobalFileType] = None):
        """Проверка существования файла и опционально его типа"""
        file_info = await self.file_service.get_file_info(file_id, self.user_id)

        if expected_type and file_info.file_type != expected_type.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type mismatch. Expected: {expected_type.value}, got: {file_info.file_type}"
            )

        return file_info

    async def attach_file_to_project(
            self,
            file_id: UUID,
            project_id: UUID,
            workspace_id: UUID,
            description: Optional[str] = None,
            tags: Optional[List[str]] = None,
    ) -> ProjectFileResponse:
        """Привязка существующего файла к проекту"""
        # Проверка прав доступа
        require_workspace_access(
            self.project_repo, workspace_id, project_id, self.user_id
        )

        # Проверяем существование файла
        file_info = await self._validate_file_exists(file_id)

        # Привязываем файл к проекту
        project_file = self.file_repo.attach_file_to_project(
            file_id=file_id,
            project_id=project_id,
            uploaded_by=self.user_id,
            workspace_id=workspace_id,
            description=description,
            tags=tags
        )

        # Получаем URL для файла
        download_url = await self.file_service.get_file_url(
            file_id=file_id,
            user_id=self.user_id
        )

        return ProjectFileResponse(
            id=file_info.id,
            original_filename=file_info.original_filename,
            file_type=file_info.file_type,
            mime_type=file_info.mime_type,
            size_bytes=file_info.size_bytes,
            uploaded_by=file_info.uploaded_by,
            uploaded_at=file_info.uploaded_at,
            project_id=project_id,
            workspace_id=workspace_id,
            description=description,
            tags=tags,
            download_url=download_url,
            preview_url=download_url if file_info.mime_type.startswith('image/') else None,
        )

    async def list_project_files(
            self,
            project_id: UUID,
            workspace_id: UUID,
            limit: int = 100,
            offset: int = 0,
    ) -> ProjectFileListResponse:
        """Получение списка файлов проекта"""
        require_workspace_access(
            self.project_repo, workspace_id, project_id, self.user_id
        )

        # Получаем все файлы проекта
        files = self.file_repo.get_project_files(
            project_id=project_id,
            workspace_id=workspace_id,
            limit=limit
        )

        # Получаем URL для всех файлов одним batch-запросом
        urls = await self._get_file_urls_batch(files)

        # Формируем ответ
        result_files = []
        for file_meta in files:
            project_file = file_meta.project_files[0] if file_meta.project_files else None
            download_url = urls.get(file_meta.id)

            result_files.append(ProjectFileResponse(
                id=file_meta.id,
                original_filename=file_meta.original_filename,
                file_type=file_meta.file_type,
                mime_type=file_meta.mime_type,
                size_bytes=file_meta.size_bytes,
                uploaded_by=file_meta.uploaded_by,
                uploaded_at=file_meta.uploaded_at,
                project_id=project_file.project_id if project_file else None,
                workspace_id=project_file.workspace_id if project_file else None,
                description=project_file.description if project_file else None,
                tags=project_file.tags if project_file else None,
                download_url=download_url,
                preview_url=download_url if file_meta.mime_type and file_meta.mime_type.startswith('image/') else None,
            ))

        # Применяем пагинацию
        total = len(result_files)
        paginated_files = result_files[offset:offset + limit]

        return ProjectFileListResponse(
            files=paginated_files,
            total=total,
            limit=limit,
            offset=offset
        )

    async def get_file_metadata(
            self,
            file_id: UUID,
            project_id: UUID,
            workspace_id: UUID,
    ) -> ProjectFileResponse:
        """Получение метаданных файла проекта"""
        # Проверяем связь файла с проектом
        project_file = self.file_repo.get_project_file_by_id(file_id, project_id)
        if not project_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in this project"
            )

        require_workspace_access(
            self.project_repo,
            project_file.workspace_id or workspace_id,
            project_id,
            self.user_id
        )

        # Получаем метаданные файла
        file_info = await self.file_service.get_file_info(file_id, self.user_id)
        download_url = await self.file_service.get_file_url(file_id, self.user_id)

        return ProjectFileResponse(
            id=file_info.id,
            original_filename=file_info.original_filename,
            file_type=file_info.file_type,
            mime_type=file_info.mime_type,
            size_bytes=file_info.size_bytes,
            uploaded_by=file_info.uploaded_by,
            uploaded_at=file_info.uploaded_at,
            project_id=project_file.project_id,
            workspace_id=project_file.workspace_id,
            description=project_file.description,
            tags=project_file.tags,
            download_url=download_url,
            preview_url=download_url if file_info.mime_type.startswith('image/') else None,
        )

    async def update_file_metadata(
            self,
            file_id: UUID,
            project_id: UUID,
            workspace_id: UUID,
            description: Optional[str] = None,
            tags: Optional[List[str]] = None,
    ) -> ProjectFileResponse:
        """Обновление метаданных файла проекта"""
        project_file = self.file_repo.get_project_file_by_id(file_id, project_id)
        if not project_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in this project"
            )

        require_workspace_access(
            self.project_repo,
            project_file.workspace_id or workspace_id,
            project_id,
            self.user_id
        )

        # Обновляем метаданные
        if description is not None:
            project_file.description = description
        if tags is not None:
            project_file.tags = tags

        self.file_repo.session.commit()
        self.file_repo.session.refresh(project_file)

        return await self.get_file_metadata(file_id, project_id, workspace_id)

    async def detach_file_from_project(
            self,
            file_id: UUID,
            project_id: UUID,
            workspace_id: UUID,
            delete_permanently: bool = False
    ) -> bool:
        """Отвязка файла от проекта"""
        project_file = self.file_repo.get_project_file_by_id(file_id, project_id)
        if not project_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in this project"
            )

        require_workspace_access(
            self.project_repo,
            project_file.workspace_id or workspace_id,
            project_id,
            self.user_id
        )

        # Отвязываем файл от проекта
        self.file_repo.detach_file_from_project(file_id, project_id)

        # Если нужно удалить полностью
        if delete_permanently:
            await self.file_service.delete_file(file_id, self.user_id)

        return True

    async def get_download_url(
            self,
            file_id: UUID,
            expires_in: int = 3600,
            project_id: Optional[UUID] = None,
            workspace_id: Optional[UUID] = None
    ) -> str:
        """Получение ссылки для скачивания файла"""
        if project_id:
            project_file = self.file_repo.get_project_file_by_id(file_id, project_id)
            if not project_file:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="File does not belong to the specified project"
                )

            if workspace_id:
                require_workspace_access(
                    self.project_repo, workspace_id, project_id, self.user_id
                )

        return await self.file_service.get_file_url(
            file_id=file_id,
            user_id=self.user_id,
            expires_in=expires_in
        )

    # ========== AVATARS ==========

    async def set_project_avatar(
            self,
            project_id: UUID,
            file_id: UUID,
    ) -> ProjectAvatarResponse:
        """Установка аватара проекта"""
        require_project_owner(self.project_repo, project_id, self.user_id)

        # Проверяем, что файл существует и это изображение
        file_info = await self._validate_file_exists(file_id, GlobalFileType.PROJECT_AVATAR)

        if not file_info.mime_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )

        # Получаем старый аватар
        old_avatar = self.file_repo.get_project_avatar(project_id)

        # Обновляем проект
        self.project_repo.update_project(project_id, avatar_file_id=file_id)

        if old_avatar:
            await self.file_service.delete_file(old_avatar.id)

        # Получаем URL для аватара
        avatar_url = await self.file_service.get_file_url(
            file_id=file_id,
            user_id=self.user_id,
            expires_in=AVATAR_URL_EXPIRY
        )

        return ProjectAvatarResponse(
            file_id=file_id,
            avatar_url=avatar_url,
            original_filename=file_info.original_filename,
            mime_type=file_info.mime_type,
            size_bytes=file_info.size_bytes,
            project_id=project_id,
            uploaded_at=file_info.uploaded_at,
        )

    async def get_project_avatar(
            self,
            project_id: UUID,
    ) -> ProjectAvatarResponse:
        """Получение аватара проекта"""
        avatar = self.file_repo.get_project_avatar(project_id)
        if not avatar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project avatar not found"
            )

        avatar_url = await self.file_service.get_file_url(
            file_id=avatar.id,
            user_id=self.user_id,
            expires_in=AVATAR_URL_EXPIRY
        )

        return ProjectAvatarResponse(
            file_id=avatar.id,
            avatar_url=avatar_url,
            original_filename=avatar.original_filename,
            mime_type=avatar.mime_type,
            size_bytes=avatar.size_bytes,
            project_id=project_id,
            uploaded_at=avatar.uploaded_at,
        )

    async def remove_project_avatar(
            self,
            project_id: UUID,
    ) -> bool:
        """Удаление аватара проекта (отвязка)"""
        require_project_owner(self.project_repo, project_id, self.user_id)

        avatar = self.file_repo.get_project_avatar(project_id)
        if not avatar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project avatar not found"
            )

        # Отвязываем аватар от проекта
        self.project_repo.update_project(project_id, avatar_file_id=None)

        await self.file_service.delete_file(avatar.id)

        return True