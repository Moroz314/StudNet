from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, not_
from ..base_repository import BaseRepository
from ...models import Relationship, RelationshipStatus, UserProfile


class RelationShipRepository(BaseRepository):
    """Репозиторий для работы с отношениями между пользователями"""

    def __init__(self, session: Session):
        super().__init__(session)
        self.model = Relationship

    def _get_base_query(self):
        """Базовый запрос с оптимизированной загрузкой связанных данных"""
        return self.session.query(self.model).options(
            joinedload(self.model.user),
            joinedload(self.model.related_user),
            joinedload(self.model.action_user)
        )

    def create_relationship(
            self,
            user_id: int,
            related_user_id: int,
            status: RelationshipStatus,
            action_user_id: int
    ) -> Relationship:
        """Создание новой записи об отношениях"""
        relationship = self.model(
            user_id=user_id,
            related_user_id=related_user_id,
            status=status.value,
            action_user_id=action_user_id
        )
        self.session.add(relationship)
        self.session.flush()
        return relationship

    def get_relationship(self, user_id: int, related_user_id: int) -> Optional[Relationship]:
        """Получение отношений между двумя пользователями"""
        return self._get_base_query().filter(
            or_(
                and_(self.model.user_id == user_id, self.model.related_user_id == related_user_id),
                and_(self.model.user_id == related_user_id, self.model.related_user_id == user_id)
            )
        ).first()

    def get_relationship_by_id(self, relationship_id: int) -> Optional[Relationship]:
        """Получение отношений по ID"""
        return self._get_base_query().filter(self.model.id == relationship_id).first()

    def update_relationship_status(
            self,
            relationship: Relationship,
            new_status: RelationshipStatus,
            action_user_id: int
    ) -> Relationship:
        """Обновление статуса отношений"""
        relationship.status = new_status.value
        relationship.action_user_id = action_user_id
        #relationship.updated_at = func.now()
        self.session.flush()
        return relationship

    def delete_relationship(self, relationship: Relationship) -> None:
        """Удаление записи об отношениях"""
        self.session.delete(relationship)
        self.session.flush()

    def get_user_friends(
            self,
            user_id: int,
            offset: int = 0,
            limit: int = 100
    ) -> Tuple[List[UserProfile], int]:
        """Получение списка друзей пользователя с пагинацией"""
        # Получаем все записи, где пользователь является другом
        friends_subquery = self.session.query(
            self.model.user_id.label('friend_id')
        ).filter(
            self.model.related_user_id == user_id,
            self.model.status == RelationshipStatus.FRIEND.value
        ).union(
            self.session.query(
                self.model.related_user_id.label('friend_id')
            ).filter(
                self.model.user_id == user_id,
                self.model.status == RelationshipStatus.FRIEND.value
            )
        ).subquery()

        # Получаем профили друзей с пагинацией
        query = self.session.query(UserProfile).filter(
            UserProfile.user_id.in_(friends_subquery)
        ).options(
            selectinload(UserProfile.avatar_file)
        )

        total = query.count()
        friends = query.offset(offset).limit(limit).all()

        return friends, total

    def get_pending_requests(
            self,
            user_id: int,
            offset: int = 0,
            limit: int = 100
    ) -> Tuple[List[UserProfile], int]:
        """Получение входящих заявок в друзья"""
        query = self.session.query(UserProfile).join(
            self.model,
            and_(
                self.model.user_id == UserProfile.user_id,
                self.model.related_user_id == user_id,
                self.model.status == RelationshipStatus.PENDING.value
            )
        ).options(
            selectinload(UserProfile.avatar_file)
        )

        total = query.count()
        requests = query.offset(offset).limit(limit).all()

        return requests, total

    def get_sent_requests(
            self,
            user_id: int,
            offset: int = 0,
            limit: int = 100
    ) -> Tuple[List[UserProfile], int]:
        """Получение исходящих заявок в друзья"""
        query = self.session.query(UserProfile).join(
            self.model,
            and_(
                self.model.related_user_id == UserProfile.user_id,
                self.model.user_id == user_id,
                self.model.status == RelationshipStatus.PENDING.value
            )
        ).options(
            selectinload(UserProfile.avatar_file)
        )

        total = query.count()
        requests = query.offset(offset).limit(limit).all()

        return requests, total

    def get_blocked_users(
            self,
            user_id: int,
            offset: int = 0,
            limit: int = 100
    ) -> Tuple[List[UserProfile], int]:
        """Получение списка заблокированных пользователей"""
        # Пользователи, которых заблокировал текущий пользователь
        blocked_by_user = self.session.query(
            self.model.related_user_id.label('blocked_id')
        ).filter(
            self.model.user_id == user_id,
            self.model.status == RelationshipStatus.BLOCKED.value
        )

        # Пользователи, которые заблокировали текущего пользователя
        blocked_user = self.session.query(
            self.model.user_id.label('blocked_id')
        ).filter(
            self.model.related_user_id == user_id,
            self.model.status == RelationshipStatus.BLOCKED.value
        )

        all_blocked = blocked_by_user.union(blocked_user).subquery()

        query = self.session.query(UserProfile).filter(
            UserProfile.user_id.in_(all_blocked)
        ).options(
            selectinload(UserProfile.avatar_file)
        )

        total = query.count()
        blocked = query.offset(offset).limit(limit).all()

        return blocked, total

    def check_block_status(self, user_id: int, other_user_id: int) -> bool:
        """Проверка, заблокировал ли один пользователь другого"""
        block_exists = self.session.query(self.model).filter(
            or_(
                and_(
                    self.model.user_id == user_id,
                    self.model.related_user_id == other_user_id,
                    self.model.status == RelationshipStatus.BLOCKED.value
                ),
                and_(
                    self.model.user_id == other_user_id,
                    self.model.related_user_id == user_id,
                    self.model.status == RelationshipStatus.BLOCKED.value
                )
            )
        ).first()

        return block_exists is not None

    def get_relationship_status(self, user_id: int, other_user_id: int) -> Optional[str]:
        """Получение статуса отношений между пользователями"""
        relationship = self.get_relationship(user_id, other_user_id)
        return relationship.status if relationship else None

    def get_mutual_friends(
            self,
            user_id: int,
            other_user_id: int,
            offset: int = 0,
            limit: int = 100
    ) -> Tuple[List[UserProfile], int]:
        """Получение общих друзей между двумя пользователями"""
        # Друзья первого пользователя
        user_friends = self.session.query(
            self.model.related_user_id.label('friend_id')
        ).filter(
            self.model.user_id == user_id,
            self.model.status == RelationshipStatus.FRIEND.value
        ).union(
            self.session.query(
                self.model.user_id.label('friend_id')
            ).filter(
                self.model.related_user_id == user_id,
                self.model.status == RelationshipStatus.FRIEND.value
            )
        ).subquery()

        # Друзья второго пользователя
        other_friends = self.session.query(
            self.model.related_user_id.label('friend_id')
        ).filter(
            self.model.user_id == other_user_id,
            self.model.status == RelationshipStatus.FRIEND.value
        ).union(
            self.session.query(
                self.model.user_id.label('friend_id')
            ).filter(
                self.model.related_user_id == other_user_id,
                self.model.status == RelationshipStatus.FRIEND.value
            )
        ).subquery()

        # Находим пересечение
        mutual_friends_query = self.session.query(UserProfile).filter(
            UserProfile.user_id.in_(user_friends),
            UserProfile.user_id.in_(other_friends)
        ).options(
            selectinload(UserProfile.avatar_file)
        )

        total = mutual_friends_query.count()
        mutual_friends = mutual_friends_query.offset(offset).limit(limit).all()

        return mutual_friends, total