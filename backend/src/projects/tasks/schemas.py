from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from enum import Enum


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    IDEA = "idea"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    IDEA = "idea"
    TASK = "task"
    URGENT_TASK = "urgent_task"


class TaskAssigneesUpdate(BaseModel):
    """Схема для обновления списка назначенных пользователей"""
    assignees: List[int] = Field(..., description="Список ID пользователей, назначенных на задачу")


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    task_type: TaskType
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: Optional[datetime] = None
    estimated_hours: Optional[int] = Field(None, ge=0)
    assignees: Optional[List[int]] = Field(None, description="Список пользователей, кто может работать с задачей")

    @field_validator('deadline')
    @classmethod
    def validate_deadline_for_urgent(cls, v: Optional[datetime], info):
        values = info.data
        if values.get('task_type') == TaskType.URGENT_TASK and v is None:
            raise ValueError('Urgent tasks must have a deadline')
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    task_type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    deadline: Optional[datetime] = None
    estimated_hours: Optional[int] = Field(None, ge=0)
    actual_hours: Optional[int] = Field(None, ge=0)
    assignees: Optional[List[int]] = Field(None, description="Список пользователей, кто может работать с задачей")

    @field_validator('deadline')
    @classmethod
    def validate_deadline_for_urgent(cls, v: Optional[datetime], info):
        values = info.data
        if values.get('task_type') == TaskType.URGENT_TASK and v is None:
            raise ValueError('Urgent tasks must have a deadline')
        return v


class TaskCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    file_ids: List[UUID] = Field(default_factory=list)


class TaskCommentUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class FileMetadataBase(BaseModel):
    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    download_url: Optional[str] = None


class TaskCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: UUID
    user_id: int
    content: str
    attachments: List[FileMetadataBase] = []
    created_at: datetime
    updated_at: datetime
    is_edited: bool


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    created_by: int
    title: str
    description: Optional[str]
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    deadline: Optional[datetime]
    estimated_hours: Optional[int]
    actual_hours: int
    assignees: List[int] = []
    comments: List[TaskCommentResponse] = []
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False

    @field_validator('is_overdue', mode='before')
    @classmethod
    def calculate_overdue(cls, v, info):
        values = info.data
        if 'deadline' in values and values['deadline']:
            return (
                    values['deadline'] < datetime.now() and
                    values['status'] not in [TaskStatus.DONE, TaskStatus.CANCELLED]
            )
        return False


class TaskListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    title: str
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    deadline: Optional[datetime]
    estimated_hours: Optional[int]
    actual_hours: int
    assignees: List[int] = []
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False


class TaskStatisticResponse(BaseModel):
    total_tasks: int
    status_distribution: Dict[str, int]
    type_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    urgent_tasks: int
    overdue_tasks: int
    overdue_urgent_tasks: int
    total_estimated_hours: int
    total_actual_hours: int
    completion_rate: float
    average_completion_time_hours: Optional[float]
    tasks_created_today: int
    tasks_completed_today: int


class TaskFilter(BaseModel):
    search: Optional[str] = None
    task_type: Optional[TaskType] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    has_deadline: Optional[bool] = None
    deadline_before: Optional[datetime] = None
    deadline_after: Optional[datetime] = None
    assignee_id: Optional[int] = Field(None, description="Фильтр по назначенному пользователю")
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class TaskStatisticHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    total_tasks: int
    idea_count: int
    todo_count: int
    in_progress_count: int
    review_count: int
    done_count: int
    cancelled_count: int
    urgent_total: int
    urgent_overdue: int
    total_estimated_hours: int
    total_actual_hours: int
    tasks_created: int
    tasks_completed: int


class UpcomingDeadlinesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    deadline: datetime
    priority: TaskPriority
    status: TaskStatus
    days_until_deadline: int