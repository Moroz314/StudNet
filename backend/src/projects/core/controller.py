from fastapi import APIRouter, Depends, status, Query
from .service import get_profile_service, ProjectService
from .schemas import *
from ...users.auth.service.utils import verify_token
from typing import List, Optional
from uuid import UUID

project_router = APIRouter(prefix="/projects", tags=["projects"])


# ============ PROJECT ENDPOINTS ============

@project_router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
        project_data: ProjectCreate,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    return await project_service.create_project(project_data, user_id)


@project_router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
        project_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    return await project_service.get_project_by_id(project_id, user_id)


@project_router.get("/", response_model=List[ProjectListResponse])
async def get_user_projects(
        status_filter: Optional[ProjectStatus] = Query(None, alias="status"),
        tags: Optional[List[str]] = Query(None),
        search: Optional[str] = Query(None),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    filters = ProjectFilter(
        status=status_filter,
        tags=tags,
        search=search,
        limit=limit,
        offset=offset
    )
    return await project_service.get_user_projects(user_id, filters)


@project_router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
        project_id: UUID,
        update_data: ProjectUpdate,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    return await project_service.update_project(project_id, update_data, user_id)


@project_router.delete("/{project_id}/archive", status_code=status.HTTP_200_OK)
async def archive_project(
        project_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    result = await project_service.archive_project(project_id, user_id)
    return {"message": "Project archived successfully", "success": result}


@project_router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
        project_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    return await project_service.restore_project(project_id, user_id)


@project_router.delete("/{project_id}", status_code=status.HTTP_200_OK)
async def delete_project(
        project_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    result = await project_service.delete_project(project_id, user_id)
    return {
        "message": "Project permanently deleted successfully",
        "success": result
    }


# ============ INVITATION ENDPOINTS ============

@project_router.get("/invitations/personal", response_model=List[InvitationResponse])
async def get_my_invitations(
        status_filter: Optional[InvitationStatus] = Query(None, alias="status"),
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    return await project_service.get_user_invitations(user_id, status_filter)


@project_router.post("/invitations/{invitation_id}/respond", response_model=InvitationResponse)
async def respond_to_invitation(
        invitation_id: int,
        action_data: InvitationAction,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    return await project_service.respond_to_invitation(invitation_id, action_data.action, user_id)


@project_router.delete("/invitations/{invitation_id}", status_code=status.HTTP_200_OK)
async def cancel_invitation(
        invitation_id: int,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """Отменить приглашение (только для создателя приглашения или админа проекта)"""
    result = await project_service.delete_invitation(invitation_id, user_id)
    return {"message": "Invitation deleted successfully", "success": result}


@project_router.post("/{project_id}/invitations", response_model=List[InvitationResponse],
                     status_code=status.HTTP_201_CREATED)
async def create_invitations(
        project_id: UUID,
        invitation_data: InvitationCreate,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """Создать приглашения в проект для нескольких пользователей"""
    return await project_service.create_invitations(project_id, invitation_data, user_id)


@project_router.get("/{project_id}/invitations", response_model=List[InvitationResponse])
async def get_project_invitations(
        project_id: UUID,
        status_filter: Optional[InvitationStatus] = Query(None, alias="status"),
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """Получить все приглашения для конкретного проекта (для админов)"""
    return await project_service.get_project_invitations(project_id, user_id, status_filter)


# ============ WORKSPACE ENDPOINTS ============

@project_router.post("/{project_id}/workspaces", response_model=WorkspaceResponse,
                     status_code=status.HTTP_201_CREATED)
async def create_workspace(
        project_id: UUID,
        workspace_data: WorkspaceCreate,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """Создать рабочее пространство в проекте"""
    return await project_service.create_workspace(project_id, workspace_data, user_id)


@project_router.get("/{project_id}/workspaces", response_model=List[WorkspaceResponse])
async def get_project_workspaces(
        project_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """Получить все рабочие пространства проекта"""
    return await project_service.get_project_workspaces(project_id, user_id)


@project_router.get("/{project_id}/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
        project_id: UUID,
        workspace_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """
    Получить информацию о рабочем пространстве.
    Требуется project_id для валидации принадлежности workspace к проекту.
    """
    return await project_service.get_workspace_by_id(project_id, workspace_id, user_id)


@project_router.patch("/{project_id}/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
        project_id: UUID,
        workspace_id: UUID,
        update_data: WorkspaceUpdate,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """
    Обновить рабочее пространство.
    Требуется project_id для валидации принадлежности workspace к проекту.
    """
    return await project_service.update_workspace(project_id, workspace_id, update_data, user_id)


@project_router.delete("/{project_id}/workspaces/{workspace_id}", status_code=status.HTTP_200_OK)
async def delete_workspace(
        project_id: UUID,
        workspace_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """
    Удалить рабочее пространство.
    Требуется project_id для валидации принадлежности workspace к проекту.
    """
    result = await project_service.delete_workspace(project_id, workspace_id, user_id)
    return {"message": "Workspace deleted successfully", "success": result}


# ============ PARTICIPANT ENDPOINTS ============

@project_router.post("/{project_id}/workspaces/{workspace_id}/participants",
                     response_model=List[ParticipantResponse],
                     status_code=status.HTTP_201_CREATED)
async def add_workspace_participants(
        project_id: UUID,
        workspace_id: UUID,
        participant_data: ParticipantAdd,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """
    Добавить участников в рабочее пространство.
    """
    return await project_service.add_participants_to_workspace(project_id, workspace_id, participant_data, user_id)


@project_router.get("/{project_id}/participants", response_model=List[ParticipantResponse])
async def get_project_participants(
        project_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """Получить участников проекта"""
    return await project_service.get_project_participants(project_id, user_id)


@project_router.get("/{project_id}/workspaces/{workspace_id}/participants",
                    response_model=List[ParticipantResponse])
async def get_workspace_participants(
        project_id: UUID,
        workspace_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """
    Получить участников рабочего пространства.
    Требуется project_id для валидации принадлежности workspace к проекту.
    """
    return await project_service.get_workspace_participants(project_id, workspace_id, user_id)


@project_router.delete("/{project_id}/participants", status_code=status.HTTP_200_OK)
async def remove_project_participants(
        project_id: UUID,
        participant_user_ids: List[int] = Query(..., description="List of user IDs to remove from project"),
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """
    Удалить участников из проекта (из всех workspace).
    Требует прав администратора или владельца проекта.
    Нельзя удалить создателя проекта.
    """
    result = await project_service.remove_participants_from_project(
        project_id,
        participant_user_ids,
        user_id
    )
    return {
        "message": f"{len(participant_user_ids)} participant(s) removed from project successfully",
        "success": result
    }


@project_router.delete("/{project_id}/workspaces/{workspace_id}/participants", status_code=status.HTTP_200_OK)
async def remove_workspace_participants(
        project_id: UUID,
        workspace_id: UUID,
        participant_user_ids: List[int] = Query(...),
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """
    Удалить участников из рабочего пространства.
    Требуется project_id для валидации принадлежности workspace к проекту.
    """
    result = await project_service.remove_participants_from_workspace(
        project_id, workspace_id, participant_user_ids, user_id
    )
    return {
        "message": f"{len(participant_user_ids)} participant(s) removed successfully",
        "success": result
    }


@project_router.delete("/{project_id}/leave", status_code=status.HTTP_200_OK)
async def leave_project(
        project_id: UUID,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """Покинуть проект"""
    result = await project_service.leave_project(project_id, user_id)
    return {"message": "Successfully left the project", "success": result}


@project_router.patch("/{project_id}/participants/{participant_user_id}", response_model=ParticipantResponse)
async def update_participant(
        project_id: UUID,
        participant_user_id: int,
        update_data: ParticipantUpdate,
        project_service: ProjectService = Depends(get_profile_service),
        user_id: int = Depends(verify_token)
):
    """Обновить статус или роль участника проекта"""
    return await project_service.update_participant_status(
        project_id, participant_user_id, update_data, user_id
    )