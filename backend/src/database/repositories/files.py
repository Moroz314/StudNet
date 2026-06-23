from src.database.repositories.base_repository import BaseRepository
from src.database.models import *
from sqlalchemy import and_, or_, func, desc, update
from sqlalchemy.orm import Session, joinedload
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime


class FileRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    # ========== Базовые операции с FileMetadata ==========

    def create_file_metadata(
            self,
            s3_key: str,
            original_filename: str,
            file_type: str,
            mime_type: str,
            size_bytes: int,
            uploaded_by: Optional[int] = None,
    ) -> FileMetadata:
        """Создание метаданных файла"""
        file_metadata = FileMetadata(
            s3_key=s3_key,
            original_filename=original_filename,
            file_type=file_type,
            mime_type=mime_type,
            size_bytes=size_bytes,
            uploaded_by=uploaded_by,
        )
        self.session.add(file_metadata)
        self.session.commit()
        self.session.refresh(file_metadata)
        return file_metadata

    def get_file_by_id(self, file_id: uuid.UUID) -> Optional[FileMetadata]:
        """Получение файла по ID"""
        return self.session.query(FileMetadata).filter(
            FileMetadata.id == file_id
        ).first()

    def get_files_by_ids(self, file_ids: List[uuid.UUID]) -> Dict[uuid.UUID, FileMetadata]:
        """Получение нескольких файлов по списку ID"""
        if not file_ids:
            return {}
        files = self.session.query(FileMetadata).filter(
            FileMetadata.id.in_(file_ids)
        ).all()
        return {file.id: file for file in files}

    def get_files_by_ids_and_type(
            self,
            file_ids: List[uuid.UUID],
            file_type: str,
            user_id: Optional[int] = None
    ) -> Dict[uuid.UUID, FileMetadata]:
        """
        Получение файлов по списку ID и типу.
        Если user_id указан, дополнительно проверяет принадлежность пользователю.
        Возвращает словарь {file_id: FileMetadata} только для валидных файлов.
        """
        if not file_ids:
            return {}

        query = self.session.query(FileMetadata).filter(
            FileMetadata.id.in_(file_ids),
            FileMetadata.file_type == file_type
        )

        if user_id is not None:
            query = query.filter(FileMetadata.uploaded_by == user_id)

        files = query.all()
        return {file.id: file for file in files}

    def delete_file_metadata(self, file_id: uuid.UUID) -> bool:
        """Удаление метаданных файла (связи удалятся каскадно)"""
        file_metadata = self.get_file_by_id(file_id)
        if not file_metadata:
            return False
        self.session.delete(file_metadata)
        self.session.commit()
        return True

    def update_file_metadata(
            self,
            file_id: uuid.UUID,
            **kwargs
    ) -> Optional[FileMetadata]:
        """Обновление метаданных файла"""
        file_metadata = self.get_file_by_id(file_id)
        if not file_metadata:
            return None

        for key, value in kwargs.items():
            if hasattr(file_metadata, key) and value is not None:
                setattr(file_metadata, key, value)

        self.session.commit()
        self.session.refresh(file_metadata)
        return file_metadata

    # ========== Работа с файлами проектов (ProjectFile) ==========

    def get_project_avatar(self, project_id: uuid.UUID) -> Optional[FileMetadata]:
        """
        Получение аватарки проекта
        """
        return self.session.query(FileMetadata).join(
            Project, Project.avatar_file_id == FileMetadata.id
        ).filter(
            Project.id == project_id,
            FileMetadata.file_type == FileType.PROJECT_AVATAR.value
        ).first()

    def attach_file_to_project(
            self,
            file_id: uuid.UUID,
            project_id: uuid.UUID,
            uploaded_by: int,
            workspace_id: Optional[uuid.UUID],
            description: Optional[str] = None,
            tags: Optional[List[str]] = None
    ) -> ProjectFile:
        """Привязка файла к проекту"""
        existing = self.session.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.file_id == file_id
        ).first()

        if existing:
            return existing

        project_file = ProjectFile(
            project_id=project_id,
            file_id=file_id,
            workspace_id=workspace_id,
            uploaded_by=uploaded_by,
            description=description,
            tags=tags
        )
        self.session.add(project_file)
        self.session.commit()
        self.session.refresh(project_file)
        return project_file

    def get_project_file_by_id(self, file_id: uuid.UUID, project_id: uuid.UUID) -> Optional[ProjectFile]:
        """Получение связи файла с проектом по ID файла и проекта"""
        return self.session.query(ProjectFile).filter(
            ProjectFile.file_id == file_id,
            ProjectFile.project_id == project_id
        ).first()

    def get_project_files(
            self,
            project_id: uuid.UUID,
            workspace_id: Optional[uuid.UUID] = None,
            limit: int = 100
    ) -> List[FileMetadata]:
        """Получение файлов проекта"""
        query = self.session.query(FileMetadata).join(
            ProjectFile, ProjectFile.file_id == FileMetadata.id
        ).filter(
            ProjectFile.project_id == project_id
        )
        if workspace_id:
            query = query.filter(ProjectFile.workspace_id == workspace_id)
        return query.order_by(desc(ProjectFile.uploaded_at)).limit(limit).all()

    def detach_file_from_project(
            self,
            file_id: uuid.UUID,
            project_id: uuid.UUID
    ) -> bool:
        """Отвязка файла от проекта"""
        result = self.session.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.file_id == file_id
        ).delete()
        self.session.commit()
        return result > 0

    # ========== Работа с файлами постов проектов (ProjectPostFile) ==========

    def attach_file_to_project_post(
            self,
            file_id: uuid.UUID,
            post_id: uuid.UUID,
            order: int = 0
    ) -> 'ProjectPostFile':
        """Привязка файла к посту проекта"""
        existing = self.session.query(ProjectPostFile).filter(
            ProjectPostFile.post_id == post_id,
            ProjectPostFile.file_id == file_id
        ).first()

        if existing:
            return existing

        post_file = ProjectPostFile(
            post_id=post_id,
            file_id=file_id,
            order=order
        )
        self.session.add(post_file)
        self.session.commit()
        self.session.refresh(post_file)
        return post_file

    def get_project_post_files(
            self,
            post_id: uuid.UUID
    ) -> List[FileMetadata]:
        """Получение файлов, прикреплённых к посту проекта"""
        return self.session.query(FileMetadata).join(
            ProjectPostFile, ProjectPostFile.file_id == FileMetadata.id
        ).filter(
            ProjectPostFile.post_id == post_id
        ).order_by(ProjectPostFile.order).all()

    def detach_file_from_project_post(
            self,
            file_id: uuid.UUID,
            post_id: uuid.UUID
    ) -> bool:
        """Отвязка файла от поста проекта"""
        result = self.session.query(ProjectPostFile).filter(
            ProjectPostFile.post_id == post_id,
            ProjectPostFile.file_id == file_id
        ).delete()
        self.session.commit()
        return result > 0

    def update_post_file_order(
            self,
            post_id: uuid.UUID,
            file_orders: Dict[uuid.UUID, int]
    ) -> bool:
        """Обновление порядка файлов в посте"""
        for file_id, order in file_orders.items():
            self.session.query(ProjectPostFile).filter(
                ProjectPostFile.post_id == post_id,
                ProjectPostFile.file_id == file_id
            ).update({"order": order})
        self.session.commit()
        return True

    # ========== Работа с вложениями сообщений (MessageAttachment) ==========

    def attach_file_to_message(
            self,
            file_id: uuid.UUID,
            message_id: int
    ) -> MessageAttachment:
        """Привязка файла к сообщению"""
        existing = self.session.query(MessageAttachment).filter(
            MessageAttachment.message_id == message_id,
            MessageAttachment.file_id == file_id
        ).first()

        if existing:
            return existing

        message_attachment = MessageAttachment(
            message_id=message_id,
            file_id=file_id
        )
        self.session.add(message_attachment)
        self.session.commit()
        self.session.refresh(message_attachment)
        return message_attachment

    def get_message_attachments(
            self,
            message_id: int
    ) -> List[FileMetadata]:
        """Получение файлов, прикреплённых к сообщению"""
        return self.session.query(FileMetadata).join(
            MessageAttachment, MessageAttachment.file_id == FileMetadata.id
        ).filter(
            MessageAttachment.message_id == message_id
        ).order_by(MessageAttachment.attached_at).all()

    def detach_file_from_message(
            self,
            file_id: uuid.UUID,
            message_id: int
    ) -> bool:
        """Отвязка файла от сообщения"""
        result = self.session.query(MessageAttachment).filter(
            MessageAttachment.message_id == message_id,
            MessageAttachment.file_id == file_id
        ).delete()
        self.session.commit()
        return result > 0

    def get_messages_attachments(
            self,
            message_ids: List[int]
    ) -> Dict[int, List[FileMetadata]]:
        """Получение файлов для нескольких сообщений"""
        if not message_ids:
            return {}

        results = self.session.query(MessageAttachment, FileMetadata).join(
            FileMetadata, MessageAttachment.file_id == FileMetadata.id
        ).filter(
            MessageAttachment.message_id.in_(message_ids)
        ).order_by(MessageAttachment.attached_at).all()

        attachments_by_message = {}
        for attachment, file in results:
            if attachment.message_id not in attachments_by_message:
                attachments_by_message[attachment.message_id] = []
            attachments_by_message[attachment.message_id].append(file)

        return attachments_by_message

    # ========== Работа с вложениями комментариев задач (TaskAttachment) ==========

    def attach_file_to_task_comment(
            self,
            file_id: uuid.UUID,
            comment_id: int
    ) -> TaskAttachment:
        """Привязка файла к комментарию задачи"""
        existing = self.session.query(TaskAttachment).filter(
            TaskAttachment.comment_id == comment_id,
            TaskAttachment.file_id == file_id
        ).first()

        if existing:
            return existing

        task_attachment = TaskAttachment(
            comment_id=comment_id,
            file_id=file_id
        )
        self.session.add(task_attachment)
        self.session.commit()
        self.session.refresh(task_attachment)
        return task_attachment

    def get_task_comment_attachments(
            self,
            comment_id: int
    ) -> List[FileMetadata]:
        """Получение файлов, прикреплённых к комментарию задачи"""
        return self.session.query(FileMetadata).join(
            TaskAttachment, TaskAttachment.file_id == FileMetadata.id
        ).filter(
            TaskAttachment.comment_id == comment_id
        ).order_by(TaskAttachment.attached_at).all()

    def detach_file_from_task_comment(
            self,
            file_id: uuid.UUID,
            comment_id: int
    ) -> bool:
        """Отвязка файла от комментария задачи"""
        result = self.session.query(TaskAttachment).filter(
            TaskAttachment.comment_id == comment_id,
            TaskAttachment.file_id == file_id
        ).delete()
        self.session.commit()
        return result > 0

    # ========== Работа с файлами объявлений (AnnouncementFile) ==========

    def attach_files_to_announcement(
            self,
            announcement_id: uuid.UUID,
            file_ids: List[uuid.UUID]
    ) -> None:
        """Привязка файлов к объявлению"""
        for file_id in file_ids:
            existing = self.session.query(AnnouncementFile).filter(
                AnnouncementFile.announcement_id == announcement_id,
                AnnouncementFile.file_id == file_id
            ).first()
            if not existing:
                announcement_file = AnnouncementFile(
                    announcement_id=announcement_id,
                    file_id=file_id
                )
                self.session.add(announcement_file)
        self.session.commit()

    def get_announcement_files(
            self,
            announcement_id: uuid.UUID
    ) -> List[FileMetadata]:
        """Получение файлов, прикреплённых к объявлению"""
        return self.session.query(FileMetadata).join(
            AnnouncementFile, AnnouncementFile.file_id == FileMetadata.id
        ).filter(
            AnnouncementFile.announcement_id == announcement_id
        ).order_by(AnnouncementFile.attached_at).all()

    def detach_files_from_announcement(
            self,
            announcement_id: uuid.UUID
    ) -> None:
        """Отвязка всех файлов от объявления"""
        self.session.query(AnnouncementFile).filter(
            AnnouncementFile.announcement_id == announcement_id
        ).delete()
        self.session.commit()

    # ========== Работа с файлами заявок (ApplicationFile) ==========

    def attach_files_to_application(
            self,
            application_id: uuid.UUID,
            file_ids: List[uuid.UUID]
    ) -> None:
        """Привязка файлов к заявке"""
        for file_id in file_ids:
            existing = self.session.query(ApplicationFile).filter(
                ApplicationFile.application_id == application_id,
                ApplicationFile.file_id == file_id
            ).first()
            if not existing:
                application_file = ApplicationFile(
                    application_id=application_id,
                    file_id=file_id
                )
                self.session.add(application_file)
        self.session.commit()

    def get_application_files(
            self,
            application_id: uuid.UUID
    ) -> List[FileMetadata]:
        """Получение файлов, прикреплённых к заявке"""
        return self.session.query(FileMetadata).join(
            ApplicationFile, ApplicationFile.file_id == FileMetadata.id
        ).filter(
            ApplicationFile.application_id == application_id
        ).order_by(ApplicationFile.attached_at).all()


    # championships files
    def detach_files_from_application(
            self,
            application_id: uuid.UUID
    ) -> None:
        """Отвязка всех файлов от заявки"""
        self.session.query(ApplicationFile).filter(
            ApplicationFile.application_id == application_id
        ).delete()
        self.session.commit()

    # ========== Вспомогательные методы ==========

    def get_user_files(
            self,
            user_id: int,
            file_type: Optional[str] = None,
            limit: int = 100
    ) -> List[FileMetadata]:
        """Получение файлов пользователя"""
        query = self.session.query(FileMetadata).filter(
            FileMetadata.uploaded_by == user_id
        )
        if file_type:
            query = query.filter(FileMetadata.file_type == file_type)
        return query.order_by(desc(FileMetadata.uploaded_at)).limit(limit).all()

    def attach_files_to_championship(
            self,
            championship_id: uuid.UUID,
            file_ids: List[uuid.UUID]
    ) -> None:
        """Привязка файлов к чемпионату"""
        for file_id in file_ids:
            existing = self.session.query(ChampionshipFile).filter(
                ChampionshipFile.championship_id == championship_id,
                ChampionshipFile.file_id == file_id
            ).first()
            if not existing:
                championship_file = ChampionshipFile(
                    championship_id=championship_id,
                    file_id=file_id
                )
                self.session.add(championship_file)
        self.session.commit()

    def get_championship_files(
            self,
            championship_id: uuid.UUID
    ) -> List[FileMetadata]:
        """Получение файлов, прикреплённых к чемпионату"""
        return self.session.query(FileMetadata).join(
            ChampionshipFile, ChampionshipFile.file_id == FileMetadata.id
        ).filter(
            ChampionshipFile.championship_id == championship_id
        ).order_by(ChampionshipFile.attached_at).all()

    def detach_files_from_championship(
            self,
            championship_id: uuid.UUID,
            file_ids: Optional[List[uuid.UUID]] = None
    ) -> None:
        """Отвязка файлов от чемпионата"""
        query = self.session.query(ChampionshipFile).filter(
            ChampionshipFile.championship_id == championship_id
        )
        if file_ids:
            query = query.filter(ChampionshipFile.file_id.in_(file_ids))
        query.delete()
        self.session.commit()