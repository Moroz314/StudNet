from datetime import datetime, timedelta
import pytest
from .fixtures import *

class TestCompleteProjectWithTasks:
    """Комплексный тест: проект -> workspace -> задачи -> комментарии -> статистика"""

    def test_complete_project_tasks_flow(self, authenticated_client, sample_project_data):
        """Полный тест workflow: проект, задачи, комментарии, статистика"""
        print("\n=== Запуск комплексного теста Project + Tasks ===\n")

        # 1. Создаем проект
        project = authenticated_client.create_project(sample_project_data)
        project_id = project["id"]
        print(f"✓ Создан проект: {project['name']} (ID: {project_id})")

        # 2. Создаем рабочее пространство
        workspace_data = {
            "name": "Development Workspace",
            "description": "Рабочее пространство для разработки",
            "create_chat": True
        }
        workspace = authenticated_client.create_workspace(project_id, workspace_data)
        workspace_id = workspace["id"]
        print(f"✓ Создано рабочее пространство: {workspace['name']} (ID: {workspace_id})")

        # 3. Создаем различные типы задач
        tasks = []

        # Обычная задача
        task1_data = {
            "title": "Implement API endpoints",
            "description": "Разработать REST API для управления проектами",
            "task_type": "task",
            "priority": "high",
            "deadline": (datetime.now() + timedelta(days=3)).isoformat(),
            "estimated_hours": 16
        }
        task1 = authenticated_client.create_task(workspace_id, task1_data)
        tasks.append(task1)
        print(f"✓ Создана задача: {task1['title']} (приоритет: {task1['priority']})")

        # Идея
        task2_data = {
            "title": "AI integration",
            "description": "Добавить поддержку AI для автоматизации",
            "task_type": "idea",
            "priority": "low"
        }
        task2 = authenticated_client.create_task(workspace_id, task2_data)
        tasks.append(task2)
        print(f"✓ Создана идея: {task2['title']} (статус: {task2['status']})")

        # Срочная задача
        task3_data = {
            "title": "Fix critical bug",
            "description": "Исправить критическую ошибку в продакшене",
            "task_type": "urgent_task",
            "priority": "urgent",
            "deadline": (datetime.now() + timedelta(hours=12)).isoformat(),
            "estimated_hours": 2
        }
        task3 = authenticated_client.create_task(workspace_id, task3_data)
        tasks.append(task3)
        print(f"✓ Создана срочная задача: {task3['title']}")

        # 4. Добавляем комментарии к задачам
        for task in tasks[:2]:
            comment_data = {
                "content": f"Обсуждение задачи: {task['title']}",
                "file_ids": []
            }
            comment = authenticated_client.create_task_comment(workspace_id, task["id"], comment_data)
            print(f"✓ Добавлен комментарий к задаче {task['id'][:8]}...")

        # 5. Обновляем статус задачи
        authenticated_client.update_task(
            workspace_id,
            task1["id"],
            {"status": "in_progress", "actual_hours": 4}
        )
        print(f"✓ Обновлен статус задачи {task1['id'][:8]}... → in_progress")

        # 6. Получаем статистику рабочего пространства
        statistics = authenticated_client.get_workspace_statistics(workspace_id)
        print(f"✓ Получена статистика:")
        print(f"  - Всего задач: {statistics['total_tasks']}")
        print(f"  - Срочных задач: {statistics['urgent_tasks']}")
        print(f"  - Просроченных задач: {statistics['overdue_tasks']}")

        # 7. Получаем предстоящие дедлайны
        deadlines = authenticated_client.get_upcoming_deadlines(workspace_id, days_ahead=7)
        print(f"✓ Найдено предстоящих дедлайнов: {len(deadlines)}")

        # Проверки
        assert len(tasks) == 3
        assert statistics["total_tasks"] >= 3
        assert statistics["urgent_tasks"] >= 1

        print("\n✓ Комплексный тест успешно завершен!\n")