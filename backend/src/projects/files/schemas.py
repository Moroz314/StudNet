from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ========== Request Models ==========

class AttachFileToProjectRequest(BaseModel):
    """Модель запроса для привязки файла к проекту"""
    file_id: UUID = Field(..., description="ID файла, полученный при загрузке через /files/upload")
    workspace_id: UUID = Field(..., description="ID рабочего пространства проекта")
    description: Optional[str] = Field(None, description="Описание файла")
    tags: Optional[List[str]] = Field(None, description="Теги для поиска и категоризации")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Дизайн-макет главной страницы",
                "tags": ["дизайн", "макет", "figma"]
            }
        }
    )


class UpdateProjectFileRequest(BaseModel):
    """Модель запроса для обновления метаданных файла проекта"""
    description: Optional[str] = Field(None, description="Новое описание файла")
    tags: Optional[List[str]] = Field(None, description="Новые теги")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Обновленное описание файла",
                "tags": ["обновленный", "тег"]
            }
        }
    )


class SetProjectAvatarRequest(BaseModel):
    """Модель запроса для установки аватара проекта"""
    file_id: UUID = Field(..., description="ID файла изображения, загруженного через /files/upload с file_type=project_avatar")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


# ========== Response Models ==========

class ProjectFileResponse(BaseModel):
    """Ответ с информацией о файле проекта"""
    id: UUID = Field(..., description="Уникальный идентификатор файла")
    original_filename: str = Field(..., description="Оригинальное имя файла")
    file_type: str = Field(..., description="Тип файла")
    mime_type: str = Field(..., description="MIME-тип файла")
    size_bytes: int = Field(..., description="Размер файла в байтах")
    uploaded_by: Optional[int] = Field(None, description="ID пользователя, загрузившего файл")
    project_id: Optional[UUID] = Field(None, description="ID проекта, к которому привязан файл")
    workspace_id: Optional[UUID] = Field(None, description="ID рабочего пространства")
    description: Optional[str] = Field(None, description="Описание файла")
    tags: Optional[List[str]] = Field(None, description="Теги файла")
    uploaded_at: datetime = Field(..., description="Дата и время загрузки файла")
    download_url: Optional[str] = Field(None, description="URL для скачивания файла")
    preview_url: Optional[str] = Field(None, description="URL для предпросмотра (только для изображений)")

    model_config = ConfigDict(from_attributes=True)


class ProjectFileListResponse(BaseModel):
    """Ответ со списком файлов проекта"""
    files: List[ProjectFileResponse] = Field(..., description="Список файлов")
    total: int = Field(..., description="Общее количество файлов")
    limit: int = Field(..., description="Лимит на странице")
    offset: int = Field(..., description="Смещение для пагинации")

    model_config = ConfigDict(from_attributes=True)


class ProjectAvatarResponse(BaseModel):
    """Ответ с информацией об аватаре проекта"""
    file_id: UUID = Field(..., description="ID файла аватара")
    avatar_url: str = Field(..., description="URL для доступа к аватару")
    original_filename: str = Field(..., description="Оригинальное имя файла")
    mime_type: str = Field(..., description="MIME-тип изображения")
    size_bytes: int = Field(..., description="Размер файла в байтах")
    project_id: UUID = Field(..., description="ID проекта")
    uploaded_at: datetime = Field(..., description="Дата и время загрузки")

    model_config = ConfigDict(from_attributes=True)


class DownloadUrlResponse(BaseModel):
    """Ответ с URL для скачивания файла"""
    url: str = Field(..., description="URL для скачивания")
    expires_in: int = Field(..., description="Время жизни ссылки в секундах")
    file_id: UUID = Field(..., description="ID файла")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://s3.amazonaws.com/bucket/file.pdf?signature=...",
                "expires_in": 3600,
                "file_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


class DeleteFileResponse(BaseModel):
    """Ответ при удалении/отвязке файла"""
    status: str = Field(..., description="Статус операции")
    message: str = Field(..., description="Сообщение о результате")
    file_id: Optional[UUID] = Field(None, description="ID файла")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "File detached successfully",
                "file_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )