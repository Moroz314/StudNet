from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
from ...database.core import get_db
from ...database.models import *
from ...database.repositories.project.tasks import TaskRepository
from ...database.repositories.project.core import ProjectRepository
from ...database.repositories.files import FileRepository
from ...files.service import FileService
from ...files.schemas import FileType as GlobalFileType
from ..validation import require_project_access, require_project_admin, require_workspace_access
from .schemas import *
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime, UTC
from ...users.auth.service.utils import verify_token


def _enum_value(value):
    if value is None:
        return value
    return value.value if hasattr(value, 'value') else value


def get_task_service(
        db: Session = Depends(get_db),
        user_id: int = Depends(verify_token)
):
    task_repo = TaskRepository(session=db)
    project_repo = ProjectRepository(session=db)
    file_repo = FileRepository(session=db)
    file_service = FileService(session=db)

    return TaskService(
        task_repo=task_repo,
        project_repo=project_repo,
        file_repo=file_repo,
        file_service=file_service,
        user_id=user_id
    )


class TaskService:
    def __init__(
            self,
            task_repo: TaskRepository,
            project_repo: ProjectRepository,
            file_repo: FileRepository,
            file_service: FileService,
            user_id: int
    ):
        self.task_repo = task_repo
        self.project_repo = project_repo
        self.file_repo = file_repo
        self.file_service = file_service
        self.user_id = user_id

    async def _get_file_with_url(self, file_metadata, expires_in: int = 3600):
        """Получение файла с presigned URL через FileService"""
        try:
            download_url = await self.file_service.get_file_url(
                file_id=file_metadata.id,
                user_id=self.user_id,
                expires_in=expires_in
            )

            return FileMetadataBase(
                id=file_metadata.id,
                original_filename=file_metadata.original_filename,
                mime_type=file_metadata.mime_type,
                size_bytes=file_metadata.size_bytes,
                download_url=download_url
            )
        except Exception:
            # Если не удалось получить URL, возвращаем без него
            return FileMetadataBase(
                id=file_metadata.id,
                original_filename=file_metadata.original_filename,
                mime_type=file_metadata.mime_type,
                size_bytes=file_metadata.size_bytes,
                download_url=None
            )

    async def _enrich_comment_with_files(self, comment: TaskComment) -> dict:
        """Обогащает комментарий данными о файлах с URL"""
        comment_dict = {c.key: getattr(comment, c.key) for c in comment.__table__.columns}

        attachments = []
        for attachment in comment.attachments:
            if attachment.file:
                file_with_url = await self._get_file_with_url(attachment.file)
                attachments.append(file_with_url)

        comment_dict['attachments'] = attachments
        return comment_dict

    async def _validate_files_for_workspace(
            self,
            workspace_id: UUID,
            file_ids: List[UUID]
    ) -> List[UUID]:
        """
        Валидация файлов для workspace.
        Проверяет что файлы существуют, принадлежат workspace и загружены пользователем.
        """
        if not file_ids:
            return []

        # Получаем файлы через FileService
        files_dict = await self.file_service.get_file_urls_batch(
            file_ids=file_ids,
            user_id=self.user_id,
            expires_in=60  # Небольшой expiry для валидации
        )

        # Проверяем, что все файлы найдены
        missing_ids = set(file_ids) - set(files_dict.keys())
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Some files are invalid",
                    "invalid_file_ids": [str(fid) for fid in missing_ids],
                    "reason": "Files do not exist or were not uploaded by you"
                }
            )

        return list(files_dict.keys())

    async def create_task(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_data: TaskCreate,
            user_id: int
    ) -> TaskResponse:
        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            task = self.task_repo.create_task(
                workspace_id=workspace_id,
                created_by=user_id,
                title=task_data.title,
                description=task_data.description,
                task_type=task_data.task_type.value,
                priority=task_data.priority.value,
                deadline=task_data.deadline,
                estimated_hours=task_data.estimated_hours,
                assignees=task_data.assignees
            )

            return await self.get_task_by_id(project_id, workspace_id, task.id, user_id)

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create task: {str(e)}"
            )

    async def get_task_by_id(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_id: UUID,
            user_id: int
    ) -> TaskResponse:
        task = self.task_repo.get_task_by_id(task_id, include_relations=True)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Проверяем, что задача принадлежит указанному workspace
        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        # Конвертируем task в response с обработкой комментариев
        task_dict = {c.key: getattr(task, c.key) for c in task.__table__.columns}

        # Обрабатываем комментарии с файлами
        comments_with_files = []
        for comment in task.comments:
            comment_dict = await self._enrich_comment_with_files(comment)
            comments_with_files.append(TaskCommentResponse(**comment_dict))

        task_dict['comments'] = comments_with_files
        return TaskResponse(**task_dict)

    async def get_workspace_tasks(
            self,
            project_id: UUID,
            workspace_id: UUID,
            user_id: int,
            filters: Optional[TaskFilter] = None
    ) -> List[TaskListResponse]:
        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            # Применяем фильтры
            if filters:
                tasks = self.task_repo.search_tasks(
                    workspace_id=workspace_id,
                    search_query=filters.search,
                    task_type=filters.task_type.value if filters.task_type else None,
                    status=filters.status.value if filters.status else None,
                    priority=filters.priority.value if filters.priority else None,
                    has_deadline=filters.has_deadline,
                    deadline_before=filters.deadline_before,
                    deadline_after=filters.deadline_after,
                    assignee_id=filters.assignee_id,
                    limit=filters.limit or 100,
                    offset=filters.offset or 0
                )
            else:
                tasks = self.task_repo.get_tasks_by_workspace(
                    workspace_id=workspace_id,
                    limit=100,
                    offset=0
                )

            return [TaskListResponse.model_validate(task) for task in tasks]

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get tasks: {str(e)}"
            )

    async def update_task(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_id: UUID,
            update_data: TaskUpdate,
            user_id: int
    ) -> TaskResponse:
        task = self.task_repo.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Проверяем, что задача принадлежит указанному workspace
        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            update_dict = update_data.model_dump(mode='json', exclude_unset=True)

            # Конвертируем enum значения в строки
            if 'task_type' in update_dict and update_dict['task_type']:
                update_dict['task_type'] = _enum_value(update_dict['task_type'])
            if 'priority' in update_dict and update_dict['priority']:
                update_dict['priority'] = _enum_value(update_dict['priority'])
            if 'status' in update_dict and update_dict['status']:
                update_dict['status'] = _enum_value(update_dict['status'])

            updated_task = self.task_repo.update_task(task_id, **update_dict)

            if not updated_task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )

            return await self.get_task_by_id(project_id, workspace_id, task_id, user_id)

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update task: {str(e)}"
            )

    async def delete_task(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_id: UUID,
            user_id: int
    ) -> bool:
        task = self.task_repo.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Проверяем, что задача принадлежит указанному workspace
        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            success = self.task_repo.delete_task(task_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )

            return True

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete task: {str(e)}"
            )

    async def add_task_comment(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_id: UUID,
            comment_data: TaskCommentCreate,
            user_id: int
    ) -> TaskCommentResponse:
        """Добавление комментария к задаче с файлами через FileRepository"""
        # Получаем задачу
        task = self.task_repo.get_task_by_id(task_id, include_relations=False)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Проверяем, что задача принадлежит указанному workspace
        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            # Валидируем файлы если они есть
            if comment_data.file_ids:
                await self._validate_files_for_workspace(workspace_id, comment_data.file_ids)

            # Создаем комментарий
            comment = self.task_repo.add_task_comment(
                task_id=task_id,
                user_id=user_id,
                content=comment_data.content,
            )

            # Прикрепляем файлы через FileRepository
            if comment_data.file_ids:
                for file_id in comment_data.file_ids:
                    self.file_repo.attach_file_to_task_comment(
                        file_id=file_id,
                        comment_id=comment.id
                    )

            # Получаем полную информацию о комментарии с файлами
            full_comment = self.task_repo.get_full_comment(comment.id)

            if not full_comment:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve created comment"
                )

            comment_dict = await self._enrich_comment_with_files(full_comment)
            return TaskCommentResponse(**comment_dict)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add comment: {str(e)}"
            )

    async def get_task_comments(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_id: UUID,
            user_id: int,
            limit: int = 50,
            offset: int = 0
    ) -> List[TaskCommentResponse]:
        task = self.task_repo.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Проверяем, что задача принадлежит указанному workspace
        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            comments = self.task_repo.get_task_comments(task_id, limit, offset)

            result = []
            for comment in comments:
                comment_dict = await self._enrich_comment_with_files(comment)
                result.append(TaskCommentResponse(**comment_dict))

            return result

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get comments: {str(e)}"
            )

    async def add_attachments_to_comment(
            self,
            project_id: UUID,
            workspace_id: UUID,
            comment_id: int,
            file_ids: List[UUID],
            user_id: int
    ) -> TaskCommentResponse:
        """Добавление файлов к существующему комментарию"""
        # Проверяем существование комментария и права
        result = self.task_repo.get_comment_with_task(comment_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )

        comment, task = result

        # Проверяем, что задача принадлежит указанному workspace
        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        # Проверяем, что пользователь является автором комментария
        if not self.task_repo.check_comment_ownership(comment_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете изменять только свои комментарии."
            )

        try:
            # Валидируем файлы
            await self._validate_files_for_workspace(workspace_id, file_ids)

            # Прикрепляем файлы через FileRepository
            for file_id in file_ids:
                self.file_repo.attach_file_to_task_comment(
                    file_id=file_id,
                    comment_id=comment_id
                )

            # Получаем обновленный комментарий
            updated_comment = self.task_repo.get_full_comment(comment_id)

            if not updated_comment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Comment not found"
                )

            comment_dict = await self._enrich_comment_with_files(updated_comment)
            return TaskCommentResponse(**comment_dict)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add attachments: {str(e)}"
            )

    async def remove_attachment_from_comment(
            self,
            project_id: UUID,
            workspace_id: UUID,
            comment_id: int,
            file_id: UUID,
            user_id: int
    ) -> bool:
        """Удаление файла из комментария"""
        # Проверяем существование комментария
        result = self.task_repo.get_comment_with_task(comment_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )

        comment, task = result

        # Проверяем, что задача принадлежит указанному workspace
        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        # Проверяем права
        is_owner = self.task_repo.check_comment_ownership(comment_id, user_id)

        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете удалять вложения только из своих комментариев."
            )

        try:
            success = self.file_repo.detach_file_from_task_comment(comment_id, file_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Attachment not found"
                )

            return True

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to remove attachment: {str(e)}"
            )

    async def update_task_comment(
            self,
            project_id: UUID,
            workspace_id: UUID,
            comment_id: int,
            update_data: TaskCommentUpdate,
            user_id: int
    ) -> TaskCommentResponse:
        """Обновление комментария задачи"""
        # Проверяем существование комментария
        comment = self.task_repo.get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )

        # Получаем задачу для проверки workspace
        task = self.task_repo.get_task_by_id(comment.task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Проверяем, что задача принадлежит указанному workspace
        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        # Проверяем права на обновление
        if not self.task_repo.check_comment_ownership(comment_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете редактировать только свои комментарии."
            )

        try:
            updated_comment = self.task_repo.update_task_comment(
                comment_id=comment_id,
                content=update_data.content
            )

            if not updated_comment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Comment not found"
                )

            # Получаем полный комментарий с файлами
            full_comment = self.task_repo.get_full_comment(comment_id)
            comment_dict = await self._enrich_comment_with_files(full_comment)
            return TaskCommentResponse(**comment_dict)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update comment: {str(e)}"
            )

    async def delete_task_comment(
            self,
            project_id: UUID,
            workspace_id: UUID,
            comment_id: int,
            user_id: int
    ) -> bool:
        """Удаление комментария задачи"""
        # Проверяем существование комментария
        result = self.task_repo.get_comment_with_task(comment_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )

        comment, task = result

        # Проверяем, что задача принадлежит указанному workspace
        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        # Проверяем доступ к рабочему пространству
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        # Проверяем права
        is_owner = self.task_repo.check_comment_ownership(comment_id, user_id)

        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете удалять только свои комментарии."
            )

        try:
            success = self.task_repo.delete_task_comment(comment_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Comment not found"
                )

            return True

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete comment: {str(e)}"
            )

    async def get_workspace_statistics(
            self,
            project_id: UUID,
            workspace_id: UUID,
            user_id: int,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> TaskStatisticResponse:
        """Получение статистики рабочего пространства"""
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            stats = self.task_repo.get_workspace_statistics(workspace_id, start_date, end_date)
            return TaskStatisticResponse(**stats)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get statistics: {str(e)}"
            )

    async def get_statistics_history(
            self,
            project_id: UUID,
            workspace_id: UUID,
            user_id: int,
            days: int = 30
    ) -> List[TaskStatisticHistoryResponse]:
        """Получение истории статистики"""
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )
        try:
            history = self.task_repo.get_task_statistics_history(workspace_id, days)
            return [TaskStatisticHistoryResponse.model_validate(stat) for stat in history]

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get statistics history: {str(e)}"
            )

    async def get_upcoming_deadlines(
            self,
            project_id: UUID,
            workspace_id: UUID,
            user_id: int,
            days_ahead: int = 7
    ) -> List[UpcomingDeadlinesResponse]:
        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            tasks = self.task_repo.get_upcoming_deadlines(workspace_id, days_ahead)

            result = []
            for task in tasks:
                days_until = (task.deadline - datetime.now(UTC)).days
                result.append(UpcomingDeadlinesResponse(
                    id=task.id,
                    title=task.title,
                    deadline=task.deadline,
                    priority=TaskPriority(task.priority),
                    status=TaskStatus(task.status),
                    days_until_deadline=days_until
                ))

            return result

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get upcoming deadlines: {str(e)}"
            )

    # ========== Методы для работы с назначенными пользователями ==========

    async def get_task_assignees(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_id: UUID,
            user_id: int
    ) -> List[int]:
        """Получить список назначенных пользователей"""
        task = self.task_repo.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        return self.task_repo.get_task_assignees(task)

    async def add_assignees_to_task(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_id: UUID,
            assignees_data: TaskAssigneesUpdate,
            user_id: int
    ) -> TaskResponse:
        """Добавление пользователей в список назначенных"""
        task = self.task_repo.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            success = self.task_repo.add_assignee_to_task(task_id, assignees_data.assignees)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to add assignees to task"
                )

            return await self.get_task_by_id(project_id, workspace_id, task_id, user_id)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add assignees: {str(e)}"
            )

    async def remove_assignee_from_task(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_id: UUID,
            assignee_id: int,
            user_id: int
    ) -> TaskResponse:
        """Удаление пользователя из списка назначенных"""
        task = self.task_repo.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            success = self.task_repo.remove_assignee_from_task(task_id, assignee_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assignee not found in task"
                )

            return await self.get_task_by_id(project_id, workspace_id, task_id, user_id)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to remove assignee: {str(e)}"
            )

    async def set_task_assignees(
            self,
            project_id: UUID,
            workspace_id: UUID,
            task_id: UUID,
            assignees_data: TaskAssigneesUpdate,
            user_id: int
    ) -> TaskResponse:
        """Установить список назначенных пользователей (полная замена)"""
        task = self.task_repo.get_task_by_id(task_id, include_relations=True)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        if task.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task does not belong to this workspace"
            )

        require_workspace_access(
            self.project_repo,
            workspace_id,
            project_id,
            user_id
        )

        try:
            success = self.task_repo.set_task_assignees(task_id, assignees_data.assignees)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to set task assignees"
                )

            return await self.get_task_by_id(project_id, workspace_id, task_id, user_id)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to set assignees: {str(e)}"
            )