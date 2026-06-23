from pydantic import BaseModel, Field, validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    """Типы файлов для валидации"""
    AVATAR = "avatar"
    PROJECT_FILE = "project_file"
    MESSAGE_ATTACHMENT = "message_attachment"
    PROJECT_AVATAR = "project_avatar"
    USER_DOCUMENT = "user_document"
    ANNOUNCEMENT_FILE = "announcement_file"
    APPLICATION_FILE = "application_file"
    PROJECT_POST_FILE = "project_post_file"
    TASK_ATTACHMENT = "task_attachment"
    OTHER = "other"


class FileValidationConfig(BaseModel):
    """Конфигурация валидации для разных типов файлов"""
    max_size_mb: int = 10


# Конфигурации для разных типов файлов (только ограничение по размеру)
FILE_VALIDATION_CONFIGS = {
    FileType.AVATAR: FileValidationConfig(
        max_size_mb=5
    ),
    FileType.PROJECT_AVATAR: FileValidationConfig(
        max_size_mb=5
    ),
    FileType.PROJECT_FILE: FileValidationConfig(
        max_size_mb=100
    ),
    FileType.MESSAGE_ATTACHMENT: FileValidationConfig(
        max_size_mb=25
    ),
    FileType.TASK_ATTACHMENT: FileValidationConfig(
        max_size_mb=50
    ),
    FileType.ANNOUNCEMENT_FILE: FileValidationConfig(
        max_size_mb=25
    ),
    FileType.APPLICATION_FILE: FileValidationConfig(
        max_size_mb=15
    ),
    FileType.PROJECT_POST_FILE: FileValidationConfig(
        max_size_mb=50
    ),
    FileType.USER_DOCUMENT: FileValidationConfig(
        max_size_mb=25
    ),
    FileType.OTHER: FileValidationConfig(
        max_size_mb=50
    )
}


class FileUploadRequest(BaseModel):
    """Запрос на загрузку файла"""
    file_type: FileType = Field(..., description="Тип файла для валидации")
    metadata: Optional[dict] = Field(default=None, description="Дополнительная метаинформация")


class FileUploadResponse(BaseModel):
    """Ответ после загрузки файла"""
    file_id: UUID = Field(..., description="ID загруженного файла")
    original_filename: str = Field(..., description="Оригинальное имя файла")
    file_type: str = Field(..., description="Тип файла")
    size_bytes: int = Field(..., description="Размер файла в байтах")
    mime_type: str = Field(..., description="MIME тип файла")
    uploaded_at: datetime = Field(..., description="Дата загрузки")
    url: Optional[str] = Field(None, description="URL для доступа к файлу (если публичный)")


class MultipleFilesUploadResponse(BaseModel):
    """Ответ при загрузке нескольких файлов"""
    files: List[FileUploadResponse] = Field(..., description="Загруженные файлы")
    failed: List[dict] = Field(default=[], description="Неудачные загрузки")
    total: int = Field(..., description="Всего файлов")
    success_count: int = Field(..., description="Успешно загружено")
    failed_count: int = Field(..., description="Неудачных загрузок")


class FileInfoResponse(BaseModel):
    """Информация о файле"""
    id: UUID
    original_filename: str
    file_type: str
    mime_type: str
    size_bytes: int
    uploaded_by: Optional[int]
    uploaded_at: datetime
    url: Optional[str] = None


class FileDeleteResponse(BaseModel):
    """Ответ при удалении файла"""
    success: bool
    message: str
    file_id: UUID


class FileValidationError(BaseModel):
    """Ошибка валидации файла"""
    filename: str
    error: str