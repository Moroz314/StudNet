from fastapi import APIRouter, Depends, HTTPException, Query, status
from .service import get_user_feed_service, FeedService
from .schemas import *
from ..auth.service.utils import verify_token

user_feed_router = APIRouter()


@user_feed_router.get("/feed/users", response_model=UserFeedResponse)
def get_user_feed(
        query: UserFeedQuery,
        service: FeedService = Depends(get_user_feed_service),
        user_id=Depends(verify_token)
):
    try:
        return service.get_user_feed(query)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении ленты пользователей: {str(e)}"
        )


@user_feed_router.get("/search/users", response_model=UserFeedResponse)
async def search_users(  # 1. Добавили async
        q: str = Query(..., min_length=1, max_length=100, description="Поисковый запрос"),
        page: int = Query(1, ge=1, description="Номер страницы"),
        page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
        service: FeedService = Depends(get_user_feed_service),
        user_id=Depends(verify_token)
):
    try:
        query = SearchUsersQuery(
            query=q,
            page=page,
            page_size=page_size
        )

        # 2. Добавили await
        return await service.search_users(query) 
        
    except Exception as e:
        # Рекомендую также логировать ошибку в консоль сервера, 
        # чтобы видеть реальную причину, если await не поможет
        print(f"Error: {e}") 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при поиске пользователей: {str(e)}"
        )
