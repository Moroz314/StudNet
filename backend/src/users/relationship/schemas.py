from pydantic import BaseModel, Field, computed_field, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum
from uuid import UUID


class RelationshipStatus(str, Enum):
    PENDING = "pending"
    FRIEND = "friend"
    BLOCKED = "blocked"


class UserProfileBase(BaseModel):
    user_id: int
    name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    university: Optional[str] = None
    faculty: Optional[str] = None
    course: Optional[int] = None
    avatar_file_id: Optional[UUID] = None


class UserProfileResponse(UserProfileBase):
    avatar_url: Optional[str] = Field(None, description="Presigned URL for avatar")

    model_config = ConfigDict(from_attributes=True)


class RelationshipResponse(BaseModel):
    id: int
    user_id: int
    related_user_id: int
    status: RelationshipStatus
    action_user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FriendRequest(BaseModel):
    user_id: int = Field(..., description="ID пользователя, которому отправляется заявка")


class FriendRequestResponse(BaseModel):
    message: str
    relationship: RelationshipResponse


class FriendListResponse(BaseModel):
    items: List[UserProfileResponse]
    total: int
    offset: int
    limit: int


class PendingRequestsResponse(BaseModel):
    incoming: List[UserProfileResponse]
    outgoing: List[UserProfileResponse]
    incoming_total: int
    outgoing_total: int


class BlockUserRequest(BaseModel):
    user_id: int = Field(..., description="ID пользователя для блокировки")


class RelationshipActionResponse(BaseModel):
    message: str
    success: bool


class MutualFriendsResponse(BaseModel):
    items: List[UserProfileResponse]
    total: int
    count: int