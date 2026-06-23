import os
from fastapi import HTTPException, status, Depends, UploadFile
from uuid import UUID
from typing import List, Optional, Dict
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from ...database.repositories.user.chat import ChatRepository, ChatRoomType
from ...database.repositories.project.core import ProjectRepository
from ...database.redis.redis_presence import RedisPresence
from ...files.service import FileService
from ...files.schemas import FileType as GlobalFileType
from ...database.core import get_db
from ...websockets.connection import connection_manager
from .schemas import *
from ...database.models import Chat, Message, FileMetadata
from ...projects.validation import require_project_permission, is_project_owner
from ...users.auth.service.utils import verify_token
from dotenv import load_dotenv

load_dotenv()

AVATAR_URL_EXPIRY = 86400  # 24 часа
MEDIA_URL_EXPIRY = 3600  # 1 час


class ChannelService:
    def __init__(
            self,
            chat_repo: ChatRepository,
            project_repo: ProjectRepository,
            presence_service: RedisPresence,
            file_service: FileService,
            user_id: int
    ):
        self.chat_repo = chat_repo
        self.project_repo = project_repo
        self.presence_service = presence_service
        self.file_service = file_service
        self.user_id = user_id

    # ============ МЕТОДЫ ДЛЯ РАБОТЫ С ФАЙЛАМИ ============

    async def _get_avatar_url(self, avatar_file: Optional[FileMetadata]) -> Optional[str]:
        """Получение URL аватара через FileService"""
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

    async def _get_media_urls_batch(self, file_ids: List[UUID]) -> Dict[UUID, str]:
        """Получение URL для медиа-файлов batch-запросом"""
        if not file_ids:
            return {}
        return await self.file_service.get_file_urls_batch(
            file_ids=file_ids,
            user_id=self.user_id,
            expires_in=MEDIA_URL_EXPIRY
        )

    def _determine_media_type(self, mime_type: str) -> str:
        """Определить тип медиа по MIME типу"""
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        else:
            return 'document'

    async def _generate_media_urls(self, media_files: List[FileMetadata]) -> List[Dict]:
        """Сгенерировать presigned URLs для медиа-файлов через FileService"""
        if not media_files:
            return []

        file_ids = [media.id for media in media_files]
        urls_map = await self._get_media_urls_batch(file_ids)

        media_urls = []
        for media in media_files:
            url = urls_map.get(media.id, "")
            media_urls.append({
                'url': url,
                'type': media.mime_type,
                'media_type': self._determine_media_type(media.mime_type),
                'filename': media.original_filename,
                'size': media.size_bytes,
                'id': str(media.id)
            })
        return media_urls

    # ============ ОСНОВНЫЕ МЕТОДЫ ============

    async def create_channel(
            self,
            channel_data: ChannelCreate,
            user_id: int
    ) -> ChannelDTO:
        """Создать канал для проекта"""
        # Проверяем права (только админ проекта может создать канал)
        require_project_permission(
            self.project_repo,
            channel_data.project_id,
            user_id,
            ['owner', 'admin']
        )

        # Проверяем, не существует ли уже канал для этого проекта
        existing_channel = self.chat_repo.get_project_channel(channel_data.project_id)
        if existing_channel:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Project already has a channel",
                    "project_id": str(channel_data.project_id),
                    "existing_channel_id": str(existing_channel.id),
                    "existing_channel_name": existing_channel.name
                }
            )

        # Проверяем, существует ли проект
        project = self.project_repo.get_project_by_id(channel_data.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Создаем канал
        try:
            channel = self.chat_repo.create_project_channel(
                project_id=channel_data.project_id,
                name=channel_data.name,
                description=channel_data.description,
                created_by=user_id
            )

            # Уведомляем всех участников проекта о создании канала
            await self._notify_channel_created(channel, user_id)

            return await self._create_channel_dto(channel, user_id)

        except Exception as e:
            # Ловим возможные ошибки уникальности на уровне БД
            if "unique constraint" in str(e).lower() or "uq_project_channel" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project already has a channel (database constraint)"
                )
            raise e

    async def publish_media_message(
            self,
            channel_id: UUID,
            user_id: int,
            files: List[UploadFile],
            caption: Optional[str] = None
    ) -> ChannelMessageDTO:
        """
        Отправить медиа-сообщение в канал.
        Загружает файлы через FileService.
        """
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        require_project_permission(self.project_repo, channel.project_id, user_id, ['admin', 'owner'])

        # Загружаем файлы через FileService
        file_ids = []
        for file in files:
            upload_result = await self.file_service.upload_file(
                file=file,
                file_type=GlobalFileType.MESSAGE_ATTACHMENT,
                user_id=user_id,
                metadata={
                    "channel_id": str(channel_id),
                    "sender_id": str(user_id)
                },
                public=False
            )
            file_ids.append(upload_result.file_id)

        # Создаем сообщение в БД с медиа-файлами
        message_dict = {
            "chat_id": channel_id,
            "user_id": user_id,
            "content": caption or "",
            "message_type": "media"
        }

        message = self.chat_repo.message.save_media_message(message_dict, file_ids)

        # Создаем DTO с presigned URLs
        message_dto = await self._create_channel_message_dto(message, user_id)

        # Отправляем уведомление подписчикам
        await self._notify_new_message(message_dto, channel_id, user_id)

        return message_dto

    async def publish_text_message(
            self,
            channel_id: UUID,
            user_id: int,
            content: str
    ) -> ChannelMessageDTO:
        """Отправить текстовое сообщение в канал"""
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        require_project_permission(self.project_repo, channel.project_id, user_id, ['admin', 'owner'])

        # Создаем сообщение
        message_dict = {
            "chat_id": channel_id,
            "user_id": user_id,
            "content": content,
            "message_type": "text"
        }

        message = self.chat_repo.message.save_message(message_dict)

        # Создаем DTO
        message_dto = await self._create_channel_message_dto(message, user_id)

        # Отправляем уведомление подписчикам
        await self._notify_new_message(message_dto, channel_id, user_id)

        return message_dto

    async def get_channel(self, channel_id: UUID, user_id: int) -> ChannelDetailDTO:
        """Получить информацию о канале"""
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        # Получаем подписчиков
        subscribers = self.chat_repo.get_channel_subscribers(channel_id)
        subscribers_count = len(subscribers)
        is_subscribed = self.chat_repo.is_channel_subscriber(channel_id, user_id)

        # Получаем последнее сообщение
        last_message = self.chat_repo.message.get_last_message(channel_id)

        # Создаем DTO
        channel_dto = await self._create_channel_dto(
            channel, user_id, subscribers_count, is_subscribed, last_message
        )

        # Получаем статусы присутствия для подписчиков
        presence_data = {}
        for sub in subscribers:
            data = await self.presence_service.get_user_presence_data(sub.user_id)
            presence_data[sub.user_id] = data

        # Формируем список подписчиков с аватарками
        subscribers_dto = []
        for sub in subscribers:
            avatar_url = None
            if sub.user_profile and sub.user_profile.avatar_file:
                avatar_url = await self._get_avatar_url(sub.user_profile.avatar_file)

            user_status = presence_data.get(sub.user_id, {})
            subscribers_dto.append(ChannelSubscriberDTO(
                user_id=sub.user_id,
                username=sub.user_profile.username if sub.user_profile else "Unknown",
                name=sub.user_profile.name if sub.user_profile else None,
                lastname=sub.user_profile.lastname if sub.user_profile else None,
                avatar_url=avatar_url,
                subscribed_at=sub.joined_at,
                is_online=user_status.get('status') == 'online' if user_status else False,
                last_seen=user_status.get('last_seen') if user_status else None
            ))

        # Получаем информацию о создателе
        creator_profile = None
        for sub in subscribers:
            if sub.user_id == channel.created_by:
                creator_profile = sub.user_profile
                break

        return ChannelDetailDTO(
            **channel_dto.model_dump(),
            subscribers=subscribers_dto,
            creator_username=creator_profile.username if creator_profile else None,
            creator_name=creator_profile.name if creator_profile else None
        )

    async def update_channel(
            self,
            channel_id: UUID,
            update_data: ChannelUpdate,
            user_id: int
    ) -> ChannelDTO:
        """Обновить канал"""
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        # Проверяем права (только админ проекта может обновить канал)
        require_project_permission(
            self.project_repo,
            channel.project_id,
            user_id,
            ['owner', 'admin']
        )

        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
        if update_dict:
            update_dict["updated_at"] = datetime.now(UTC)
            updated_channel = self.chat_repo.update_channel(channel_id, update_dict)

            # Уведомляем подписчиков об обновлении канала
            await self._notify_channel_updated(updated_channel, user_id)
        else:
            updated_channel = channel

        return await self._create_channel_dto(updated_channel, user_id)

    async def delete_channel(self, channel_id: UUID, user_id: int) -> bool:
        """Удалить канал"""
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        # Проверяем права (только владелец проекта может удалить канал)
        if not is_project_owner(self.project_repo, channel.project_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owner can delete channel"
            )

        success = self.chat_repo.delete_channel(channel_id)

        if success:
            # Уведомляем подписчиков об удалении канала
            subscribers = self.chat_repo.get_channel_subscribers(channel_id)
            ws_message = {
                "event": "channel_deleted",
                "data": {
                    "channel_id": str(channel_id),
                    "project_id": str(channel.project_id),
                    "deleted_by": user_id,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_chat(
                [sub.user_id for sub in subscribers],
                ws_message
            )

        return success

    async def subscribe_to_channel(self, channel_id: UUID, user_id: int) -> ChannelSubscriptionResponse:
        """Подписаться на канал"""
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        if self.chat_repo.is_channel_subscriber(channel_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already subscribed to this channel"
            )

        success = self.chat_repo.subscribe_to_channel(channel_id, user_id)

        if success:
            # Получаем время подписки
            participant = self.chat_repo.get_participant_info(user_id, channel_id)
            subscribed_at = participant.joined_at if participant else datetime.now(UTC)

            # Уведомляем других подписчиков
            subscribers = self.chat_repo.get_channel_subscribers(channel_id)
            ws_message = {
                "event": "channel_subscriber_added",
                "data": {
                    "channel_id": str(channel_id),
                    "user_id": user_id,
                    "project_id": str(channel.project_id),
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_chat(
                [sub.user_id for sub in subscribers if sub.user_id != user_id],
                ws_message
            )

            return ChannelSubscriptionResponse(
                channel_id=channel_id,
                user_id=user_id,
                subscribed_at=subscribed_at,
                message="Successfully subscribed to channel"
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to channel"
        )

    async def unsubscribe_from_channel(self, channel_id: UUID, user_id: int) -> bool:
        """Отписаться от канала"""
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        # Проверяем, не владелец ли канала
        owner_id = self.chat_repo.get_channel_owner_id(channel_id)
        if owner_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel owner cannot unsubscribe"
            )

        success = self.chat_repo.unsubscribe_from_channel(channel_id, user_id)

        if success:
            # Уведомляем других подписчиков
            subscribers = self.chat_repo.get_channel_subscribers(channel_id)
            ws_message = {
                "event": "channel_subscriber_removed",
                "data": {
                    "channel_id": str(channel_id),
                    "user_id": user_id,
                    "project_id": str(channel.project_id),
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_chat(
                [sub.user_id for sub in subscribers],
                ws_message
            )

        return success

    async def get_user_subscribed_channels(self, user_id: int, limit: int, offset: int) -> List[ChannelDTO]:
        """Получить все каналы, на которые подписан пользователь"""
        channels = self.chat_repo.get_user_subscribed_channels(user_id, limit, offset)

        result = []
        chat_ids = [ch.id for ch in channels]

        if chat_ids:
            last_messages = self.chat_repo.message.get_last_messages_for_chats(chat_ids)
        else:
            last_messages = {}

        for channel in channels:
            last_message = last_messages.get(channel.id)
            subscribers_count = self.chat_repo.get_channel_subscribers_count(channel.id)

            channel_dto = await self._create_channel_dto(
                channel, user_id, subscribers_count, True, last_message
            )
            result.append(channel_dto)

        return result

    async def get_user_admin_channels(
            self,
            user_id: int,
            limit: int = 100,
            offset: int = 0
    ) -> List[ChannelDTO]:
        """
        Получить каналы проектов, где пользователь является админом или владельцем
        """
        channels, total = self.chat_repo.get_user_admin_channels(user_id, limit, offset)

        result = []
        if channels:
            chat_ids = [ch.id for ch in channels]
            last_messages = self.chat_repo.message.get_last_messages_for_chats(chat_ids)

            for channel in channels:
                last_message = last_messages.get(channel.id)
                subscribers_count = self.chat_repo.get_channel_subscribers_count(channel.id)
                is_subscribed = self.chat_repo.is_channel_subscriber(channel.id, user_id)

                channel_dto = await self._create_channel_dto(
                    channel, user_id, subscribers_count, is_subscribed, last_message
                )
                result.append(channel_dto)

        return result

    async def get_project_channel(self, project_id: UUID, user_id: int) -> Optional[ChannelDTO]:
        """Получить канал конкретного проекта"""
        channel = self.chat_repo.get_project_channel(project_id)
        if not channel:
            return None

        subscribers_count = self.chat_repo.get_channel_subscribers_count(channel.id)
        is_subscribed = self.chat_repo.is_channel_subscriber(channel.id, user_id)
        last_message = self.chat_repo.message.get_last_message(channel.id)

        return await self._create_channel_dto(
            channel, user_id, subscribers_count, is_subscribed, last_message
        )

    async def get_channel_messages(
            self,
            channel_id: UUID,
            user_id: int,
            limit: int = 50,
            offset: int = 0
    ) -> ChannelMessageResponse:
        """Получить сообщения канала"""
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        messages = self.chat_repo.message.get_chat_messages(channel_id, limit, offset)
        total = self.chat_repo.message.get_chat_messages_count(channel_id)

        message_dtos = []
        for message in messages:
            dto = await self._create_channel_message_dto(message, user_id)
            message_dtos.append(dto)

        return ChannelMessageResponse(
            messages=message_dtos,
            total=total,
            has_more=(offset + limit) < total
        )

    async def like_channel_message(self, message_id: int, user_id: int, channel_id: UUID) -> Dict:
        """Поставить лайк сообщению в канале"""
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        message = self.chat_repo.message.get_message_by_id(message_id)
        if not message or message.chat_id != channel_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found in this channel"
            )

        success = self.chat_repo.message.add_like(message_id, user_id)

        if success:
            updated_message = self.chat_repo.message.get_message_full(message_id)

            # Уведомляем подписчиков
            subscribers = self.chat_repo.get_channel_subscribers(channel_id)
            ws_message = {
                "event": "channel_message_liked",
                "data": {
                    "message_id": message_id,
                    "channel_id": str(channel_id),
                    "user_id": user_id,
                    "likes_count": updated_message.likes_count,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_chat(
                [sub.user_id for sub in subscribers],
                ws_message,
                exclude_user_id=user_id
            )

            return {
                "message_id": message_id,
                "likes_count": updated_message.likes_count,
                "liked": True
            }

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already liked this message"
        )

    async def unlike_channel_message(self, message_id: int, user_id: int, channel_id: UUID) -> Dict:
        """Убрать лайк с сообщения в канале"""
        channel = self.chat_repo.get_chat_by_id(channel_id)
        if not channel or channel.type != ChatRoomType.CHANNEL.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        message = self.chat_repo.message.get_message_by_id(message_id)
        if not message or message.chat_id != channel_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found in this channel"
            )

        success = self.chat_repo.message.remove_like(message_id, user_id)

        if success:
            updated_message = self.chat_repo.message.get_message_full(message_id)

            # Уведомляем подписчиков
            subscribers = self.chat_repo.get_channel_subscribers(channel_id)
            ws_message = {
                "event": "channel_message_unliked",
                "data": {
                    "message_id": message_id,
                    "channel_id": str(channel_id),
                    "user_id": user_id,
                    "likes_count": updated_message.likes_count,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_chat(
                [sub.user_id for sub in subscribers],
                ws_message,
                exclude_user_id=user_id
            )

            return {
                "message_id": message_id,
                "likes_count": updated_message.likes_count,
                "liked": False
            }

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not liked this message"
        )

    # ============ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============

    async def _notify_channel_created(self, channel: Chat, created_by: int):
        """Уведомить о создании канала"""
        # Получаем всех участников проекта
        project_participants = self.project_repo.get_project_participants(channel.project_id)
        participant_ids = [p.user_id for p in project_participants if p.user_id != created_by]

        ws_message = {
            "event": "channel_created",
            "data": {
                "channel_id": str(channel.id),
                "project_id": str(channel.project_id),
                "name": channel.name,
                "description": channel.description,
                "created_by": created_by,
                "created_at": channel.created_at.isoformat()
            }
        }

        await connection_manager.send_to_chat(participant_ids, ws_message)

    async def _notify_channel_updated(self, channel: Chat, updated_by: int):
        """Уведомить об обновлении канала"""
        subscribers = self.chat_repo.get_channel_subscribers(channel.id)
        subscriber_ids = [sub.user_id for sub in subscribers if sub.user_id != updated_by]

        ws_message = {
            "event": "channel_updated",
            "data": {
                "channel_id": str(channel.id),
                "project_id": str(channel.project_id),
                "name": channel.name,
                "description": channel.description,
                "updated_by": updated_by,
                "updated_at": channel.updated_at.isoformat()
            }
        }

        await connection_manager.send_to_chat(subscriber_ids, ws_message)

    async def _notify_new_message(self, message_dto: ChannelMessageDTO, channel_id: UUID, sender_id: int):
        """Уведомить о новом сообщении"""
        subscribers = self.chat_repo.get_channel_subscribers(channel_id)
        ws_message = {
            "event": "channel_message",
            "data": message_dto.model_dump(mode="json")
        }
        await connection_manager.send_to_chat(
            [sub.user_id for sub in subscribers],
            ws_message,
            exclude_user_id=sender_id
        )

    async def _create_channel_dto(
            self,
            channel: Chat,
            current_user_id: int,
            subscribers_count: Optional[int] = None,
            is_subscribed: Optional[bool] = None,
            last_message: Optional[Message] = None
    ) -> ChannelDTO:
        """Внутренний метод для создания DTO канала"""
        if subscribers_count is None:
            subscribers_count = self.chat_repo.get_channel_subscribers_count(channel.id)

        if is_subscribed is None:
            is_subscribed = self.chat_repo.is_channel_subscriber(channel.id, current_user_id)

        return ChannelDTO(
            id=channel.id,
            name=channel.name,
            description=getattr(channel, 'description', None),
            project_id=channel.project_id,
            created_by=channel.created_by,
            created_at=channel.created_at,
            updated_at=channel.updated_at,
            subscribers_count=subscribers_count,
            is_subscribed=is_subscribed,
            last_message_at=last_message.created_at if last_message else None,
            last_message_preview=last_message.content[:100] + "..." if last_message and len(
                last_message.content) > 100 else last_message.content if last_message else None,
            last_message_sender_id=last_message.user_id if last_message else None,
        )

    async def _create_channel_message_dto(
            self,
            message: Message,
            user_id: int
    ) -> ChannelMessageDTO:
        """Внутренний метод для создания DTO сообщения канала"""
        # Получаем медиа-файлы и генерируем для них presigned URLs
        media_files = self.chat_repo.message.get_message_media(message.id)
        media_urls = await self._generate_media_urls(media_files)

        is_liked = False
        if message.likes and str(user_id) in message.likes:
            is_liked = True

        # Получаем информацию об отправителе
        username = None
        name = None
        lastname = None
        avatar_url = None

        if message.user_profile:
            username = message.user_profile.username
            name = message.user_profile.name
            lastname = message.user_profile.lastname
            if message.user_profile.avatar_file:
                avatar_url = await self._get_avatar_url(message.user_profile.avatar_file)

        return ChannelMessageDTO(
            id=message.id,
            channel_id=message.chat_id,
            user_id=message.user_id,
            username=username,
            name=name,
            lastname=lastname,
            avatar_url=avatar_url,
            content=message.content,
            message_type=message.message_type,
            media_urls=media_urls,
            likes_count=message.likes_count or 0,
            is_liked_by_user=is_liked,
            created_at=message.created_at,
            updated_at=message.updated_at
        )


def get_channel_service(
        db: Session = Depends(get_db),
        user_id: int = Depends(verify_token)
) -> ChannelService:
    chat_repo = ChatRepository(db)
    project_repo = ProjectRepository(db)
    presence_service = RedisPresence()
    file_service = FileService(session=db)

    return ChannelService(
        chat_repo=chat_repo,
        project_repo=project_repo,
        presence_service=presence_service,
        file_service=file_service,
        user_id=user_id
    )