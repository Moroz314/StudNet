from typing import Dict, Any, Optional, List
from .base import BaseAPIClient


class StatisticsClientMixin:
    """Миксин для работы со статистикой задач"""

    def get_workspace_statistics(
            self: BaseAPIClient,
            workspace_id: str,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получает статистику рабочего пространства

        GET /workspaces/{workspace_id}/tasks/statistics/current
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        response = self.client.get(
            f"/workspaces/{workspace_id}/tasks/statistics/current",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get statistics failed: {response.text}"
        return response.json()

    def get_statistics_history(self: BaseAPIClient, workspace_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Получает историю статистики рабочего пространства

        GET /workspaces/{workspace_id}/tasks/statistics/history
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/workspaces/{workspace_id}/tasks/statistics/history",
            params={"days": days},
            headers=headers
        )
        assert response.status_code == 200, f"Get statistics history failed: {response.text}"
        return response.json()

    def get_upcoming_deadlines(self: BaseAPIClient, workspace_id: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Получает предстоящие дедлайны

        GET /workspaces/{workspace_id}/tasks/upcoming-deadlines
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(
            f"/workspaces/{workspace_id}/tasks/upcoming-deadlines",
            params={"days_ahead": days_ahead},
            headers=headers
        )
        assert response.status_code == 200, f"Get upcoming deadlines failed: {response.text}"
        return response.json()