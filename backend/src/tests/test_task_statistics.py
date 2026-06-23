from datetime import datetime, timedelta
import pytest
from .fixtures import *


class TestTaskStatistics:
    """Тесты для статистики задач"""

    def test_get_workspace_statistics(self, authenticated_client, project_with_owner, created_workspace):
        """Тест получения статистики рабочего пространства"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        statistics = authenticated_client.get_workspace_statistics(project_id, workspace_id)

        assert "total_tasks" in statistics
        assert "status_distribution" in statistics
        assert "type_distribution" in statistics
        assert "priority_distribution" in statistics
        assert "completion_rate" in statistics
        assert "tasks_created_today" in statistics

        print(f"✓ Получена статистика, всего задач: {statistics['total_tasks']}")

    def test_get_statistics_history(self, authenticated_client, project_with_owner, created_workspace):
        """Тест получения истории статистики"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        history = authenticated_client.get_statistics_history(project_id, workspace_id, days=7)

        assert isinstance(history, list)
        if len(history) > 0:
            item = history[0]
            assert "date" in item
            assert "total_tasks" in item
            assert "tasks_created" in item

    def test_get_upcoming_deadlines(self, authenticated_client, project_with_owner, created_workspace):
        """Тест получения предстоящих дедлайнов"""
        project_id = project_with_owner["id"]
        workspace_id = created_workspace["id"]

        deadlines = authenticated_client.get_upcoming_deadlines(project_id, workspace_id, days_ahead=7)

        assert isinstance(deadlines, list)
        if len(deadlines) > 0:
            item = deadlines[0]
            assert "id" in item
            assert "title" in item
            assert "deadline" in item
            assert "days_until_deadline" in item