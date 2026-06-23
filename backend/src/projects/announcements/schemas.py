from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ========== Request Models ==========

class AnnouncementCreate(BaseModel):
    """Создание объявления"""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    questions: List[str] = Field(default_factory=list)
    file_ids: Optional[List[UUID]] = Field(None, description="ID файлов для прикрепления")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Набор в команду разработки",
                "content": "Ищем разработчиков для нового проекта...",
                "questions": ["Какой у вас опыт?", "Какие технологии знаете?"],
                "file_ids": ["550e8400-e29b-41d4-a716-446655440000"]
            }
        }
    )


class AnnouncementUpdate(BaseModel):
    """Обновление объявления"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    questions: Optional[List[str]] = None
    file_ids: Optional[List[UUID]] = Field(None, description="ID файлов для прикрепления")


class ApplicationCreate(BaseModel):
    """Создание заявки"""
    content: str = Field(..., min_length=1)
    links: Optional[List[str]] = None
    file_ids: Optional[List[UUID]] = Field(None, description="ID файлов для прикрепления")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Я хочу присоединиться к проекту...",
                "links": ["https://github.com/username"],
                "file_ids": ["550e8400-e29b-41d4-a716-446655440000"]
            }
        }
    )


class ApplicationUpdate(BaseModel):
    """Обновление заявки"""
    content: Optional[str] = None
    links: Optional[List[str]] = None
    file_ids: Optional[List[UUID]] = Field(None, description="ID файлов для прикрепления")


class VoteRequest(BaseModel):
    """Запрос на голосование"""
    vote_type: str = Field(..., pattern="^(like|dislike|remove)$")


# ========== Response Models ==========

class FileResponse(BaseModel):
    """Ответ с информацией о файле"""
    id: UUID
    url: str
    original_filename: str
    mime_type: str
    size_bytes: int


class CreatorResponse(BaseModel):
    """Информация о создателе"""
    user_id: int
    name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class UserShortResponse(BaseModel):
    """Краткая информация о пользователе"""
    user_id: int
    name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class ProjectShortResponse(BaseModel):
    """Краткая информация о проекте для ленты"""
    project_id: UUID
    project_name: str
    project_description: Optional[str] = None
    project_status: Optional[str] = None


class AnnouncementFeedItem(BaseModel):
    """Элемент ленты объявлений"""
    id: UUID
    title: str
    content: str
    project_id: UUID
    workspace_id: UUID
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator: CreatorResponse
    project: Optional[ProjectShortResponse] = None
    applications_count: int = 0
    questions_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AnnouncementResponse(BaseModel):
    """Ответ с объявлением"""
    id: UUID
    title: str
    content: str
    questions: List[str]
    project_id: UUID
    workspace_id: UUID
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    files: List[FileResponse] = []
    creator: CreatorResponse
    applications_count: int = 0
    has_user_application: bool = False
    user_application_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class AnnouncementListResponse(BaseModel):
    """Список объявлений"""
    items: List[AnnouncementResponse]
    total: int
    skip: int
    limit: int


class AnnouncementFeedResponse(BaseModel):
    """Лента объявлений (публичный доступ)"""
    items: List[AnnouncementFeedItem]
    total: int
    skip: int
    limit: int


class ApplicationResponse(BaseModel):
    """Ответ с заявкой"""
    id: UUID
    announcement_id: UUID
    user_id: int
    content: str
    links: List[str] = []
    status: str
    likes_count: int = 0
    dislikes_count: int = 0
    user_vote: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    files: List[FileResponse] = []
    user: UserShortResponse
    announcement_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    """Список заявок"""
    items: List[ApplicationResponse]
    total: int
    skip: int
    limit: int