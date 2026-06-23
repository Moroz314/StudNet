from src.database.repositories.base_repository import BaseRepository
from src.database.models import *
from sqlalchemy import and_, or_, update, exists, func, desc, case, text, Date as sqlDate
from sqlalchemy.orm import Session, joinedload, selectinload, aliased
import uuid
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, date, timedelta


class TaskRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    # ========== CRUD операции с задачами ==========

    def create_task(
            self,
            workspace_id: uuid.UUID,
            created_by: int,
            title: str,
            task_type: str,
            description: Optional[str] = None,
            priority: str = TaskPriority.MEDIUM.value,
            status: str = TaskStatus.TODO.value,
            deadline: Optional[datetime] = None,
            estimated_hours: Optional[int] = None,
            assignees: Optional[List[int]] = None
    ) -> Task:
        if task_type == TaskType.URGENT_TASK.value and not deadline:
            raise ValueError("Urgent tasks must have a deadline")

        if task_type == TaskType.IDEA.value:
            status = TaskStatus.IDEA.value

        task = Task(
            workspace_id=workspace_id,
            created_by=created_by,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            status=status,
            deadline=deadline,
            estimated_hours=estimated_hours,
            actual_hours=0,
            assignees=assignees or []
        )

        self.session.add(task)
        self.session.commit()

        # Обновляем статистику
        self._update_statistics(workspace_id)

        return task

    def get_task_by_id(self, task_id: uuid.UUID, include_relations: bool = False) -> Optional[Task]:
        """Получение задачи по ID"""
        query = self.session.query(Task)

        if include_relations:
            query = query.options(
                selectinload(Task.workspace),
                selectinload(Task.creator_profile),
                selectinload(Task.comments)
                .selectinload(TaskComment.user_profile),
                selectinload(Task.comments)
                .selectinload(TaskComment.attachments)
                .selectinload(TaskAttachment.file)
            )

        return query.filter(Task.id == task_id).first()

    def get_tasks_by_workspace(
            self,
            workspace_id: uuid.UUID,
            task_type: Optional[str] = None,
            status: Optional[str] = None,
            priority: Optional[str] = None,
            include_overdue: bool = False,
            limit: int = 100,
            offset: int = 0
    ) -> List[Task]:
        """Получение задач рабочего пространства"""
        query = self.session.query(Task).filter(
            Task.workspace_id == workspace_id
        )

        if task_type:
            query = query.filter(Task.task_type == task_type)

        if status:
            query = query.filter(Task.status == status)

        if priority:
            query = query.filter(Task.priority == priority)

        if include_overdue:
            now = datetime.now(UTC)
            query = query.filter(
                and_(
                    Task.deadline.isnot(None),
                    Task.deadline < now,
                    Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value])
                )
            )

        return query.order_by(
            case(
                (Task.priority == TaskPriority.URGENT.value, 1),
                (Task.priority == TaskPriority.HIGH.value, 2),
                (Task.priority == TaskPriority.MEDIUM.value, 3),
                else_=4
            ),
            desc(Task.created_at)
        ).limit(limit).offset(offset).all()

    def update_task(
            self,
            task_id: uuid.UUID,
            **kwargs
    ) -> Optional[Task]:
        """Обновление задачи"""
        task = self.get_task_by_id(task_id)
        if not task:
            return None

        # Проверка для срочных задач
        if 'task_type' in kwargs and kwargs['task_type'] == TaskType.URGENT_TASK.value:
            if 'deadline' not in kwargs or not kwargs['deadline']:
                if not task.deadline:
                    raise ValueError("Urgent tasks must have a deadline")

        # Обновление actual_hours с логикой
        if 'actual_hours' in kwargs and kwargs['actual_hours'] is not None:
            kwargs['actual_hours'] = max(0, kwargs['actual_hours'])

        # Если статус меняется на DONE и есть estimated_hours, но нет actual_hours
        if ('status' in kwargs and kwargs['status'] == TaskStatus.DONE.value and
                task.estimated_hours and not task.actual_hours):
            kwargs['actual_hours'] = task.estimated_hours

        if 'assignees' in kwargs and kwargs['assignees'] is not None:
            # Убираем дубликаты
            kwargs['assignees'] = list(set(kwargs['assignees']))

        for key, value in kwargs.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)

        self.session.commit()

        # Обновляем статистику
        self._update_statistics(task.workspace_id)

        return task

    def delete_task(self, task_id: uuid.UUID) -> bool:
        """Удаление задачи"""
        task = self.get_task_by_id(task_id)
        if not task:
            return False

        workspace_id = task.workspace_id

        self.session.delete(task)
        self.session.commit()

        # Обновляем статистику
        self._update_statistics(workspace_id)

        return True

    def check_user_can_comment_on_task(self, task_id: uuid.UUID, user_id: int) -> bool:
        """
        Проверка, может ли пользователь оставлять комментарии к задаче

        Правила:
        - Если assignees пуст или None - все могут комментировать
        - Если assignees не пуст - только пользователи из списка могут комментировать
        - Создатель задачи всегда может комментировать
        - Админы/владельцы проекта всегда могут комментировать
        """
        task = self.get_task_by_id(task_id)
        if not task:
            return False

        # Создатель задачи всегда может комментировать
        if task.created_by == user_id:
            return True

        # Если assignees пуст или None - все могут комментировать
        if not task.assignees or len(task.assignees) == 0:
            return True

        # Проверяем, есть ли пользователь в списке assignees
        return user_id in task.assignees

    def check_user_can_attach_files_to_task(self, task_id: uuid.UUID, user_id: int) -> bool:
        """
        Проверка, может ли пользователь прикреплять файлы к задаче

        Те же правила, что и для комментариев
        """
        return self.check_user_can_comment_on_task(task_id, user_id)

    def get_task_assignees(self, task: Task) -> List[int]:
        """Получить список пользователей, назначенных на задачу"""
        assignees = task.assignees
        return assignees or []

    def add_assignee_to_task(self, task_id: uuid.UUID, user_ids: List[int]) -> bool:
        """Добавить пользователей в список назначенных на задачу"""
        task = self.get_task_by_id(task_id)
        if not task:
            return False

        if task.assignees is None:
            task.assignees = []

        # Проверяем, есть ли уже такие пользователи
        existing_users = set(task.assignees)
        new_users = set(user_ids) - existing_users

        if not new_users:
            return False

        task.assignees = task.assignees + list(new_users)
        self.session.commit()

        return True

    def remove_assignee_from_task(self, task_id: uuid.UUID, user_id: int) -> bool:
        """Удалить пользователя из списка назначенных на задачу"""
        task = self.get_task_by_id(task_id)
        if not task:
            return False

        if task.assignees and user_id in task.assignees:
            task.assignees.remove(user_id)
            self.session.commit()
            return True

        return False

    def set_task_assignees(self, task_id: uuid.UUID, user_ids: List[int]) -> bool:
        """Установить список назначенных пользователей"""
        task = self.get_task_by_id(task_id)
        if not task:
            return False

        task.assignees = list(set(user_ids))  # Убираем дубликаты
        self.session.commit()
        return True

    # ========== Операции с комментариями ==========

    def get_comment_by_id(self, comment_id: int, include_relations: bool = False) -> Optional[TaskComment]:
        """Получение комментария по ID"""
        query = self.session.query(TaskComment)

        if include_relations:
            query = query.options(
                selectinload(TaskComment.user_profile),
                selectinload(TaskComment.attachments).selectinload(TaskAttachment.file)
            )

        return query.filter(TaskComment.id == comment_id).first()

    def get_full_comment(self, comment_id: int) -> Optional[TaskComment]:
        """
        Получение комментария со всеми связанными данными (без N+1)
        """
        return self.session.query(TaskComment).options(
            selectinload(TaskComment.user_profile),
            selectinload(TaskComment.attachments).selectinload(TaskAttachment.file)
        ).filter(
            TaskComment.id == comment_id
        ).first()

    def get_comment_with_task(self, comment_id: int) -> Optional[Tuple[TaskComment, Task]]:
        """Получение комментария вместе с задачей"""
        comment = self.get_full_comment(comment_id)
        if not comment:
            return None

        task = self.get_task_by_id(comment.task_id)
        return comment, task

    def check_comment_ownership(self, comment_id: int, user_id: int) -> bool:
        """Проверка, является ли пользователь автором комментария"""
        comment = self.session.query(TaskComment).filter(
            TaskComment.id == comment_id
        ).first()

        if not comment:
            return False

        return comment.user_id == user_id

    # ========== УПРОЩЁННЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С КОММЕНТАРИЯМИ ==========

    def add_task_comment(
            self,
            task_id: uuid.UUID,
            user_id: int,
            content: str,
    ) -> TaskComment:
        """
        Добавление комментария к задаче.
        Файлы теперь добавляются отдельно через FileRepository.
        """
        comment = TaskComment(
            task_id=task_id,
            user_id=user_id,
            content=content
        )

        self.session.add(comment)
        self.session.commit()

        # Обновляем статистику
        task = self.get_task_by_id(task_id)
        if task:
            self._update_statistics(task.workspace_id)

        return comment

    def get_task_comments(
            self,
            task_id: uuid.UUID,
            limit: int = 50,
            offset: int = 0
    ) -> List[TaskComment]:
        """Получение комментариев задачи с файлами"""
        return self.session.query(TaskComment).options(
            selectinload(TaskComment.user_profile),
            selectinload(TaskComment.attachments).selectinload(TaskAttachment.file)
        ).filter(
            TaskComment.task_id == task_id
        ).order_by(
            desc(TaskComment.created_at)
        ).limit(limit).offset(offset).all()

    def update_task_comment(
            self,
            comment_id: int,
            content: str
    ) -> Optional[TaskComment]:
        """Обновление комментария"""
        comment = self.get_comment_by_id(comment_id)
        if not comment:
            return None

        comment.content = content
        comment.is_edited = True

        self.session.commit()
        return comment

    def delete_task_comment(self, comment_id: int) -> bool:
        """Удаление комментария задачи"""
        comment = self.get_comment_by_id(comment_id)
        if not comment:
            return False

        task_id = comment.task_id

        self.session.delete(comment)
        self.session.commit()

        # Обновляем статистику
        task = self.get_task_by_id(task_id)
        if task:
            self._update_statistics(task.workspace_id)

        return True

    # ========== Статистика и поиск ==========

    def get_workspace_statistics(
            self,
            workspace_id: uuid.UUID,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Получение статистики по рабочему пространству"""
        # Базовый запрос
        base_query = self.session.query(Task).filter(
            Task.workspace_id == workspace_id
        )

        # Применяем фильтры по дате, если указаны
        if start_date or end_date:
            if start_date:
                base_query = base_query.filter(Task.created_at >= start_date)
            if end_date:
                base_query = base_query.filter(Task.created_at <= end_date)

        total_tasks = base_query.count()

        # Статистика по статусам
        status_counts = base_query.with_entities(
            Task.status,
            func.count(Task.id)
        ).group_by(Task.status).all()

        status_stats = {status: count for status, count in status_counts}

        # Статистика по типам
        type_counts = base_query.with_entities(
            Task.task_type,
            func.count(Task.id)
        ).group_by(Task.task_type).all()

        type_stats = {task_type: count for task_type, count in type_counts}

        # Статистика по приоритетам
        priority_counts = base_query.with_entities(
            Task.priority,
            func.count(Task.id)
        ).group_by(Task.priority).all()

        priority_stats = {priority: count for priority, count in priority_counts}

        # Срочные задачи
        now = datetime.now(UTC)
        urgent_tasks = base_query.filter(
            Task.task_type == TaskType.URGENT_TASK.value
        ).count()

        overdue_tasks = base_query.filter(
            and_(
                Task.deadline.isnot(None),
                Task.deadline < now,
                Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value])
            )
        ).count()

        overdue_urgent = base_query.filter(
            and_(
                Task.task_type == TaskType.URGENT_TASK.value,
                Task.deadline.isnot(None),
                Task.deadline < now,
                Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value])
            )
        ).count()

        # Метрики времени
        total_estimated = base_query.with_entities(
            func.coalesce(func.sum(Task.estimated_hours), 0)
        ).scalar() or 0

        total_actual = base_query.with_entities(
            func.coalesce(func.sum(Task.actual_hours), 0)
        ).scalar() or 0

        # Расчет completion rate
        completion_rate = 0
        if total_tasks > 0:
            done_count = status_stats.get(TaskStatus.DONE.value, 0)
            completion_rate = (done_count / total_tasks) * 100

        # Среднее время выполнения задач
        avg_completion_time = self.session.query(
            func.avg(
                func.extract('epoch', Task.updated_at - Task.created_at) / 3600
            )
        ).filter(
            and_(
                Task.workspace_id == workspace_id,
                Task.status == TaskStatus.DONE.value,
                Task.created_at.isnot(None),
                Task.updated_at.isnot(None)
            )
        ).scalar() or 0

        # Задачи созданные и завершенные сегодня
        today = date.today()
        tasks_created_today = self.session.query(Task).filter(
            and_(
                Task.workspace_id == workspace_id,
                func.date(Task.created_at) == today
            )
        ).count()

        tasks_completed_today = self.session.query(Task).filter(
            and_(
                Task.workspace_id == workspace_id,
                Task.status == TaskStatus.DONE.value,
                func.date(Task.updated_at) == today
            )
        ).count()

        return {
            "total_tasks": total_tasks,
            "status_distribution": status_stats,
            "type_distribution": type_stats,
            "priority_distribution": priority_stats,
            "urgent_tasks": urgent_tasks,
            "overdue_tasks": overdue_tasks,
            "overdue_urgent_tasks": overdue_urgent,
            "total_estimated_hours": total_estimated,
            "total_actual_hours": total_actual,
            "completion_rate": round(completion_rate, 2),
            "average_completion_time_hours": round(avg_completion_time, 2),
            "tasks_created_today": tasks_created_today,
            "tasks_completed_today": tasks_completed_today
        }

    def get_task_statistics_history(
            self,
            workspace_id: uuid.UUID,
            days: int = 30
    ) -> List[TaskStatistic]:
        """Получение истории статистики"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        return self.session.query(TaskStatistic).filter(
            and_(
                TaskStatistic.workspace_id == workspace_id,
                TaskStatistic.date >= start_date,
                TaskStatistic.date <= end_date
            )
        ).order_by(TaskStatistic.date).all()

    def _update_statistics(self, workspace_id: uuid.UUID):
        """Обновление статистики для рабочего пространства"""
        today = date.today()

        # Получаем или создаем запись статистики на сегодня
        stat = self.session.query(TaskStatistic).filter(
            and_(
                TaskStatistic.workspace_id == workspace_id,
                TaskStatistic.date == today
            )
        ).first()

        if not stat:
            stat = TaskStatistic(
                workspace_id=workspace_id,
                date=today
            )
            self.session.add(stat)

        # Получаем текущие данные
        tasks = self.session.query(Task).filter(
            Task.workspace_id == workspace_id
        ).all()

        # Задачи созданные сегодня
        tasks_created_today = sum(
            1 for t in tasks
            if t.created_at and t.created_at.date() == today
        )

        # Задачи завершенные сегодня
        tasks_completed_today = sum(
            1 for t in tasks
            if t.status == TaskStatus.DONE.value and
            t.updated_at and
            t.updated_at.date() == today
        )

        # Обновляем счетчики
        stat.total_tasks = len(tasks)
        stat.idea_count = sum(1 for t in tasks if t.status == TaskStatus.IDEA.value)
        stat.todo_count = sum(1 for t in tasks if t.status == TaskStatus.TODO.value)
        stat.in_progress_count = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS.value)
        stat.review_count = sum(1 for t in tasks if t.status == TaskStatus.REVIEW.value)
        stat.done_count = sum(1 for t in tasks if t.status == TaskStatus.DONE.value)
        stat.cancelled_count = sum(1 for t in tasks if t.status == TaskStatus.CANCELLED.value)

        # Срочные задачи
        now = datetime.now(UTC)
        urgent_tasks = [t for t in tasks if t.task_type == TaskType.URGENT_TASK.value]
        stat.urgent_total = len(urgent_tasks)
        stat.urgent_overdue = sum(1 for t in urgent_tasks
                                  if t.deadline and t.deadline < now and
                                  t.status not in [TaskStatus.DONE.value, TaskStatus.CANCELLED.value])

        # Метрики времени
        stat.total_estimated_hours = sum(t.estimated_hours or 0 for t in tasks)
        stat.total_actual_hours = sum(t.actual_hours or 0 for t in tasks)

        # Количество созданных и завершенных задач
        stat.tasks_created = tasks_created_today
        stat.tasks_completed = tasks_completed_today

        self.session.commit()

    def search_tasks(
            self,
            workspace_id: uuid.UUID,
            search_query: Optional[str] = None,
            task_type: Optional[str] = None,
            status: Optional[str] = None,
            priority: Optional[str] = None,
            has_deadline: Optional[bool] = None,
            deadline_before: Optional[datetime] = None,
            deadline_after: Optional[datetime] = None,
            assignee_id: Optional[int] = None,
            limit: int = 100,
            offset: int = 0
    ) -> List[Task]:
        """Поиск задач по различным критериям"""
        query = self.session.query(Task).filter(
            Task.workspace_id == workspace_id
        )

        if search_query:
            query = query.filter(
                or_(
                    Task.title.ilike(f"%{search_query}%"),
                    Task.description.ilike(f"%{search_query}%")
                )
            )

        if task_type:
            query = query.filter(Task.task_type == task_type)

        if status:
            query = query.filter(Task.status == status)

        if priority:
            query = query.filter(Task.priority == priority)

        if has_deadline is not None:
            if has_deadline:
                query = query.filter(Task.deadline.isnot(None))
            else:
                query = query.filter(Task.deadline.is_(None))

        if deadline_before:
            query = query.filter(Task.deadline < deadline_before)

        if deadline_after:
            query = query.filter(Task.deadline > deadline_after)

        # Фильтрация по назначенному пользователю
        if assignee_id is not None:
            query = query.filter(Task.assignees.contains([assignee_id]))

        return query.order_by(
            desc(Task.created_at)
        ).limit(limit).offset(offset).all()

    def get_upcoming_deadlines(
            self,
            workspace_id: uuid.UUID,
            days_ahead: int = 7
    ) -> List[Task]:
        """Получение предстоящих дедлайнов"""
        now = datetime.now(UTC)
        future_date = now + timedelta(days=days_ahead)

        return self.session.query(Task).filter(
            and_(
                Task.workspace_id == workspace_id,
                Task.deadline.isnot(None),
                Task.deadline > now,
                Task.deadline <= future_date,
                Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value])
            )
        ).order_by(Task.deadline).all()

    def count_workspace_tasks(self, workspace_id: uuid.UUID) -> int:
        """Подсчет количества задач в рабочем пространстве"""
        return self.session.query(Task).filter(
            Task.workspace_id == workspace_id
        ).count()