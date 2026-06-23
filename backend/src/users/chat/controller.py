from fastapi import APIRouter, WebSocket, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from .schemas import *
from .chat_service import get_chat_service, build_chat_service, ChatService
from ..auth.service.utils import verify_token, decode_token
from ...database.core import get_db
from uuid import UUID
from typing import List, Set, Optional

chat_router = APIRouter(tags=['Chats'])


# ============ WEBSOCKET (только для событий реального времени) ============

@chat_router.websocket("/ws")
async def global_websocket_endpoint(
        websocket: WebSocket,
        token: str = Query(None),
        user_agent: str = Query(None),
        db: Session = Depends(get_db),
):
    """
    WebSocket endpoint только для событий реального времени:
    - печать сообщения (user_typing, user_stop_typing)
    - прочтение сообщений (message_read, messages_read)
    - лайки (like_message, unlike_message)
    - статус присутствия (get_presence)

    Отправка сообщений осуществляется через REST API.
    """
    if not token:
        await websocket.close(code=4000, reason="Missing token")
        return

    try:
        user_id = decode_token(token)
    except HTTPException:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    device_info = {
        "user_agent": user_agent or "unknown",
        "ip_address": websocket.client.host if websocket.client else "unknown",
        "device_type": "web",
    }

    chat_service = build_chat_service(db, user_id)
    await chat_service.handle_ws(websocket, user_id, device_info)


# ============ REST API ДЛЯ ЧАТОВ ============

@chat_router.get("/chats", response_model=List[ChatDTO])
async def get_user_chats(
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token),
):
    """Получить все чаты пользователя"""
    return await chat_service.get_user_chats(user_id)


@chat_router.post("/chat", response_model=ChatDTO, status_code=status.HTTP_201_CREATED)
async def create_chat(
        chat_data: ChatCreate,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token),
):
    """Создать новый чат"""
    return await chat_service.create_chat(chat_data, user_id)


