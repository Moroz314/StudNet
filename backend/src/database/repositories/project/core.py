from ...repositories.base_repository import BaseRepository
from ...models import *
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_, or_, func, update, select, delete, exists
from uuid import UUID
from typing import List, Optional, Dict, Any
from ....database.repositories.user.chat import ChatRepository


class ProjectRepository(BaseRepository):

    def __init__(self, session: Session):
        super().__init__(session)
        self.chat_repo = ChatRepository(session)

    # ============ USER HELPER METHODS ============

    @property
    def user(self):
        """Для доступа к методам пользователя"""
        return self.chat_repo.user

    # ============ PROJECT METHODS ============

    def get_project_by_id(self, project_id: UUID, include_relations: bool = False) -> Optional[Project]:
        """Получить проект по ID с опциональной загрузкой связей"""
        query = select(Project).where(Project.id == project_id)

        if include_relations:
            query = query.options(
                selectinload(Project.workspaces).selectinload(ProjectWorkspace.chat),
                selectinload(Project.project_participants).selectinload(ProjectParticipant.user_profile),
                selectinload(Project.creator),
                selectinload(Project.avatar_file),
                selectinload(Project.invitations).selectinload(ProjectInvitation.invited_user),
                selectinload(Project.invitations).selectinload(ProjectInvitation.inviter)
            )

        result = self.session.execute(query)
        return result.unique().scalar_one_or_none()

    def get_user_projects(self, user_id: int, filters: Optional[Dict[str, Any]] = None,
                          include_relations: bool = False) -> List[Project]:
        """Получить проекты пользователя с фильтрацией"""
        # Используем подзапрос для получения уникальных проектов
        subquery = (
            select(ProjectParticipant.project_id)
            .where(ProjectParticipant.user_id == user_id)
            .distinct()
            .subquery()
        )

        query = select(Project).where(Project.id.in_(subquery))

        if filters:
            if filters.get('status'):
                query = query.where(Project.status == filters['status'])

            if filters.get('search'):
                search_pattern = f"%{filters['search']}%"
                query = query.where(
                    or_(
                        Project.name.ilike(search_pattern),
                        Project.description.ilike(search_pattern)
                    )
                )

            if filters.get('tags'):
                query = query.where(Project.tags.overlap(filters['tags']))

            if filters.get('category'):
                query = query.where(Project.category == filters['category'])

        if include_relations:
            query = query.options(
                selectinload(Project.workspaces).selectinload(ProjectWorkspace.chat),
                selectinload(Project.project_participants).selectinload(ProjectParticipant.user_profile),
                selectinload(Project.creator),
                selectinload(Project.channel),
                selectinload(Project.avatar_file)
            )
        else:
            query = query.options(
                selectinload(Project.avatar_file),
                selectinload(Project.workspaces).selectinload(ProjectWorkspace.chat)
            )

        # Пагинация
        if filters:
            if filters.get('offset'):
                query = query.offset(filters['offset'])
            if filters.get('limit'):
                query = query.limit(filters['limit'])

        query = query.order_by(Project.updated_at.desc())

        result = self.session.execute(query)
        return list(result.unique().scalars().all())

    def get_projects_with_participants_count(self, project_ids: List[UUID]) -> Dict[UUID, int]:
        """Получить количество уникальных участников для проектов"""
        if not project_ids:
            return {}

        # Считаем уникальных пользователей в проекте (не записи)
        query = (
            select(
                ProjectParticipant.project_id,
                func.count(func.distinct(ProjectParticipant.user_id)).label('count')
            )
            .where(ProjectParticipant.project_id.in_(project_ids))
            .group_by(ProjectParticipant.project_id)
        )

        result = self.session.execute(query)
        return {row.project_id: row.count for row in result}

    def get_pending_invitations_count(self, project_ids: List[UUID]) -> Dict[UUID, int]:
        """Получить количество ожидающих приглашений для проектов"""
        if not project_ids:
            return {}

        query = (
            select(
                ProjectInvitation.project_id,
                func.count(ProjectInvitation.id).label('count')
            )
            .where(
                and_(
                    ProjectInvitation.project_id.in_(project_ids),
                    ProjectInvitation.status == InvitationStatus.PENDING.value
                )
            )
            .group_by(ProjectInvitation.project_id)
        )

        result = self.session.execute(query)
        return {row.project_id: row.count for row in result}

    def update_project(self, project_id: UUID, **kwargs) -> Optional[Project]:
        """Обновить проект"""
        try:
            query = (
                update(Project)
                .where(Project.id == project_id)
                .values(**kwargs, updated_at=func.now())
                .returning(Project)
            )

            result = self.session.execute(query)
            self.session.commit()
            return result.scalar_one_or_none()

        except Exception as e:
            self.session.rollback()
            raise e

    def archive_project(self, project_id: UUID) -> bool:
        """Архивировать проект"""
        try:
            query = (
                update(Project)
                .where(Project.id == project_id)
                .values(status=ProjectStatus.ARCHIVED.value, updated_at=func.now())
            )

            self.session.execute(query)
            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            raise e

    def restore_project(self, project_id: UUID) -> Optional[Project]:
        """Восстановить проект из архива"""
        try:
            query = (
                update(Project)
                .where(
                    and_(
                        Project.id == project_id,
                        Project.status == ProjectStatus.ARCHIVED.value
                    )
                )
                .values(status=ProjectStatus.ACTIVE.value, updated_at=func.now())
                .returning(Project)
            )

            result = self.session.execute(query)
            self.session.commit()
            return result.scalar_one_or_none()

        except Exception as e:
            self.session.rollback()
            raise e

    def delete_project(self, project_id: UUID) -> bool:
        """
        Удалить проект.
        Все связанные записи удалятся каскадно благодаря ondelete="CASCADE" в моделях
        """
        try:
            query = delete(Project).where(Project.id == project_id).returning(Project.id)
            result = self.session.execute(query)
            self.session.commit()
            return result.scalar_one_or_none() is not None

        except Exception as e:
            self.session.rollback()
            raise e

    def create_project(self, name: str, description: str, created_by: int,
                        create_chat: bool, category: str = None,
                       tags: List[str] = None, links: List[str] = None, github_links: List[str] = None) -> Project:
        """Создать новый проект"""
        try:
            project = Project(
                name=name,
                description=description,
                created_by=created_by,
                tags=tags,
                links=links,
                github_links=github_links,
                category=category
            )

            self.session.add(project)
            self.session.flush()

            chat = None
            if create_chat:
                chat = self.chat_repo.create_chat({
                    'name': f"Чат проекта: {name}",
                    'type': ChatRoomType.GROUP.value,
                    'created_by': created_by
                })

            main_workspace = ProjectWorkspace(
                project_id=project.id,
                name=f"{name} - Основное пространство",
                description="Главное рабочее пространство проекта",
                is_main=True,
                chat_id=chat.id if chat else None
            )

            self.session.add(main_workspace)
            self.session.flush()

            chat_participant_id = None
            if chat:
                chat_participant = ChatParticipant(
                    chat_id=chat.id,
                    user_id=created_by,
                    role=UserRole.OWNER.value
                )
                self.session.add(chat_participant)
                self.session.flush()
                chat_participant_id = chat_participant.id

            # Добавляем создателя как участника проекта
            creator_participant = ProjectParticipant(
                project_id=project.id,
                user_id=created_by,
                status=ProjectParticipantStatus.OWNER.value,
                role=ProjectRole.PROJECT_MANAGER.value
            )
            self.session.add(creator_participant)
            self.session.flush()

            # Добавляем создателя в main workspace
            workspace_participant = WorkspaceParticipant(
                workspace_id=main_workspace.id,
                project_participant_id=creator_participant.id,
                workspace_chat_participant_id=chat_participant_id
            )
            self.session.add(workspace_participant)

            self.session.commit()

            return self.get_project_by_id(project.id, include_relations=True)

        except Exception as e:
            self.session.rollback()
            raise e

    def add_user_to_project(
            self,
            project_id: UUID,
            user_id: int,
            status: str = ProjectParticipantStatus.VIEWER.value,
            role: str = ProjectRole.OTHER.value
    ) -> ProjectParticipant:

        try:
            # Проверяем, не участник ли уже
            existing = self.session.execute(
                select(ProjectParticipant)
                .where(
                    and_(
                        ProjectParticipant.project_id == project_id,
                        ProjectParticipant.user_id == user_id
                    )
                )
                .limit(1)
            ).scalar_one_or_none()

            if existing:
                return existing

            # Создаем нового участника
            participant = ProjectParticipant(
                project_id=project_id,
                user_id=user_id,
                status=status,
                role=role
            )
            self.session.add(participant)
            self.session.flush()

            # Добавляем во все workspace проекта
            workspaces = self.get_project_workspaces(project_id)
            for workspace in workspaces:
                try:
                    self.add_participants_to_workspace(
                        workspace_id=workspace.id,
                        user_ids=[user_id]
                    )
                except ValueError:
                    # Пользователь уже в workspace - ок
                    pass

            self.session.commit()
            return participant

        except Exception as e:
            self.session.rollback()
            raise e

    # ============ INVITATION METHODS ============

    def create_invitation(self, project_id: UUID, invited_user_id: int, invited_by: int,
                          role: ProjectRole = ProjectRole.OTHER,
                          permission_level: ProjectParticipantStatus = ProjectParticipantStatus.VIEWER,
                          message: Optional[str] = None) -> ProjectInvitation:

        try:
            invitation = ProjectInvitation(
                project_id=project_id,
                invited_user_id=invited_user_id,
                invited_by=invited_by,
                status=InvitationStatus.PENDING.value,
                role=role.value if hasattr(role, 'value') else role,
                permission_level=permission_level.value if hasattr(permission_level, 'value') else permission_level,
                message=message
            )

            self.session.add(invitation)
            self.session.flush()
            self.session.commit()

            return self.get_invitation_by_id(invitation.id)

        except Exception as e:
            self.session.rollback()
            raise e

    def get_project_user_invitation(self, project_id: UUID, user_id: int) -> Optional[ProjectInvitation]:
        """Получить ожидающее приглашение"""
        query = (
            select(ProjectInvitation)
            .where(
                and_(
                    ProjectInvitation.project_id == project_id,
                    ProjectInvitation.invited_user_id == user_id,
                )
            )
            .options(
                selectinload(ProjectInvitation.project),
                selectinload(ProjectInvitation.invited_user),
                selectinload(ProjectInvitation.inviter)
            )
        )

        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def get_invitation_by_id(self, invitation_id: int) -> Optional[ProjectInvitation]:
        """Получить приглашение по ID"""
        query = (
            select(ProjectInvitation)
            .where(ProjectInvitation.id == invitation_id)
            .options(
                selectinload(ProjectInvitation.project),
                selectinload(ProjectInvitation.invited_user),
                selectinload(ProjectInvitation.inviter)
            )
        )

        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def get_user_invitations(self, user_id: int, status_filter: Optional[InvitationStatus] = None) -> List[
        ProjectInvitation]:
        """Получить приглашения пользователя"""
        query = (
            select(ProjectInvitation)
            .where(ProjectInvitation.invited_user_id == user_id)
            .options(
                selectinload(ProjectInvitation.project),
                selectinload(ProjectInvitation.invited_user),
                selectinload(ProjectInvitation.inviter)
            )
        )

        if status_filter:
            query = query.where(ProjectInvitation.status == status_filter.value)

        query = query.order_by(ProjectInvitation.invited_at.desc())

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_project_invitations(self, project_id: UUID, status_filter: Optional[InvitationStatus] = None) -> List[
        ProjectInvitation]:
        """Получить приглашения проекта"""
        query = (
            select(ProjectInvitation)
            .where(ProjectInvitation.project_id == project_id)
            .options(
                selectinload(ProjectInvitation.invited_user),
                selectinload(ProjectInvitation.inviter)
            )
        )

        if status_filter:
            query = query.where(ProjectInvitation.status == status_filter.value)

        query = query.order_by(ProjectInvitation.invited_at.desc())

        result = self.session.execute(query)
        return list(result.scalars().all())

    def update_invitation_status(self, invitation_id: int, status: InvitationStatus) -> Optional[ProjectInvitation]:
        """Обновить статус приглашения"""
        try:
            query = (
                update(ProjectInvitation)
                .where(ProjectInvitation.id == invitation_id)
                .values(
                    status=status.value,
                    responded_at=func.now()
                )
                .returning(ProjectInvitation)
            )

            result = self.session.execute(query)
            self.session.commit()
            return result.scalar_one_or_none()

        except Exception as e:
            self.session.rollback()
            raise e

    def delete_invitation(self, invitation_id: int) -> bool:
        try:
            query = delete(ProjectInvitation).where(ProjectInvitation.id == invitation_id)
            result = self.session.execute(query)
            self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            self.session.rollback()
            raise e


    # ============ WORKSPACE METHODS ============

    def get_project_workspaces(self, project_id: UUID) -> List[ProjectWorkspace]:
        """Получить все workspace проекта"""
        query = (
            select(ProjectWorkspace)
            .where(
                ProjectWorkspace.project_id == project_id,
            )
            .options(
                joinedload(ProjectWorkspace.chat),
                selectinload(ProjectWorkspace.workspace_participants)
                .selectinload(WorkspaceParticipant.project_participant)
                .selectinload(ProjectParticipant.user_profile)
            )
        )

        result = self.session.execute(query)
        return list(result.unique().scalars().all())

    def get_main_workspace(self, project_id: UUID) -> Optional[ProjectWorkspace]:
        """Получить основной workspace проекта"""
        query = (
            select(ProjectWorkspace)
            .where(
                and_(
                    ProjectWorkspace.project_id == project_id,
                    ProjectWorkspace.is_main == True
                )
            )
            .options(
                joinedload(ProjectWorkspace.chat),
                selectinload(ProjectWorkspace.workspace_participants)
            )
        )

        result = self.session.execute(query)
        return result.unique().scalar_one_or_none()

    def get_workspace_by_id(self, workspace_id: UUID, include_relations: bool = False) -> Optional[ProjectWorkspace]:
        """Получить workspace по ID"""
        query = select(ProjectWorkspace).where(ProjectWorkspace.id == workspace_id)

        if include_relations:
            query = query.options(
                joinedload(ProjectWorkspace.project),
                joinedload(ProjectWorkspace.chat),
                selectinload(ProjectWorkspace.workspace_participants)
                .selectinload(WorkspaceParticipant.project_participant)
                .selectinload(ProjectParticipant.user_profile)
            )

        result = self.session.execute(query)
        return result.unique().scalar_one_or_none()

    def update_workspace(self, workspace_id: UUID, **kwargs) -> Optional[ProjectWorkspace]:
        """Обновить workspace"""
        try:
            query = (
                update(ProjectWorkspace)
                .where(ProjectWorkspace.id == workspace_id)
                .values(**kwargs, updated_at=func.now())
                .returning(ProjectWorkspace)
            )

            result = self.session.execute(query)
            self.session.commit()
            return result.scalar_one_or_none()

        except Exception as e:
            self.session.rollback()
            raise e

    def delete_workspace(self, workspace_id: UUID) -> bool:
        """
        Удалить workspace.
        Связанные WorkspaceParticipant удалятся каскадно
        """
        try:
            # Проверяем, не основной ли это workspace
            workspace = self.session.get(ProjectWorkspace, workspace_id)
            if not workspace:
                return False

            if workspace.is_main:
                raise ValueError("Cannot delete main workspace")

            query = delete(ProjectWorkspace).where(ProjectWorkspace.id == workspace_id)
            self.session.execute(query)
            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            raise e

    def create_workspace(self, project_id: UUID, name: str, description: str,
                         created_by: int, create_chat: bool,
                         links: List[str] = None, github_links: List[str] = None) -> ProjectWorkspace:
        """Создать новый workspace"""
        try:
            project = self.get_project_by_id(project_id)
            if not project:
                raise ValueError("Project not found")

            # Проверяем, что создатель является участником проекта
            if not self.is_user_in_project(project_id, created_by):
                raise ValueError("Creator must be a project participant")

            chat = None
            chat_participant_id = None

            if create_chat:
                chat = self.chat_repo.create_chat({
                    'name': f"{project.name} - {name}",
                    'type': ChatRoomType.GROUP.value,
                    'created_by': created_by
                })

                chat_participant = ChatParticipant(
                    chat_id=chat.id,
                    user_id=created_by,
                    role=UserRole.OWNER.value
                )
                self.session.add(chat_participant)
                self.session.flush()
                chat_participant_id = chat_participant.id

            workspace = ProjectWorkspace(
                project_id=project_id,
                name=name,
                description=description,
                chat_id=chat.id if create_chat else None,
                links=links,
                github_links=github_links,
                is_main=False
            )

            self.session.add(workspace)
            self.session.flush()

            # Получаем ProjectParticipant создателя
            project_participant = self.session.execute(
                select(ProjectParticipant)
                .where(
                    and_(
                        ProjectParticipant.project_id == project_id,
                        ProjectParticipant.user_id == created_by
                    )
                )
                .limit(1)
            ).scalar_one()

            # Добавляем создателя в новый workspace
            workspace_participant = WorkspaceParticipant(
                workspace_id=workspace.id,
                project_participant_id=project_participant.id,
                workspace_chat_participant_id=chat_participant_id
            )
            self.session.add(workspace_participant)

            self.session.commit()

            return self.get_workspace_by_id(workspace.id, include_relations=True)

        except Exception as e:
            self.session.rollback()
            raise e

    # ============ PARTICIPANT METHODS ============

    def add_project_participant_from_invitation(self, project_id: UUID, user_id: int,
                                                invitation_id: int) -> Optional[ProjectParticipant]:
        """
        Добавить пользователя в проект при принятии приглашения.
        Требуется invitation_id для валидации.
        """
        try:
            # Проверяем, что приглашение действительно существует и принадлежит пользователю
            invitation = self.session.execute(
                select(ProjectInvitation)
                .where(
                    and_(
                        ProjectInvitation.id == invitation_id,
                        ProjectInvitation.invited_user_id == user_id,
                        ProjectInvitation.project_id == project_id,
                        ProjectInvitation.status == InvitationStatus.PENDING.value
                    )
                )
            ).scalar_one_or_none()

            if not invitation:
                raise ValueError("Invalid or expired invitation")

            # Проверяем, не участник ли уже
            if self.is_user_in_project(project_id, user_id):
                raise ValueError("User is already a participant in this project")

            # Получаем основной workspace
            main_workspace = self.get_main_workspace(project_id)
            if not main_workspace:
                raise ValueError("Main workspace not found")

            # Создаем участника проекта
            project_participant = ProjectParticipant(
                project_id=project_id,
                user_id=user_id,
                status=invitation.permission_level,
                role=invitation.role
            )
            self.session.add(project_participant)
            self.session.flush()

            # Добавляем в основной workspace
            chat_participant_id = None
            if main_workspace.chat_id:
                chat_participant_id = self._get_or_create_chat_participant(user_id, main_workspace.chat_id)

            workspace_participant = WorkspaceParticipant(
                workspace_id=main_workspace.id,
                project_participant_id=project_participant.id,
                workspace_chat_participant_id=chat_participant_id
            )
            self.session.add(workspace_participant)

            self.session.commit()

            return self.session.execute(
                select(ProjectParticipant)
                .where(ProjectParticipant.id == project_participant.id)
                .options(
                    selectinload(ProjectParticipant.user_profile),
                    selectinload(ProjectParticipant.workspace_participations)
                    .selectinload(WorkspaceParticipant.workspace)
                )
            ).scalar_one()

        except Exception as e:
            self.session.rollback()
            raise e

    def add_participants_to_workspace(self, workspace_id: UUID, user_ids: List[int]) -> List[WorkspaceParticipant]:
        """
        Добавить существующих участников проекта в конкретный workspace.
        Проверяет, что все пользователи уже являются участниками проекта.
        """
        try:
            if not user_ids:
                return []

            # Получаем workspace и проверяем его существование
            workspace = self.session.get(ProjectWorkspace, workspace_id)
            if not workspace:
                raise ValueError("Workspace not found")

            # Получаем всех участников проекта, которые уже есть в этом проекте
            project_participants = {
                pp.user_id: pp
                for pp in self.session.execute(
                    select(ProjectParticipant)
                    .where(
                        and_(
                            ProjectParticipant.project_id == workspace.project_id,
                            ProjectParticipant.user_id.in_(user_ids)
                        )
                    )
                    .options(selectinload(ProjectParticipant.workspace_participations))
                ).scalars().all()
            }

            # Проверяем, все ли запрашиваемые пользователи являются участниками проекта
            not_in_project = [uid for uid in user_ids if uid not in project_participants]
            if not_in_project:
                raise ValueError(f"Users {not_in_project} are not participants of the project")

            # Проверяем, кто уже в workspace
            existing_in_workspace = {
                wp.project_participant.user_id: wp
                for wp in self.session.execute(
                    select(WorkspaceParticipant)
                    .where(WorkspaceParticipant.workspace_id == workspace_id)
                    .options(selectinload(WorkspaceParticipant.project_participant))
                ).scalars().all()
            }

            added_participants = []

            for user_id in user_ids:
                # Пропускаем уже добавленных
                if user_id in existing_in_workspace:
                    continue

                project_participant = project_participants[user_id]

                # Добавляем в чат workspace если он есть
                chat_participant_id = None
                if workspace.chat_id:
                    chat_participant_id = self._get_or_create_chat_participant(user_id, workspace.chat_id)

                workspace_participant = WorkspaceParticipant(
                    workspace_id=workspace_id,
                    project_participant_id=project_participant.id,
                    workspace_chat_participant_id=chat_participant_id
                )
                self.session.add(workspace_participant)
                self.session.flush()
                added_participants.append(workspace_participant)

            self.session.commit()

            # Загружаем добавленных с отношениями
            if added_participants:
                participant_ids = [wp.id for wp in added_participants]
                return self.session.execute(
                    select(WorkspaceParticipant)
                    .where(WorkspaceParticipant.id.in_(participant_ids))
                    .options(
                        selectinload(WorkspaceParticipant.project_participant)
                        .selectinload(ProjectParticipant.user_profile)
                    )
                ).scalars().all()

            return []

        except Exception as e:
            self.session.rollback()
            raise e

    def _get_or_create_chat_participant(self, user_id: int, chat_id: UUID) -> Optional[int]:
        """Вспомогательный метод для получения или создания участника чата"""
        if not chat_id:
            return None

        chat_participant = self.session.execute(
            select(ChatParticipant)
            .where(
                and_(
                    ChatParticipant.chat_id == chat_id,
                    ChatParticipant.user_id == user_id
                )
            )
        ).scalar_one_or_none()

        if chat_participant:
            return chat_participant.id

        chat_participant = ChatParticipant(
            chat_id=chat_id,
            user_id=user_id,
            role=UserRole.MEMBER.value
        )
        self.session.add(chat_participant)
        self.session.flush()
        return chat_participant.id

    def remove_participants_from_workspace(self, workspace_id: UUID, user_ids: List[int]) -> bool:
        """
        Удалить участников из workspace одним запросом
        """
        try:
            if not user_ids:
                return True

            # Удаляем WorkspaceParticipant для указанных пользователей
            subquery = (
                select(WorkspaceParticipant.id)
                .join(WorkspaceParticipant.project_participant)
                .where(
                    and_(
                        WorkspaceParticipant.workspace_id == workspace_id,
                        ProjectParticipant.user_id.in_(user_ids)
                    )
                )
                .subquery()
            )

            query = delete(WorkspaceParticipant).where(WorkspaceParticipant.id.in_(subquery))
            self.session.execute(query)
            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            raise e

    def remove_participants_from_project(self, project_id: UUID, user_ids: List[int]) -> bool:
        """
        Удалить участников из проекта (из всех workspace).
        Все связанные записи удалятся каскадно благодаря ondelete="CASCADE" в моделях.
        """
        try:
            if not user_ids:
                return True

            # Получаем все workspace проекта, чтобы потом удалить из чатов
            workspaces = self.get_project_workspaces(project_id)
            workspace_chat_ids = [ws.chat_id for ws in workspaces if ws.chat_id]

            # Для каждого пользователя удаляем из чатов workspace
            for user_id in user_ids:
                for chat_id in workspace_chat_ids:
                    if chat_id:
                        self.chat_repo.remove_user_from_chat(chat_id, user_id)

            # Удаляем ProjectParticipant для указанных пользователей
            # WorkspaceParticipant удалятся каскадно
            query = (
                delete(ProjectParticipant)
                .where(
                    and_(
                        ProjectParticipant.project_id == project_id,
                        ProjectParticipant.user_id.in_(user_ids)
                    )
                )
            )

            result = self.session.execute(query)
            self.session.commit()

            return result.rowcount > 0

        except Exception as e:
            self.session.rollback()
            raise e

    def leave_project(self, project_id: UUID, user_id: int) -> bool:
        """
        Пользователь покидает проект.
        Удаляет все записи пользователя из проекта (из всех workspace)
        """
        try:
            # Проверяем, не является ли пользователь создателем
            project = self.get_project_by_id(project_id)
            if project and project.created_by == user_id:
                raise ValueError("Project creator cannot leave the project")

            # Получаем ProjectParticipant пользователя
            project_participants = self.session.execute(
                select(ProjectParticipant)
                .where(
                    and_(
                        ProjectParticipant.project_id == project_id,
                        ProjectParticipant.user_id == user_id
                    )
                )
            ).scalars().all()

            if not project_participants:
                return False

            # Получаем все workspace, в которых участвует пользователь
            workspace_ids = [
                wp.workspace_id
                for pp in project_participants
                for wp in pp.workspace_participations
            ]

            # Удаляем из чатов всех workspace
            for workspace_id in workspace_ids:
                workspace = self.session.get(ProjectWorkspace, workspace_id)
                if workspace and workspace.chat_id:
                    self.chat_repo.remove_user_from_chat(workspace.chat_id, user_id)

            # Удаляем все записи пользователя в проекте (WorkspaceParticipant удалятся каскадно)
            for pp in project_participants:
                self.session.delete(pp)

            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            raise e

    def get_project_participants(self, project_id: UUID, include_user_info: bool = False) -> List[ProjectParticipant]:
        """Получить уникальных участников проекта"""
        query = (
            select(ProjectParticipant)
            .where(ProjectParticipant.project_id == project_id)
            .distinct(ProjectParticipant.user_id)
        )

        if include_user_info:
            query = query.options(
                selectinload(ProjectParticipant.user_profile),
                selectinload(ProjectParticipant.workspace_participations)
                .selectinload(WorkspaceParticipant.workspace)
            )

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_workspace_participants(self, workspace_id: UUID, include_user_info: bool = False) -> List[
        WorkspaceParticipant]:
        """Получить участников workspace"""
        query = (
            select(WorkspaceParticipant)
            .where(WorkspaceParticipant.workspace_id == workspace_id)
        )

        if include_user_info:
            query = query.options(
                selectinload(WorkspaceParticipant.project_participant)
                .selectinload(ProjectParticipant.user_profile)
            )

        result = self.session.execute(query)
        return list(result.scalars().all())

    def is_user_in_project(self, project_id: UUID, user_id: int) -> bool:
        """Проверить, является ли пользователь участником проекта"""
        query = select(exists().where(
            and_(
                ProjectParticipant.project_id == project_id,
                ProjectParticipant.user_id == user_id
            )
        ))
        result = self.session.execute(query)
        return result.scalar()

    def is_user_in_workspace(self, workspace_id: UUID, user_id: int) -> bool:
        """Проверить, является ли пользователь участником workspace"""
        query = select(exists().where(
            and_(
                WorkspaceParticipant.workspace_id == workspace_id,
                WorkspaceParticipant.project_participant.has(
                    ProjectParticipant.user_id == user_id
                )
            )
        ))
        result = self.session.execute(query)
        return result.scalar()

    def check_user_permission(self, project_id: UUID, user_id: int,
                              allowed_statuses: List[str]) -> bool:
        """Проверить права пользователя в проекте"""
        participant = self.session.execute(
            select(ProjectParticipant)
            .where(
                and_(
                    ProjectParticipant.project_id == project_id,
                    ProjectParticipant.user_id == user_id
                )
            )
            .limit(1)
        ).scalar_one_or_none()

        if not participant:
            return False

        return participant.status in [s for s in allowed_statuses]

    def update_participant(self, updater_id: int, project_id: UUID, participant_user_id: int,
                           new_status: Optional[str] = None,
                           new_role: Optional[str] = None) -> Optional[ProjectParticipant]:
        """Обновить статус или роль участника проекта"""
        try:
            # Получаем участника
            participant = self.session.execute(
                select(ProjectParticipant)
                .where(
                    and_(
                        ProjectParticipant.project_id == project_id,
                        ProjectParticipant.user_id == participant_user_id
                    )
                )
                .limit(1)
            ).scalar_one_or_none()

            if not participant:
                raise ValueError("Participant not found")

            # Нельзя менять статус самого себя
            if participant.user_id == updater_id:
                raise ValueError("Cannot change your own status")

            # Проверяем права на изменение статуса
            if new_status == ProjectParticipantStatus.OWNER.value:
                updater = self.session.execute(
                    select(ProjectParticipant)
                    .where(
                        and_(
                            ProjectParticipant.project_id == project_id,
                            ProjectParticipant.user_id == updater_id
                        )
                    )
                    .limit(1)
                ).scalar_one_or_none()

                if not updater or updater.status != ProjectParticipantStatus.OWNER.value:
                    raise ValueError("Only owner can transfer ownership")

                # Понижаем текущего владельца до админа во всех его участиях
                self.session.execute(
                    update(ProjectParticipant)
                    .where(
                        and_(
                            ProjectParticipant.project_id == project_id,
                            ProjectParticipant.user_id == updater_id
                        )
                    )
                    .values(status=ProjectParticipantStatus.ADMIN.value)
                )

            # Обновляем поля
            if new_status or new_role:
                update_values = {}
                if new_status:
                    update_values['status'] = new_status
                if new_role:
                    update_values['role'] = new_role

                self.session.execute(
                    update(ProjectParticipant)
                    .where(
                        and_(
                            ProjectParticipant.project_id == project_id,
                            ProjectParticipant.user_id == participant_user_id
                        )
                    )
                    .values(**update_values)
                )

            self.session.commit()

            # Возвращаем обновленного участника
            return self.session.execute(
                select(ProjectParticipant)
                .where(
                    and_(
                        ProjectParticipant.project_id == project_id,
                        ProjectParticipant.user_id == participant_user_id
                    )
                )
                .options(selectinload(ProjectParticipant.user_profile))
                .limit(1)
            ).scalar_one()

        except Exception as e:
            self.session.rollback()
            raise e