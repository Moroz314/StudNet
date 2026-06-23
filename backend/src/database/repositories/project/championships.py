# championships.py - полная реализация

from ...repositories.base_repository import BaseRepository
from ...models import *
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_, or_, func, update, select, delete, exists
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChampionshipRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    # ============ CHAMPIONSHIP CRUD ============

    def create_championship(
            self,
            title: str,
            description: str,
            created_by: int,
            max_winners: int,
            max_participants: int,
            prize_amount: int,
            prize_distribution: List[int],
            deadline: datetime,
            organizer_project_id: Optional[UUID] = None
    ) -> Championship:
        """Создание нового чемпионата"""
        try:
            # Валидация распределения призов
            if sum(prize_distribution) != prize_amount:
                raise ValueError("Sum of prize distribution must equal prize_amount")
            if len(prize_distribution) != max_winners:
                raise ValueError("Prize distribution length must equal max_winners")

            championship = Championship(
                title=title,
                description=description,
                created_by=created_by,
                max_winners=max_winners,
                max_participants=max_participants,
                prize_amount=prize_amount,
                prize_distribution=prize_distribution,
                deadline=deadline,
                organizer_project_id=organizer_project_id,
                status="inactive"
            )

            self.session.add(championship)
            self.session.commit()
            self.session.refresh(championship)
            return championship

        except Exception as e:
            self.session.rollback()
            raise e

    def get_championship_by_id(
            self,
            championship_id: UUID,
            include_relations: bool = False
    ) -> Optional[Championship]:
        """Получение чемпионата по ID"""
        query = select(Championship).where(Championship.id == championship_id)

        if include_relations:
            query = query.options(
                selectinload(Championship.creator),
                selectinload(Championship.organizer_project),
                selectinload(Championship.championship_files).selectinload(ChampionshipFile.file),
                selectinload(Championship.solutions).selectinload(ChampionshipSolution.project),
                selectinload(Championship.solutions).selectinload(ChampionshipSolution.submitter)
            )

        result = self.session.execute(query)
        return result.unique().scalar_one_or_none()

    def get_championships(
            self,
            filters: Optional[Dict[str, Any]] = None,
            include_relations: bool = False
    ) -> List[Championship]:
        """Получение списка чемпионатов с фильтрацией"""
        query = select(Championship)

        if filters:
            if filters.get('status'):
                query = query.where(Championship.status == filters['status'])
            if filters.get('created_by'):
                query = query.where(Championship.created_by == filters['created_by'])
            if filters.get('search'):
                search_pattern = f"%{filters['search']}%"
                query = query.where(
                    or_(
                        Championship.title.ilike(search_pattern),
                        Championship.description.ilike(search_pattern)
                    )
                )

        if include_relations:
            query = query.options(
                selectinload(Championship.creator),
                selectinload(Championship.solutions)
            )

        # Пагинация
        if filters:
            if filters.get('offset'):
                query = query.offset(filters['offset'])
            if filters.get('limit'):
                query = query.limit(filters['limit'])

        query = query.order_by(Championship.created_at.desc())

        result = self.session.execute(query)
        return list(result.unique().scalars().all())

    def update_championship(
            self,
            championship_id: UUID,
            **kwargs
    ) -> Optional[Championship]:
        """Обновление чемпионата"""
        try:
            query = (
                update(Championship)
                .where(Championship.id == championship_id)
                .values(**kwargs, updated_at=func.now())
                .returning(Championship)
            )

            result = self.session.execute(query)
            self.session.commit()
            return result.scalar_one_or_none()

        except Exception as e:
            self.session.rollback()
            raise e

    def delete_championship(self, championship_id: UUID) -> bool:
        """Удаление чемпионата"""
        try:
            query = delete(Championship).where(Championship.id == championship_id)
            result = self.session.execute(query)
            self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            self.session.rollback()
            raise e

    # ============ SOLUTIONS CRUD ============

    def submit_solution(
            self,
            championship_id: UUID,
            project_id: UUID,
            user_id: int
    ) -> ChampionshipSolution:
        """Отправка решения на чемпионат"""
        try:
            # Проверяем существование чемпионата
            championship = self.get_championship_by_id(championship_id)
            if not championship:
                raise ValueError("Championship not found")

            # Проверяем статус чемпионата
            if championship.status != "active":
                raise ValueError("Championship is not active")

            # Проверяем дедлайн
            if datetime.now() > championship.deadline:
                raise ValueError("Championship deadline has passed")

            # Проверяем, что пользователь не создатель чемпионата
            if championship.created_by == user_id:
                raise ValueError("Championship creator cannot submit solution")

            # Проверяем лимит решений
            solutions_count = self.session.execute(
                select(func.count(ChampionshipSolution.id))
                .where(ChampionshipSolution.championship_id == championship_id)
            ).scalar()

            if solutions_count >= championship.max_participants:
                raise ValueError("Maximum number of solutions reached")

            # Проверяем, что пользователь не отправил уже решение в этот чемпионат
            user_already_submitted = self.session.execute(
                select(exists().where(
                    and_(
                        ChampionshipSolution.championship_id == championship_id,
                        ChampionshipSolution.submitted_by == user_id
                    )
                ))
            ).scalar()

            if user_already_submitted:
                raise ValueError("User already submitted a solution to this championship")

            # Проверяем, что проект не является решением в другом чемпионате
            project_in_championship = self.session.execute(
                select(exists().where(
                    ChampionshipSolution.project_id == project_id
                ))
            ).scalar()

            if project_in_championship:
                raise ValueError("Project is already submitted to a championship")

            solution = ChampionshipSolution(
                championship_id=championship_id,
                project_id=project_id,
                submitted_by=user_id,
                status="submitted"
            )

            self.session.add(solution)
            self.session.commit()
            self.session.refresh(solution)
            return solution

        except Exception as e:
            self.session.rollback()
            raise e

    def get_solutions(
            self,
            championship_id: UUID,
            include_relations: bool = False
    ) -> List[ChampionshipSolution]:
        """Получение всех решений чемпионата"""
        query = select(ChampionshipSolution).where(
            ChampionshipSolution.championship_id == championship_id
        )

        if include_relations:
            query = query.options(
                selectinload(ChampionshipSolution.project),
                selectinload(ChampionshipSolution.submitter)
            )

        query = query.order_by(ChampionshipSolution.created_at)

        result = self.session.execute(query)
        return list(result.unique().scalars().all())

    def get_solution_by_id(
            self,
            solution_id: UUID,
            include_relations: bool = False
    ) -> Optional[ChampionshipSolution]:
        """Получение решения по ID"""
        query = select(ChampionshipSolution).where(
            ChampionshipSolution.id == solution_id
        )

        if include_relations:
            query = query.options(
                selectinload(ChampionshipSolution.championship),
                selectinload(ChampionshipSolution.project),
                selectinload(ChampionshipSolution.submitter)
            )

        result = self.session.execute(query)
        return result.unique().scalar_one_or_none()

    def update_solution(
            self,
            solution_id: UUID,
            **kwargs
    ) -> Optional[ChampionshipSolution]:
        """Обновление решения (статус, место)"""
        try:
            query = (
                update(ChampionshipSolution)
                .where(ChampionshipSolution.id == solution_id)
                .values(**kwargs, updated_at=func.now())
                .returning(ChampionshipSolution)
            )

            result = self.session.execute(query)
            self.session.commit()
            return result.scalar_one_or_none()

        except Exception as e:
            self.session.rollback()
            raise e

    def get_user_solutions(
            self,
            user_id: int,
            include_relations: bool = False
    ) -> List[ChampionshipSolution]:
        """Получение всех решений пользователя"""
        query = select(ChampionshipSolution).where(
            ChampionshipSolution.submitted_by == user_id
        )

        if include_relations:
            query = query.options(
                selectinload(ChampionshipSolution.championship),
                selectinload(ChampionshipSolution.project)
            )

        query = query.order_by(ChampionshipSolution.created_at.desc())

        result = self.session.execute(query)
        return list(result.unique().scalars().all())

    # ============ VALIDATION METHODS ============

    def get_championship_solutions_count(self, championship_id: UUID) -> int:
        """Получение количества решений чемпионата"""
        return self.session.execute(
            select(func.count(ChampionshipSolution.id))
            .where(ChampionshipSolution.championship_id == championship_id)
        ).scalar()

    def is_user_championship_participant(self, championship_id: UUID, user_id: int) -> bool:
        """Проверка, является ли пользователь участником чемпионата"""
        return self.session.execute(
            select(exists().where(
                and_(
                    ChampionshipSolution.championship_id == championship_id,
                    ChampionshipSolution.submitted_by == user_id
                )
            ))
        ).scalar()