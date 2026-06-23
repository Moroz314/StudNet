from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import re
from ...database.models import ProjectStatus, ProjectParticipantStatus, InvitationStatus, ProjectRole, ProjectCategory


# Вспомогательные функции для валидации ссылок
def validate_url(url: str) -> str:
    # Простая проверка формата URL
    url_pattern = re.compile(
        r'^https?://'  # http:// или https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # домен
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # порт
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if not url_pattern.match(url):
        raise ValueError(f"Некорректный формат URL: {url}")
    return url


def validate_github_url(url: str) -> str:
    github_pattern = re.compile(
        r'^https?://(www\.)?github\.com/[\w-]+/[\w.-]+/?$',
        re.IGNORECASE
    )

    if not github_pattern.match(url):
        raise ValueError(f"Некорректный формат GitHub ссылки: {url}. "
                         f"Ожидается формат: https://github.com/username/repo")
    return url


# Response schemas
class UserProfileShort(BaseModel):
    user_id: int
    name: Optional[str]
    lastname: Optional[str]
    username: Optional[str]

    class Config:
        from_attributes = True


class ChatShort(BaseModel):
    id: UUID
    name: str
    type: str

    class Config:
        from_attributes = True


class WorkspaceParticipantInfo(BaseModel):
    """Информация об участии в конкретном workspace"""
    workspace_id: UUID
    joined_at: datetime
    workspace_name: str
    is_main: bool

    class Config:
        from_attributes = True


# Invitation schemas
class InvitationBase(BaseModel):
    role: Optional[ProjectRole] = ProjectRole.OTHER
    permission_level: Optional[ProjectParticipantStatus] = ProjectParticipantStatus.VIEWER
    message: Optional[str] = Field(None, max_length=500)


class InvitationCreate(InvitationBase):
    user_ids: List[int] = Field(..., min_items=1, max_items=50)


class InvitationResponse(BaseModel):
    id: int
    project_id: UUID
    invited_user_id: int
    invited_by: int
    status: InvitationStatus
    role: ProjectRole
    permission_level: ProjectParticipantStatus
    invited_at: datetime
    responded_at: Optional[datetime]
    message: Optional[str]

    invited_user: UserProfileShort
    inviter: UserProfileShort

    class Config:
        from_attributes = True


class InvitationAction(BaseModel):
    action: str = Field(..., pattern="^(accept|reject)$")


def validate_links_list(v):
    """Общий валидатор для списка ссылок"""
    if v is None:
        return v
    if not isinstance(v, list):
        raise ValueError("links должен быть списком")
    validated_links = []
    for link in v:
        if not isinstance(link, str):
            raise ValueError(f"Ссылка должна быть строкой: {link}")
        validated_links.append(validate_url(link))
    return validated_links


def validate_github_links_list(v):
    if v is None:
        return v
    if not isinstance(v, list):
        raise ValueError("github_links должен быть списком")
    validated_links = []
    for link in v:
        if not isinstance(link, str):
            raise ValueError(f"GitHub ссылка должна быть строкой: {link}")
        validated_links.append(validate_github_url(link))

    # Проверка уникальности
    if len(validated_links) != len(set(validated_links)):
        raise ValueError("GitHub ссылки должны быть уникальными")
    return validated_links

# Project schemas
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    links: Optional[List[str]] = None
    github_links: Optional[List[str]] = None
    category: Optional[ProjectCategory] = None

    # Валидация всех ссылок проекта
    @field_validator('links')
    @classmethod
    def validate_project_links(cls, v):
        return validate_links_list(v)

    @field_validator('github_links')
    @classmethod
    def validate_github_links(cls, v):
        return validate_github_links_list(v)


class ProjectCreate(ProjectBase):
    create_chat: Optional[bool] = True



class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    tags: Optional[List[str]] = None
    links: Optional[List[str]] = None
    github_links: Optional[List[str]] = None
    category: Optional[ProjectCategory] = None

    # Валидация обновляемых ссылок
    @field_validator('links')
    @classmethod
    def validate_project_links(cls, v):
        return validate_links_list(v)

    @field_validator('github_links')
    @classmethod
    def validate_github_links(cls, v):
        return validate_github_links_list(v)


class ProjectWorkspaceResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    is_main: bool
    created_at: datetime
    updated_at: datetime
    chat: Optional[ChatShort]
    links: Optional[List[str]] = None
    github_links: Optional[List[str]] = None
    participants_count: Optional[int] = Field(0, description="Количество участников в workspace")

    class Config:
        from_attributes = True


class ProjectResponse(ProjectBase):
    id: UUID
    created_by: int
    status: ProjectStatus
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    creator: UserProfileShort
    workspaces: List[ProjectWorkspaceResponse]
    channel: Optional[ChatShort] = None
    participants_count: Optional[int] = Field(0, description="Общее количество участников проекта")
    pending_invitations_count: Optional[int] = Field(0, description="Количество ожидающих приглашений")

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    status: ProjectStatus
    category: Optional[ProjectCategory] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    participant_count: int
    unread_messages_count: Optional[int] = 0
    tags: Optional[List[str]] = None
    links: Optional[List[str]] = None
    github_links: Optional[List[str]] = None
    pending_invitations_count: Optional[int] = 0

    class Config:
        from_attributes = True


# Workspace schemas
class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    links: Optional[List[str]] = None
    github_links: Optional[List[str]] = None

    # Валидация всех ссылок рабочего пространства
    @field_validator('links')
    @classmethod
    def validate_workspace_links(cls, v):
        return validate_links_list(v)

    @field_validator('github_links')
    @classmethod
    def validate_github_links(cls, v):
        return validate_github_links_list(v)


class WorkspaceCreate(WorkspaceBase):
    create_chat: bool = Field(default=True)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    links: Optional[List[str]] = None
    github_links: Optional[List[str]] = None

    # Валидация обновляемых ссылок
    @field_validator('links')
    @classmethod
    def validate_workspace_links(cls, v):
        return validate_links_list(v)

    @field_validator('github_links')
    @classmethod
    def validate_github_links(cls, v):
        return validate_github_links_list(v)


class WorkspaceResponse(WorkspaceBase):
    id: UUID
    project_id: UUID
    is_main: bool
    created_at: datetime
    updated_at: datetime
    chat: Optional[ChatShort]
    participants: List['ParticipantResponse']
    participants_count: Optional[int] = Field(0, description="Количество участников в workspace")

    class Config:
        from_attributes = True


# Participant schemas
class ParticipantAdd(BaseModel):
    user_ids: List[int] = Field(..., min_items=1, max_items=50)
    role: Optional[ProjectRole] = ProjectRole.OTHER
    status: Optional[ProjectParticipantStatus] = ProjectParticipantStatus.VIEWER


class ParticipantUpdate(BaseModel):
    status: Optional[ProjectParticipantStatus] = None
    role: Optional[ProjectRole] = None


class ParticipantResponse(BaseModel):
    """Ответ с информацией об участнике проекта"""
    user_id: int
    username: Optional[str]
    name: Optional[str]
    lastname: Optional[str]
    status: ProjectParticipantStatus
    role: ProjectRole
    joined_at: datetime
    project_id: Optional[UUID] = None

    # Информация об участии в workspace (если применимо)
    workspace_id: Optional[UUID] = None
    workspace_joined_at: Optional[datetime] = None
    workspace_name: Optional[str] = None
    is_main_workspace: Optional[bool] = None

    # Список всех workspace, в которых участвует пользователь
    workspaces: List[WorkspaceParticipantInfo] = []

    class Config:
        from_attributes = True


class ParticipantDetailResponse(ParticipantResponse):
    """Детальная информация об участнике со всеми workspace"""
    workspaces: List[WorkspaceParticipantInfo] = []


# Search and filter schemas
class ProjectFilter(BaseModel):
    status: Optional[ProjectStatus] = None
    tags: Optional[List[str]] = None
    category: Optional[ProjectCategory] = None
    search: Optional[str] = Field(None, min_length=2, description="Поиск по названию и описанию")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class WorkspaceFilter(BaseModel):
    is_main: Optional[bool] = None
    search: Optional[str] = Field(None, min_length=2, description="Поиск по названию и описанию")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ParticipantFilter(BaseModel):
    status: Optional[List[ProjectParticipantStatus]] = None
    role: Optional[List[ProjectRole]] = None
    workspace_id: Optional[UUID] = None
    search: Optional[str] = Field(None, min_length=2, description="Поиск по имени пользователя")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


# Для корректной работы forward references
ProjectResponse.model_rebuild()
WorkspaceResponse.model_rebuild()
InvitationResponse.model_rebuild()
ParticipantResponse.model_rebuild()