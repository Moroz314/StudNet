from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from ...database.redis.redis_presence import UserStatus
from enum import Enum
import uuid


class FileTypeEnum(str, Enum):
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


class AvatarResponse(BaseModel):
    """Ответ при загрузке аватарки"""
    file_id: uuid.UUID
    avatar_url: str
    original_filename: str
    mime_type: str
    size_bytes: int

    class Config:
        from_attributes = True


class DeleteAvatarResponse(BaseModel):
    """Ответ при удалении аватарки"""
    status: str
    message: str
    deleted_file_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class UserProfileCreate(BaseModel):
    """Данные для создания профиля"""
    name: str = Field(..., min_length=1, max_length=100)
    lastname: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    birth_date: date
    university: str = Field(..., min_length=1, max_length=200)
    faculty: Optional[str] = Field(None, max_length=200)
    course: int = Field(..., ge=1, le=6)
    info: str = Field(..., max_length=1000)
    interests: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    links: Optional[List[str]] = None

    class Config:
        from_attributes = True


class PresenceData(BaseModel):
    """Данные о присутствии пользователя"""
    status: UserStatus
    last_seen: datetime
    last_device: str

    class Config:
        from_attributes = True


class UserProfile(UserProfileCreate):
    """Полный профиль пользователя"""
    user_id: int
    avatar_file_id: Optional[uuid.UUID] = None
    avatar_url: Optional[str] = None
    presence_data: Optional[PresenceData] = None
    github_access_token: Optional[str] = None

    class Config:
        from_attributes = True


class UserProfileProjectItem(BaseModel):
    """Проект, в котором участвует пользователь (для просмотра профиля)"""
    project_id: uuid.UUID
    name: str
    description: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published_in_feed: bool = False
    feed_post_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class UserProfileProjectsResponse(BaseModel):
    items: List[UserProfileProjectItem]
    total: int
    offset: int
    limit: int


class UserProfileEdit(BaseModel):
    """Данные для редактирования профиля"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    lastname: Optional[str] = Field(None, min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    birth_date: Optional[date] = None
    university: Optional[str] = Field(None, min_length=1, max_length=200)
    faculty: Optional[str] = Field(None, max_length=200)
    course: Optional[int] = Field(None, ge=1, le=6)
    interests: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    info: Optional[str] = Field(None, max_length=1000)
    links: Optional[List[str]] = None

    class Config:
        from_attributes = True