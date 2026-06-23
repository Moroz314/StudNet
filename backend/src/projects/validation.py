import mimetypes
import uuid
from datetime import datetime, UTC, timedelta
from pathlib import Path
from uuid import UUID
from typing import List, Optional
from fastapi import HTTPException, status, UploadFile
from ..database.models import ProjectParticipantStatus, ProjectRole, InvitationStatus
from ..database.repositories.project.core import ProjectRepository


def is_user_in_project(project_repo: ProjectRepository, project_id: UUID, user_id: int) -> bool:
    """Проверяет, является ли пользователь участником проекта."""
    return project_repo.is_user_in_project(project_id, user_id)


def is_project_admin(project_repo: ProjectRepository, project_id: UUID, user_id: int) -> bool:
    """Проверяет, является ли пользователь владельцем или админом проекта."""
    return project_repo.check_user_permission(
        project_id, user_id,
        [ProjectParticipantStatus.OWNER.value, ProjectParticipantStatus.ADMIN.value]
    )


def is_project_owner(project_repo: ProjectRepository, project_id: UUID, user_id: int) -> bool:
    """Проверяет, является ли пользователь владельцем проекта."""
    return project_repo.check_user_permission(project_id, user_id, [ProjectParticipantStatus.OWNER.value])


def require_workspace_access(
        project_repo: ProjectRepository,
        workspace_id: UUID,
        project_id: UUID,
        user_id: int
):
    require_project_access(project_repo, project_id, user_id)
    workspace = project_repo.get_workspace_by_id(workspace_id, include_relations=True)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if workspace.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace does not belong to the specified project"
        )

    if not project_repo.is_user_in_workspace(workspace_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому рабочему пространству. Попросите администратора проекта добавить вас в workspace."
        )

def require_project_access(
    project_repo: ProjectRepository,
    project_id: UUID,
    user_id: int
) -> None:
    """
    Проверяет доступ к проекту. Выбрасывает HTTPException 403, если пользователь не участник.
    """
    check_project_exists(project_repo, project_id)

    if not project_repo.is_user_in_project(project_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому проекту."
        )


def require_project_permission(
    project_repo: ProjectRepository,
    project_id: UUID,
    user_id: int,
    allowed_statuses: List[str]
) -> None:
    """
    Проверяет, что у пользователя есть одна из указанных ролей в проекте.
    Выбрасывает HTTPException 403 при отсутствии прав.
    """
    if not project_repo.check_user_permission(project_id, user_id, allowed_statuses):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action"
        )


def require_project_admin(project_repo: ProjectRepository, project_id: UUID, user_id: int) -> None:
    """Требует права владельца или админа проекта."""

    check_project_exists(project_repo,  project_id)
    require_project_permission(
        project_repo, project_id, user_id,
        [ProjectParticipantStatus.OWNER.value, ProjectParticipantStatus.ADMIN.value]
    )

def check_project_exists(project_repo: ProjectRepository, project_id: UUID):
    project = project_repo.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )

def require_project_owner(project_repo: ProjectRepository, project_id: UUID, user_id: int) -> None:
    """Требует права только владельца проекта."""
    check_project_exists(project_repo, project_id)
    require_project_permission(project_repo, project_id, user_id, [ProjectParticipantStatus.OWNER.value])



def require_can_invite_users(
    project_repo: ProjectRepository,
    project_id: UUID,
    user_id: int
) -> None:
    """Требует права на приглашение пользователей (owner, admin)."""
    require_project_permission(
        project_repo, project_id, user_id,
        [ProjectParticipantStatus.OWNER.value, ProjectParticipantStatus.ADMIN.value]
    )


def validate_invitation_target(
    project_repo: ProjectRepository,
    project_id: UUID,
    invited_user_id: int,
    inviter_id: int
) -> None:
    """
    Проверяет возможность приглашения пользователя:
    - Пользователь не должен быть уже участником проекта
    - Не должно быть активного приглашения
    - Нельзя приглашать самого себя
    """
    if invited_user_id == inviter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot invite yourself to the project"
        )

    if project_repo.is_user_in_project(project_id, invited_user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {invited_user_id} is already a member of this project"
        )

    existing_invitation = project_repo.get_project_user_invitation(project_id, invited_user_id)
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {invited_user_id} already has an invitation to this project"
        )


def validate_invitation_action(
    project_repo: ProjectRepository,
    invitation_id: int,
    user_id: int
) -> None:
    """
    Проверяет возможность действия над приглашением:
    - Приглашение должно существовать
    - Пользователь должен быть тем, кого пригласили
    - Приглашение должно быть в статусе PENDING
    """
    invitation = project_repo.get_invitation_by_id(invitation_id)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    if invitation.invited_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is not for you"
        )

    if invitation.status != InvitationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation is already {invitation.status}"
        )



allowed_avatar_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
allowed_avatar_mime_types = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}
MAX_AVATAR_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".md", ".csv", ".json", ".xml", ".zip", ".rar",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"
}


def validate_file(file: UploadFile) -> None:
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

def validate_project_avatar(file: UploadFile) -> None:
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {MAX_AVATAR_SIZE // (1024 * 1024)}MB",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_avatar_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(sorted(allowed_avatar_extensions))}",
        )

    mime_type = mimetypes.guess_type(file.filename)[0]
    if not mime_type or mime_type not in allowed_avatar_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type. Allowed: {', '.join(sorted(allowed_avatar_mime_types))}",
        )


def require_announcement_access(
        announce_repo,
        announcement_id: UUID,
        user_id: int
) -> None:
    """Проверяет доступ к объявлению через workspace"""
    announcement = announce_repo.get_announcement_by_id(announcement_id)
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )

    if not announce_repo.check_workspace_access(user_id, announcement.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this announcement"
        )