from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, Path, Body
from .service import get_announcement_service, AnnouncementService
from .schemas import *

announcement_router = APIRouter(prefix="/projects", tags=["announcements"])


# ========== Announcement Endpoints ==========

@announcement_router.post(
    "/{project_id}/workspaces/{workspace_id}/announcements",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_announcement(
        project_id: UUID = Path(..., description="ID проекта"),
        workspace_id: UUID = Path(..., description="ID рабочего пространства"),
        data: AnnouncementCreate = Body(..., description="Данные объявления"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Создание объявления в рабочем пространстве"""
    return await service.create_announcement(project_id, workspace_id, data)


@announcement_router.get(
    "/announcements/feed",
    response_model=AnnouncementFeedResponse
)
async def get_announcements_feed(
        skip: int = Query(0, ge=0, description="Смещение"),
        limit: int = Query(100, ge=1, le=500, description="Лимит"),
        project_id: Optional[UUID] = Query(None, description="Фильтр по проекту"),
        workspace_id: Optional[UUID] = Query(None, description="Фильтр по workspace"),
        status: Optional[str] = Query(None, description="Фильтр по статусу"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Получение публичной ленты объявлений"""
    return await service.get_announcements_feed(skip, limit, project_id, workspace_id, status)


@announcement_router.get(
    "/{project_id}/workspaces/{workspace_id}/announcements",
    response_model=AnnouncementListResponse
)
async def get_workspace_announcements(
        project_id: UUID = Path(..., description="ID проекта"),
        workspace_id: UUID = Path(..., description="ID рабочего пространства"),
        skip: int = Query(0, ge=0, description="Смещение"),
        limit: int = Query(100, ge=1, le=500, description="Лимит"),
        status: Optional[str] = Query(None, description="Фильтр по статусу"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Получение списка объявлений рабочего пространства"""
    return await service.get_workspace_announcements(project_id, workspace_id, skip, limit, status)


@announcement_router.get(
    "/announcements/{announcement_id}",
    response_model=AnnouncementResponse
)
async def get_announcement(
        announcement_id: UUID = Path(..., description="ID объявления"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Получение объявления по ID"""
    return await service.get_announcement(announcement_id)


@announcement_router.patch(
    "/announcements/{announcement_id}",
    response_model=AnnouncementResponse
)
async def update_announcement(
        announcement_id: UUID = Path(..., description="ID объявления"),
        data: AnnouncementUpdate = Body(..., description="Данные для обновления"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Обновление объявления"""
    return await service.update_announcement(announcement_id, data)


@announcement_router.delete(
    "/announcements/{announcement_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict
)
async def delete_announcement(
        announcement_id: UUID = Path(..., description="ID объявления"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Удаление объявления"""
    await service.delete_announcement(announcement_id)
    return {"status": "success", "message": "Announcement deleted successfully"}


# ========== Application Endpoints ==========

@announcement_router.post(
    "/announcements/{announcement_id}/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_application(
        announcement_id: UUID = Path(..., description="ID объявления"),
        data: ApplicationCreate = Body(..., description="Данные заявки"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Подача заявки на объявление"""
    return await service.create_application(announcement_id, data)


@announcement_router.get(
    "/announcements/{announcement_id}/applications",
    response_model=ApplicationListResponse
)
async def get_announcement_applications(
        announcement_id: UUID = Path(..., description="ID объявления"),
        skip: int = Query(0, ge=0, description="Смещение"),
        limit: int = Query(100, ge=1, le=500, description="Лимит"),
        status: Optional[str] = Query(None, description="Фильтр по статусу"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Получение списка заявок объявления"""
    return await service.get_announcement_applications(announcement_id, skip, limit, status)


@announcement_router.get(
    "/applications/my",
    response_model=ApplicationListResponse
)
async def get_my_applications(
        skip: int = Query(0, ge=0, description="Смещение"),
        limit: int = Query(100, ge=1, le=500, description="Лимит"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Получение моих заявок"""
    return await service.get_my_applications(skip, limit)


@announcement_router.get(
    "/applications/{application_id}",
    response_model=ApplicationResponse
)
async def get_application(
        application_id: UUID = Path(..., description="ID заявки"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Получение заявки по ID"""
    return await service.get_application(application_id)


@announcement_router.patch(
    "/applications/{application_id}",
    response_model=ApplicationResponse
)
async def update_application(
        application_id: UUID = Path(..., description="ID заявки"),
        data: ApplicationUpdate = Body(..., description="Данные для обновления"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Обновление заявки (только владелец)"""
    return await service.update_application(application_id, data)


@announcement_router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict
)
async def delete_application(
        application_id: UUID = Path(..., description="ID заявки"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Удаление заявки (только владелец)"""
    await service.delete_application(application_id)
    return {"status": "success", "message": "Application deleted successfully"}


@announcement_router.patch(
    "/applications/{application_id}/status",
    response_model=ApplicationResponse
)
async def update_application_status(
        application_id: UUID = Path(..., description="ID заявки"),
        status: str = Query(..., pattern="^(pending|approved|rejected|withdrawn)$"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Обновление статуса заявки (только админы)"""
    return await service.update_application_status(application_id, status)


@announcement_router.post(
    "/applications/{application_id}/vote",
    response_model=ApplicationResponse
)
async def vote_application(
        application_id: UUID = Path(..., description="ID заявки"),
        vote: VoteRequest = Body(..., description="Тип голоса"),
        service: AnnouncementService = Depends(get_announcement_service)
):
    """Голосование за заявку"""
    return await service.vote_application(application_id, vote.vote_type)