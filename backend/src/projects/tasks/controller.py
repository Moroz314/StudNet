from fastapi import APIRouter, Depends, status, Query
from .schemas import *
from .service import TaskService, get_task_service
from ...users.auth.service.utils import verify_token
from uuid import UUID
from typing import List, Optional
from datetime import datetime, date

tasks_router = APIRouter(prefix="/projects/{project_id}/workspaces/{workspace_id}/tasks", tags=["Tasks"])


@tasks_router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
        project_id: UUID,
        workspace_id: UUID,
        task_data: TaskCreate,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Создание новой задачи в рабочем пространстве"""
    return await task_service.create_task(project_id, workspace_id, task_data, current_user)


@tasks_router.get("/", response_model=List[TaskListResponse])
async def get_workspace_tasks(
        project_id: UUID,
        workspace_id: UUID,
        search: Optional[str] = Query(None),
        task_type: Optional[TaskType] = Query(None),
        status: Optional[TaskStatus] = Query(None),
        priority: Optional[TaskPriority] = Query(None),
        has_deadline: Optional[bool] = Query(None),
        deadline_before: Optional[datetime] = Query(None),
        deadline_after: Optional[datetime] = Query(None),
        assignee_id: Optional[int] = Query(None, description="Фильтр по назначенному пользователю"),
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Получение задач рабочего пространства с фильтрацией"""
    filters = TaskFilter(
        search=search,
        task_type=task_type,
        status=status,
        priority=priority,
        has_deadline=has_deadline,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
        assignee_id=assignee_id,
        limit=limit,
        offset=offset
    )

    return await task_service.get_workspace_tasks(project_id, workspace_id, current_user, filters)


@tasks_router.get("/upcoming-deadlines", response_model=List[UpcomingDeadlinesResponse])
async def get_upcoming_deadlines(
        project_id: UUID,
        workspace_id: UUID,
        days_ahead: int = Query(7, ge=1, le=90),
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Получение предстоящих дедлайнов"""
    return await task_service.get_upcoming_deadlines(project_id, workspace_id, current_user, days_ahead)


@tasks_router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
        project_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Получение задачи по ID"""
    return await task_service.get_task_by_id(project_id, workspace_id, task_id, current_user)


@tasks_router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
        project_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        update_data: TaskUpdate,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Обновление задачи"""
    return await task_service.update_task(project_id, workspace_id, task_id, update_data, current_user)


@tasks_router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
        project_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Удаление задачи"""
    await task_service.delete_task(project_id, workspace_id, task_id, current_user)
    return {'status': 'task was deleted successfully.'}


# ========== Эндпоинты для работы с назначенными пользователями ==========

@tasks_router.get("/{task_id}/assignees", response_model=List[int])
async def get_task_assignees(
        project_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Получение списка пользователей, назначенных на задачу"""
    return await task_service.get_task_assignees(project_id, workspace_id, task_id, current_user)


@tasks_router.post("/{task_id}/assignees", response_model=TaskResponse)
async def add_assignees_to_task(
        project_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        assignees_data: TaskAssigneesUpdate,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Добавление пользователей в список назначенных на задачу"""
    return await task_service.add_assignees_to_task(project_id, workspace_id, task_id, assignees_data, current_user)


@tasks_router.put("/{task_id}/assignees", response_model=TaskResponse)
async def set_task_assignees(
        project_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        assignees_data: TaskAssigneesUpdate,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Установка списка назначенных пользователей (полная замена)"""
    return await task_service.set_task_assignees(project_id, workspace_id, task_id, assignees_data, current_user)


@tasks_router.delete("/{task_id}/assignees/{assignee_id}", response_model=TaskResponse)
async def remove_assignee_from_task(
        project_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        assignee_id: int,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Удаление пользователя из списка назначенных на задачу"""
    return await task_service.remove_assignee_from_task(project_id, workspace_id, task_id, assignee_id, current_user)


# ========== Эндпоинты для работы с комментариями ==========

@tasks_router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_task_comment(
        project_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        comment_data: TaskCommentCreate,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Добавление комментария к задаче"""
    return await task_service.add_task_comment(project_id, workspace_id, task_id, comment_data, current_user)


@tasks_router.post("/comments/{comment_id}/attachments", response_model=TaskCommentResponse)
async def add_attachments_to_comment(
        project_id: UUID,
        workspace_id: UUID,
        comment_id: int,
        file_ids: List[UUID],
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Добавление файлов к комментарию"""
    return await task_service.add_attachments_to_comment(project_id, workspace_id, comment_id, file_ids, current_user)


@tasks_router.delete("/comments/{comment_id}/attachments/{file_id}", status_code=status.HTTP_200_OK)
async def remove_attachment_from_comment(
        project_id: UUID,
        workspace_id: UUID,
        comment_id: int,
        file_id: UUID,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Удаление файла из комментария"""
    await task_service.remove_attachment_from_comment(project_id, workspace_id, comment_id, file_id, current_user)
    return {'status': 'file was deleted successfully.'}


@tasks_router.get("/{task_id}/comments", response_model=List[TaskCommentResponse])
async def get_task_comments(
        project_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Получение комментариев задачи"""
    return await task_service.get_task_comments(project_id, workspace_id, task_id, current_user, limit, offset)


@tasks_router.put("/comments/{comment_id}", response_model=TaskCommentResponse)
async def update_task_comment(
        project_id: UUID,
        workspace_id: UUID,
        comment_id: int,
        update_data: TaskCommentUpdate,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Обновление комментария задачи"""
    return await task_service.update_task_comment(project_id, workspace_id, comment_id, update_data, current_user)


@tasks_router.delete("/comments/{comment_id}", status_code=status.HTTP_200_OK)
async def delete_task_comment(
        project_id: UUID,
        workspace_id: UUID,
        comment_id: int,
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Удаление комментария задачи"""
    await task_service.delete_task_comment(project_id, workspace_id, comment_id, current_user)
    return {'status': 'comment was deleted successfully.'}


# ========== Эндпоинты для статистики ==========

@tasks_router.get("/statistics/current", response_model=TaskStatisticResponse)
async def get_workspace_statistics(
        project_id: UUID,
        workspace_id: UUID,
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None),
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Получение текущей статистики рабочего пространства"""
    return await task_service.get_workspace_statistics(project_id, workspace_id, current_user, start_date, end_date)


@tasks_router.get("/statistics/history", response_model=List[TaskStatisticHistoryResponse])
async def get_statistics_history(
        project_id: UUID,
        workspace_id: UUID,
        days: int = Query(30, ge=1, le=365),
        current_user: int = Depends(verify_token),
        task_service: TaskService = Depends(get_task_service)
):
    """Получение истории статистики рабочего пространства"""
    return await task_service.get_statistics_history(project_id, workspace_id, current_user, days)