from typing import Optional, List, BinaryIO, Dict, Any, Tuple
from uuid import UUID
import logging
import mimetypes
import json
import os
from pathlib import Path
from collections import defaultdict

from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, Depends

from ..database.repositories.files import FileRepository
from ..database.s3.base import S3Service
from ..database.core import get_db
from .schemas import (
    FileType, FileValidationConfig, FILE_VALIDATION_CONFIGS,
    FileUploadResponse, FileInfoResponse
)

logger = logging.getLogger(__name__)


class FileService:
    def __init__(
            self,
            session: Session
    ):
        self.session = session
        self.file_repo = FileRepository(session)
        # Кэш для S3 сервисов по bucket
        self._s3_services_cache: Dict[str, S3Service] = {}

    def _get_s3_service(self, bucket: str) -> S3Service:
        """Создает или возвращает из кэша S3Service для конкретного bucket"""
        if bucket not in self._s3_services_cache:
            self._s3_services_cache[bucket] = S3Service(bucket)
        return self._s3_services_cache[bucket]

    @staticmethod
    def _to_public_url(url: str) -> str:
        """Replace internal MinIO URL with browser-accessible public URL."""
        internal_origin = (os.getenv('S3_URL') or '').rstrip('/')
        public_origin = (os.getenv('S3_PUBLIC_URL') or '').rstrip('/')
        if internal_origin and public_origin and url.startswith(internal_origin):
            return f"{public_origin}{url[len(internal_origin):]}"
        return url

    def _get_bucket_for_file_type(self, file_type: FileType) -> str:
        """Определение корзины S3 для типа файла"""
        import os
        bucket_mapping = {
            FileType.AVATAR: os.getenv('S3_AVATARS_BUCKET', 'avatars'),
            FileType.PROJECT_AVATAR: os.getenv('S3_AVATARS_BUCKET', 'avatars'),
            FileType.PROJECT_FILE: os.getenv('S3_PROJECT_FILES_BUCKET', 'project-files'),
            FileType.MESSAGE_ATTACHMENT: os.getenv('S3_MEDIA_BUCKET', 'media-bucket'),
            FileType.TASK_ATTACHMENT: os.getenv('S3_PROJECT_FILES_BUCKET', 'project-files'),
            FileType.ANNOUNCEMENT_FILE: os.getenv('S3_ANNOUNCEMENT_BUCKET', 'announcement-bucket'),
            FileType.APPLICATION_FILE: os.getenv('S3_ANNOUNCEMENT_BUCKET', 'announcement-bucket'),
            FileType.PROJECT_POST_FILE: os.getenv('S3_MEDIA_BUCKET', 'media-bucket'),
            FileType.USER_DOCUMENT: os.getenv('S3_PROJECT_FILES_BUCKET', 'project-files'),
            FileType.OTHER: os.getenv('S3_PROJECT_FILES_BUCKET', 'project-files'),
        }
        return bucket_mapping.get(file_type, os.getenv('S3_PROJECT_FILES_BUCKET', 'project-files'))

    def _generate_s3_key(self, file_type: FileType, original_filename: str, user_id: int) -> str:
        """Генерация уникального ключа для S3"""
        from uuid import uuid4
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y/%m/%d")
        unique_id = uuid4()
        safe_filename = original_filename.replace(" ", "_")

        prefix_mapping = {
            FileType.AVATAR: f"avatars/{user_id}",
            FileType.PROJECT_AVATAR: f"project-avatars/{timestamp}",
            FileType.PROJECT_FILE: f"projects/{timestamp}",
            FileType.MESSAGE_ATTACHMENT: f"messages/{timestamp}",
            FileType.TASK_ATTACHMENT: f"tasks/{timestamp}",
            FileType.ANNOUNCEMENT_FILE: f"announcements/{timestamp}",
            FileType.APPLICATION_FILE: f"applications/{timestamp}",
            FileType.PROJECT_POST_FILE: f"posts/{timestamp}",
            FileType.USER_DOCUMENT: f"users/{user_id}/documents",
            FileType.OTHER: f"other/{timestamp}",
        }

        prefix = prefix_mapping.get(file_type, f"files/{timestamp}")
        return f"{prefix}/{unique_id}/{safe_filename}"

    def _validate_file_size(
            self,
            file: UploadFile,
            file_type: FileType,
            config: FileValidationConfig
    ) -> Tuple[bool, str]:
        """Валидация размера файла согласно конфигурации"""
        # Определяем размер файла
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

        max_size_bytes = config.max_size_mb * 1024 * 1024
        if size > max_size_bytes:
            return False, f"File size exceeds {config.max_size_mb}MB limit. Actual: {size / (1024 * 1024):.2f}MB"

        return True, ""

    async def validate_files_batch(
            self,
            file_ids: List[UUID],
            file_type: FileType,
            user_id: int
    ) -> List[UUID]:
        """
        Валидация списка файлов:
        - все файлы должны существовать
        - все файлы должны принадлежать пользователю
        - все файлы должны соответствовать указанному типу
        Возвращает список валидных ID.
        """
        if not file_ids:
            return []

        files_dict = self.file_repo.get_files_by_ids_and_type(
            file_ids=file_ids,
            file_type=file_type.value,
            user_id=user_id
        )

        missing_ids = set(file_ids) - set(files_dict.keys())
        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Files not found, wrong type, or not owned by user: {list(missing_ids)}"
            )

        return file_ids

    async def get_file_urls_batch(
            self,
            file_ids: List[UUID],
            user_id: int,
            expires_in: int = 3600
    ) -> Dict[UUID, str]:
        """
        Получение URL для списка файлов.
        Оптимизировано: группирует файлы по bucket и типу, чтобы не создавать S3Service для каждого файла.
        """
        if not file_ids:
            return {}

        # Получаем все файлы из БД одним запросом
        files_dict = self.file_repo.get_files_by_ids(file_ids)

        # Проверяем, что все файлы найдены
        missing_ids = set(file_ids) - set(files_dict.keys())
        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Files not found: {list(missing_ids)}"
            )

        # Группируем файлы по bucket (который определяется по file_type)
        files_by_bucket: Dict[str, List[tuple]] = defaultdict(list)

        for file_id, file_metadata in files_dict.items():
            file_type = FileType(file_metadata.file_type)
            bucket = self._get_bucket_for_file_type(file_type)
            files_by_bucket[bucket].append((file_id, file_metadata))

        # Для каждого bucket получаем S3 сервис (один на bucket)
        urls: Dict[UUID, str] = {}

        for bucket, bucket_files in files_by_bucket.items():
            s3_service = self._get_s3_service(bucket)

            for file_id, file_metadata in bucket_files:
                url = await s3_service.generate_presigned_url(
                    s3_key=file_metadata.s3_key,
                    expires_in=expires_in
                )
                urls[file_id] = self._to_public_url(url)

        return urls

    async def upload_file(
            self,
            file: UploadFile,
            file_type: FileType,
            user_id: int,
            metadata: Optional[Dict[str, str]] = None,
            public: bool = False
    ) -> FileUploadResponse:
        """Загрузка одного файла"""
        config = FILE_VALIDATION_CONFIGS.get(file_type, FileValidationConfig())

        # Проверяем только размер файла
        is_valid, error_msg = self._validate_file_size(file, file_type, config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        bucket = self._get_bucket_for_file_type(file_type)
        s3_service = self._get_s3_service(bucket)

        s3_key = self._generate_s3_key(file_type, file.filename, user_id)
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'

        try:
            file.file.seek(0)
            await s3_service.upload_fileobj(
                file_obj=file.file,
                s3_key=s3_key,
                content_type=content_type,
                metadata=metadata or {},
                public=public
            )

            file.file.seek(0, 2)
            size_bytes = file.file.tell()
            file.file.seek(0)

            file_metadata = self.file_repo.create_file_metadata(
                s3_key=s3_key,
                original_filename=file.filename,
                file_type=file_type.value,
                mime_type=content_type,
                size_bytes=size_bytes,
                uploaded_by=user_id
            )

            url = self._to_public_url(
                await s3_service.generate_presigned_url(
                    s3_key=s3_key,
                    expires_in=86400,
                )
            )

            return FileUploadResponse(
                file_id=file_metadata.id,
                original_filename=file_metadata.original_filename,
                file_type=file_metadata.file_type,
                size_bytes=file_metadata.size_bytes,
                mime_type=file_metadata.mime_type,
                uploaded_at=file_metadata.uploaded_at,
                url=url
            )

        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    async def upload_multiple_files(
            self,
            files: List[UploadFile],
            file_type: FileType,
            user_id: int,
            metadata: Optional[Dict[str, str]] = None,
            public: bool = False
    ) -> Dict[str, Any]:
        """Загрузка нескольких файлов"""
        uploaded = []
        failed = []

        for file in files:
            try:
                result = await self.upload_file(file, file_type, user_id, metadata, public)
                uploaded.append(result.model_dump())
            except HTTPException as e:
                failed.append({
                    "filename": file.filename,
                    "error": e.detail
                })
            except Exception as e:
                failed.append({
                    "filename": file.filename,
                    "error": str(e)
                })

        return {
            "files": uploaded,
            "failed": failed,
            "total": len(files),
            "success_count": len(uploaded),
            "failed_count": len(failed)
        }

    async def get_file_info(
            self,
            file_id: UUID,
            user_id: Optional[int] = None
    ) -> FileInfoResponse:
        """Получение информации о файле"""
        file_metadata = self.file_repo.get_file_by_id(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        bucket = self._get_bucket_for_file_type(FileType(file_metadata.file_type))
        s3_service = self._get_s3_service(bucket)
        url = self._to_public_url(
            await s3_service.generate_presigned_url(
                s3_key=file_metadata.s3_key,
                expires_in=3600,
            )
        )

        return FileInfoResponse(
            id=file_metadata.id,
            original_filename=file_metadata.original_filename,
            file_type=file_metadata.file_type,
            mime_type=file_metadata.mime_type,
            size_bytes=file_metadata.size_bytes,
            uploaded_by=file_metadata.uploaded_by,
            uploaded_at=file_metadata.uploaded_at,
            url=url
        )

    async def delete_file(
            self,
            file_id: UUID
    ) -> Dict[str, Any]:
        """Удаление файла"""
        file_metadata = self.file_repo.get_file_by_id(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        try:
            bucket = self._get_bucket_for_file_type(FileType(file_metadata.file_type))
            s3_service = self._get_s3_service(bucket)
            await s3_service.delete_file(file_metadata.s3_key)

            success = self.file_repo.delete_file_metadata(file_id)

            if success:
                return {
                    "success": True,
                    "message": "File deleted successfully",
                    "file_id": file_id
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to delete file metadata")

        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

    async def get_file_url(
            self,
            file_id: UUID,
            user_id: Optional[int] = None,
            expires_in: int = 3600
    ) -> str:
        """Получение URL для доступа к файлу (с подписью для приватных файлов)"""
        file_metadata = self.file_repo.get_file_by_id(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        bucket = self._get_bucket_for_file_type(FileType(file_metadata.file_type))
        s3_service = self._get_s3_service(bucket)

        return self._to_public_url(
            await s3_service.generate_presigned_url(
                s3_key=file_metadata.s3_key,
                expires_in=expires_in
            )
        )

    async def get_user_files(
            self,
            user_id: int,
            file_type: Optional[FileType] = None,
            limit: int = 100
    ) -> List[FileInfoResponse]:
        """Получение всех файлов пользователя"""
        files = self.file_repo.get_user_files(
            user_id=user_id,
            file_type=file_type.value if file_type else None,
            limit=limit
        )

        result = []
        for file_metadata in files:
            url = self._to_public_url(
                await self._get_s3_service(
                    self._get_bucket_for_file_type(FileType(file_metadata.file_type))
                ).generate_presigned_url(
                    s3_key=file_metadata.s3_key,
                    expires_in=3600,
                )
            )

            result.append(FileInfoResponse(
                id=file_metadata.id,
                original_filename=file_metadata.original_filename,
                file_type=file_metadata.file_type,
                mime_type=file_metadata.mime_type,
                size_bytes=file_metadata.size_bytes,
                uploaded_by=file_metadata.uploaded_by,
                uploaded_at=file_metadata.uploaded_at,
                url=url
            ))

        return result


def get_file_service(
        db: Session = Depends(get_db)
) -> FileService:
    """Dependency для получения экземпляра FileService"""
    return FileService(db)