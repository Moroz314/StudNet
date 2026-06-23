import os
import sys
import pytest
from pathlib import Path
from config import BASE_URL, TEST_EMAIL, TEST_AVATAR_PATH, TEST_PROJECT_FILE_PATH


# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    print("=" * 60)
    print("ЗАПУСК ТЕСТОВ API ПРОЕКТОВ")
    print("=" * 60)
    print(f"API URL: {BASE_URL}")
    print(f"Тестовый пользователь: {TEST_EMAIL}")
    print(f"Файл аватарки: {TEST_AVATAR_PATH}")
    print(f"Файл проекта: {TEST_PROJECT_FILE_PATH}")
    print("=" * 60)
    print()

    # Запуск тестов через pytest
    pytest.main([
        "-v",
        "-s",
        "--tb=short",
        "--strict-markers",
        Path(__file__).parent
    ])