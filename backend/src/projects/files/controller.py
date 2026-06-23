from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, Path, Body
from .service import get_project_files_service, ProjectFilesService
from .schemas import *

project_files_router = APIRouter(prefix="/projects", tags=["project-files"])


@project_files_router.post(
    "/{project_id}/files/attach",
    response_model=ProjectFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_file_to_project(
        project_id: UUID = Path(..., description="ID проекта"),
        request: AttachFileToProjectRequest = Body(..., description="Данные для привязки файла"),
        service: ProjectFilesService = Depends(get_project_files_service),
):
    """
    Привязка существующего файла к проекту.

    **Предварительно файл должен быть загружен через /files/upload**

    - Требует прав администратора проекта
    - Файл привязывается к указанному workspace
    - Один файл может быть привязан к нескольким проектам
    """
    return await service.attach_file_to_project(
        file_id=request.file_id,
        project_id=project_id,
        workspace_id=request.workspace_id,
        description=request.description,
        tags=request.tags,
    )


@project_files_router.get(
    "/{project_id}/files",
    response_model=ProjectFileListResponse,
)
async def list_project_files(
        project_id: UUID = Path(..., description="ID проекта"),
        workspace_id: UUID = Query(..., description="ID рабочего пространства"),
        limit: int = Query(100, ge=1, le=500, description="Количество файлов на странице"),
        offset: int = Query(0, ge=0, description="Смещение для пагинации"),
        service: ProjectFilesService = Depends(get_project_files_service),
):
    """
    Получение списка файлов проекта или рабочего пространства.

    - workspace_id обязателен, возвращаются файлы только из этого workspace
    - Каждый файл содержит presigned URL для скачивания
    """
    return await service.list_project_files(
        project_id=project_id,
        workspace_id=workspace_id,
        limit=limit,
        offset=offset,
    )


@project_files_router.get(
    "/{project_id}/files/{file_id}",
    response_model=ProjectFileResponse,
)
async def get_project_file(
        project_id: UUID = Path(..., description="ID проекта"),
        file_id: UUID = Path(..., description="ID файла"),
        workspace_id: UUID = Query(..., description="ID рабочего пространства"),
        service: ProjectFilesService = Depends(get_project_files_service),
):
    """
    Получение метаданных файла проекта с presigned URL.

    - Проверяет доступ пользователя к файлу
    - Возвращает download_url и preview_url (для изображений)
    """
    return await service.get_file_metadata(
        file_id=file_id,
        project_id=project_id,
        workspace_id=workspace_id
    )


@project_files_router.patch(
    "/{project_id}/files/{file_id}",
    response_model=ProjectFileResponse,
)
async def update_project_file_metadata(
        project_id: UUID = Path(..., description="ID проекта"),
        file_id: UUID = Path(..., description="ID файла"),
        workspace_id: UUID = Query(..., description="ID рабочего пространства"),
        request: UpdateProjectFileRequest = Body(..., description="Обновляемые метаданные"),
        service: ProjectFilesService = Depends(get_project_files_service),
):
    """
    Обновление метаданных файла проекта (описание, теги).

    - Требует прав администратора проекта
    """
    return await service.update_file_metadata(
        file_id=file_id,
        project_id=project_id,
        workspace_id=workspace_id,
        description=request.description,
        tags=request.tags,
    )


@project_files_router.get(
    "/{project_id}/files/{file_id}/download-url",
    response_model=DownloadUrlResponse,
)
async def get_project_file_download_url(
        project_id: UUID = Path(..., description="ID проекта"),
        file_id: UUID = Path(..., description="ID файла"),
        workspace_id: UUID = Query(..., description="ID рабочего пространства"),
        expires_in: int = Query(3600, ge=60, le=86400, description="Время жизни ссылки в секундах"),
        service: ProjectFilesService = Depends(get_project_files_service),
):
    """
    Получение временной ссылки для скачивания файла проекта.

    - Ссылка действительна в течение указанного времени (от 60 сек до 24 часов)
    - По умолчанию 1 час (3600 секунд)
    """
    url = await service.get_download_url(
        file_id=file_id,
        expires_in=expires_in,
        project_id=project_id,
        workspace_id=workspace_id
    )

    return DownloadUrlResponse(
        url=url,
        expires_in=expires_in,
        file_id=file_id
    )


@project_files_router.delete(
    "/{project_id}/files/{file_id}",
    status_code=status.HTTP_200_OK,
    response_model=DeleteFileResponse,
)
async def detach_file_from_project(
        project_id: UUID = Path(..., description="ID проекта"),
        file_id: UUID = Path(..., description="ID файла"),
        workspace_id: UUID = Query(..., description="ID рабочего пространства"),
        delete_permanently: bool = Query(False, description="Удалить файл полностью из системы"),
        service: ProjectFilesService = Depends(get_project_files_service),
):
    """
    Отвязка файла от проекта.

    - Требует прав администратора проекта
    - По умолчанию файл только отвязывается от проекта (остается в системе)
    - При delete_permanently=True файл удаляется из S3 и БД полностью
    """
    await service.detach_file_from_project(
        file_id=file_id,
        project_id=project_id,
        workspace_id=workspace_id,
        delete_permanently=delete_permanently
    )

    action = "deleted permanently" if delete_permanently else "detached"
    return DeleteFileResponse(
        status="success",
        message=f"File {action} successfully",
        file_id=file_id
    )


# ========== Эндпоинты для работы с аватарками проектов ==========

@project_files_router.post(
    "/{project_id}/avatar",
    response_model=ProjectAvatarResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_project_avatar(
        project_id: UUID = Path(..., description="ID проекта"),
        request: SetProjectAvatarRequest = Body(..., description="Данные для установки аватара"),
        service: ProjectFilesService = Depends(get_project_files_service),
):
    """
    Установка аватара проекта из существующего файла.

    **Предварительно файл должен быть загружен через /files/upload с file_type=project_avatar**

    - Требует прав администратора проекта
    - Старый аватар автоматически отвязывается
    - Файл должен быть изображением
    """
    return await service.set_project_avatar(
        project_id=project_id,
        file_id=request.file_id
    )


@project_files_router.get(
    "/{project_id}/avatar",
    response_model=ProjectAvatarResponse,
)
async def get_project_avatar(
        project_id: UUID = Path(..., description="ID проекта"),
        service: ProjectFilesService = Depends(get_project_files_service),
):
    """
    Получение аватара проекта.

    - Возвращает информацию об аватаре и URL для скачивания
    - Если аватар не установлен, возвращает 404
    """
    return await service.get_project_avatar(project_id)


@project_files_router.delete(
    "/{project_id}/avatar",
    status_code=status.HTTP_200_OK,
    response_model=DeleteFileResponse,
)
async def remove_project_avatar(
        project_id: UUID = Path(..., description="ID проекта"),
        service: ProjectFilesService = Depends(get_project_files_service),
):
    """
    Удаление аватара проекта.

    - Требует прав администратора проекта
    - Аватар отвязывается от проекта (файл остается в системе)
    """
    await service.remove_project_avatar(project_id)

    return DeleteFileResponse(
        status="success",
        message="Project avatar removed successfully",
        file_id=None
    )