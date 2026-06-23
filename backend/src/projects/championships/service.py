from ...database.repositories.project.championships import ChampionshipRepository
from ...database.repositories.files import FileRepository
from ...database.repositories.project.core import ProjectRepository
from ..files.service import FileService
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from ...users.auth.service.utils import verify_token
from ...database.core import get_db
from ...database.models import *
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import aiohttp
from urllib.parse import urlencode
from tonsdk.utils import Address as TONAddress, bytes_to_b64str
from tonsdk.boc import begin_cell, Cell
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from .schemas import *
from ..validation import require_project_admin, require_project_owner


class ContractClient:
    """Клиент для работы с TON контрактом MasterChallenge"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or "your_api_key_here"
        self.toncenter_url = "https://testnet.toncenter.com/api/v2/jsonRPC"
        self.contract_address = "kQBAK6X6mM5aOGp4lwG3pfVO6fhMzjqoG9XhQOKSHr9JqeUA"

        # Коды операций контракта
        self.OP_CREATE_CHALLENGE = 0x4c474f50
        self.OP_SELECT_WINNER = 0x5f57494e
        self.OP_CLAIM_REWARD = 0x636c6169

    async def _ton_request(self, method: str, params: dict) -> dict:
        """Базовый запрос к TonCenter API"""
        url = f"{self.toncenter_url}?{urlencode({'api_key': self.api_key})}"
        payload = {"id": 1, "jsonrpc": "2.0", "method": method, "params": params}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json()

    async def get_balance(self, address: str) -> float:
        """Получение баланса кошелька"""
        result = await self._ton_request("getAddressInformation", {"address": address})
        return int(result["result"]["balance"]) / 1_000_000_000 if result.get("ok") else 0

    async def get_challenges_count(self) -> int:
        """Получение количества челленджей в контракте"""
        result = await self._ton_request("runGetMethod", {
            "address": self.contract_address,
            "method": "challengesCount",
            "stack": []
        })
        if result.get("ok") and result["result"].get("stack"):
            return int(result["result"]["stack"][0][1], 16)
        return 0

    def build_create_challenge_body(
            self,
            creator_address: str,
            deadline: datetime
    ) -> Cell:
        """
        Создание тела сообщения для создания челленджа

        Сообщение CreateChallenge в Tact:
        - deadline: Int (Unix timestamp)
        - creator: Address
        """
        deadline_timestamp = int(deadline.timestamp())

        return (
            begin_cell()
            .store_uint(self.OP_CREATE_CHALLENGE, 32)
            .store_uint(0, 64)  # query_id
            .store_uint(deadline_timestamp, 32)
            .store_address(TONAddress(creator_address))
            .end_cell()
        )

    def build_select_winner_body(
            self,
            challenge_id: int,
            creator_address: str,
            winner_address: str
    ) -> Cell:
        """
        Создание тела сообщения для выбора победителя

        Сообщение SelectWinner в Tact:
        - challengeId: Int
        - winner: Address
        - creator: Address
        """
        return (
            begin_cell()
            .store_uint(self.OP_SELECT_WINNER, 32)
            .store_uint(0, 64)  # query_id
            .store_uint(challenge_id, 32)
            .store_address(TONAddress(winner_address))
            .store_address(TONAddress(creator_address))
            .end_cell()
        )

    def build_claim_reward_body(self, challenge_id: int) -> Cell:
        """
        Создание тела сообщения для получения награды

        Сообщение ClaimReward в Tact:
        - challengeId: Int
        """
        return (
            begin_cell()
            .store_uint(self.OP_CLAIM_REWARD, 32)
            .store_uint(0, 64)  # query_id
            .store_uint(challenge_id, 32)
            .end_cell()
        )

    async def verify_payment(
            self,
            challenge_id: int,
            expected_amount: int,
            sender_address: str
    ) -> bool:
        """
        Проверка, что средства поступили в контракт

        Args:
            challenge_id: ID челленджа
            expected_amount: Ожидаемая сумма в нанотонах
            sender_address: Адрес отправителя

        Returns:
            bool: True если средства поступили
        """
        # TODO: Реализовать проверку через get-метод контракта
        # Пока не реализовано, так как контракт дорабатывается
        return True

    async def check_challenge_exists(self, challenge_id: int) -> bool:
        """Проверка существования челленджа в контракте"""
        result = await self._ton_request("runGetMethod", {
            "address": self.contract_address,
            "method": "getChallenge",
            "stack": [["num", hex(challenge_id)]]
        })

        if result.get("ok") and result["result"].get("stack"):
            return result["result"]["stack"][0][0] != "null"
        return False


class ChampionshipService:
    def __init__(
            self,
            champ_repo: ChampionshipRepository,
            file_service: FileService,
            file_repo: FileRepository,
            project_repo: ProjectRepository,
            user_id: int
    ):
        self.champ_repo = champ_repo
        self.file_service = file_service
        self.file_repo = file_repo
        self.project_repo = project_repo
        self.user_id = user_id
        self.contract_client = ContractClient()

    async def create_championship(
            self,
            data: ChampionshipCreateRequest
    ) -> ChampionshipResponse:
        """
        Создание нового чемпионата

        Steps:
        1. Валидация входных данных
        2. Валидация файлов (если есть)
        3. Валидация проекта-организатора (если указан)
        4. Создание чемпионата в БД
        5. Привязка файлов
        """
        # Валидация распределения призов
        if sum(data.prize_distribution) != data.prize_amount:
            raise HTTPException(
                status_code=400,
                detail="Sum of prize distribution must equal prize_amount"
            )

        if len(data.prize_distribution) != data.max_winners:
            raise HTTPException(
                status_code=400,
                detail="Prize distribution length must equal max_winners"
            )

        # Валидация дедлайна
        if data.deadline <= datetime.now():
            raise HTTPException(
                status_code=400,
                detail="Deadline must be in the future"
            )

        # Валидация файлов
        if data.file_ids:
            validated_files = await self.file_service.validate_files_batch(
                file_ids=data.file_ids,
                file_type=FileType.CHAMPIONSHIP_FILE,
                user_id=self.user_id
            )
            data.file_ids = validated_files

        # Валидация проекта-организатора
        if data.organizer_project_id:
            project = self.project_repo.get_project_by_id(data.organizer_project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Organizer project not found")

            # Проверяем права на проект
            require_project_owner(
                self.project_repo,
                data.organizer_project_id,
                self.user_id
            )


        # Создаем чемпионат
        championship = self.champ_repo.create_championship(
            title=data.title,
            description=data.description,
            created_by=self.user_id,
            max_winners=data.max_winners,
            max_participants=data.max_participants,
            prize_amount=data.prize_amount,
            prize_distribution=data.prize_distribution,
            deadline=data.deadline,
            organizer_project_id=data.organizer_project_id
        )

        # Привязываем файлы
        if data.file_ids:
            self.file_repo.attach_files_to_championship(
                championship_id=championship.id,
                file_ids=data.file_ids
            )

        # Получаем созданный чемпионат с отношениями
        championship = self.champ_repo.get_championship_by_id(
            championship.id,
            include_relations=True
        )

        return await self._format_championship_response(championship)

    async def get_championship(
            self,
            championship_id: UUID
    ) -> ChampionshipResponse:
        """Получение чемпионата по ID"""
        championship = self.champ_repo.get_championship_by_id(
            championship_id,
            include_relations=True
        )

        if not championship:
            raise HTTPException(status_code=404, detail="Championship not found")

        return await self._format_championship_response(championship)

    async def get_championships(
            self,
            status: Optional[str] = None,
            search: Optional[str] = None,
            limit: int = 20,
            offset: int = 0
    ) -> List[ChampionshipResponse]:
        """Получение списка чемпионатов"""
        filters = {}
        if status:
            filters['status'] = status
        if search:
            filters['search'] = search
        filters['limit'] = limit
        filters['offset'] = offset

        championships = self.champ_repo.get_championships(
            filters=filters,
            include_relations=True
        )

        return [await self._format_championship_response(c) for c in championships]

    async def submit_solution(
            self,
            championship_id: UUID,
            project_id: UUID
    ) -> SolutionResponse:
        """
        Отправка решения на чемпионат
        """
        # Валидация чемпионата
        championship = self.champ_repo.get_championship_by_id(championship_id)
        if not championship:
            raise HTTPException(status_code=404, detail="Championship not found")

        if championship.status != "active":
            raise HTTPException(status_code=400, detail="Championship is not active")

        if datetime.now() > championship.deadline:
            raise HTTPException(status_code=400, detail="Championship deadline has passed")

        # Валидация проекта
        project = self.project_repo.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # # if not project.wallet_id:
        #     raise HTTPException(
        #         status_code=400,
        #         detail="Project must have wallet_id set for championship participation"
        #     )

        require_project_admin(
            self.project_repo,
            project_id,
            self.user_id
        )

        # Создаем решение
        solution = self.champ_repo.submit_solution(
            championship_id=championship_id,
            project_id=project_id,
            user_id=self.user_id
        )

        # Добавляем организатора как viewer в проект (и автоматически во все workspace)
        self.project_repo.add_user_to_project(
            project_id=project_id,
            user_id=championship.created_by,
            status=ProjectParticipantStatus.VIEWER.value,
            role=ProjectRole.OTHER.value
        )

        # Получаем решение с отношениями
        solution = self.champ_repo.get_solution_by_id(
            solution.id,
            include_relations=True
        )

        return self._format_solution_response(solution)

    async def get_solutions(
            self,
            championship_id: UUID
    ) -> List[SolutionResponse]:
        """Получение решений чемпионата"""
        championship = self.champ_repo.get_championship_by_id(championship_id)
        if not championship:
            raise HTTPException(status_code=404, detail="Championship not found")

        solutions = self.champ_repo.get_solutions(
            championship_id=championship_id,
            include_relations=True
        )

        return [self._format_solution_response(s) for s in solutions]

    async def update_championship(
            self,
            championship_id: UUID,
            data: ChampionshipUpdateRequest
    ) -> ChampionshipResponse:
        """Обновление чемпионата"""
        championship = self.champ_repo.get_championship_by_id(championship_id)
        if not championship:
            raise HTTPException(status_code=404, detail="Championship not found")

        if championship.created_by != self.user_id:
            raise HTTPException(status_code=403, detail="Only creator can update championship")

        if championship.status != "inactive":
            raise HTTPException(status_code=400, detail="Can only update inactive championships")

        update_data = data.model_dump(exclude_unset=True)

        # Валидация файлов если указаны
        if 'file_ids' in update_data and update_data['file_ids']:
            validated_files = await self.file_service.validate_files_batch(
                file_ids=update_data['file_ids'],
                file_type=FileType.CHAMPIONSHIP_FILE,
                user_id=self.user_id
            )
            update_data['file_ids'] = validated_files

            # Обновляем файлы
            self.file_repo.detach_files_from_championship(championship_id)
            self.file_repo.attach_files_to_championship(
                championship_id=championship_id,
                file_ids=validated_files
            )
            del update_data['file_ids']

        championship = self.champ_repo.update_championship(
            championship_id=championship_id,
            **update_data
        )

        championship = self.champ_repo.get_championship_by_id(
            championship_id,
            include_relations=True
        )

        return await self._format_championship_response(championship)

    async def select_winners(
            self,
            championship_id: UUID,
            winner_solution_ids: List[UUID]
    ) -> ChampionshipResponse:
        """Выбор победителей чемпионата"""
        championship = self.champ_repo.get_championship_by_id(championship_id)
        if not championship:
            raise HTTPException(status_code=404, detail="Championship not found")

        if championship.created_by != self.user_id:
            raise HTTPException(status_code=403, detail="Only creator can select winners")

        if championship.status != "active":
            raise HTTPException(status_code=400, detail="Championship must be active")

        if len(winner_solution_ids) > championship.max_winners:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum winners: {championship.max_winners}"
            )

        solutions = self.champ_repo.get_solutions(championship_id)
        solution_ids = {s.id for s in solutions}

        for winner_id in winner_solution_ids:
            if winner_id not in solution_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"Solution {winner_id} not found in championship"
                )

        # Назначаем места победителям
        for place, solution_id in enumerate(winner_solution_ids, 1):
            self.champ_repo.update_solution(
                solution_id=solution_id,
                status="winner",
                place=place
            )

        # Обновляем статус чемпионата
        self.champ_repo.update_championship(
            championship_id=championship_id,
            status="completed"
        )

        championship = self.champ_repo.get_championship_by_id(
            championship_id,
            include_relations=True
        )

        return await self._format_championship_response(championship)

    async def delete_championship(
            self,
            championship_id: UUID
    ) -> Dict[str, str]:
        """Удаление чемпионата (только создатель и только inactive)"""
        championship = self.champ_repo.get_championship_by_id(championship_id)

        if not championship:
            raise HTTPException(status_code=404, detail="Championship not found")

        if championship.created_by != self.user_id:
            raise HTTPException(status_code=403, detail="Only creator can delete championship")

        if championship.status not in ["inactive", "completed"]:
            raise HTTPException(
                status_code=400,
                detail="Can only delete inactive or completed championships"
            )

        success = self.champ_repo.delete_championship(championship_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete championship")

        return {"message": "Championship deleted successfully", "championship_id": str(championship_id)}

    async def get_my_championships(
            self,
            status: Optional[str] = None,
            limit: int = 20,
            offset: int = 0
    ) -> List[ChampionshipResponse]:
        """Получение моих чемпионатов (созданных текущим пользователем)"""
        filters = {"created_by": self.user_id}
        if status:
            filters['status'] = status
        filters['limit'] = limit
        filters['offset'] = offset

        championships = self.champ_repo.get_championships(
            filters=filters,
            include_relations=True
        )

        return [await self._format_championship_response(c) for c in championships]

    async def get_my_solutions(
            self,
            limit: int = 20,
            offset: int = 0
    ) -> List[SolutionResponse]:
        """Получение моих решений (отправленных текущим пользователем)"""
        solutions = self.champ_repo.get_user_solutions(
            user_id=self.user_id,
            include_relations=True
        )

        return [self._format_solution_response(s) for s in solutions][offset:offset + limit]

    async def _format_championship_response(self, championship: Championship) -> ChampionshipResponse:
        """Форматирование ответа чемпионата"""
        # Получаем URLs для файлов
        file_ids = [f.file_id for f in championship.championship_files]
        file_urls = await self.file_service.get_file_urls_batch(file_ids, self.user_id)

        # Формируем список файлов с URLs
        files = [
            FileResponse(
                id=f.file.id,
                url=file_urls.get(f.file_id),
                original_filename=f.file.original_filename,
                mime_type=f.file.mime_type,
                size_bytes=f.file.size_bytes
            )
            for f in championship.championship_files
            if f.file
        ]

        return ChampionshipResponse(
            id=championship.id,
            title=championship.title,
            description=championship.description,
            status=championship.status,
            max_winners=championship.max_winners,
            max_participants=championship.max_participants,
            prize_amount=championship.prize_amount,
            prize_distribution=championship.prize_distribution,
            created_by=championship.created_by,
            organizer_project_id=championship.organizer_project_id,
            deadline=championship.deadline,
            created_at=championship.created_at,
            updated_at=championship.updated_at,
            solutions_count=len(championship.solutions),
            creator=CreatorResponse(
                user_id=championship.creator.user_id,
                name=championship.creator.name,
                lastname=championship.creator.lastname,
                username=championship.creator.username,
                avatar_url=championship.creator.avatar_url
            ) if championship.creator else None,
            files=files
        )

    def _format_solution_response(self, solution: ChampionshipSolution) -> SolutionResponse:
        """Форматирование ответа решения"""
        return SolutionResponse(
            id=solution.id,
            championship_id=solution.championship_id,
            project_id=solution.project_id,
            submitted_by=solution.submitted_by,
            status=solution.status,
            place=solution.place,
            created_at=solution.created_at,
            updated_at=solution.updated_at,
            project_name=solution.project.name if solution.project else None,
            submitter_name=f"{solution.submitter.name} {solution.submitter.lastname}" if solution.submitter else None
        )


# dependency
def get_championship_service(
        db: Session = Depends(get_db),
        user_id: int = Depends(verify_token)
) -> ChampionshipService:
    champ_repo = ChampionshipRepository(db)
    file_service = FileService(session=db)
    file_repo = FileRepository(session=db)
    project_repo = ProjectRepository(session=db)

    return ChampionshipService(
        champ_repo=champ_repo,
        file_service=file_service,
        file_repo=file_repo,
        project_repo=project_repo,
        user_id=user_id
    )