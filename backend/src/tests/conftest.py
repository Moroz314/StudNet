# tests/conftest.py (дополнение)

import pytest
from .clients.extended import ExtendedAPIClient
from .config import (
    BASE_URL, TEST_EMAIL, TEST_PASSWORD,
    SECOND_TEST_EMAIL, SECOND_TEST_PASSWORD,
    THIRD_TEST_EMAIL, THIRD_TEST_PASSWORD  # Добавьте в config.py
)


@pytest.fixture(scope="session")
def api_client():
    """Фикстура для создания клиента API"""
    client = ExtendedAPIClient()
    yield client
    client.cleanup()


@pytest.fixture(scope="session")
def authenticated_client(api_client):
    """Фикстура для аутентифицированного клиента (уже аутентифицирован)"""
    return api_client


@pytest.fixture(scope="session")
def second_authenticated_client():
    """Фикстура для второго аутентифицированного клиента"""
    try:
        if not SECOND_TEST_EMAIL or not SECOND_TEST_PASSWORD:
            pytest.skip("Второй пользователь не настроен")

        client = ExtendedAPIClient()
        client.login(email=SECOND_TEST_EMAIL, password=SECOND_TEST_PASSWORD)
        yield client
        client.cleanup()
    except (ImportError, AttributeError, Exception) as e:
        pytest.skip(f"Второй пользователь не настроен: {e}")


@pytest.fixture(scope="session")
def third_authenticated_client():
    """Фикстура для третьего аутентифицированного клиента"""
    try:
        if not THIRD_TEST_EMAIL or not THIRD_TEST_PASSWORD:
            pytest.skip("Третий пользователь не настроен")

        client = ExtendedAPIClient()
        client.login(email=THIRD_TEST_EMAIL, password=THIRD_TEST_PASSWORD)
        yield client
        client.cleanup()
    except (ImportError, AttributeError, Exception) as e:
        pytest.skip(f"Третий пользователь не настроен: {e}")

@pytest.fixture(autouse=True)
def cleanup_relationships(request, multiple_users):
    """Автоматическая очистка отношений после каждого теста"""
    yield
    # Очищаем отношения для всех пользователей
    for i, user in enumerate(multiple_users):
        other_users = [u for j, u in enumerate(multiple_users) if j != i]
        other_user_ids = [u.user_id for u in other_users]
        try:
            user.cleanup_relationships(other_user_ids)
        except Exception:
            pass

@pytest.fixture
def client():
    """Фикстура для неаутентифицированного клиента"""
    client = ExtendedAPIClient()
    # Сбрасываем токен, чтобы клиент был неаутентифицированным
    client.access_token = None
    client.user_id = None
    yield client
    client.cleanup()