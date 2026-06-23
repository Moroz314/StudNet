from typing import Optional, List, Tuple
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, UTC
import uuid
from .schemas import *
from ...database.repositories.user.relationship import RelationShipRepository
from ...database.core import get_db
from ..auth.service.utils import verify_token
from ...database.models import RelationshipStatus as ModelStatus, UserProfile, FileMetadata
from ...websockets.connection import connection_manager
from ...files.service import FileService

AVATAR_URL_EXPIRY = 3600  # 1 час


class RelationShipService:
    def __init__(
            self,
            user_id: int,
            db: Session,
            file_service: FileService,
            relation_repo: Optional[RelationShipRepository] = None
    ):
        self.user_id = user_id
        self.db = db
        self.relation_repo = relation_repo or RelationShipRepository(db)
        self.file_service = file_service

    async def _get_avatar_urls_batch(self, profiles: List[UserProfile]) -> dict:
        """Массовое получение presigned URL для аватаров пользователей"""
        if not profiles:
            return {}

        # Собираем ID всех аватаров
        avatar_file_ids = [p.avatar_file.id for p in profiles if p.avatar_file]

        if not avatar_file_ids:
            return {}

        # Получаем все URL одним batch-запросом
        return await self.file_service.get_file_urls_batch(
            file_ids=avatar_file_ids,
            user_id=self.user_id,
            expires_in=AVATAR_URL_EXPIRY
        )

    async def _get_user_profile_with_avatar(
            self,
            user_profile: UserProfile,
            avatar_urls: dict = None
    ) -> UserProfileResponse:
        """Преобразование UserProfile в UserProfileResponse с presigned URL для аватара"""
        response = UserProfileResponse.model_validate(user_profile)

        # Генерируем presigned URL для аватара, если он есть
        if user_profile.avatar_file_id and user_profile.avatar_file:
            try:
                if avatar_urls is not None:
                    response.avatar_url = avatar_urls.get(user_profile.avatar_file.id)
                else:
                    response.avatar_url = await self.file_service.get_file_url(
                        file_id=user_profile.avatar_file.id,
                        user_id=self.user_id,
                        expires_in=AVATAR_URL_EXPIRY
                    )
            except Exception as e:
                # Логируем ошибку, но не прерываем выполнение
                print(f"Error generating avatar URL: {e}")
                response.avatar_url = None

        return response

    async def _enrich_user_profiles_with_avatars(self, user_profiles: List[UserProfile]) -> List[UserProfileResponse]:
        """Обогащение списка профилей пользователей presigned URL для аватаров (оптимизировано)"""
        if not user_profiles:
            return []

        # Получаем все URL аватаров одним batch-запросом
        avatar_urls = await self._get_avatar_urls_batch(user_profiles)

        # Строим ответы
        result = []
        for profile in user_profiles:
            enriched = await self._get_user_profile_with_avatar(profile, avatar_urls)
            result.append(enriched)
        return result

    async def _send_notification(self, target_user_id: int, notification_type: str, data: dict):
        """Отправка уведомления через WebSocket"""
        notification = {
            "type": "friend_notification",
            "subtype": notification_type,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat()
        }
        await connection_manager.send_to_user(target_user_id, notification)

    async def send_friend_request(self, target_user_id: int) -> FriendRequestResponse:
        """Отправка заявки в друзья"""
        # Проверка на самому себе
        if self.user_id == target_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send friend request to yourself"
            )

        # Проверяем существование пользователя
        target_user = self.db.query(UserProfile).filter(
            UserProfile.user_id == target_user_id
        ).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Проверяем существующие отношения
        existing = self.relation_repo.get_relationship(self.user_id, target_user_id)

        if existing:
            if existing.status == ModelStatus.FRIEND.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You are already friends"
                )
            elif existing.status == ModelStatus.BLOCKED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot send request to blocked user"
                )
            elif existing.status == ModelStatus.PENDING.value:
                if existing.action_user_id == self.user_id:
                    return FriendRequestResponse(
                        message="Friend request already sent",
                        relationship=RelationshipResponse.model_validate(existing)
                    )
                if existing.related_user_id == self.user_id:
                    await self.accept_friend_request(existing.user_id)
                    refreshed = self.relation_repo.get_relationship(self.user_id, target_user_id)
                    return FriendRequestResponse(
                        message="Friend request accepted",
                        relationship=RelationshipResponse.model_validate(refreshed)
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Friend request already exists"
                )

        # Проверяем, не заблокировал ли нас целевой пользователь
        if self.relation_repo.check_block_status(target_user_id, self.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot send request to this user"
            )

        # Создаем заявку
        relationship = self.relation_repo.create_relationship(
            user_id=self.user_id,
            related_user_id=target_user_id,
            status=ModelStatus.PENDING,
            action_user_id=self.user_id
        )

        self.db.commit()

        # Получаем данные отправителя для уведомления
        sender = self.db.query(UserProfile).filter(
            UserProfile.user_id == self.user_id
        ).first()

        # Обогащаем данные отправителя avatar_url для уведомления
        sender_data = await self._get_user_profile_with_avatar(sender)

        # Отправляем уведомление получателю
        await self._send_notification(
            target_user_id=target_user_id,
            notification_type="friend_request_received",
            data={
                "request_id": relationship.id,
                "from_user": sender_data.model_dump(),
                "created_at": relationship.created_at.isoformat()
            }
        )

        return FriendRequestResponse(
            message="Friend request sent successfully",
            relationship=RelationshipResponse.model_validate(relationship)
        )

    async def cancel_friend_request(self, target_user_id: int) -> RelationshipActionResponse:
        """Отмена отправленной заявки в друзья"""
        # Получаем отношения
        relationship = self.relation_repo.get_relationship(self.user_id, target_user_id)

        # Проверяем, существует ли заявка
        if not relationship or relationship.status != ModelStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )

        # Проверяем, что заявка отправлена текущим пользователем
        if relationship.action_user_id != self.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own friend requests"
            )

        # Проверяем, что это действительно исходящая заявка (пользователь - отправитель)
        if relationship.user_id != self.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel requests you sent"
            )

        # Получаем данные отменяющего пользователя для уведомления
        canceller = self.db.query(UserProfile).filter(
            UserProfile.user_id == self.user_id
        ).first()

        # Обогащаем данные отменителя avatar_url для уведомления
        canceller_data = await self._get_user_profile_with_avatar(canceller)

        # Удаляем заявку
        self.relation_repo.delete_relationship(relationship)
        self.db.commit()

        # Отправляем уведомление получателю о том, что заявка отменена
        await self._send_notification(
            target_user_id=target_user_id,
            notification_type="friend_request_cancelled",
            data={
                "by_user": canceller_data.model_dump(),
                "cancelled_at": datetime.now(UTC).isoformat()
            }
        )

        return RelationshipActionResponse(
            message="Friend request cancelled successfully",
            success=True
        )

    async def accept_friend_request(self, request_user_id: int) -> RelationshipActionResponse:
        """Принятие заявки в друзья"""
        relationship = self.relation_repo.get_relationship(request_user_id, self.user_id)

        if not relationship or relationship.status != ModelStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )

        # Проверяем, что заявка адресована нам
        if relationship.related_user_id != self.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only accept requests addressed to you"
            )

        # Обновляем статус
        self.relation_repo.update_relationship_status(
            relationship=relationship,
            new_status=ModelStatus.FRIEND,
            action_user_id=self.user_id
        )

        self.db.commit()

        # Получаем данные принявшего пользователя
        accepter = self.db.query(UserProfile).filter(
            UserProfile.user_id == self.user_id
        ).first()

        # Обогащаем данные accepter avatar_url для уведомления
        accepter_data = await self._get_user_profile_with_avatar(accepter)

        # Отправляем уведомление отправителю заявки
        await self._send_notification(
            target_user_id=request_user_id,
            notification_type="friend_request_accepted",
            data={
                "by_user": accepter_data.model_dump(),
                "updated_at": relationship.updated_at.isoformat()
            }
        )

        return RelationshipActionResponse(
            message="Friend request accepted",
            success=True
        )

    async def reject_friend_request(self, request_user_id: int) -> RelationshipActionResponse:
        """Отклонение заявки в друзья"""
        relationship = self.relation_repo.get_relationship(request_user_id, self.user_id)

        if not relationship or relationship.status != ModelStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )

        # Проверяем, что заявка адресована нам
        if relationship.related_user_id != self.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reject requests addressed to you"
            )

        # Получаем данные отклоняющего пользователя
        rejector = self.db.query(UserProfile).filter(
            UserProfile.user_id == self.user_id
        ).first()

        # Обогащаем данные rejector avatar_url для уведомления
        rejector_data = await self._get_user_profile_with_avatar(rejector)

        # Удаляем заявку
        self.relation_repo.delete_relationship(relationship)
        self.db.commit()

        # Отправляем уведомление отправителю заявки
        await self._send_notification(
            target_user_id=request_user_id,
            notification_type="friend_request_rejected",
            data={
                "by_user": rejector_data.model_dump()
            }
        )

        return RelationshipActionResponse(
            message="Friend request rejected",
            success=True
        )

    async def remove_friend(self, friend_user_id: int) -> RelationshipActionResponse:
        """Удаление из друзей"""
        relationship = self.relation_repo.get_relationship(self.user_id, friend_user_id)

        if not relationship or relationship.status != ModelStatus.FRIEND.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friendship not found"
            )

        # Получаем данные удаляющего пользователя
        remover = self.db.query(UserProfile).filter(
            UserProfile.user_id == self.user_id
        ).first()

        # Обогащаем данные remover avatar_url для уведомления
        remover_data = await self._get_user_profile_with_avatar(remover)

        # Удаляем запись
        self.relation_repo.delete_relationship(relationship)
        self.db.commit()

        # Отправляем уведомление бывшему другу
        await self._send_notification(
            target_user_id=friend_user_id,
            notification_type="friend_removed",
            data={
                "by_user": remover_data.model_dump()
            }
        )

        return RelationshipActionResponse(
            message="Friend removed successfully",
            success=True
        )

    async def block_user(self, block_user_id: int) -> RelationshipActionResponse:
        """Блокировка пользователя"""
        if self.user_id == block_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block yourself"
            )

        relationship = self.relation_repo.get_relationship(self.user_id, block_user_id)
        was_friend = False

        if relationship:
            was_friend = relationship.status == ModelStatus.FRIEND.value
            if relationship.status == ModelStatus.BLOCKED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already blocked"
                )
            # Обновляем существующую запись
            self.relation_repo.update_relationship_status(
                relationship=relationship,
                new_status=ModelStatus.BLOCKED,
                action_user_id=self.user_id
            )
        else:
            # Создаем новую запись о блокировке
            self.relation_repo.create_relationship(
                user_id=self.user_id,
                related_user_id=block_user_id,
                status=ModelStatus.BLOCKED,
                action_user_id=self.user_id
            )

        self.db.commit()

        # Если это был друг, отправляем уведомление о блокировке
        if was_friend:
            blocker = self.db.query(UserProfile).filter(
                UserProfile.user_id == self.user_id
            ).first()

            # Обогащаем данные blocker avatar_url для уведомления
            blocker_data = await self._get_user_profile_with_avatar(blocker)

            await self._send_notification(
                target_user_id=block_user_id,
                notification_type="user_blocked_you",
                data={
                    "by_user": blocker_data.model_dump()
                }
            )

        return RelationshipActionResponse(
            message="User blocked successfully",
            success=True
        )

    async def unblock_user(self, unblock_user_id: int) -> RelationshipActionResponse:
        """Разблокировка пользователя"""
        relationship = self.relation_repo.get_relationship(self.user_id, unblock_user_id)

        if not relationship or relationship.status != ModelStatus.BLOCKED.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Block not found"
            )

        # Проверяем, что блокировка создана текущим пользователем
        if relationship.user_id != self.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only unblock users you have blocked"
            )

        # Удаляем запись о блокировке
        self.relation_repo.delete_relationship(relationship)
        self.db.commit()

        # Отправляем уведомление разблокированному пользователю
        unblocker = self.db.query(UserProfile).filter(
            UserProfile.user_id == self.user_id
        ).first()

        # Обогащаем данные unblocker avatar_url для уведомления
        unblocker_data = await self._get_user_profile_with_avatar(unblocker)

        await self._send_notification(
            target_user_id=unblock_user_id,
            notification_type="user_unblocked_you",
            data={
                "by_user": unblocker_data.model_dump()
            }
        )

        return RelationshipActionResponse(
            message="User unblocked successfully",
            success=True
        )

    async def get_friends(
            self,
            offset: int = 0,
            limit: int = 100
    ) -> FriendListResponse:
        """Получение списка друзей"""
        friends, total = self.relation_repo.get_user_friends(
            user_id=self.user_id,
            offset=offset,
            limit=limit
        )

        # Обогащаем профили друзей avatar_url
        enriched_friends = await self._enrich_user_profiles_with_avatars(friends)

        return FriendListResponse(
            items=enriched_friends,
            total=total,
            offset=offset,
            limit=limit
        )

    async def get_pending_requests(
            self,
            offset: int = 0,
            limit: int = 100
    ) -> PendingRequestsResponse:
        """Получение входящих и исходящих заявок"""
        incoming, incoming_total = self.relation_repo.get_pending_requests(
            user_id=self.user_id,
            offset=offset,
            limit=limit
        )

        outgoing, outgoing_total = self.relation_repo.get_sent_requests(
            user_id=self.user_id,
            offset=offset,
            limit=limit
        )

        # Обогащаем профили avatar_url
        enriched_incoming = await self._enrich_user_profiles_with_avatars(incoming)
        enriched_outgoing = await self._enrich_user_profiles_with_avatars(outgoing)

        return PendingRequestsResponse(
            incoming=enriched_incoming,
            outgoing=enriched_outgoing,
            incoming_total=incoming_total,
            outgoing_total=outgoing_total
        )

    async def get_blocked_users(
            self,
            offset: int = 0,
            limit: int = 100
    ) -> FriendListResponse:
        """Получение списка заблокированных пользователей"""
        blocked, total = self.relation_repo.get_blocked_users(
            user_id=self.user_id,
            offset=offset,
            limit=limit
        )

        # Обогащаем профили заблокированных пользователей avatar_url
        enriched_blocked = await self._enrich_user_profiles_with_avatars(blocked)

        return FriendListResponse(
            items=enriched_blocked,
            total=total,
            offset=offset,
            limit=limit
        )

    async def get_relationship_status(self, other_user_id: int) -> dict:
        """Получение статуса отношений с пользователем"""
        relationship = self.relation_repo.get_relationship(self.user_id, other_user_id)
        status_value = relationship.status if relationship else None
        is_blocked = self.relation_repo.check_block_status(self.user_id, other_user_id)

        can_send_request = (
            not is_blocked
            and status_value != ModelStatus.FRIEND.value
            and status_value != ModelStatus.BLOCKED.value
        )

        return {
            "user_id": other_user_id,
            "status": status_value,
            "is_blocked": is_blocked,
            "can_send_request": can_send_request
        }

    async def get_mutual_friends(
            self,
            other_user_id: int,
            offset: int = 0,
            limit: int = 100
    ) -> MutualFriendsResponse:
        """Получение общих друзей"""
        mutual_friends, total = self.relation_repo.get_mutual_friends(
            user_id=self.user_id,
            other_user_id=other_user_id,
            offset=offset,
            limit=limit
        )

        # Обогащаем профили общих друзей avatar_url
        enriched_mutual = await self._enrich_user_profiles_with_avatars(mutual_friends)

        return MutualFriendsResponse(
            items=enriched_mutual,
            total=total,
            count=len(mutual_friends)
        )


# Dependency для получения сервиса
async def get_relationship_service(
        user_id: int = Depends(verify_token),
        db: Session = Depends(get_db)
) -> RelationShipService:
    file_service = FileService(session=db)
    return RelationShipService(
        user_id=user_id,
        db=db,
        file_service=file_service
    )