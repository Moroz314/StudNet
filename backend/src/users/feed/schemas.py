from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import date

class SortField(str, Enum):
    NAME = "name"
    LASTNAME = "lastname"
    USERNAME = "username"
    COURSE = "course"
    CREATED_AT = "created_at"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class UserFeedFilter(BaseModel):
    name: Optional[str] = Field(None, description="Поиск по имени")
    lastname: Optional[str] = Field(None, description="Поиск по фамилии")
    username: Optional[str] = Field(None, description="Поиск по username")
    university: Optional[str] = Field(None, description="Фильтр по университету")
    faculty: Optional[str] = Field(None, description="Фильтр по факультету")
    course: Optional[int] = Field(None, description="Фильтр по курсу")
    min_course: Optional[int] = Field(None, ge=1, le=6, description="Минимальный курс")
    max_course: Optional[int] = Field(None, ge=1, le=6, description="Максимальный курс")
    interests: Optional[List[str]] = Field(None, description="Список интересов")
    skills: Optional[List[str]] = Field(None, description="Список навыков")

    class Config:
        use_enum_values = True


class UserFeedQuery(BaseModel):
    page: int = Field(1, ge=1, description="Номер страницы")
    page_size: int = Field(20, ge=1, le=100, description="Размер страницы")
    sort_by: SortField = Field(SortField.USERNAME, description="Поле для сортировки")
    sort_order: SortOrder = Field(SortOrder.ASC, description="Порядок сортировки")
    filter: Optional[UserFeedFilter] = Field(None, description="Фильтры")

    class Config:
        use_enum_values = True


class SearchUsersQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=100, description="Поисковый запрос")
    page: int = Field(1, ge=1, description="Номер страницы")
    page_size: int = Field(20, ge=1, le=100, description="Размер страницы")

class FeedUserProfile(BaseModel):
    """Профиль пользователя для ленты"""
    user_id: int
    name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    birth_date: Optional[date] = None
    avatar_url: Optional[str] = None
    university: Optional[str] = None
    faculty: Optional[str] = None
    course: Optional[int] = None
    info: Optional[str] = None
    interests: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    links: Optional[List[str]] = None

    class Config:
        from_attributes = True

class UserFeedResponse(BaseModel):
    profiles: List[FeedUserProfile] = Field(..., description="Список профилей")
    total_count: int = Field(..., description="Общее количество записей")
    page: int = Field(..., description="Текущая страница")
    page_size: int = Field(..., description="Размер страницы")
    total_pages: int = Field(..., description="Общее количество страниц")

    class Config:
        from_attributes = True