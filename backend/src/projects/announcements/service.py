import os
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status as http_status, Depends
from sqlalchemy.orm import Session
from ...database.models import Application, ApplicationStatus, AnnouncementStatus, Announcement
from ...users.auth.service.utils import verify_token
from ...database.core import get_db
from ...database.repositories.project.announcements import AnnounceRepository
from ...database.repositories.files import FileRepository
from ...database.repositories.project.core import ProjectRepository
from ...files.service import FileService
from ...files.schemas import FileType as GlobalFileType
from .schemas import *
from ..validation import require_workspace_access, require_project_admin, require_project_owner
from ...websockets.connection import connection_manager
from datetime import datetime, UTC

FILE_URL_EXPIRY = 3600  # 1 час
AVATAR_URL_EXPIRY = 86400  # 24 часа


def get_announcement_service(
        db: Session = Depends(get_db),
        user_id: int = Depends(verify_token)
) -> "AnnouncementService":
    announce_repo = AnnounceRepository(session=db)
    file_repo = FileRepository(session=db)
    project_repo = ProjectRepository(session=db)
    file_service = FileService(session=db)

    return AnnouncementService(
        announce_repo=announce_repo,
        file_repo=file_repo,
        project_repo=project_repo,
        file_service=file_service,
        user_id=user_id
    )


