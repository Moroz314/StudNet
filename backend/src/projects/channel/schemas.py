from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any, Dict


class ChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Название канала")
    description: Optional[str] = Field(None, max_length=1000, description="Описание канала")


class ChannelCreate(ChannelBase):
    project_id: UUID = Field(..., description="ID проекта, которому принадлежит канал")


class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class ChannelSubscriberDTO(BaseModel):
    user_id: int
    username: str
    name: Optional[str] = None
    lastname: Optional[str] = None
    avatar_url: Optional[str] = None
    subscribed_at: datetime
    is_online: bool = False
    last_seen: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChannelDTO(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    project_id: UUID
    created_by: int
    created_at: datetime
    updated_at: datetime
    subscribers_count: int = 0
    is_subscribed: bool = False
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    last_message_sender_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ChannelDetailDTO(ChannelDTO):
    subscribers: List[ChannelSubscriberDTO] = []
    creator_username: Optional[str] = None
    creator_name: Optional[str] = None


class ChannelMessageDTO(BaseModel):
    """DTO для сообщений в канале"""
    id: int
    channel_id: UUID
    user_id: int
    username: Optional[str] = None
    name: Optional[str] = None
    lastname: Optional[str] = None
    avatar_url: Optional[str] = None
    content: Optional[str] = None
    message_type: str
    media_urls: Optional[List[Dict[str, Any]]] = None
    likes_count: int = 0
    is_liked_by_user: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChannelMessageResponse(BaseModel):
    messages: List[ChannelMessageDTO]
    total: int
    has_more: bool


class ChannelSubscriptionResponse(BaseModel):
    channel_id: UUID
    user_id: int
    subscribed_at: datetime
    message: str = "Successfully subscribed to channel"