import os
from pathlib import Path

BASE_URL = "http://localhost:8000"  # Замените на ваш URL
TEST_EMAIL = "alex.ivanov1985@gmail.com"  # Замените на реальный тестовый email
TEST_PASSWORD = "12345"  # Замените на реальный тестовый пароль
SECOND_TEST_EMAIL = "maria.petrova92@yahoo.com"
SECOND_TEST_PASSWORD = "12345"
THIRD_TEST_EMAIL = "sergio.reyes@outlook.com"
THIRD_TEST_PASSWORD = "12345"

# Получаем путь к директории с тестом
TEST_DIR = Path(__file__).parent

TEST_AVATAR_PATH = str(TEST_DIR / "ava.jpg")
TEST_PROJECT_FILE_PATH = str(TEST_DIR / "document.pdf")
TEST_COMMENT_FILE_PATH = str(TEST_DIR / "document.pdf")