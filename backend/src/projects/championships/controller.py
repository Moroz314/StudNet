from fastapi import APIRouter, Depends, HTTPException, Query, status
from uuid import UUID
from typing import List, Optional
from .schemas import *
from .service import ChampionshipService, get_championship_service

championship_router = APIRouter(prefix="/championships", tags=["championships"])


@championship_router.post(
    "/",
    response_model=ChampionshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Championship",
    description="Создание нового кейс-чемпионата"
)
async def create_championship(
        data: ChampionshipCreateRequest,
        service: ChampionshipService = Depends(get_championship_service)
):
    """Создание нового чемпионата"""
    return await service.create_championship(data)


@championship_router.get(
    "/",
    response_model=ChampionshipsListResponse,
    summary="Get Championships",
    description="Получение списка чемпионатов с фильтрацией"
)
async def get_championships(
        status: Optional[str] = Query(None, description="Фильтр по статусу"),
        search: Optional[str] = Query(None, description="Поиск по названию и описанию"),
        limit: int = Query(20, ge=1, le=100, description="Лимит на странице"),
        offset: int = Query(0, ge=0, description="Смещение"),
        service: ChampionshipService = Depends(get_championship_service)
):
    """Получение списка чемпионатов"""
    championships = await service.get_championships(
        status=status,
        search=search,
        limit=limit,
        offset=offset
    )

    return ChampionshipsListResponse(
        items=championships,
        total=len(championships),
        limit=limit,
        offset=offset
    )


@championship_router.get(
    "/{championship_id}",
    response_model=ChampionshipResponse,
    summary="Get Championship",
    description="Получение чемпионата по ID"
)
async def get_championship(
        championship_id: UUID,
        service: ChampionshipService = Depends(get_championship_service)
):
    """Получение чемпионата по ID"""
    return await service.get_championship(championship_id)


@championship_router.patch(
    "/{championship_id}",
    response_model=ChampionshipResponse,
    summary="Update Championship",
    description="Обновление чемпионата (только для создателя)"
)
async def update_championship(
        championship_id: UUID,
        data: ChampionshipUpdateRequest,
        service: ChampionshipService = Depends(get_championship_service)
):
    """Обновление чемпионата"""
    return await service.update_championship(championship_id, data)


@championship_router.delete(
    "/{championship_id}",
    response_model=dict,
    summary="Delete Championship",
    description="Удаление чемпионата (только для создателя, только inactive/completed)"
)
async def delete_championship(
    championship_id: UUID,
    service: ChampionshipService = Depends(get_championship_service)
):
    """Удаление чемпионата"""
    return await service.delete_championship(championship_id)


@championship_router.get(
    "/{championship_id}/solutions",
    response_model=SolutionsListResponse,
    summary="Get Championship Solutions",
    description="Получение решений чемпионата"
)
async def get_solutions(
        championship_id: UUID,
        service: ChampionshipService = Depends(get_championship_service)
):
    """Получение решений чемпионата"""
    solutions = await service.get_solutions(championship_id)
    return SolutionsListResponse(
        items=solutions,
        total=len(solutions)
    )


@championship_router.post(
    "/{championship_id}/solutions",
    response_model=SolutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Solution",
    description="Отправка решения на чемпионат"
)
async def submit_solution(
        championship_id: UUID,
        data: SubmitSolutionRequest,
        service: ChampionshipService = Depends(get_championship_service)
):
    """Отправка решения на чемпионат"""
    return await service.submit_solution(championship_id, data.project_id)


@championship_router.post(
    "/{championship_id}/select-winners",
    response_model=ChampionshipResponse,
    summary="Select Winners",
    description="Выбор победителей чемпионата (только для создателя)"
)
async def select_winners(
        championship_id: UUID,
        data: SelectWinnersRequest,
        service: ChampionshipService = Depends(get_championship_service)
):
    """Выбор победителей чемпионата"""
    return await service.select_winners(championship_id, data.winner_solution_ids)


@championship_router.get(
    "/my/solutions",
    response_model=SolutionsListResponse,
    summary="Get My Solutions",
    description="Получение моих решений на чемпионаты"
)
async def get_my_solutions(
    limit: int = Query(20, ge=1, le=100, description="Лимит на странице"),
    offset: int = Query(0, ge=0, description="Смещение"),
    service: ChampionshipService = Depends(get_championship_service)
):
    """Получение решений текущего пользователя"""
    solutions = await service.get_my_solutions(limit=limit, offset=offset)
    return SolutionsListResponse(
        items=solutions,
        total=len(solutions)
    )


@championship_router.get(
    "/my/championships",
    response_model=ChampionshipsListResponse,
    summary="Get My Championships",
    description="Получение моих чемпионатов (созданных мной)"
)
async def get_my_championships(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    limit: int = Query(20, ge=1, le=100, description="Лимит на странице"),
    offset: int = Query(0, ge=0, description="Смещение"),
    service: ChampionshipService = Depends(get_championship_service)
):
    """Получение чемпионатов текущего пользователя"""
    championships = await service.get_my_championships(
        status=status,
        limit=limit,
        offset=offset
    )
    return ChampionshipsListResponse(
        items=championships,
        total=len(championships),
        limit=limit,
        offset=offset
    )