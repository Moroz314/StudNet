from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ========== USER SCHEMAS ==========

class UserProfileBriefResponse(BaseModel):
    """Краткая информация о пользователе"""
    user_id: int
    name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ========== FILE SCHEMAS ==========

class FileResponse(BaseModel):
    """Ответ с информацией о файле и временной ссылкой"""
    id: UUID
    url: str
    original_filename: str
    mime_type: str
    size_bytes: int

    model_config = ConfigDict(from_attributes=True)


# ========== POST SCHEMAS ==========

class ProjectFeedResponse(BaseModel):
    """Пост проекта для ленты"""
    id: UUID = Field(..., description="ID поста")
    project_id: UUID = Field(..., description="ID проекта")
    name: str = Field(..., description="Название проекта")
    description: Optional[str] = Field(None, description="Описание поста")
    category: Optional[str] = Field(None, description="Категория проекта")
    tags: Optional[List[str]] = Field(None, description="Теги проекта")
    github_links: Optional[List[str]] = Field(None, description="GitHub ссылки")
    likes_count: int = Field(0, description="Количество лайков")
    is_liked_by_user: bool = Field(False, description="Лайкнут ли текущим пользователем")
    is_from_friend: bool = Field(False, description="Создан ли другом")
    created_at: datetime = Field(..., description="Дата создания поста")
    published_at: Optional[datetime] = Field(None, description="Дата публикации")

    # Файлы с временными ссылками
    avatar: Optional[FileResponse] = Field(None, description="Аватар проекта")
    media_files: List[FileResponse] = Field(default_factory=list, description="Медиафайлы поста")

    # Создатель
    creator: UserProfileBriefResponse = Field(..., description="Создатель проекта")

    # Статистика
    participants_count: int = Field(0, description="Количество участников проекта")

    model_config = ConfigDict(from_attributes=True)


class FeedResponse(BaseModel):
    """Ответ с лентой постов"""
    items: List[ProjectFeedResponse] = Field(..., description="Список постов")
    total: int = Field(..., description="Общее количество")
    limit: int = Field(..., description="Лимит на странице")
    offset: int = Field(..., description="Смещение")
    has_next: bool = Field(..., description="Есть ли следующая страница")

    model_config = ConfigDict(from_attributes=True)


# ========== LIKE SCHEMAS ==========

class LikeResponse(BaseModel):
    """Ответ на лайк поста"""
    post_id: UUID = Field(..., description="ID поста")
    likes_count: int = Field(..., description="Количество лайков")
    is_liked: bool = Field(..., description="Статус лайка")

    model_config = ConfigDict(from_attributes=True)


# ========== CATEGORY SCHEMAS ==========

class CategoryResponse(BaseModel):
    """Категория с количеством постов"""
    name: str = Field(..., description="Название категории")
    projects_count: int = Field(..., description="Количество проектов в категории")

    model_config = ConfigDict(from_attributes=True)


# ========== TRENDING SCHEMAS ==========

class TrendingProjectResponse(BaseModel):
    """Трендовый пост"""
    project: ProjectFeedResponse = Field(..., description="Пост")
    likes_in_period: int = Field(..., description="Лайков за период")
    trend_score: float = Field(..., description="Оценка трендовости")

    model_config = ConfigDict(from_attributes=True)


# ========== PUBLISH REQUEST SCHEMAS ==========

class PublishProjectRequest(BaseModel):
    """Запрос на публикацию/обновление поста"""
    media_file_ids: List[UUID] = Field(
        default_factory=list,
        description="ID файлов для отображения в посте (загружены через /files/upload с file_type=project_post_file)"
    )
    description: Optional[str] = Field(None, description="Описание поста")
    github_links: Optional[List[str]] = Field(None, description="Ссылки на GitHub репозитории")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "media_file_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                "description": "Описание проекта для ленты",
                "github_links": ["https://github.com/user/repo"]
            }
        }
    )


# ========== COMMENT USER SCHEMAS ==========

class CommentUserResponse(BaseModel):
    """Информация о пользователе в комментарии"""
    user_id: int = Field(..., description="ID пользователя")
    name: Optional[str] = Field(None, description="Имя")
    lastname: Optional[str] = Field(None, description="Фамилия")
    username: Optional[str] = Field(None, description="Username")
    avatar_url: Optional[str] = Field(None, description="URL аватара")

    model_config = ConfigDict(from_attributes=True)


# ========== COMMENT RESPONSE SCHEMAS ==========

class CommentResponse(BaseModel):
    """Ответ с комментарием"""
    id: int = Field(..., description="ID комментария")
    post_id: UUID = Field(..., description="ID поста")
    content: str = Field(..., description="Содержание")
    likes_count: int = Field(0, description="Количество лайков")
    replies_count: int = Field(0, description="Количество ответов")
    is_liked_by_user: bool = Field(False, description="Лайкнут ли текущим пользователем")
    is_edited: bool = Field(False, description="Отредактирован ли")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    user: CommentUserResponse = Field(..., description="Автор комментария")
    parent_id: Optional[int] = Field(None, description="ID родительского комментария")

    model_config = ConfigDict(from_attributes=True)


class CommentsResponse(BaseModel):
    """Ответ со списком комментариев"""
    items: List[CommentResponse] = Field(..., description="Список комментариев")
    total: int = Field(..., description="Общее количество")
    limit: int = Field(..., description="Лимит на странице")
    offset: int = Field(..., description="Смещение")
    has_next: bool = Field(..., description="Есть ли следующая страница")

    model_config = ConfigDict(from_attributes=True)


# ========== COMMENT REQUEST SCHEMAS ==========

class CommentCreateRequest(BaseModel):
    """Запрос на создание комментария"""
    content: str = Field(..., min_length=1, max_length=5000, description="Текст комментария")
    parent_id: Optional[int] = Field(None, description="ID родительского комментария (для ответов)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Отличный проект!",
                "parent_id": None
            }
        }
    )


class CommentUpdateRequest(BaseModel):
    """Запрос на обновление комментария"""
    content: str = Field(..., min_length=1, max_length=5000, description="Новый текст комментария")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Обновленный текст комментария"
            }
        }
    )


# ========== COMMENT LIKE SCHEMAS ==========

class CommentLikeResponse(BaseModel):
    """Ответ на лайк комментария"""
    comment_id: int = Field(..., description="ID комментария")
    likes_count: int = Field(..., description="Количество лайков")
    is_liked: bool = Field(..., description="Статус лайка")

    model_config = ConfigDict(from_attributes=True)