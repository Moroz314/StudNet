from ...repositories.base_repository import BaseRepository
from ....users.feed.schemas import (
    UserFeedFilter, UserFeedQuery, SortOrder, SortField
)
from ....database.models import *
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_, func, select
from typing import Optional


class FeedRepository(BaseRepository):
    def get_user_feed(
            self,
            query: UserFeedQuery
    ) -> tuple[list[UserProfile], int]:

        # Базовый запрос с подгрузкой аватарки
        stmt = select(UserProfile).options(
            selectinload(UserProfile.user),
            selectinload(UserProfile.avatar_file)  # Добавляем подгрузку аватарки
        )

        # Применяем фильтры
        if query.filter:
            stmt = self._apply_filters(stmt, query.filter)

        # Применяем сортировку
        stmt = self._apply_sorting(stmt, query.sort_by, query.sort_order)

        # Получаем общее количество
        count_stmt = select(func.count()).select_from(UserProfile)
        if query.filter:
            count_stmt = self._apply_filters(count_stmt, query.filter)

        total_count = self.session.scalar(count_stmt)

        # Применяем пагинацию
        offset = (query.page - 1) * query.page_size
        stmt = stmt.offset(offset).limit(query.page_size)

        # Выполняем запрос
        result = self.session.execute(stmt)
        profiles = result.scalars().all()

        return profiles, total_count

    def search_users(
            self,
            search_query: str,
            page: int = 1,
            page_size: int = 20
    ) -> tuple[list[UserProfile], int]:
        """Поиск пользователей по различным полям"""

        search_pattern = f"%{search_query}%"

        # Базовый запрос с подгрузкой аватарки
        stmt = select(UserProfile).options(
            selectinload(UserProfile.user),
            selectinload(UserProfile.avatar_file)  # Добавляем подгрузку аватарки
        ).where(
            or_(
                UserProfile.name.ilike(search_pattern),
                UserProfile.lastname.ilike(search_pattern),
                UserProfile.username.ilike(search_pattern),
                UserProfile.university.ilike(search_pattern),
                UserProfile.faculty.ilike(search_pattern),
                UserProfile.info.ilike(search_pattern),
                UserProfile.interests.any(search_query),
                UserProfile.skills.any(search_query)
            )
        )

        # Получаем общее количество
        count_stmt = select(func.count()).select_from(UserProfile).where(
            or_(
                UserProfile.name.ilike(search_pattern),
                UserProfile.lastname.ilike(search_pattern),
                UserProfile.username.ilike(search_pattern),
                UserProfile.university.ilike(search_pattern),
                UserProfile.faculty.ilike(search_pattern),
                UserProfile.info.ilike(search_pattern),
                UserProfile.interests.any(search_query),
                UserProfile.skills.any(search_query)
            )
        )

        total_count = self.session.scalar(count_stmt)

        # Применяем пагинацию
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Выполняем запрос
        result = self.session.execute(stmt)
        profiles = result.scalars().all()

        return profiles, total_count

    @staticmethod
    def _apply_filters(stmt, filters: UserFeedFilter):
        conditions = []

        if filters.name:
            conditions.append(UserProfile.name.ilike(f"%{filters.name}%"))

        if filters.lastname:
            conditions.append(UserProfile.lastname.ilike(f"%{filters.lastname}%"))

        if filters.username:
            conditions.append(UserProfile.username.ilike(f"%{filters.username}%"))

        if filters.university:
            conditions.append(UserProfile.university.ilike(f"%{filters.university}%"))

        if filters.faculty:
            conditions.append(UserProfile.faculty.ilike(f"%{filters.faculty}%"))

        if filters.course:
            conditions.append(UserProfile.course == filters.course)

        if filters.min_course:
            conditions.append(UserProfile.course >= filters.min_course)

        if filters.max_course:
            conditions.append(UserProfile.course <= filters.max_course)

        if filters.interests:
            # Фильтр по интересам (хотя бы один совпадает)
            for interest in filters.interests:
                conditions.append(UserProfile.interests.any(interest))

        if filters.skills:
            # Фильтр по навыкам (хотя бы один совпадает)
            for skill in filters.skills:
                conditions.append(UserProfile.skills.any(skill))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        return stmt

    @staticmethod
    def _apply_sorting(stmt, sort_by: SortField, sort_order: SortOrder):
        sort_field_map = {
            SortField.NAME: UserProfile.name,
            SortField.LASTNAME: UserProfile.lastname,
            SortField.USERNAME: UserProfile.username,
            SortField.COURSE: UserProfile.course,
            SortField.CREATED_AT: UserProfile.id,
        }

        sort_field = sort_field_map.get(sort_by, UserProfile.username)

        if sort_order == SortOrder.DESC:
            return stmt.order_by(sort_field.desc())
        else:
            return stmt.order_by(sort_field.asc())

