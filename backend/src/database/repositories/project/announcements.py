from src.database.repositories.base_repository import BaseRepository
from src.database.models import *
from sqlalchemy import and_, or_, update, exists, func, desc, case, text, select
from sqlalchemy.orm import Session, joinedload, selectinload
import uuid
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, UTC
import logging

logger = logging.getLogger(__name__)


class AnnounceRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    # ============ Announcement Methods ============

    def create_announcement(
            self,
            title: str,
            content: str,
            questions: List[str],
            project_id: uuid.UUID,
            workspace_id: uuid.UUID,
            created_by: int
    ) -> Announcement:
        """Создание объявления (без файлов, файлы добавляются отдельно)"""
        announcement = Announcement(
            title=title,
            content=content,
            questions=questions,
            project_id=project_id,
            workspace_id=workspace_id,
            created_by=created_by,
            status=AnnouncementStatus.ACTIVE.value
        )
        self.session.add(announcement)
        self.session.commit()
        self.session.refresh(announcement)
        return announcement

    def get_announcement_by_id(
            self,
            announcement_id: uuid.UUID,
            load_relations: bool = False
    ) -> Optional[Announcement]:
        """Получение объявления по ID"""
        query = self.session.query(Announcement)

        if load_relations:
            query = query.options(
                selectinload(Announcement.project),
                selectinload(Announcement.workspace),
                selectinload(Announcement.creator),
                selectinload(Announcement.files).selectinload(AnnouncementFile.file)
            )

        return query.filter(Announcement.id == announcement_id).first()

    def get_announcements_by_workspace(
            self,
            workspace_id: uuid.UUID,
            skip: int = 0,
            limit: int = 100,
            status: Optional[str] = None
    ) -> Tuple[List[Announcement], int]:
        """Получение объявлений по workspace"""
        query = self.session.query(Announcement)
        query = query.filter(Announcement.workspace_id == workspace_id)

        if status:
            query = query.filter(Announcement.status == status)

        total = query.count()

        query = query.order_by(desc(Announcement.created_at))
        query = query.offset(skip).limit(limit)

        query = query.options(
            selectinload(Announcement.creator),
            selectinload(Announcement.files).selectinload(AnnouncementFile.file)
        )

        return query.all(), total

    def get_announcements_feed(
            self,
            skip: int = 0,
            limit: int = 100,
            project_id: Optional[uuid.UUID] = None,
            workspace_id: Optional[uuid.UUID] = None,
            status: Optional[str] = None
    ) -> Tuple[List[Announcement], int]:
        """Получение ленты объявлений (публичный доступ)"""
        query = self.session.query(Announcement)

        # Показываем только активные и закрытые объявления
        if status:
            query = query.filter(Announcement.status == status)
        else:
            query = query.filter(
                Announcement.status.in_([
                    AnnouncementStatus.ACTIVE.value,
                    AnnouncementStatus.CLOSED.value
                ])
            )

        # Опциональная фильтрация по проекту
        if project_id:
            query = query.filter(Announcement.project_id == project_id)

        # Опциональная фильтрация по workspace
        if workspace_id:
            query = query.filter(Announcement.workspace_id == workspace_id)

        total = query.count()

        query = query.order_by(desc(Announcement.created_at))
        query = query.offset(skip).limit(limit)

        query = query.options(
            selectinload(Announcement.creator),
            selectinload(Announcement.project),
            selectinload(Announcement.workspace),
            selectinload(Announcement.files).selectinload(AnnouncementFile.file)
        )

        return query.all(), total

    def update_announcement(
            self,
            announcement_id: uuid.UUID,
            **kwargs
    ) -> Optional[Announcement]:
        """Обновление объявления"""
        announcement = self.get_announcement_by_id(announcement_id)
        if not announcement:
            return None

        for key, value in kwargs.items():
            if hasattr(announcement, key) and value is not None:
                setattr(announcement, key, value)

        announcement.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(announcement)
        return announcement

    def delete_announcement(self, announcement_id: uuid.UUID) -> bool:
        """Удаление объявления (мягкое удаление)"""
        announcement = self.get_announcement_by_id(announcement_id)
        if not announcement:
            return False

        announcement.status = AnnouncementStatus.ARCHIVED.value
        self.session.commit()
        return True

    def get_announcement_files(self, announcement_id: uuid.UUID) -> List[FileMetadata]:
        """Получение файлов объявления"""
        return self.session.query(FileMetadata).join(
            AnnouncementFile, AnnouncementFile.file_id == FileMetadata.id
        ).filter(
            AnnouncementFile.announcement_id == announcement_id
        ).all()

    # ============ Application Methods ============

    def create_application(
            self,
            announcement_id: uuid.UUID,
            user_id: int,
            content: str,
            links: List[str]
    ) -> Application:
        """Создание заявки (без файлов)"""
        application = Application(
            announcement_id=announcement_id,
            user_id=user_id,
            content=content,
            links=links,
            status=ApplicationStatus.PENDING.value,
            likes={},
            dislikes={}
        )
        self.session.add(application)
        self.session.commit()
        self.session.refresh(application)
        return application

    def get_application_by_id(
            self,
            application_id: uuid.UUID,
            load_relations: bool = False
    ) -> Optional[Application]:
        """Получение заявки по ID"""
        query = self.session.query(Application)

        if load_relations:
            query = query.options(
                joinedload(Application.user),
                joinedload(Application.announcement)
                .joinedload(Announcement.creator),
                joinedload(Application.announcement)
                .joinedload(Announcement.project),
                joinedload(Application.announcement)
                .joinedload(Announcement.workspace),
                selectinload(Application.files).selectinload(ApplicationFile.file)
            )

        return query.filter(Application.id == application_id).first()

    def get_user_application_for_announcement(
            self,
            announcement_id: uuid.UUID,
            user_id: int
    ) -> Optional[Application]:
        """Проверка, подавал ли пользователь заявку"""
        return self.session.query(Application).filter(
            Application.announcement_id == announcement_id,
            Application.user_id == user_id
        ).first()

    def get_applications_by_announcement(
            self,
            announcement_id: uuid.UUID,
            skip: int = 0,
            limit: int = 100,
            status: Optional[str] = None
    ) -> Tuple[List[Application], int]:
        """Получение заявок по объявлению"""
        query = self.session.query(Application)
        query = query.filter(Application.announcement_id == announcement_id)

        if status:
            query = query.filter(Application.status == status)

        total = query.count()

        query = query.order_by(desc(Application.created_at))
        query = query.offset(skip).limit(limit)

        query = query.options(
            joinedload(Application.user),
            selectinload(Application.files).selectinload(ApplicationFile.file)
        )

        return query.all(), total

    def get_applications_by_user(
            self,
            user_id: int,
            skip: int = 0,
            limit: int = 100
    ) -> Tuple[List[Application], int]:
        """Получение заявок пользователя"""
        query = self.session.query(Application).filter(
            Application.user_id == user_id
        )

        total = query.count()
        query = query.order_by(desc(Application.created_at))
        query = query.offset(skip).limit(limit)

        query = query.options(
            joinedload(Application.user),
            joinedload(Application.announcement)
            .joinedload(Announcement.creator),
            joinedload(Application.announcement)
            .joinedload(Announcement.project),
            selectinload(Application.files).selectinload(ApplicationFile.file)
        )

        return query.all(), total

    def update_application(
            self,
            application_id: uuid.UUID,
            **kwargs
    ) -> Optional[Application]:
        """Обновление заявки"""
        application = self.get_application_by_id(application_id)
        if not application:
            return None

        for key, value in kwargs.items():
            if hasattr(application, key) and value is not None:
                setattr(application, key, value)

        application.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(application)
        return application

    def delete_application(self, application_id: uuid.UUID) -> bool:
        """Удаление заявки (только если в статусе PENDING)"""
        application = self.get_application_by_id(application_id)
        if not application or application.status != ApplicationStatus.PENDING.value:
            return False

        self.session.delete(application)
        self.session.commit()
        return True

    def get_application_files(self, application_id: uuid.UUID) -> List[FileMetadata]:
        """Получение файлов заявки"""
        return self.session.query(FileMetadata).join(
            ApplicationFile, ApplicationFile.file_id == FileMetadata.id
        ).filter(
            ApplicationFile.application_id == application_id
        ).all()

    # ============ Vote Methods ============

    def get_user_vote(self, application_id: uuid.UUID, user_id: int) -> Optional[str]:
        """Получение голоса пользователя"""
        application = self.get_application_by_id(application_id)
        if not application:
            return None

        if str(user_id) in application.likes:
            return "like"
        elif str(user_id) in application.dislikes:
            return "dislike"
        return None

    def add_vote(
            self,
            application_id: uuid.UUID,
            user_id: int,
            user_name: str,
            vote_type: str
    ) -> Application:
        """Добавление голоса"""
        application = self.get_application_by_id(application_id)
        if not application:
            raise ValueError("Application not found")

        user_id_str = str(user_id)
        vote_metadata = {
            "voted_at": datetime.now(UTC).isoformat(),
            "user_name": user_name
        }

        if vote_type == "like":
            if user_id_str in application.dislikes:
                del application.dislikes[user_id_str]
            application.likes[user_id_str] = vote_metadata
        elif vote_type == "dislike":
            if user_id_str in application.likes:
                del application.likes[user_id_str]
            application.dislikes[user_id_str] = vote_metadata
        else:
            raise ValueError("Invalid vote type")

        self.session.commit()
        self.session.refresh(application)
        return application

    def remove_vote(self, application_id: uuid.UUID, user_id: int) -> Application:
        """Удаление голоса"""
        application = self.get_application_by_id(application_id)
        if not application:
            raise ValueError("Application not found")

        user_id_str = str(user_id)
        if user_id_str in application.likes:
            del application.likes[user_id_str]
        if user_id_str in application.dislikes:
            del application.dislikes[user_id_str]

        self.session.commit()
        self.session.refresh(application)
        return application

    # ============ Permission Methods ============

    def check_workspace_access(self, user_id: int, workspace_id: uuid.UUID) -> bool:
        """Проверка доступа к workspace"""
        return self.session.query(WorkspaceParticipant).join(
            ProjectParticipant,
            WorkspaceParticipant.project_participant_id == ProjectParticipant.id
        ).filter(
            ProjectParticipant.user_id == user_id,
            WorkspaceParticipant.workspace_id == workspace_id
        ).count() > 0

    def check_announcement_access(self, user_id: int, announcement_id: uuid.UUID) -> bool:
        """Проверка доступа к объявлению"""
        announcement = self.get_announcement_by_id(announcement_id)
        if not announcement:
            return False
        return self.check_workspace_access(user_id, announcement.workspace_id)

    def check_application_access(self, user_id: int, application_id: uuid.UUID) -> bool:
        """Проверка доступа к заявке (просмотр заявок на объявление)"""
        application = self.get_application_by_id(application_id, load_relations=True)
        if not application:
            return False

        announcement = application.announcement
        if not announcement:
            return False

        return self.check_workspace_access(user_id, announcement.workspace_id)

    def is_announcement_creator(self, user_id: int, announcement_id: uuid.UUID) -> bool:
        """Проверка, является ли пользователь создателем объявления"""
        announcement = self.get_announcement_by_id(announcement_id)
        if not announcement:
            return False
        return announcement.created_by == user_id

    def is_application_owner(self, user_id: int, application_id: uuid.UUID) -> bool:
        """Проверка, является ли пользователь владельцем заявки"""
        application = self.get_application_by_id(application_id)
        if not application:
            return False
        return application.user_id == user_id

    def can_vote_on_application(self, user_id: int, application_id: uuid.UUID) -> bool:
        """Проверка, может ли пользователь голосовать за заявку"""
        application = self.get_application_by_id(application_id, load_relations=True)
        if not application:
            return False

        # Нельзя голосовать за свою заявку
        if application.user_id == user_id:
            return False

        announcement = application.announcement
        if not announcement:
            return False

        return self.check_workspace_access(user_id, announcement.workspace_id)

    def get_workspace_participants(self, workspace_id: uuid.UUID) -> List[int]:
        """Получение участников workspace"""
        participants = self.session.query(ProjectParticipant.user_id).join(
            WorkspaceParticipant,
            WorkspaceParticipant.project_participant_id == ProjectParticipant.id
        ).filter(
            WorkspaceParticipant.workspace_id == workspace_id
        ).all()
        return [p[0] for p in participants]

    def get_announcement_applications_count(self, announcement_id: uuid.UUID) -> int:
        """Количество заявок на объявление"""
        return self.session.query(func.count(Application.id)).filter(
            Application.announcement_id == announcement_id
        ).scalar() or 0

    def get_workspace_admins(self, workspace_id: uuid.UUID) -> List[int]:
        """Получение админов workspace"""
        workspace = self.session.query(ProjectWorkspace).filter(
            ProjectWorkspace.id == workspace_id
        ).first()

        if not workspace:
            return []

        admins = self.session.query(ProjectParticipant.user_id).filter(
            ProjectParticipant.project_id == workspace.project_id,
            ProjectParticipant.status.in_([
                ProjectParticipantStatus.OWNER.value,
                ProjectParticipantStatus.ADMIN.value
            ])
        ).all()

        return [a[0] for a in admins]

    def get_announcement_project_info(self, announcement_id: uuid.UUID) -> Optional[Dict]:
        """Получение информации о проекте объявления для ленты"""
        announcement = self.session.query(Announcement).options(
            joinedload(Announcement.project)
        ).filter(Announcement.id == announcement_id).first()

        if not announcement or not announcement.project:
            return None

        return {
            "project_id": str(announcement.project.id),
            "project_name": announcement.project.name,
            "project_description": announcement.project.description,
            "project_status": announcement.project.status
        }