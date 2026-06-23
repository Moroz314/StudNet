from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from ...database.models import FileType


class ChampionshipCreateRequest(BaseModel):
    """Запрос на создание чемпионата"""
    title: str = Field(..., min_length=1, max_length=500, description="Название чемпионата")
    description: Optional[str] = Field(None, description="Описание чемпионата")
    max_winners: int = Field(..., gt=0, le=10, description="Максимальное количество победителей")
    max_participants: int = Field(..., gt=0, description="Максимальное количество решений")
    prize_amount: int = Field(..., gt=0, description="Общий призовой фонд в нанотонах")
    prize_distribution: List[int] = Field(..., description="Распределение приза по местам")
    deadline: datetime = Field(..., description="Дедлайн чемпионата")
    file_ids: Optional[List[UUID]] = Field(None, description="ID файлов для прикрепления")
    organizer_project_id: Optional[UUID] = Field(None, description="ID проекта-организатора")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Hackathon 2024",
            "description": "Создайте лучшее решение для...",
            "max_winners": 3,
            "max_participants": 50,
            "prize_amount": 1000000000,  # 1 TON в нанотонах
            "prize_distribution": [500000000, 300000000, 200000000],
            "deadline": "2024-12-31T23:59:59",
            "file_ids": ["550e8400-e29b-41d4-a716-446655440000"],
            "organizer_project_id": None
        }
    })


class ChampionshipUpdateRequest(BaseModel):
    """Запрос на обновление чемпионата"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    max_winners: Optional[int] = Field(None, gt=0, le=10)
    max_participants: Optional[int] = Field(None, gt=0)
    prize_amount: Optional[int] = Field(None, gt=0)
    prize_distribution: Optional[List[int]] = None
    deadline: Optional[datetime] = None
    file_ids: Optional[List[UUID]] = None
    organizer_project_id: Optional[UUID] = None


class CreatorResponse(BaseModel):
    """Ответ с информацией о создателе"""
    user_id: int
    name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FileResponse(BaseModel):
    """Ответ с информацией о файле"""
    id: UUID
    url: Optional[str] = None
    original_filename: str
    mime_type: str
    size_bytes: int

    model_config = ConfigDict(from_attributes=True)


class ChampionshipResponse(BaseModel):
    """Ответ с чемпионатом"""
    id: UUID
    title: str
    description: Optional[str] = None
    status: str
    max_winners: int
    max_participants: int
    prize_amount: int
    prize_distribution: List[int]
    created_by: int
    organizer_project_id: Optional[UUID] = None
    deadline: datetime
    created_at: datetime
    updated_at: datetime
    solutions_count: int = 0
    creator: Optional[CreatorResponse] = None
    files: List[FileResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ChampionshipsListResponse(BaseModel):
    """Ответ со списком чемпионатов"""
    items: List[ChampionshipResponse]
    total: int
    limit: int
    offset: int


class SubmitSolutionRequest(BaseModel):
    """Запрос на отправку решения"""
    project_id: UUID = Field(..., description="ID проекта-решения")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "project_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    })


class SolutionResponse(BaseModel):
    """Ответ с решением"""
    id: UUID
    championship_id: UUID
    project_id: UUID
    submitted_by: int
    status: str
    place: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    project_name: Optional[str] = None
    submitter_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SolutionsListResponse(BaseModel):
    """Ответ со списком решений"""
    items: List[SolutionResponse]
    total: int


class SelectWinnersRequest(BaseModel):
    """Запрос на выбор победителей"""
    winner_solution_ids: List[UUID] = Field(..., description="ID решений-победителей в порядке мест")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "winner_solution_ids": [
                "550e8400-e29b-41d4-a716-446655440000",
                "660e8400-e29b-41d4-a716-446655440000"
            ]
        }
    })


class ContractInfoResponse(BaseModel):
    """Информация о контракте"""
    contract_address: str
    challenge_id: Optional[int] = None
    status: Optional[str] = None
    prize_amount: Optional[int] = None
    deadline: Optional[datetime] = None