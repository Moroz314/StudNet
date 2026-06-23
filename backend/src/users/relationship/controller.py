from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from .schemas import *
from .service import RelationShipService, get_relationship_service

relationship_router = APIRouter(prefix="/relationships", tags=["relationships"])


@relationship_router.post("/requests", response_model=FriendRequestResponse)
async def send_friend_request(
        request: FriendRequest,
        service: RelationShipService = Depends(get_relationship_service)
):
    """Отправка заявки в друзья"""
    return await service.send_friend_request(request.user_id)


@relationship_router.post("/requests/{user_id}/accept", response_model=RelationshipActionResponse)
async def accept_friend_request(
        user_id: int,
        service: RelationShipService = Depends(get_relationship_service)
):
    """Принятие заявки в друзья"""
    return await service.accept_friend_request(user_id)


@relationship_router.post("/requests/{user_id}/reject", response_model=RelationshipActionResponse)
async def reject_friend_request(
        user_id: int,
        service: RelationShipService = Depends(get_relationship_service)
):
    """Отклонение заявки в друзья"""
    return await service.reject_friend_request(user_id)


@relationship_router.delete("/friends/{user_id}", response_model=RelationshipActionResponse)
async def remove_friend(
        user_id: int,
        service: RelationShipService = Depends(get_relationship_service)
):
    """Удаление из друзей"""
    return await service.remove_friend(user_id)


@relationship_router.get("/requests", response_model=PendingRequestsResponse)
async def get_pending_requests(
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        service: RelationShipService = Depends(get_relationship_service)
):
    """Получение входящих и исходящих заявок в друзья"""
    return await service.get_pending_requests(offset=offset, limit=limit)


@relationship_router.delete("/requests/{user_id}/cancel", response_model=RelationshipActionResponse)
async def cancel_friend_request(
        user_id: int,
        service: RelationShipService = Depends(get_relationship_service)
):

    return await service.cancel_friend_request(user_id)

@relationship_router.get("/friends", response_model=FriendListResponse)
async def get_friends(
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        service: RelationShipService = Depends(get_relationship_service)
):
    """Получение списка друзей"""
    return await service.get_friends(offset=offset, limit=limit)


@relationship_router.post("/block", response_model=RelationshipActionResponse)
async def block_user(
        request: BlockUserRequest,
        service: RelationShipService = Depends(get_relationship_service)
):
    """Блокировка пользователя"""
    return await service.block_user(request.user_id)


@relationship_router.post("/unblock/{user_id}", response_model=RelationshipActionResponse)
async def unblock_user(
        user_id: int,
        service: RelationShipService = Depends(get_relationship_service)
):
    """Разблокировка пользователя"""
    return await service.unblock_user(user_id)


@relationship_router.get("/blocked", response_model=FriendListResponse)
async def get_blocked_users(
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        service: RelationShipService = Depends(get_relationship_service)
):
    """Получение списка заблокированных пользователей"""
    return await service.get_blocked_users(offset=offset, limit=limit)


@relationship_router.get("/status/{user_id}")
async def get_relationship_status(
        user_id: int,
        service: RelationShipService = Depends(get_relationship_service)
):
    """Получение статуса отношений с пользователем"""
    return await service.get_relationship_status(user_id)


@relationship_router.get("/friends/mutual/{user_id}", response_model=MutualFriendsResponse)
async def get_mutual_friends(
        user_id: int,
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        service: RelationShipService = Depends(get_relationship_service)
):
    """Получение общих друзей с пользователем"""
    return await service.get_mutual_friends(
        other_user_id=user_id,
        offset=offset,
        limit=limit
    )