class AnnouncementService:
    def __init__(
            self,
            announce_repo: AnnounceRepository,
            file_repo: FileRepository,
            project_repo: ProjectRepository,
            file_service: FileService,
            user_id: int
    ):
        self.announce_repo = announce_repo
        self.file_repo = file_repo
        self.project_repo = project_repo
        self.file_service = file_service
        self.user_id = user_id

    # ============ Вспомогательные методы для файлов ============

    async def _get_file_urls_batch(self, files: List) -> dict:
        """Получение URL для списка файлов через FileService"""
        if not files:
            return {}
        file_ids = [f.id for f in files]
        return await self.file_service.get_file_urls_batch(
            file_ids=file_ids,
            user_id=self.user_id,
            expires_in=FILE_URL_EXPIRY
        )

    async def _get_avatar_url(self, avatar_file) -> Optional[str]:
        """Получение URL аватара"""
        if not avatar_file:
            return None
        try:
            return await self.file_service.get_file_url(
                file_id=avatar_file.id,
                user_id=self.user_id,
                expires_in=AVATAR_URL_EXPIRY
            )
        except Exception:
            return None

    async def _validate_files(self, file_ids: List[UUID], expected_type: GlobalFileType) -> List[UUID]:
        if not file_ids:
            return []

        valid_file_ids = await self.file_service.validate_files_batch(
            file_ids=file_ids,
            file_type=expected_type,
            user_id=self.user_id
        )

        return valid_file_ids

    # ============ Announcement Methods ============

    async def create_announcement(
            self,
            project_id: UUID,
            workspace_id: UUID,
            data: AnnouncementCreate
    ) -> AnnouncementResponse:
        """Создание объявления (только owner проекта)"""
        # Проверяем, что пользователь - owner проекта
        require_project_owner(self.project_repo, project_id, self.user_id)

        # Валидируем файлы если есть
        valid_file_ids = []
        if data.file_ids:
            valid_file_ids = await self._validate_files(data.file_ids, GlobalFileType.ANNOUNCEMENT_FILE)

        # Создаем объявление
        announcement = self.announce_repo.create_announcement(
            title=data.title,
            content=data.content,
            questions=data.questions,
            project_id=project_id,
            workspace_id=workspace_id,
            created_by=self.user_id
        )

        # Привязываем файлы
        if valid_file_ids:
            self.file_repo.attach_files_to_announcement(announcement.id, valid_file_ids)

        # Уведомляем участников workspace
        await self._notify_announcement_created(announcement, workspace_id)

        return await self.get_announcement(announcement.id)

    async def get_announcement(self, announcement_id: UUID) -> AnnouncementResponse:
        """Получение объявления по ID"""
        announcement = self.announce_repo.get_announcement_by_id(announcement_id, load_relations=True)
        if not announcement:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Announcement not found")

        # Лента объявлений публична: любой авторизованный пользователь может просматривать объявление

        # Получаем файлы и URL
        files = self.announce_repo.get_announcement_files(announcement_id)
        urls = await self._get_file_urls_batch(files)

        file_responses = []
        for f in files:
            file_responses.append(FileResponse(
                id=f.id,
                url=urls.get(f.id, ""),
                original_filename=f.original_filename,
                mime_type=f.mime_type,
                size_bytes=f.size_bytes
            ))

        # Получаем аватар создателя
        creator_avatar = await self._get_avatar_url(announcement.creator.avatar_file if announcement.creator else None)

        # Считаем количество заявок
        applications_count = self.announce_repo.get_announcement_applications_count(announcement_id)

        # Проверяем, подавал ли пользователь заявку
        user_application = self.announce_repo.get_user_application_for_announcement(announcement_id, self.user_id)

        return AnnouncementResponse(
            id=announcement.id,
            title=announcement.title,
            content=announcement.content,
            questions=announcement.questions,
            project_id=announcement.project_id,
            workspace_id=announcement.workspace_id,
            status=announcement.status,
            created_by=announcement.created_by,
            created_at=announcement.created_at,
            updated_at=announcement.updated_at,
            files=file_responses,
            creator=CreatorResponse(
                user_id=announcement.creator.user_id if announcement.creator else 0,
                name=announcement.creator.name if announcement.creator else None,
                lastname=announcement.creator.lastname if announcement.creator else None,
                username=announcement.creator.username if announcement.creator else None,
                avatar_url=creator_avatar
            ),
            applications_count=applications_count,
            has_user_application=user_application is not None,
            user_application_id=user_application.id if user_application else None
        )

    async def get_announcements_feed(
            self,
            skip: int = 0,
            limit: int = 100,
            project_id: Optional[UUID] = None,
            workspace_id: Optional[UUID] = None,
            status: Optional[str] = None
    ) -> AnnouncementFeedResponse:
        """Получение публичной ленты объявлений"""
        announcements, total = self.announce_repo.get_announcements_feed(
            skip=skip,
            limit=limit,
            project_id=project_id,
            workspace_id=workspace_id,
            status=status
        )

        items = []
        for ann in announcements:
            creator_avatar = await self._get_avatar_url(ann.creator.avatar_file if ann.creator else None)
            applications_count = self.announce_repo.get_announcement_applications_count(ann.id)

            # Получаем информацию о проекте
            project_info = None
            if ann.project:
                project_info = ProjectShortResponse(
                    project_id=ann.project.id,
                    project_name=ann.project.name,
                    project_description=ann.project.description,
                    project_status=ann.project.status
                )

            items.append(AnnouncementFeedItem(
                id=ann.id,
                title=ann.title,
                content=ann.content,
                project_id=ann.project_id,
                workspace_id=ann.workspace_id,
                status=ann.status,
                created_by=ann.created_by,
                created_at=ann.created_at,
                updated_at=ann.updated_at,
                creator=CreatorResponse(
                    user_id=ann.creator.user_id if ann.creator else 0,
                    name=ann.creator.name if ann.creator else None,
                    lastname=ann.creator.lastname if ann.creator else None,
                    username=ann.creator.username if ann.creator else None,
                    avatar_url=creator_avatar
                ),
                project=project_info,
                applications_count=applications_count,
                questions_count=len(ann.questions) if ann.questions else 0
            ))

        return AnnouncementFeedResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def get_workspace_announcements(
            self,
            project_id: UUID,
            workspace_id: UUID,
            skip: int = 0,
            limit: int = 100,
            status: Optional[str] = None
    ) -> AnnouncementListResponse:
        """Получение объявлений workspace"""
        require_workspace_access(self.project_repo, workspace_id, project_id, self.user_id)

        announcements, total = self.announce_repo.get_announcements_by_workspace(
            workspace_id=workspace_id,
            skip=skip,
            limit=limit,
            status=status
        )

        items = []
        for ann in announcements:
            # Получаем файлы и URL
            files = self.announce_repo.get_announcement_files(ann.id)
            urls = await self._get_file_urls_batch(files)

            file_responses = []
            for f in files:
                file_responses.append(FileResponse(
                    id=f.id,
                    url=urls.get(f.id, ""),
                    original_filename=f.original_filename,
                    mime_type=f.mime_type,
                    size_bytes=f.size_bytes
                ))

            creator_avatar = await self._get_avatar_url(ann.creator.avatar_file if ann.creator else None)
            applications_count = self.announce_repo.get_announcement_applications_count(ann.id)
            user_application = self.announce_repo.get_user_application_for_announcement(ann.id, self.user_id)

            items.append(AnnouncementResponse(
                id=ann.id,
                title=ann.title,
                content=ann.content,
                questions=ann.questions,
                project_id=ann.project_id,
                workspace_id=ann.workspace_id,
                status=ann.status,
                created_by=ann.created_by,
                created_at=ann.created_at,
                updated_at=ann.updated_at,
                files=file_responses,
                creator=CreatorResponse(
                    user_id=ann.creator.user_id if ann.creator else 0,
                    name=ann.creator.name if ann.creator else None,
                    lastname=ann.creator.lastname if ann.creator else None,
                    username=ann.creator.username if ann.creator else None,
                    avatar_url=creator_avatar
                ),
                applications_count=applications_count,
                has_user_application=user_application is not None,
                user_application_id=user_application.id if user_application else None
            ))

        return AnnouncementListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def update_announcement(
            self,
            announcement_id: UUID,
            data: AnnouncementUpdate
    ) -> AnnouncementResponse:
        """Обновление объявления"""
        announcement = self.announce_repo.get_announcement_by_id(announcement_id)
        if not announcement:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Announcement not found")

        # Проверяем права (только создатель или админ)
        if not self.announce_repo.is_announcement_creator(self.user_id, announcement_id):
            require_project_admin(self.project_repo, announcement.project_id, self.user_id)

        update_dict = data.model_dump(exclude_unset=True, exclude={'file_ids'})
        if update_dict:
            self.announce_repo.update_announcement(announcement_id, **update_dict)

        # Обновляем файлы если переданы
        if data.file_ids is not None:
            valid_file_ids = await self._validate_files(data.file_ids, GlobalFileType.ANNOUNCEMENT_FILE)
            self.file_repo.detach_files_from_announcement(announcement_id)
            if valid_file_ids:
                self.file_repo.attach_files_to_announcement(announcement_id, valid_file_ids)

        return await self.get_announcement(announcement_id)

    async def delete_announcement(self, announcement_id: UUID) -> bool:
        """Удаление объявления"""
        announcement = self.announce_repo.get_announcement_by_id(announcement_id)
        if not announcement:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Announcement not found")

        # Проверяем права (только создатель или админ)
        if not self.announce_repo.is_announcement_creator(self.user_id, announcement_id):
            require_project_admin(self.project_repo, announcement.project_id, self.user_id)

        # Отвязываем файлы
        self.file_repo.detach_files_from_announcement(announcement_id)

        # Удаляем объявление
        return self.announce_repo.delete_announcement(announcement_id)

    # ============ Application Methods ============

    async def create_application(
            self,
            announcement_id: UUID,
            data: ApplicationCreate
    ) -> ApplicationResponse:
        """Создание заявки (может подать любой желающий)"""
        announcement = self.announce_repo.get_announcement_by_id(announcement_id)
        if not announcement:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Announcement not found")

        if announcement.status != AnnouncementStatus.ACTIVE.value:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Announcement is not active")

        existing = self.announce_repo.get_user_application_for_announcement(announcement_id, self.user_id)
        if existing:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="You have already applied")

        # Валидируем файлы
        valid_file_ids = []
        if data.file_ids:
            valid_file_ids = await self._validate_files(data.file_ids, GlobalFileType.APPLICATION_FILE)

        # Создаем заявку
        application = self.announce_repo.create_application(
            announcement_id=announcement_id,
            user_id=self.user_id,
            content=data.content,
            links=data.links or []
        )

        # Привязываем файлы
        if valid_file_ids:
            self.file_repo.attach_files_to_application(application.id, valid_file_ids)

        # Уведомляем создателя объявления и админов
        await self._notify_application_created(application, announcement)

        return await self.get_application(application.id)

    async def get_application(self, application_id: UUID) -> ApplicationResponse:
        """Получение заявки по ID"""
        application = self.announce_repo.get_application_by_id(application_id, load_relations=True)
        if not application:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Application not found")

        # Проверяем доступ
        is_owner = application.user_id == self.user_id
        is_admin = self.announce_repo.check_announcement_access(self.user_id, application.announcement_id)

        if not is_owner and not is_admin:
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Получаем файлы и URL
        files = self.announce_repo.get_application_files(application_id)
        urls = await self._get_file_urls_batch(files)

        file_responses = []
        for f in files:
            file_responses.append(FileResponse(
                id=f.id,
                url=urls.get(f.id, ""),
                original_filename=f.original_filename,
                mime_type=f.mime_type,
                size_bytes=f.size_bytes
            ))

        # Получаем аватар пользователя
        user_avatar = await self._get_avatar_url(application.user.avatar_file if application.user else None)

        # Проверяем голос пользователя
        user_vote = self.announce_repo.get_user_vote(application_id, self.user_id)

        return ApplicationResponse(
            id=application.id,
            announcement_id=application.announcement_id,
            user_id=application.user_id,
            content=application.content,
            links=application.links,
            status=application.status,
            likes_count=len(application.likes) if application.likes else 0,
            dislikes_count=len(application.dislikes) if application.dislikes else 0,
            user_vote=user_vote,
            created_at=application.created_at,
            updated_at=application.updated_at,
            files=file_responses,
            user=UserShortResponse(
                user_id=application.user.user_id if application.user else 0,
                name=application.user.name if application.user else None,
                lastname=application.user.lastname if application.user else None,
                username=application.user.username if application.user else None,
                avatar_url=user_avatar
            ),
            announcement_title=application.announcement.title if application.announcement else None
        )

    async def get_announcement_applications(
            self,
            announcement_id: UUID,
            skip: int = 0,
            limit: int = 100,
            status: Optional[str] = None
    ) -> ApplicationListResponse:
        """Получение заявок объявления"""
        announcement = self.announce_repo.get_announcement_by_id(announcement_id)
        if not announcement:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Announcement not found")

        # Проверяем доступ (только админы workspace)
        if not self.announce_repo.check_announcement_access(self.user_id, announcement_id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied")

        applications, total = self.announce_repo.get_applications_by_announcement(
            announcement_id=announcement_id,
            skip=skip,
            limit=limit,
            status=status
        )

        items = []
        for app in applications:
            files = self.announce_repo.get_application_files(app.id)
            urls = await self._get_file_urls_batch(files)

            file_responses = []
            for f in files:
                file_responses.append(FileResponse(
                    id=f.id,
                    url=urls.get(f.id, ""),
                    original_filename=f.original_filename,
                    mime_type=f.mime_type,
                    size_bytes=f.size_bytes
                ))

            user_avatar = await self._get_avatar_url(app.user.avatar_file if app.user else None)
            user_vote = self.announce_repo.get_user_vote(app.id, self.user_id)

            items.append(ApplicationResponse(
                id=app.id,
                announcement_id=app.announcement_id,
                user_id=app.user_id,
                content=app.content,
                links=app.links,
                status=app.status,
                likes_count=len(app.likes) if app.likes else 0,
                dislikes_count=len(app.dislikes) if app.dislikes else 0,
                user_vote=user_vote,
                created_at=app.created_at,
                updated_at=app.updated_at,
                files=file_responses,
                user=UserShortResponse(
                    user_id=app.user.user_id if app.user else 0,
                    name=app.user.name if app.user else None,
                    lastname=app.user.lastname if app.user else None,
                    username=app.user.username if app.user else None,
                    avatar_url=user_avatar
                ),
                announcement_title=None
            ))

        return ApplicationListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def get_my_applications(
            self,
            skip: int = 0,
            limit: int = 100
    ) -> ApplicationListResponse:
        """Получение моих заявок"""
        applications, total = self.announce_repo.get_applications_by_user(
            user_id=self.user_id,
            skip=skip,
            limit=limit
        )

        items = []
        for app in applications:
            files = self.announce_repo.get_application_files(app.id)
            urls = await self._get_file_urls_batch(files)

            file_responses = []
            for f in files:
                file_responses.append(FileResponse(
                    id=f.id,
                    url=urls.get(f.id, ""),
                    original_filename=f.original_filename,
                    mime_type=f.mime_type,
                    size_bytes=f.size_bytes
                ))

            user_avatar = await self._get_avatar_url(app.user.avatar_file if app.user else None)
            user_vote = self.announce_repo.get_user_vote(app.id, self.user_id)

            items.append(ApplicationResponse(
                id=app.id,
                announcement_id=app.announcement_id,
                user_id=app.user_id,
                content=app.content,
                links=app.links,
                status=app.status,
                likes_count=len(app.likes) if app.likes else 0,
                dislikes_count=len(app.dislikes) if app.dislikes else 0,
                user_vote=user_vote,
                created_at=app.created_at,
                updated_at=app.updated_at,
                files=file_responses,
                user=UserShortResponse(
                    user_id=app.user.user_id if app.user else 0,
                    name=app.user.name if app.user else None,
                    lastname=app.user.lastname if app.user else None,
                    username=app.user.username if app.user else None,
                    avatar_url=user_avatar
                ),
                announcement_title=app.announcement.title if app.announcement else None
            ))

        return ApplicationListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def update_application(
            self,
            application_id: UUID,
            data: ApplicationUpdate
    ) -> ApplicationResponse:
        """Обновление заявки (только владелец)"""
        application = self.announce_repo.get_application_by_id(application_id)
        if not application:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Application not found")

        if not self.announce_repo.is_application_owner(self.user_id, application_id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only owner can update application")

        if application.status != ApplicationStatus.PENDING.value:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST,
                                detail="Can only update pending applications")

        update_dict = data.model_dump(exclude_unset=True, exclude={'file_ids'})
        if update_dict:
            self.announce_repo.update_application(application_id, **update_dict)

        # Обновляем файлы
        if data.file_ids is not None:
            valid_file_ids = await self._validate_files(data.file_ids, GlobalFileType.APPLICATION_FILE)
            self.file_repo.detach_files_from_application(application_id)
            if valid_file_ids:
                self.file_repo.attach_files_to_application(application_id, valid_file_ids)

        return await self.get_application(application_id)

    async def delete_application(self, application_id: UUID) -> bool:
        """Удаление заявки (только владелец)"""
        application = self.announce_repo.get_application_by_id(application_id)
        if not application:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Application not found")

        if not self.announce_repo.is_application_owner(self.user_id, application_id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only owner can delete application")

        # Отвязываем файлы
        self.file_repo.detach_files_from_application(application_id)

        return self.announce_repo.delete_application(application_id)

    async def update_application_status(
            self,
            application_id: UUID,
            status: str
    ) -> ApplicationResponse:
        """Обновление статуса заявки (только админы)"""
        application = self.announce_repo.get_application_by_id(application_id, load_relations=True)
        if not application:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Application not found")

        # Проверяем права админа
        if not self.announce_repo.check_announcement_access(self.user_id, application.announcement_id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied")

        self.announce_repo.update_application(application_id, status=status)

        # Уведомляем владельца заявки
        await self._notify_application_status_changed(application, status)

        return await self.get_application(application_id)

    async def vote_application(
            self,
            application_id: UUID,
            vote_type: str
    ) -> ApplicationResponse:
        """Голосование за заявку"""
        # Проверяем возможность голосования
        if not self.announce_repo.can_vote_on_application(self.user_id, application_id):
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Cannot vote on this application")

        # Получаем имя пользователя
        profile = self.project_repo.user.get_profile_by_user_id(self.user_id)
        user_name = profile.username if profile else str(self.user_id)

        if vote_type == "like" or vote_type == "dislike":
            self.announce_repo.add_vote(application_id, self.user_id, user_name, vote_type)
        elif vote_type == "remove":
            self.announce_repo.remove_vote(application_id, self.user_id)
        else:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid vote type")

        return await self.get_application(application_id)

    # ============ Notification Methods ============

    async def _notify_announcement_created(self, announcement: Announcement, workspace_id: UUID):
        """Уведомление о создании объявления"""
        try:
            participants = self.announce_repo.get_workspace_participants(workspace_id)
            notify_ids = [p for p in participants if p != self.user_id]

            ws_message = {
                "event": "announcement_created",
                "data": {
                    "announcement_id": str(announcement.id),
                    "title": announcement.title,
                    "workspace_id": str(workspace_id),
                    "created_by": self.user_id,
                    "created_at": announcement.created_at.isoformat()
                }
            }
            await connection_manager.send_to_chat(notify_ids, ws_message)
        except Exception as e:
            print(f"Failed to send announcement notification: {e}")

    async def _notify_application_created(self, application: Application, announcement: Announcement):
        """Уведомление о создании заявки"""
        try:
            # Уведомляем создателя объявления и админов
            admins = self.announce_repo.get_workspace_admins(announcement.workspace_id)
            notify_ids = list(set(admins + [announcement.created_by]))
            notify_ids = [a for a in notify_ids if a != self.user_id]

            ws_message = {
                "event": "application_created",
                "data": {
                    "application_id": str(application.id),
                    "announcement_id": str(announcement.id),
                    "announcement_title": announcement.title,
                    "user_id": self.user_id,
                    "created_at": application.created_at.isoformat()
                }
            }
            await connection_manager.send_to_chat(notify_ids, ws_message)
        except Exception as e:
            print(f"Failed to send application notification: {e}")

    async def _notify_application_status_changed(self, application: Application, new_status: str):
        """Уведомление об изменении статуса заявки"""
        try:
            ws_message = {
                "event": "application_status_changed",
                "data": {
                    "application_id": str(application.id),
                    "announcement_id": str(application.announcement_id),
                    "new_status": new_status,
                    "updated_by": self.user_id,
                    "updated_at": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_user(application.user_id, ws_message)
        except Exception as e:
            print(f"Failed to send status change notification: {e}")