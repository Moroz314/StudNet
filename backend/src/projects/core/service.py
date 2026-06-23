from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
from ...database.repositories.project.core import ProjectRepository
from ...database.repositories.user.chat import ChatRepository
from .schemas import *
from ...database.models import *
from ...database.core import get_db
from ..validation import (
    require_project_access, require_can_invite_users, validate_invitation_target,
    validate_invitation_action, require_project_admin,
    require_project_owner, require_workspace_access
)
from ...users.auth.service.utils import verify_token
from ...files.service import FileService
from ...websockets.connection import connection_manager
import traceback

AVATAR_URL_EXPIRY = 86400  # 24 часа


def get_profile_service(
        db: Session = Depends(get_db),
        user_id: int = Depends(verify_token)
):
    project_repo = ProjectRepository(session=db)
    chat_repo = ChatRepository(db)
    file_service = FileService(session=db)
    return ProjectService(
        project_repo=project_repo,
        chat_repo=chat_repo,
        file_service=file_service,
        user_id=user_id
    )


class ProjectService:
    def __init__(
            self,
            project_repo: ProjectRepository,
            chat_repo: ChatRepository,
            file_service: FileService,
            user_id: int
    ):
        self.project_repo = project_repo
        self.chat_repo = chat_repo
        self.file_service = file_service
        self.user_id = user_id

    async def _get_avatar_url(self, avatar_file: Optional[FileMetadata]) -> Optional[str]:
        """Получение URL аватара через FileService"""
        if not avatar_file:
            return None

        try:
            return await self.file_service.get_file_url(
                file_id=avatar_file.id,
                user_id=self.user_id,
                expires_in=AVATAR_URL_EXPIRY
            )
        except Exception as e:
            print(f"Failed to generate avatar URL: {e}")
            return None

    # ============ PROJECT METHODS ============

    async def create_project(self, project_data: ProjectCreate, creator_id: int) -> ProjectResponse:
        try:
            create_dict = project_data.model_dump(mode='json', exclude_unset=True)
            project = self.project_repo.create_project(**create_dict, created_by=creator_id)

            return await self.get_project_by_id(project.id, creator_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    async def get_project_by_id(self, project_id: UUID, user_id: int) -> ProjectResponse:
        project = self.project_repo.get_project_by_id(project_id, include_relations=True)

        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        require_project_access(self.project_repo, project_id, user_id)

        # Получаем URL аватара через FileService
        avatar_url = await self._get_avatar_url(project.avatar_file)

        response = ProjectResponse.model_validate(project)
        response.avatar_url = avatar_url

        return response

    async def get_user_projects(self, user_id: int, filters: Optional[ProjectFilter] = None) -> List[
        ProjectListResponse]:
        try:
            # Подготовка фильтров для репозитория
            filter_dict = {}
            if filters:
                if filters.status:
                    filter_dict['status'] = filters.status.value
                if filters.search:
                    filter_dict['search'] = filters.search
                if filters.tags:
                    filter_dict['tags'] = filters.tags
                if filters.offset:
                    filter_dict['offset'] = filters.offset
                if filters.limit:
                    filter_dict['limit'] = filters.limit
                if filters.category:
                    filter_dict['category'] = filters.category.value if filters.category else None

            # Получаем проекты с фильтрацией на уровне БД
            projects = self.project_repo.get_user_projects(
                user_id=user_id,
                filters=filter_dict,
                include_relations=False
            )

            if not projects:
                return []

            # Получаем агрегированные данные одним запросом
            project_ids = [p.id for p in projects]
            participants_counts = self.project_repo.get_projects_with_participants_count(project_ids)
            pending_invitations_counts = self.project_repo.get_pending_invitations_count(project_ids)

            # Собираем все ID аватаров для batch-запроса URL
            avatar_file_ids = [p.avatar_file_id for p in projects if p.avatar_file_id]
            avatar_urls = {}
            if avatar_file_ids:
                avatar_urls = await self.file_service.get_file_urls_batch(
                    file_ids=avatar_file_ids,
                    user_id=user_id,
                    expires_in=AVATAR_URL_EXPIRY
                )

            result = []
            for project in projects:
                # Получаем количество непрочитанных сообщений через chat_repo
                unread_count = 0
                if project.workspaces:
                    main_workspace = next((ws for ws in project.workspaces if ws.is_main), None)
                    if main_workspace and main_workspace.chat_id:
                        unread_count = self.chat_repo.message.get_unread_messages_count(
                            main_workspace.chat_id, user_id
                        )

                # Получаем URL аватара
                avatar_url = None
                if project.avatar_file_id:
                    avatar_url = avatar_urls.get(project.avatar_file_id)

                result.append(ProjectListResponse(
                    id=project.id,
                    name=project.name,
                    description=project.description,
                    status=project.status,
                    category=project.category,
                    avatar_url=avatar_url,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                    participant_count=participants_counts.get(project.id, 0),
                    unread_messages_count=unread_count,
                    tags=project.tags,
                    links=project.links,
                    github_links=project.github_links,
                    pending_invitations_count=pending_invitations_counts.get(project.id, 0)
                ))

            return result

        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get projects: {str(e)}"
            )

    async def update_project(self, project_id: UUID, update_data: ProjectUpdate, user_id: int) -> ProjectResponse:
        require_project_owner(self.project_repo, project_id, user_id)
        try:
            update_dict = update_data.model_dump(mode='json', exclude_unset=True)
            project = self.project_repo.update_project(project_id, **update_dict)
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
            return await self.get_project_by_id(project_id, user_id)

        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update project: {str(e)}"
            )

    async def archive_project(self, project_id: UUID, user_id: int) -> bool:
        require_project_owner(self.project_repo, project_id, user_id)
        try:
            success = self.project_repo.archive_project(project_id)
            if not success:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to archive project: {str(e)}"
            )

    async def restore_project(self, project_id: UUID, user_id: int) -> ProjectResponse:
        """Восстановление проекта из архива"""
        require_project_admin(self.project_repo, project_id, user_id)
        try:
            project = self.project_repo.restore_project(project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found or not archived"
                )
            return await self.get_project_by_id(project_id, user_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to restore project: {str(e)}"
            )

    async def delete_project(self, project_id: UUID, user_id: int) -> bool:
        require_project_owner(self.project_repo, project_id, user_id)

        try:
            project = self.project_repo.get_project_by_id(project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found"
                )

            # Удаляем аватар проекта, если есть
            if project.avatar_file_id:
                try:
                    await self.file_service.delete_file(project.avatar_file_id)
                except Exception as e:
                    print(f"Failed to delete avatar file: {e}")

            # Удаляем проект - всё остальное удалится каскадно благодаря ondelete="CASCADE"
            success = self.project_repo.delete_project(project_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found"
                )

            return True

        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete project: {str(e)}"
            )

    # ============ INVITATION METHODS ============

    async def create_invitations(self, project_id: UUID, invitation_data: InvitationCreate,
                                 inviter_id: int) -> List[InvitationResponse]:
        """Создать приглашения для нескольких пользователей"""
        require_can_invite_users(self.project_repo, project_id, inviter_id)

        # Проверяем существование всех пользователей
        users_with_profiles = self.project_repo.user.get_existing_users_ids(invitation_data.user_ids)
        non_existing = [uid for uid in invitation_data.user_ids if uid not in users_with_profiles]

        if non_existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Users not found: {non_existing}"
            )

        invitations = []

        for user_id in invitation_data.user_ids:
            # Проверяем возможность приглашения
            validate_invitation_target(self.project_repo, project_id, user_id, inviter_id)

            # Создаем приглашение
            invitation = self.project_repo.create_invitation(
                project_id=project_id,
                invited_user_id=user_id,
                invited_by=inviter_id,
                role=invitation_data.role,
                permission_level=invitation_data.permission_level,
                message=invitation_data.message,
            )

            invitations.append(InvitationResponse.model_validate(invitation))

            # Отправляем уведомление через WebSocket
            await self._send_invitation_notification(invitation)

        return invitations

    async def get_user_invitations(self, user_id: int, status_filter: Optional[InvitationStatus] = None) -> List[
        InvitationResponse]:
        """Получить все приглашения пользователя"""
        try:
            invitations = self.project_repo.get_user_invitations(user_id, status_filter)
            return [InvitationResponse.model_validate(inv) for inv in invitations]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get invitations: {str(e)}"
            )

    async def get_project_invitations(self, project_id: UUID, user_id: int,
                                      status_filter: Optional[InvitationStatus] = None) -> List[InvitationResponse]:
        """Получить все приглашения для проекта (только для админов)"""
        require_project_admin(self.project_repo, project_id, user_id)

        try:
            invitations = self.project_repo.get_project_invitations(project_id, status_filter)
            return [InvitationResponse.model_validate(inv) for inv in invitations]

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get project invitations: {str(e)}"
            )

    async def respond_to_invitation(self, invitation_id: int, action: str, user_id: int) -> InvitationResponse:
        """Принять или отклонить приглашение"""
        validate_invitation_action(self.project_repo, invitation_id, user_id)

        try:
            invitation = self.project_repo.get_invitation_by_id(invitation_id)

            if action == "accept":
                # Добавляем пользователя как участника проекта
                participant = self.project_repo.add_project_participant_from_invitation(
                    project_id=invitation.project_id,
                    user_id=user_id,
                    invitation_id=invitation_id
                )

                # Обновляем статус приглашения
                updated_invitation = self.project_repo.update_invitation_status(
                    invitation_id, InvitationStatus.ACCEPTED
                )

                # Отправляем уведомление создателю приглашения
                await self._send_invitation_response_notification(updated_invitation, "accepted")

                # Уведомляем всех участников о новом участнике
                await self._notify_new_project_participant(participant)

            else:  # reject
                updated_invitation = self.project_repo.update_invitation_status(
                    invitation_id, InvitationStatus.REJECTED
                )
                await self._send_invitation_response_notification(updated_invitation, "rejected")

            return InvitationResponse.model_validate(updated_invitation)

        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to respond to invitation: {str(e)}"
            )

    async def delete_invitation(self, invitation_id: int, user_id: int) -> bool:
        invitation = self.project_repo.get_invitation_by_id(invitation_id)
        if not invitation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

        # Проверяем права: либо создатель приглашения, либо админ проекта
        if invitation.invited_by != user_id:
            require_project_admin(self.project_repo, invitation.project_id, user_id)

        try:
            # Полностью удаляем приглашение
            success = self.project_repo.delete_invitation(invitation_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invitation not found"
                )

            # Отправляем уведомление об отмене приглашения
            await self._send_invitation_deleted_notification(invitation)

            return True

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel invitation: {str(e)}"
            )

    # ============ WORKSPACE METHODS ============

    async def create_workspace(self, project_id: UUID, workspace_data: WorkspaceCreate,
                               user_id: int) -> WorkspaceResponse:
        require_project_owner(self.project_repo, project_id, user_id)
        try:
            workspace = self.project_repo.create_workspace(
                project_id=project_id,
                name=workspace_data.name,
                description=workspace_data.description,
                created_by=user_id,
                create_chat=workspace_data.create_chat,
                links=workspace_data.links,
                github_links=workspace_data.github_links
            )
            return await self.get_workspace_by_id(project_id, workspace.id, user_id)

        except ValueError as e:
            print(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create workspace: {str(e)}"
            )

    async def get_workspace_by_id(self, project_id: UUID, workspace_id: UUID, user_id: int) -> WorkspaceResponse:
        """
        Получить информацию о рабочем пространстве с проверкой принадлежности к проекту.
        """
        # Проверяем доступ
        require_workspace_access(self.project_repo, workspace_id, project_id, user_id)

        # Получаем workspace и проверяем, что он принадлежит указанному проекту
        workspace = self.project_repo.get_workspace_by_id(workspace_id, include_relations=True)

        participants = []
        for wp in workspace.workspace_participants:
            pp = wp.project_participant
            participants.append(ParticipantResponse(
                user_id=pp.user_id,
                username=pp.user_profile.username,
                name=pp.user_profile.name,
                lastname=pp.user_profile.lastname,
                status=ProjectParticipantStatus(pp.status),
                role=ProjectRole(pp.role),
                joined_at=pp.joined_at,
                project_id=project_id,
                workspace_id=workspace_id,
                workspace_joined_at=wp.joined_at
            ))

        return WorkspaceResponse(
            id=workspace.id,
            project_id=workspace.project_id,
            name=workspace.name,
            description=workspace.description,
            links=workspace.links,
            github_links=workspace.github_links,
            is_main=workspace.is_main,
            chat=workspace.chat,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            participants=participants,
            participants_count=len(participants)
        )

    async def get_project_workspaces(self, project_id: UUID, user_id: int) -> List[WorkspaceResponse]:
        require_project_access(self.project_repo, project_id, user_id)
        try:
            workspaces = self.project_repo.get_project_workspaces(project_id)

            result = []
            for ws in workspaces:
                participants = []
                for wp in ws.workspace_participants:
                    pp = wp.project_participant
                    participants.append(ParticipantResponse(
                        user_id=pp.user_id,
                        username=pp.user_profile.username,
                        name=pp.user_profile.name,
                        lastname=pp.user_profile.lastname,
                        status=ProjectParticipantStatus(pp.status),
                        role=ProjectRole(pp.role),
                        joined_at=pp.joined_at,
                        project_id=project_id,
                        workspace_id=ws.id,
                        workspace_joined_at=wp.joined_at
                    ))

                result.append(WorkspaceResponse(
                    id=ws.id,
                    project_id=ws.project_id,
                    name=ws.name,
                    description=ws.description,
                    links=ws.links,
                    github_links=ws.github_links,
                    is_main=ws.is_main,
                    chat=ws.chat,
                    created_at=ws.created_at,
                    updated_at=ws.updated_at,
                    participants=participants,
                    participants_count=len(participants)
                ))

            return result
        except Exception as e:
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get workspaces: {str(e)}"
            )

    async def update_workspace(self, project_id: UUID, workspace_id: UUID,
                               update_data: WorkspaceUpdate, user_id: int) -> WorkspaceResponse:
        """
        Обновить рабочее пространство с проверкой принадлежности к проекту.
        """
        # Проверяем доступ
        require_workspace_access(self.project_repo, workspace_id, project_id, user_id)

        try:
            update_dict = update_data.model_dump(mode='json', exclude_unset=True)
            updated_workspace = self.project_repo.update_workspace(workspace_id, **update_dict)
            if not updated_workspace:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

            return await self.get_workspace_by_id(project_id, workspace_id, user_id)
        except Exception as e:
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update workspace: {str(e)}"
            )

    async def delete_workspace(self, project_id: UUID, workspace_id: UUID, user_id: int) -> bool:
        """
        Удалить рабочее пространство с проверкой принадлежности к проекту.
        """
        # Получаем workspace и проверяем принадлежность к проекту
        workspace = await self.get_workspace_by_id(project_id, workspace_id, user_id)

        # Проверяем права админа
        require_project_owner(self.project_repo, project_id, user_id)

        try:
            # Нельзя удалить основной workspace
            if workspace.is_main:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete main workspace"
                )

            success = self.project_repo.delete_workspace(workspace_id)
            if not success:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

            return True
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete workspace: {str(e)}"
            )

    # ============ PARTICIPANT METHODS ============

    async def add_participants_to_workspace(self, project_id: UUID, workspace_id: UUID,
                                            participant_data: ParticipantAdd, requester_id: int) -> List[
        ParticipantResponse]:
        """
        Добавить существующих участников проекта в рабочее пространство.
        Все пользователи должны уже быть участниками проекта.
        """
        # Проверяем права
        require_project_admin(self.project_repo, project_id, requester_id)

        # Валидация workspace
        require_workspace_access(self.project_repo, workspace_id, project_id, requester_id)

        try:
            # Проверяем существование пользователей в принципе
            users_with_profiles = self.project_repo.user.get_existing_users_ids(participant_data.user_ids)
            non_existing = [uid for uid in participant_data.user_ids if uid not in users_with_profiles]

            if non_existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Users not found: {non_existing}"
                )

            # Добавляем в workspace
            workspace_participants = self.project_repo.add_participants_to_workspace(
                workspace_id=workspace_id,
                user_ids=participant_data.user_ids
            )

            if not workspace_participants:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No new users were added (all are already in this workspace or not project participants)"
                )

            # Преобразуем в Response
            participant_responses = []
            for wp in workspace_participants:
                pp = wp.project_participant
                participant_responses.append(ParticipantResponse(
                    user_id=pp.user_id,
                    username=pp.user_profile.username,
                    name=pp.user_profile.name,
                    lastname=pp.user_profile.lastname,
                    status=pp.status,
                    role=pp.role,
                    joined_at=pp.joined_at,
                    project_id=project_id,
                    workspace_id=workspace_id,
                    workspace_joined_at=wp.joined_at
                ))

            # Уведомляем о новых участниках в workspace
            await self._notify_new_workspace_participants(workspace_participants, workspace_id, project_id)

            return participant_responses

        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add participants to workspace: {str(e)}"
            )

    async def remove_participants_from_workspace(self, project_id: UUID, workspace_id: UUID,
                                                 participant_user_ids: List[int], requester_id: int) -> bool:
        """
        Удалить участников из рабочего пространства
        """
        # Получаем workspace и проверяем принадлежность к проекту
        require_workspace_access(self.project_repo, workspace_id, project_id, requester_id)

        # Проверяем права: либо админ, либо удаляет сам себя (только если один пользователь)
        is_self_removal = len(participant_user_ids) == 1 and participant_user_ids[0] == requester_id

        if not is_self_removal:
            require_project_admin(self.project_repo, project_id, requester_id)

        workspace = await self.get_workspace_by_id(project_id, workspace_id, requester_id)

        try:
            # Нельзя удалить создателя проекта из основного workspace
            if workspace.is_main:
                project = self.project_repo.get_project_by_id(project_id)
                if project.created_by in participant_user_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot remove project creator from main workspace"
                    )

            success = self.project_repo.remove_participants_from_workspace(workspace_id, participant_user_ids)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Participants not found in this workspace"
                )

            # Отправляем уведомления об удалении
            for removed_user_id in participant_user_ids:
                await self._notify_participant_removed(project_id, workspace_id, removed_user_id, requester_id)

            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to remove participants: {str(e)}"
            )

    async def leave_project(self, project_id: UUID, user_id: int) -> bool:
        try:
            # Проверяем, не является ли пользователь создателем
            project = self.project_repo.get_project_by_id(project_id)
            if project.created_by == user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project creator cannot leave the project. Transfer ownership first or delete the project."
                )

            success = self.project_repo.leave_project(project_id, user_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="You are not a participant of this project"
                )

            # Отправляем уведомление о выходе из проекта
            await self._notify_participant_left(project_id, user_id)

            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to leave project: {str(e)}"
            )

    async def remove_participants_from_project(self, project_id: UUID, user_ids: List[int], requester_id: int) -> bool:
        """
        Удалить участников из проекта (из всех workspace).
        Проверяет права и валидирует, что нельзя удалить создателя проекта.
        """
        # Проверяем права на удаление (админ или владелец)
        require_project_owner(self.project_repo, project_id, requester_id)

        try:
            # Получаем проект для проверки создателя
            project = self.project_repo.get_project_by_id(project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project not found"
                )

            # Проверяем, что никто не пытается удалить создателя проекта
            if project.created_by in user_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove project creator from the project"
                )

            # Проверяем, что все указанные пользователи действительно участники проекта
            existing_participants = self.project_repo.get_project_participants(project_id)
            existing_user_ids = [p.user_id for p in existing_participants]

            non_existing = [uid for uid in user_ids if uid not in existing_user_ids]
            if non_existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Users {non_existing} are not participants of this project"
                )

            # Проверяем существование пользователей в принципе
            users_with_profiles = self.project_repo.user.get_existing_users_ids(user_ids)
            non_existing_users = [uid for uid in user_ids if uid not in users_with_profiles]
            if non_existing_users:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Users not found: {non_existing_users}"
                )

            # Удаляем участников из проекта
            success = self.project_repo.remove_participants_from_project(project_id, user_ids)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No participants were removed"
                )

            # Отправляем уведомления об удалении
            for removed_user_id in user_ids:
                await self._notify_participant_removed_from_project(project_id, removed_user_id, requester_id)

            return True

        except HTTPException:
            raise

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to remove participants from project: {str(e)}"
            )

    async def get_project_participants(self, project_id: UUID, user_id: int) -> List[ParticipantResponse]:
        require_project_access(self.project_repo, project_id, user_id)
        try:
            participants = self.project_repo.get_project_participants(project_id, include_user_info=True)

            result = []
            for p in participants:
                # Получаем информацию об участии в основном workspace
                main_workspace = self.project_repo.get_main_workspace(project_id)
                workspace_participation = next(
                    (wp for wp in p.workspace_participations if wp.workspace_id == main_workspace.id),
                    None
                ) if main_workspace else None

                result.append(ParticipantResponse(
                    user_id=p.user_id,
                    username=p.user_profile.username,
                    name=p.user_profile.name,
                    lastname=p.user_profile.lastname,
                    status=p.status,
                    role=p.role,
                    joined_at=p.joined_at,
                    workspace_id=main_workspace.id if main_workspace else None,
                    workspace_joined_at=workspace_participation.joined_at if workspace_participation else None
                ))

            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get participants: {str(e)}"
            )

    async def get_workspace_participants(self, project_id: UUID, workspace_id: UUID,
                                         user_id: int) -> List[ParticipantResponse]:
        """
        Получить участников рабочего пространства с проверкой принадлежности к проекту.
        """
        require_project_access(self.project_repo, project_id, user_id)
        workspace = await self.get_workspace_by_id(project_id, workspace_id, user_id)

        try:
            workspace_participants = self.project_repo.get_workspace_participants(workspace_id, include_user_info=True)

            result = []
            for wp in workspace_participants:
                pp = wp.project_participant
                result.append(ParticipantResponse(
                    user_id=pp.user_id,
                    username=pp.user_profile.username,
                    name=pp.user_profile.name,
                    lastname=pp.user_profile.lastname,
                    status=pp.status,
                    role=pp.role,
                    joined_at=pp.joined_at,
                    workspace_id=workspace_id,
                    workspace_joined_at=wp.joined_at,
                    project_id=workspace.project_id
                ))

            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get workspace participants: {str(e)}"
            )

    async def update_participant_status(self, project_id: UUID, participant_user_id: int,
                                        update_data: ParticipantUpdate, requester_id: int) -> ParticipantResponse:
        require_project_owner(self.project_repo, project_id, requester_id)

        try:
            if not update_data.status and not update_data.role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nothing to update. Provide status or role."
                )

            # Нельзя изменить роль создателя проекта
            project = self.project_repo.get_project_by_id(project_id)
            if project.created_by == participant_user_id and update_data.role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change project creator's role"
                )

            participant = self.project_repo.update_participant(
                updater_id=requester_id,
                project_id=project_id,
                participant_user_id=participant_user_id,
                new_status=update_data.status.value if update_data.status else None,
                new_role=update_data.role.value if update_data.role else None
            )

            if not participant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Participant not found"
                )

            # Отправляем уведомление об изменении статуса
            await self._notify_participant_updated(participant, requester_id)

            return ParticipantResponse(
                user_id=participant.user_id,
                username=participant.user_profile.username,
                name=participant.user_profile.name,
                lastname=participant.user_profile.lastname,
                status=participant.status,
                role=participant.role,
                joined_at=participant.joined_at
            )

        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update participant: {str(e)}"
            )

    # ============ NOTIFICATION METHODS ============

    async def _send_invitation_notification(self, invitation):
        """Отправить уведомление о новом приглашении"""
        try:
            ws_message = {
                "event": "project_invitation_received",
                "data": {
                    "invitation_id": invitation.id,
                    "project_id": str(invitation.project_id),
                    "project_name": invitation.project.name,
                    "invited_by": {
                        "user_id": invitation.inviter.user_id,
                        "username": invitation.inviter.username,
                        "name": invitation.inviter.name,
                        "lastname": invitation.inviter.lastname
                    },
                    "role": invitation.role,
                    "permission_level": invitation.permission_level,
                    "message": invitation.message,
                    "invited_at": invitation.invited_at.isoformat()
                }
            }
            await connection_manager.send_to_user(invitation.invited_user_id, ws_message)
        except Exception as e:
            print(f"Failed to send invitation notification: {e}")

    async def _send_invitation_response_notification(self, invitation, action: str):
        """Отправить уведомление об ответе на приглашение"""
        try:
            ws_message = {
                "event": "project_invitation_response",
                "data": {
                    "invitation_id": invitation.id,
                    "project_id": str(invitation.project_id),
                    "project_name": invitation.project.name,
                    "user": {
                        "user_id": invitation.invited_user.user_id,
                        "username": invitation.invited_user.username,
                        "name": invitation.invited_user.name,
                        "lastname": invitation.invited_user.lastname
                    },
                    "action": action,
                    "responded_at": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_user(invitation.invited_by, ws_message)
        except Exception as e:
            print(f"Failed to send invitation response notification: {e}")

    async def _notify_new_project_participant(self, participant: ProjectParticipant):
        """Уведомить о новом участнике проекта"""
        try:
            project_id = participant.project_id
            project_participants = self.project_repo.get_project_participants(project_id)
            participant_user_ids = [p.user_id for p in project_participants if p.user_id != participant.user_id]

            ws_message = {
                "event": "project_participant_joined",
                "data": {
                    "project_id": str(project_id),
                    "participant": {
                        "user_id": participant.user_id,
                        "username": participant.user_profile.username,
                        "name": participant.user_profile.name,
                        "lastname": participant.user_profile.lastname,
                        "role": participant.role,
                        "status": participant.status
                    },
                    "joined_at": participant.joined_at.isoformat()
                }
            }

            await connection_manager.send_to_chat(participant_user_ids, ws_message)
        except Exception as e:
            print(f"Failed to send new project participant notification: {e}")

    async def _notify_new_workspace_participants(self, workspace_participants: List[WorkspaceParticipant],
                                                 workspace_id: UUID, project_id: UUID):
        """Уведомить о новых участниках в workspace"""
        try:
            if not workspace_participants:
                return

            # Получаем всех участников workspace для уведомления
            all_workspace_participants = self.project_repo.get_workspace_participants(workspace_id)
            all_user_ids = [wp.project_participant.user_id for wp in all_workspace_participants]

            for wp in workspace_participants:
                pp = wp.project_participant
                # Не уведомляем самого добавленного пользователя
                notify_user_ids = [uid for uid in all_user_ids if uid != pp.user_id]

                ws_message = {
                    "event": "workspace_participant_joined",
                    "data": {
                        "project_id": str(project_id),
                        "workspace_id": str(workspace_id),
                        "participant": {
                            "user_id": pp.user_id,
                            "username": pp.user_profile.username,
                            "name": pp.user_profile.name,
                            "lastname": pp.user_profile.lastname,
                            "role": pp.role,
                            "status": pp.status
                        },
                        "joined_at": wp.joined_at.isoformat()
                    }
                }

                await connection_manager.send_to_chat(notify_user_ids, ws_message)
        except Exception as e:
            print(f"Failed to send new workspace participant notification: {e}")

    async def _notify_participant_removed(self, project_id: UUID, workspace_id: UUID,
                                          removed_user_id: int, removed_by_id: int):
        """Уведомить об удалении участника из workspace"""
        try:
            project_participants = self.project_repo.get_project_participants(project_id)
            participant_user_ids = [p.user_id for p in project_participants if p.user_id != removed_user_id]

            ws_message = {
                "event": "workspace_participant_removed",
                "data": {
                    "project_id": str(project_id),
                    "workspace_id": str(workspace_id),
                    "removed_user_id": removed_user_id,
                    "removed_by_id": removed_by_id,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }

            await connection_manager.send_to_chat(participant_user_ids, ws_message)

            # Отдельно уведомляем удаленного пользователя
            await connection_manager.send_to_user(removed_user_id, ws_message)

        except Exception as e:
            print(f"Failed to send participant removed notification: {e}")

    async def _notify_participant_left(self, project_id: UUID, left_user_id: int):
        """Уведомить о выходе участника из проекта"""
        try:
            project_participants = self.project_repo.get_project_participants(project_id)
            participant_user_ids = [p.user_id for p in project_participants if p.user_id != left_user_id]

            ws_message = {
                "event": "project_participant_left",
                "data": {
                    "project_id": str(project_id),
                    "user_id": left_user_id,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }

            await connection_manager.send_to_chat(participant_user_ids, ws_message)
        except Exception as e:
            print(f"Failed to send participant left notification: {e}")

    async def _notify_participant_updated(self, participant, updater_id: int):
        """Уведомить об изменении статуса/роли участника"""
        try:
            project_participants = self.project_repo.get_project_participants(participant.project_id)
            participant_user_ids = [p.user_id for p in project_participants if p.user_id != participant.user_id]

            ws_message = {
                "event": "participant_updated",
                "data": {
                    "project_id": str(participant.project_id),
                    "user_id": participant.user_id,
                    "updater_id": updater_id,
                    "new_status": participant.status,
                    "new_role": participant.role,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }

            await connection_manager.send_to_chat(participant_user_ids, ws_message)

            # Отдельно уведомляем обновленного пользователя
            await connection_manager.send_to_user(participant.user_id, ws_message)

        except Exception as e:
            print(f"Failed to send participant updated notification: {e}")

    async def _send_invitation_deleted_notification(self, invitation):
        """Отправить уведомление об отмене приглашения"""
        try:
            ws_message = {
                "event": "project_invitation_deleted",
                "data": {
                    "invitation_id": invitation.id,
                    "project_id": str(invitation.project_id),
                    "project_name": invitation.project.name,
                    "deleted_by": {
                        "user_id": invitation.inviter.user_id,
                        "username": invitation.inviter.username,
                        "name": invitation.inviter.name,
                        "lastname": invitation.inviter.lastname
                    },
                    "cancelled_at": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_user(invitation.invited_user_id, ws_message)
        except Exception as e:
            print(f"Failed to send invitation cancelled notification: {e}")

    async def _notify_participant_removed_from_project(self, project_id: UUID, removed_user_id: int,
                                                       removed_by_id: int):
        """Уведомить об удалении участника из проекта"""
        try:
            # Получаем всех оставшихся участников проекта для уведомления
            project_participants = self.project_repo.get_project_participants(project_id)
            participant_user_ids = [p.user_id for p in project_participants if p.user_id != removed_user_id]

            ws_message = {
                "event": "project_participant_removed",
                "data": {
                    "project_id": str(project_id),
                    "removed_user_id": removed_user_id,
                    "removed_by_id": removed_by_id,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }

            # Уведомляем оставшихся участников
            await connection_manager.send_to_chat(participant_user_ids, ws_message)

            # Уведомляем удаленного пользователя
            await connection_manager.send_to_user(removed_user_id, ws_message)

        except Exception as e:
            print(f"Failed to send project participant removed notification: {e}")