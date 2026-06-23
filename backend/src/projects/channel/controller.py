from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from uuid import UUID
from typing import List, Optional
from .schemas import *
from .service import ChannelService, get_channel_service
from ...users.auth.service.utils import verify_token

channel_router = APIRouter(prefix="/channels", tags=["channels"])


@channel_router.post("", response_model=ChannelDTO, status_code=status.HTTP_201_CREATED)
async def create_channel(
        channel_data: ChannelCreate,
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """
    Создать канал для проекта.

    - Только один канал может быть создан для проекта
    - Только админ проекта может создать канал
    """
    return await channel_service.create_channel(channel_data, user_id)


@channel_router.get("/my", response_model=List[ChannelDTO])
async def get_my_channels(
        limit: int = Query(100, ge=1, le=200, description="Количество каналов на странице"),
        offset: int = Query(0, ge=0, description="Смещение для пагинации"),
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """Получить все каналы, на которые подписан текущий пользователь"""
    return await channel_service.get_user_subscribed_channels(user_id, limit=limit, offset=offset)


@channel_router.get("/{channel_id}", response_model=ChannelDetailDTO)
async def get_channel(
        channel_id: UUID,
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """Получить подробную информацию о канале со списком подписчиков"""
    return await channel_service.get_channel(channel_id, user_id)


@channel_router.put("/{channel_id}", response_model=ChannelDTO)
async def update_channel(
        channel_id: UUID,
        update_data: ChannelUpdate,
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    return await channel_service.update_channel(channel_id, update_data, user_id)


@channel_router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
        channel_id: UUID,
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """
    Удалить канал.

    - Только владелец проекта может удалить канал
    """
    success = await channel_service.delete_channel(channel_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete channel"
        )
    return None


@channel_router.post("/{channel_id}/subscribe", response_model=ChannelSubscriptionResponse)
async def subscribe_to_channel(
        channel_id: UUID,
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """
    Подписаться на канал.

    - Только участники проекта могут подписаться
    - Владелец канала не может отписаться
    """
    return await channel_service.subscribe_to_channel(channel_id, user_id)


@channel_router.post("/{channel_id}/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_channel(
        channel_id: UUID,
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """
    Отписаться от канала.

    - Владелец канала не может отписаться
    """
    success = await channel_service.unsubscribe_from_channel(channel_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to unsubscribe from channel"
        )
    return None


@channel_router.get("/project/{project_id}", response_model=Optional[ChannelDTO])
async def get_project_channel(
        project_id: UUID,
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):

    return await channel_service.get_project_channel(project_id, user_id)


@channel_router.get("/admin/channels", response_model=List[ChannelDTO])
async def get_admin_channels(
        limit: int = Query(100, ge=1, le=200, description="Количество каналов на странице"),
        offset: int = Query(0, ge=0, description="Смещение для пагинации"),
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):

    return await channel_service.get_user_admin_channels(
        user_id=user_id,
        limit=limit,
        offset=offset
    )


@channel_router.get("/{channel_id}/messages", response_model=ChannelMessageResponse)
async def get_channel_messages(
        channel_id: UUID,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """
    Получить сообщения канала с пагинацией.

    - Только подписчики канала могут просматривать сообщения
    """
    return await channel_service.get_channel_messages(channel_id, user_id, limit, offset)


@channel_router.post("/{channel_id}/messages/text", response_model=ChannelMessageDTO)
async def publish_text_message(
        channel_id: UUID,
        content: str = Query(..., min_length=1, max_length=5000),
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """
    Отправить текстовое сообщение в канал.

    - Только подписчики канала могут отправлять сообщения
    """
    return await channel_service.publish_text_message(channel_id, user_id, content)


@channel_router.post("/{channel_id}/messages/media", response_model=ChannelMessageDTO)
async def publish_media_message(
        channel_id: UUID,
        files: List[UploadFile] = File(..., description="Media files to upload (images, videos, documents)"),
        caption: Optional[str] = Query(None, max_length=2000),
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """
    Отправить медиа-сообщение в канал.

    Поддерживаются изображения, видео и документы.
    Все файлы загружаются в S3 и доступны по presigned URL.

    - Только подписчики канала могут отправлять сообщения
    """
    return await channel_service.publish_media_message(
        channel_id=channel_id,
        user_id=user_id,
        files=files,
        caption=caption
    )


@channel_router.post("/{channel_id}/messages/{message_id}/like")
async def like_message(
        channel_id: UUID,
        message_id: int,
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """
    Поставить лайк сообщению в канале.

    - Только подписчики канала могут ставить лайки
    """
    return await channel_service.like_channel_message(message_id, user_id, channel_id)


@channel_router.post("/{channel_id}/messages/{message_id}/unlike")
async def unlike_message(
        channel_id: UUID,
        message_id: int,
        channel_service: ChannelService = Depends(get_channel_service),
        user_id: int = Depends(verify_token)
):
    """
    Убрать лайк с сообщения в канале.

    - Только подписчики канала могут убирать лайки
    """
    return await channel_service.unlike_channel_message(message_id, user_id, channel_id)