@chat_router.get("/chats/{chat_id}", response_model=ChatDTO)
async def get_chat(
        chat_id: UUID,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    return await chat_service.get_chat(user_id, chat_id)


# ============ REST API ДЛЯ СООБЩЕНИЙ ============

@chat_router.post("/chats/{chat_id}/messages/text", response_model=MessageDTO)
async def send_text_message(
        chat_id: UUID,
        message_data: MessageSend,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """
    Отправить текстовое сообщение в чат.
    Поддерживает ответы на сообщения и пересылку.
    """
    # Убеждаемся, что chat_id в пути совпадает с chat_id в теле запроса
    if message_data.chat_id != chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat ID in path must match chat_id in request body"
        )

    return await chat_service.send_text_message_rest(message_data, user_id)


@chat_router.post("/chats/{chat_id}/messages/media", response_model=MessageDTO)
async def send_media_message(
        chat_id: UUID,
        files: List[UploadFile] = File(..., description="Media files (images, videos, documents)"),
        caption: Optional[str] = Query(None, max_length=2000),
        reply_to_message_id: Optional[int] = Query(None),
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """
    Отправить медиа-сообщение (фото, видео, файлы) в чат.
    Все файлы загружаются в S3 bucket 'media-bucket'.
    """
    return await chat_service.send_media_message_rest(
        chat_id=chat_id,
        sender_id=user_id,
        files=files,
        caption=caption,
        reply_to_message_id=reply_to_message_id
    )


@chat_router.post("/chats/{chat_id}/messages/forward", response_model=Dict)
async def forward_messages(
        chat_id: UUID,  # Целевой чат
        forward_data: ForwardRequest,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """
    Переслать сообщения в указанные чаты.
    """
    return await chat_service.forward_messages_rest(forward_data, user_id)


@chat_router.get("/chats/{chat_id}/messages", response_model=List[MessageDTO])
async def get_chat_messages(
        chat_id: UUID,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Получить сообщения чата с пагинацией"""
    return await chat_service.get_chat_messages(chat_id, user_id, limit, offset)


@chat_router.get("/chats/{chat_id}/messages/{message_id}/replies", response_model=List[MessageDTO])
async def get_message_replies(
        chat_id: UUID,
        message_id: int,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Получить ответы на конкретное сообщение"""
    return await chat_service.get_message_replies(message_id, user_id, limit, offset)


@chat_router.put("/chats/{chat_id}/messages/{message_id}", response_model=MessageDTO)
async def edit_message(
        chat_id: UUID,
        message_id: int,
        message_edit: MessageEdit,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Редактировать сообщение"""
    return await chat_service.edit_message(message_id, user_id, message_edit.content)


@chat_router.delete("/chats/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
        chat_id: UUID,
        message_id: int,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Удалить сообщение"""
    success = await chat_service.delete_message(message_id, user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Ошибка при удалении сообщения")
    return None


@chat_router.get("/chats/{chat_id}/messages/search", response_model=List[MessageDTO])
async def search_messages(
        chat_id: UUID,
        query: str = Query(..., min_length=1),
        limit: int = Query(50, ge=1, le=100),
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Поиск сообщений в чате"""
    return await chat_service.search_messages(chat_id, user_id, query, limit)


# ============ REST API ДЛЯ УЧАСТНИКОВ ЧАТА ============

@chat_router.post("/chats/{chat_id}/users")
async def add_users_to_chat(
        chat_id: UUID,
        user_ids: Set[int] = Query(...),
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Добавить пользователей в чат (только для админов/владельцев)"""
    await chat_service.add_users_to_chat(chat_id, user_id, user_ids)
    return {"message": "Пользователи успешно добавлены в чат"}


@chat_router.get("/chats/{chat_id}/participants", response_model=ChatWithParticipantsDTO)
async def get_chat_participants(
        chat_id: UUID,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Получить список участников чата"""
    participants = await chat_service.get_chat_participants(user_id=user_id, chat_id=chat_id)
    # Получаем информацию о чате
    chats = await chat_service.get_user_chats(user_id)
    chat = next((c for c in chats if c.id == chat_id), None)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Создаем DTO с участниками
    return ChatWithParticipantsDTO(
        **chat.model_dump(),
        participants=participants
    )


# ============ REST API ДЛЯ ПРОЧТЕНИЯ ============

@chat_router.post("/chats/{chat_id}/read")
async def mark_chat_as_read(
        chat_id: UUID,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token),
        message_ids: list[int] = Query(default=[]),
        mark_all: bool = False
):
    """
    Отметить сообщения в чате как прочитанные.
    - Если mark_all=True, отмечаются все непрочитанные сообщения
    - Иначе отмечаются только сообщения из message_ids
    """
    await chat_service.mark_chat_messages_as_read(user_id, chat_id, message_ids, mark_all=mark_all)
    return {"message": "Сообщения отмечены как прочитанные"}


@chat_router.post("/messages/{message_id}/read")
async def mark_message_as_read(
        message_id: int,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Отметить конкретное сообщение как прочитанное"""
    await chat_service.mark_message_as_read(user_id, message_id)
    return {"message": "Сообщение отмечено как прочитанное"}


# ============ REST API ДЛЯ ЛАЙКОВ ============

@chat_router.post("/chats/{chat_id}/messages/{message_id}/like")
async def like_message(
        chat_id: UUID,
        message_id: int,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Поставить лайк сообщению"""
    return await chat_service.like_message(user_id, message_id, chat_id)


@chat_router.post("/chats/{chat_id}/messages/{message_id}/unlike")
async def unlike_message(
        chat_id: UUID,
        message_id: int,
        chat_service: ChatService = Depends(get_chat_service),
        user_id: int = Depends(verify_token)
):
    """Убрать лайк с сообщения"""
    return await chat_service.unlike_message(user_id, message_id, chat_id)