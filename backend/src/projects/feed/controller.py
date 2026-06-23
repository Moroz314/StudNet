from fastapi import APIRouter, Depends, Query, Path, status, HTTPException, Body
from typing import List, Optional
from uuid import UUID
from .schemas import *
from .service import FeedService, get_feed_service

feed_router = APIRouter(prefix="/feed", tags=["feed"])


# ============ FEED ENDPOINTS ============

@feed_router.get("/posts", response_model=FeedResponse)
async def get_feed(
        limit: int = Query(20, ge=1, le=100, description="Количество постов на странице"),
        offset: int = Query(0, ge=0, description="Смещение для пагинации"),
        category: Optional[str] = Query(None, description="Фильтр по категории проекта"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Получение ленты постов"""
    return await feed_service.get_feed(
        limit=limit,
        offset=offset,
        category=category
    )


@feed_router.get("/posts/trending", response_model=List[TrendingProjectResponse])
async def get_trending_posts(
        days: int = Query(7, ge=1, le=30, description="Период в днях для подсчета трендов"),
        limit: int = Query(20, ge=1, le=50, description="Количество постов"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Получение трендовых постов"""
    return await feed_service.get_trending_posts(
        days=days,
        limit=limit
    )


@feed_router.get("/posts/recommended", response_model=FeedResponse)
async def get_recommended_posts(
        limit: int = Query(20, ge=1, le=50, description="Количество рекомендаций"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Получение рекомендованных постов"""
    return await feed_service.get_recommended_posts(limit=limit)


@feed_router.get("/posts/liked", response_model=FeedResponse)
async def get_liked_posts(
        limit: int = Query(20, ge=1, le=100, description="Количество постов"),
        offset: int = Query(0, ge=0, description="Смещение для пагинации"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Получение постов, лайкнутых пользователем"""
    return await feed_service.get_user_liked_posts(
        limit=limit,
        offset=offset
    )


@feed_router.get("/posts/user/{user_id}", response_model=FeedResponse)
async def get_posts_by_creator(
        user_id: int = Path(..., description="ID создателя"),
        limit: int = Query(20, ge=1, le=100, description="Количество постов"),
        offset: int = Query(0, ge=0, description="Смещение для пагинации"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Получение постов создателя"""
    return await feed_service.get_posts_by_creator(
        creator_id=user_id,
        limit=limit,
        offset=offset
    )


@feed_router.get("/posts/project/{project_id}", response_model=ProjectFeedResponse)
async def get_post_by_project(
        project_id: UUID = Path(..., description="ID проекта"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Получение поста по ID проекта"""
    return await feed_service.get_post_by_project_id(project_id)


@feed_router.post("/posts/{post_id}/like", response_model=LikeResponse)
async def like_post(
        post_id: UUID = Path(..., description="ID поста"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Лайкнуть пост"""
    return await feed_service.like_post(post_id)


@feed_router.delete("/posts/{post_id}/like", response_model=LikeResponse)
async def unlike_post(
        post_id: UUID = Path(..., description="ID поста"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Убрать лайк с поста"""
    return await feed_service.unlike_post(post_id)


@feed_router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
        feed_service: FeedService = Depends(get_feed_service)
):
    """Получение категорий с количеством постов"""
    return await feed_service.get_categories()


# ============ PUBLISH ENDPOINTS ============

@feed_router.post("/projects/{project_id}/publish", response_model=ProjectFeedResponse)
async def publish_project(
        project_id: UUID = Path(..., description="ID проекта"),
        request: PublishProjectRequest = Body(..., description="Данные для публикации"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """
    Публикация проекта - создание поста и изменение статуса проекта на PUBLISHED.

    - **media_file_ids**: список ID файлов для отображения в посте
    - **description**: описание поста
    - **github_links**: ссылки на GitHub репозитории
    - Проект становится видимым в ленте
    - Нельзя опубликовать уже опубликованный проект
    """
    return await feed_service.publish_project(project_id, request)


@feed_router.post("/projects/{project_id}/unpublish", response_model=dict)
async def unpublish_project(
        project_id: UUID = Path(..., description="ID проекта"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """
    Снятие проекта с публикации - удаление поста и изменение статуса на ACTIVE.

    - Проект становится невидимым в ленте
    - Все лайки, комментарии и связи с файлами удаляются
    """
    return await feed_service.unpublish_project(project_id)


@feed_router.put("/projects/{project_id}/post", response_model=ProjectFeedResponse)
async def update_post(
        project_id: UUID = Path(..., description="ID проекта"),
        request: PublishProjectRequest = Body(..., description="Данные для обновления"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """
    Обновление существующего поста (только для опубликованных проектов).

    - Можно обновить описание, github_links и медиафайлы
    - Если media_file_ids передан, файлы полностью заменяются
    """
    return await feed_service.update_post(project_id, request)


# ============ COMMENTS ENDPOINTS ============

@feed_router.get("/posts/{post_id}/comments", response_model=CommentsResponse)
async def get_post_comments(
        post_id: UUID = Path(..., description="ID поста"),
        limit: int = Query(20, ge=1, le=100, description="Количество комментариев"),
        offset: int = Query(0, ge=0, description="Смещение для пагинации"),
        parent_id: Optional[int] = Query(None, description="ID родительского комментария (для ответов)"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Получение комментариев поста"""
    return await feed_service.get_post_comments(
        post_id=post_id,
        limit=limit,
        offset=offset,
        parent_id=parent_id
    )


@feed_router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
        post_id: UUID = Path(..., description="ID поста"),
        request: CommentCreateRequest = Body(..., description="Данные комментария"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Создание комментария"""
    return await feed_service.create_comment(post_id, request)


@feed_router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
        comment_id: int = Path(..., description="ID комментария"),
        request: CommentUpdateRequest = Body(..., description="Обновленный текст"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Обновление комментария"""
    return await feed_service.update_comment(comment_id, request)


@feed_router.delete("/comments/{comment_id}", response_model=dict)
async def delete_comment(
        comment_id: int = Path(..., description="ID комментария"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Удаление комментария"""
    return await feed_service.delete_comment(comment_id)


@feed_router.post("/comments/{comment_id}/like", response_model=CommentLikeResponse)
async def like_comment(
        comment_id: int = Path(..., description="ID комментария"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Лайкнуть комментарий"""
    return await feed_service.like_comment(comment_id)


@feed_router.delete("/comments/{comment_id}/like", response_model=CommentLikeResponse)
async def unlike_comment(
        comment_id: int = Path(..., description="ID комментария"),
        feed_service: FeedService = Depends(get_feed_service)
):
    """Убрать лайк с комментария"""
    return await feed_service.unlike_comment(comment_id)