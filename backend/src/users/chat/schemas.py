from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    MEDIA = "media"
    REPLY = "reply"
    FORWARD = "forward"


class ChatRoomType(str, Enum):
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"


class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


# === БАЗОВЫЕ СХЕМЫ ДЛЯ СООБЩЕНИЙ ===

class MessageSend(BaseModel):
    chat_id: UUID
    content: str
    message_type: MessageType = MessageType.TEXT
    reply_to_message_id: Optional[int] = None  # Для ответа на сообщение
    forward_message_id: Optional[int] = None  # Для пересылки сообщения


class MessageEdit(BaseModel):
    content: str


class MessageReadBy(BaseModel):
    username: str
    avatar: str
    read_at: datetime

    class Config:
        from_attributes = True


# === СХЕМЫ ДЛЯ ПРЕВЬЮ СООБЩЕНИЙ (ДЛЯ ОТВЕТОВ И ПЕРЕСЫЛОК) ===

class UserShortInfo(BaseModel):
    user_id: int
    username: Optional[str]
    name: Optional[str]
    lastname: Optional[str]
    avatar_url: Optional[str]


class ChatShortInfo(BaseModel):
    chat_id: UUID
    name: str
    type: str


class MessagePreview(BaseModel):
    id: int
    chat_id: UUID
    user_id: int
    content: str
    message_type: MessageType
    created_at: datetime
    is_edited: bool = False

    sender: Optional[UserShortInfo] = None
    chat: Optional[ChatShortInfo] = None

    class Config:
        from_attributes = True


# === ПОЛНЫЕ СХЕМЫ СООБЩЕНИЙ ===

class MessageDTO(BaseModel):
    id: int
    chat_id: UUID
    user_id: int
    username: Optional[str] = None
    name: Optional[str] = None
    lastname: Optional[str] = None
    avatar_url: Optional[str] = None
    content: str
    message_type: MessageType
    created_at: datetime
    is_edited: bool
    read_by: Optional[Dict[str, MessageReadBy]] = None
    media_urls: Optional[List[Dict[str, Any]]] = None
    likes_count: int = Field(default=0, description="Количество лайков")
    is_liked_by_user: bool = Field(default=False, description="Лайкнул ли текущий пользователь")

    # Поля для ответов
    reply_to_message_id: Optional[int] = None
    reply_to: Optional[MessagePreview] = None

    # Поля для пересылок
    is_forwarded: bool = False
    original_message_id: Optional[int] = None
    forwarded_at: Optional[datetime] = None
    # Теперь получаем информацию через связь
    original_message_preview: Optional[MessagePreview] = None

    # Счетчики и дополнительная информация
    replies_count: int = 0

    class Config:
        from_attributes = True


# === СХЕМЫ ДЛЯ ОПЕРАЦИЙ С СООБЩЕНИЯМИ ===

class ForwardRequest(BaseModel):
    """Запрос на пересылку сообщений"""
    message_ids: List[int]
    target_chat_ids: List[UUID]
    include_original_info: bool = True


class MessageReplyRequest(BaseModel):
    content: str
    chat_id: UUID
    reply_to_message_id: int


class MessagesBulkRead(BaseModel):
    message_ids: List[int]
    chat_id: UUID
    mark_all: bool = False


# === СУЩЕСТВУЮЩИЕ СХЕМЫ С ОБНОВЛЕНИЯМИ ===

class ChatData(BaseModel):
    name: str
    type: ChatRoomType


class ChatCreate(BaseModel):
    data: ChatData
    members: Optional[list[int]] = None


class ChatDTO(BaseModel):
    id: UUID
    name: str
    type: ChatRoomType
    created_by: int
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0
    participants_count: int = 0

    class Config:
        from_attributes = True


class ChatParticipantDTO(BaseModel):
    id: int
    chat_id: UUID
    user_id: int
    role: UserRole
    joined_at: datetime
    username: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class UserPresenceDTO(BaseModel):
    user_id: int
    status: str
    last_seen: Optional[datetime] = None
    last_device: Optional[str] = None


# Обновляем enum для WebSocket событий
class WSEventType(str, Enum):
    MESSAGE_SEND = "message_send"
    MESSAGE_EDIT = "message_edit"
    MESSAGE_DELETE = "message_delete"
    USER_TYPING = "user_typing"
    USER_STOP_TYPING = "user_stop_typing"
    USER_PRESENCE = "user_presence"
    MESSAGE_READ = "message_read"
    MESSAGES_READ = "messages_read"
    MESSAGE_REPLIED = "message_replied"
    MESSAGES_FORWARDED = "messages_forwarded"
    USERS_ADDED_TO_CHAT = "users_added_to_chat"


class WSMessage(BaseModel):
    event: WSEventType
    data: Dict[str, Any]


class SearchMessagesResponse(BaseModel):
    messages: List[MessageDTO]
    total_count: int
    has_more: bool


class ChatListResponse(BaseModel):
    chats: List[ChatDTO]
    total_count: int


class UserDTO(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    university: Optional[str] = None
    faculty: Optional[str] = None

    class Config:
        from_attributes = True


class MessageWithUserDTO(MessageDTO):
    user: Optional[UserDTO] = None


class ChatWithParticipantsDTO(ChatDTO):
    participants: List[ChatParticipantDTO]


class TypingEvent(BaseModel):
    user_id: int
    chat_id: UUID
    is_typing: bool


class ReadReceipt(BaseModel):
    user_id: int
    message_id: int
    chat_id: UUID
    read_at: datetime


class ChatStats(BaseModel):
    chat_id: UUID
    total_messages: int
    total_participants: int
    last_activity: Optional[datetime] = None
    unread_count: int = 0