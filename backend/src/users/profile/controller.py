from starlette.responses import JSONResponse
from .service import *
from .schemas import *

from fastapi import APIRouter, Depends, status, File, UploadFile, Query

profile_router = APIRouter(tags=["profile"])


@profile_router.post("/user/profile",
                     response_model=UserProfile,
                     status_code=status.HTTP_201_CREATED,
                     description="Создание профиля пользователя.")
async def create_profile(
        data: UserProfileCreate,
        service: ProfileService = Depends(get_profile_service)
) -> UserProfile:
    response = await service.create_profile(data)
    return response


@profile_router.get("/user/profile/personal",
                    response_model=UserProfile,
                    status_code=status.HTTP_200_OK,
                    description="Получение личного профиля пользователя."
                    )
async def get_personal_user_profile(
        service: ProfileService = Depends(get_profile_service)
) -> UserProfile:
    profile = await service.get_personal_profile()
    return profile


@profile_router.get(
    "/user/profile",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    description="Получение профиля пользователя по id."
)
async def get_user_profile(
        user_id: int = Query(..., description="ID пользователя"),
        service: ProfileService = Depends(get_profile_service)
):
    profile = await service.get_user_profile(user_id=user_id)
    return profile


@profile_router.get(
    "/user/profile/projects",
    response_model=UserProfileProjectsResponse,
    status_code=status.HTTP_200_OK,
    description="Проекты пользователя для просмотра на странице профиля."
)
async def get_user_profile_projects(
        user_id: int = Query(..., description="ID пользователя"),
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        service: ProfileService = Depends(get_profile_service)
):
    return await service.get_user_profile_projects(
        user_id=user_id,
        offset=offset,
        limit=limit
    )


@profile_router.put("/user/profile",
                    response_model=UserProfile,
                    status_code=status.HTTP_200_OK,
                    description="Редактирование профиля пользователя(кроме аватарки).")
async def edit_profile(
        data: UserProfileEdit,
        service: ProfileService = Depends(get_profile_service)
) -> UserProfile:
    response = await service.edit_profile(data)
    return response


@profile_router.delete("/user/profile",
                       status_code=status.HTTP_200_OK,
                       description="Удаление профиля пользователя.")
async def delete_profile(
        service: ProfileService = Depends(get_profile_service)
):
    response = await service.delete_profile()

    if response:
        return JSONResponse(
            content={'message': 'Профиль успешно удалён'}
        )


@profile_router.post(
    "/user/avatar",
    response_model=AvatarResponse,
    status_code=status.HTTP_200_OK,
    description="Загрузка аватарки пользователя."
)
async def upload_avatar(
        avatar: UploadFile = File(..., description="Изображение для аватара"),
        description: str = Query(None, description="Описание аватарки"),
        service: ProfileService = Depends(get_profile_service)
):
    """
    Загрузка аватарки пользователя.

    - Поддерживаемые форматы: JPEG, PNG, GIF, WebP
    - Максимальный размер: 5MB
    - Старая аватарка автоматически удаляется
    """
    response = await service.upload_avatar(file=avatar, description=description)
    return response


@profile_router.delete(
    "/user/avatar",
    response_model=DeleteAvatarResponse,
    status_code=status.HTTP_200_OK,
    description="Удаление аватарки пользователя."
)
async def delete_avatar(
        service: ProfileService = Depends(get_profile_service)
):
    response = await service.delete_avatar()
    return response


@profile_router.get(
    "/user/avatar/url",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    description="Получение URL аватарки пользователя."
)
async def get_avatar_url(
        service: ProfileService = Depends(get_profile_service)
):
    url = await service.get_avatar_url()
    if url is None:
        return {"avatar_url": None, "message": "Avatar not found"}
    return {"avatar_url": url}