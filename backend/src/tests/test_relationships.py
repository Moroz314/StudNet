import pytest
from typing import Dict, Any, List
from .fixtures import *

class TestRelationships:
    """Тесты для эндпоинтов отношений между пользователями (friends/block)"""

    def test_send_friend_request(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест отправки заявки в друзья"""
        # Получаем ID второго пользователя
        second_user_id = second_authenticated_client.user_id

        # Отправляем заявку в друзья
        result = authenticated_client.send_friend_request(second_user_id)

        assert "message" in result
        assert "relationship" in result
        assert result["relationship"]["status"] == "pending"
        assert result["relationship"]["user_id"] == authenticated_client.user_id
        assert result["relationship"]["related_user_id"] == second_user_id

        # Проверяем, что заявка появилась в исходящих
        requests = authenticated_client.get_pending_requests()
        assert any(req["user_id"] == second_user_id for req in requests["outgoing"])

    def test_get_pending_requests(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест получения входящих и исходящих заявок"""
        # Получаем ID второго пользователя
        second_user_id = second_authenticated_client.user_id

        # Отправляем заявку
        authenticated_client.send_friend_request(second_user_id)

        # Получаем список заявок
        result = authenticated_client.get_pending_requests(limit=10, offset=0)

        assert "incoming" in result
        assert "outgoing" in result
        assert "incoming_total" in result
        assert "outgoing_total" in result

        # Проверяем, что исходящая заявка есть
        assert result["outgoing_total"] > 0
        assert any(
            req["user_id"] == second_user_id
            for req in result["outgoing"]
        )

    def test_cancel_friend_request(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест отмены отправленной заявки в друзья"""
        # Получаем ID второго пользователя
        second_user_id = second_authenticated_client.user_id

        # Отправляем заявку
        authenticated_client.send_friend_request(second_user_id)

        # Проверяем, что заявка есть
        requests_before = authenticated_client.get_pending_requests()
        assert any(req["user_id"] == second_user_id for req in requests_before["outgoing"])

        # Отменяем заявку
        result = authenticated_client.cancel_friend_request(second_user_id)

        assert result["success"] is True
        assert "message" in result

        # Проверяем, что заявка исчезла
        requests_after = authenticated_client.get_pending_requests()
        assert not any(req["user_id"] == second_user_id for req in requests_after["outgoing"])

    def test_cancel_nonexistent_request(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест отмены несуществующей заявки"""
        with pytest.raises(AssertionError) as excinfo:
            authenticated_client.cancel_friend_request(second_authenticated_client.user_id)
        assert "Cancel friend request failed" in str(excinfo.value)

    def test_cannot_cancel_request_sent_by_other(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест: нельзя отменить заявку, отправленную другим пользователем"""
        # Второй пользователь отправляет заявку первому
        second_authenticated_client.send_friend_request(authenticated_client.user_id)

        # Первый пытается отменить чужую заявку
        with pytest.raises(AssertionError) as excinfo:
            authenticated_client.cancel_friend_request(second_authenticated_client.user_id)
        assert "Cancel friend request failed" in str(excinfo.value)

    def test_accept_friend_request(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест принятия заявки в друзья"""
        # Получаем ID первого пользователя
        first_user_id = authenticated_client.user_id

        # Второй пользователь отправляет заявку первому
        second_authenticated_client.send_friend_request(first_user_id)

        # Первый пользователь принимает заявку
        result = authenticated_client.accept_friend_request(second_authenticated_client.user_id)

        assert result["success"] is True
        assert "message" in result

        # Проверяем статус отношений
        status = authenticated_client.get_relationship_status(second_authenticated_client.user_id)
        assert status.get("status") == "friend"

    def test_reject_friend_request(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест отклонения заявки в друзья"""
        # Получаем ID первого пользователя
        first_user_id = authenticated_client.user_id

        # Второй пользователь отправляет заявку первому
        second_authenticated_client.send_friend_request(first_user_id)

        # Первый пользователь отклоняет заявку
        result = authenticated_client.reject_friend_request(second_authenticated_client.user_id)

        assert result["success"] is True
        assert "message" in result

        # Проверяем, что заявка исчезла
        requests = authenticated_client.get_pending_requests()
        assert not any(req["user_id"] == second_authenticated_client.user_id for req in requests["incoming"])

    def test_get_friends_list(
        self,
        authenticated_client,
        second_authenticated_client,
        third_authenticated_client
    ):
        """Тест получения списка друзей"""
        # Создаем дружеские связи
        first_user_id = authenticated_client.user_id
        second_user_id = second_authenticated_client.user_id
        third_user_id = third_authenticated_client.user_id

        # Первый добавляет в друзья второго
        authenticated_client.send_friend_request(second_user_id)
        second_authenticated_client.accept_friend_request(first_user_id)

        # Первый добавляет в друзья третьего
        authenticated_client.send_friend_request(third_user_id)
        third_authenticated_client.accept_friend_request(first_user_id)

        # Получаем список друзей первого пользователя
        result = authenticated_client.get_friends(limit=10, offset=0)

        assert "items" in result
        assert "total" in result
        assert result["total"] >= 2

        # Проверяем, что оба пользователя в списке друзей
        friend_ids = [friend["user_id"] for friend in result["items"]]
        assert second_user_id in friend_ids
        assert third_user_id in friend_ids

    def test_remove_friend(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест удаления из друзей"""
        # Создаем дружескую связь
        first_user_id = authenticated_client.user_id
        second_user_id = second_authenticated_client.user_id

        # Первый добавляет в друзья второго
        authenticated_client.send_friend_request(second_user_id)
        second_authenticated_client.accept_friend_request(first_user_id)

        # Удаляем из друзей
        result = authenticated_client.remove_friend(second_user_id)

        assert result["success"] is True
        assert "message" in result

        # Проверяем, что пользователь удален из друзей
        friends_result = authenticated_client.get_friends()
        friend_ids = [friend["user_id"] for friend in friends_result["items"]]
        assert second_user_id not in friend_ids

    def test_block_user(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест блокировки пользователя"""
        # Получаем ID второго пользователя
        second_user_id = second_authenticated_client.user_id

        # Блокируем пользователя
        result = authenticated_client.block_user(second_user_id)

        assert result["success"] is True
        assert "message" in result

        # Проверяем статус отношений
        status = authenticated_client.get_relationship_status(second_user_id)
        assert status.get("status") == "blocked"

    def test_unblock_user(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест разблокировки пользователя"""
        # Получаем ID второго пользователя
        second_user_id = second_authenticated_client.user_id

        # Блокируем пользователя
        authenticated_client.block_user(second_user_id)

        # Разблокируем пользователя
        result = authenticated_client.unblock_user(second_user_id)

        assert result["success"] is True
        assert "message" in result

        # Проверяем статус отношений (должен быть None или другой статус)
        status = authenticated_client.get_relationship_status(second_user_id)
        assert status.get("status") != "blocked"

    def test_get_blocked_users(
        self,
        authenticated_client,
        second_authenticated_client,
        third_authenticated_client
    ):
        """Тест получения списка заблокированных пользователей"""
        # Получаем ID пользователей
        second_user_id = second_authenticated_client.user_id
        third_user_id = third_authenticated_client.user_id

        # Блокируем двух пользователей
        authenticated_client.block_user(second_user_id)
        authenticated_client.block_user(third_user_id)

        # Получаем список заблокированных
        result = authenticated_client.get_blocked_users(limit=10, offset=0)

        assert "items" in result
        assert "total" in result
        assert result["total"] >= 2

        # Проверяем, что оба пользователя в списке заблокированных
        blocked_ids = [user["user_id"] for user in result["items"]]
        assert second_user_id in blocked_ids
        assert third_user_id in blocked_ids

    def test_get_relationship_status(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест получения статуса отношений с пользователем"""
        # Получаем ID второго пользователя
        second_user_id = second_authenticated_client.user_id

        # Проверяем начальный статус
        initial_status = authenticated_client.get_relationship_status(second_user_id)

        # Отправляем заявку
        authenticated_client.send_friend_request(second_user_id)

        # Проверяем статус после отправки заявки
        status = authenticated_client.get_relationship_status(second_user_id)
        # Статус должен измениться (зависит от реализации API)

    def test_get_mutual_friends(
        self,
        authenticated_client,
        second_authenticated_client,
        third_authenticated_client
    ):
        """Тест получения общих друзей с пользователем"""
        # Создаем дружеские связи
        first_user_id = authenticated_client.user_id
        second_user_id = second_authenticated_client.user_id
        third_user_id = third_authenticated_client.user_id

        # Первый и второй друзья
        authenticated_client.send_friend_request(second_user_id)
        second_authenticated_client.accept_friend_request(first_user_id)

        # Первый и третий друзья
        authenticated_client.send_friend_request(third_user_id)
        third_authenticated_client.accept_friend_request(first_user_id)

        # Получаем общих друзей между вторым и третьим
        result = second_authenticated_client.get_mutual_friends(
            third_user_id,
            limit=10,
            offset=0
        )

        assert "items" in result
        assert "total" in result
        assert "count" in result

        # Проверяем, что первый пользователь есть в списке общих друзей
        if result["total"] > 0:
            mutual_ids = [friend["user_id"] for friend in result["items"]]
            assert first_user_id in mutual_ids

    def test_cannot_send_request_to_self(self, authenticated_client):
        """Тест: нельзя отправить заявку самому себе"""
        with pytest.raises(AssertionError) as excinfo:
            authenticated_client.send_friend_request(authenticated_client.user_id)
        assert "Send friend request failed" in str(excinfo.value)

    def test_cannot_send_duplicate_request(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест: нельзя отправить повторную заявку тому же пользователю"""
        second_user_id = second_authenticated_client.user_id

        # Первая заявка
        authenticated_client.send_friend_request(second_user_id)

        # Повторная заявка должна вызвать ошибку
        with pytest.raises(AssertionError) as excinfo:
            authenticated_client.send_friend_request(second_user_id)
        assert "Send friend request failed" in str(excinfo.value)

    def test_cannot_accept_nonexistent_request(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест: нельзя принять несуществующую заявку"""
        with pytest.raises(AssertionError) as excinfo:
            authenticated_client.accept_friend_request(second_authenticated_client.user_id)
        assert "Accept friend request failed" in str(excinfo.value)

    def test_cannot_block_self(self, authenticated_client):
        """Тест: нельзя заблокировать самого себя"""
        with pytest.raises(AssertionError) as excinfo:
            authenticated_client.block_user(authenticated_client.user_id)
        assert "Block user failed" in str(excinfo.value)

    def test_full_relationship_flow(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест полного цикла отношений: заявка -> принятие -> удаление -> блокировка"""
        first_user_id = authenticated_client.user_id
        second_user_id = second_authenticated_client.user_id

        # 1. Отправка заявки
        result1 = authenticated_client.send_friend_request(second_user_id)
        assert result1["relationship"]["status"] == "pending"

        # 2. Принятие заявки
        result2 = second_authenticated_client.accept_friend_request(first_user_id)
        assert result2["success"] is True

        # 3. Проверка, что они друзья
        friends_result = authenticated_client.get_friends()
        assert any(friend["user_id"] == second_user_id for friend in friends_result["items"])

        # 4. Удаление из друзей
        result3 = authenticated_client.remove_friend(second_user_id)
        assert result3["success"] is True

        # 5. Проверка, что не друзья
        friends_result2 = authenticated_client.get_friends()
        assert not any(friend["user_id"] == second_user_id for friend in friends_result2["items"])

        # 6. Блокировка
        result4 = authenticated_client.block_user(second_user_id)
        assert result4["success"] is True

        # 7. Проверка статуса
        status = authenticated_client.get_relationship_status(second_user_id)
        assert status.get("status") == "blocked"

        # 8. Разблокировка
        result5 = authenticated_client.unblock_user(second_user_id)
        assert result5["success"] is True

        # 9. Проверка, что не заблокирован
        status2 = authenticated_client.get_relationship_status(second_user_id)
        assert status2.get("status") != "blocked"


class TestRelationshipsEdgeCases:
    """Тесты для граничных случаев в отношениях"""

    def test_pagination_in_friends_list(
        self,
        authenticated_client,
        multiple_users
    ):
        """Тест пагинации в списке друзей"""
        # Добавляем нескольких друзей
        for client in multiple_users[1:3]:  # Пропускаем первого (это authenticated_client)
            user_id = client.user_id
            authenticated_client.send_friend_request(user_id)
            client.accept_friend_request(authenticated_client.user_id)

        # Проверяем пагинацию
        page1 = authenticated_client.get_friends(limit=1, offset=0)
        page2 = authenticated_client.get_friends(limit=1, offset=1)

        assert len(page1["items"]) == 1
        assert len(page2["items"]) == 1
        assert page1["items"][0]["user_id"] != page2["items"][0]["user_id"]

    def test_pagination_in_pending_requests(
        self,
        authenticated_client,
        second_authenticated_client,
        third_authenticated_client
    ):
        """Тест пагинации в списке заявок"""
        # Отправляем несколько заявок (от второго и третьего к первому)
        second_authenticated_client.send_friend_request(authenticated_client.user_id)
        third_authenticated_client.send_friend_request(authenticated_client.user_id)

        # Проверяем входящие заявки у первого с пагинацией
        requests = authenticated_client.get_pending_requests(limit=1, offset=0)

        assert len(requests["incoming"]) == 1
        assert requests["incoming_total"] >= 2

    def test_pagination_in_outgoing_requests(
        self,
        authenticated_client,
        second_authenticated_client,
        third_authenticated_client
    ):
        """Тест пагинации в исходящих заявках"""
        # Отправляем несколько исходящих заявок
        authenticated_client.send_friend_request(second_authenticated_client.user_id)
        authenticated_client.send_friend_request(third_authenticated_client.user_id)

        # Проверяем исходящие заявки с пагинацией
        requests = authenticated_client.get_pending_requests(limit=1, offset=0)

        assert len(requests["outgoing"]) == 1
        assert requests["outgoing_total"] >= 2

    def test_mutual_friends_with_no_friends(
        self,
        authenticated_client,
        second_authenticated_client,
        third_authenticated_client
    ):
        """Тест общих друзей, когда у пользователей нет общих друзей"""
        second_user_id = second_authenticated_client.user_id
        third_user_id = third_authenticated_client.user_id

        # У second и third нет общих друзей
        result = second_authenticated_client.get_mutual_friends(third_user_id)

        assert result["total"] == 0
        assert result["count"] == 0
        assert len(result["items"]) == 0

    def test_blocked_user_cannot_send_request(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест: заблокированный пользователь не может отправить заявку"""
        second_user_id = second_authenticated_client.user_id

        # Первый блокирует второго
        authenticated_client.block_user(second_user_id)

        # Второй пытается отправить заявку первому
        with pytest.raises(AssertionError) as excinfo:
            second_authenticated_client.send_friend_request(authenticated_client.user_id)
        assert "Send friend request failed" in str(excinfo.value)

    def test_cleanup_after_block(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест: блокировка удаляет существующую дружбу"""
        # Создаем дружбу
        authenticated_client.send_friend_request(second_authenticated_client.user_id)
        second_authenticated_client.accept_friend_request(authenticated_client.user_id)

        # Проверяем, что они друзья
        friends = authenticated_client.get_friends()
        assert any(f["user_id"] == second_authenticated_client.user_id for f in friends["items"])

        # Блокируем
        authenticated_client.block_user(second_authenticated_client.user_id)

        # Проверяем, что дружба удалена
        friends_after = authenticated_client.get_friends()
        assert not any(f["user_id"] == second_authenticated_client.user_id for f in friends_after["items"])

        # Проверяем статус
        status = authenticated_client.get_relationship_status(second_authenticated_client.user_id)
        assert status.get("status") == "blocked"

    def test_cleanup_after_cancel(
        self,
        authenticated_client,
        second_authenticated_client
    ):
        """Тест: отмена заявки удаляет ее из списка"""
        second_user_id = second_authenticated_client.user_id

        # Отправляем заявку
        authenticated_client.send_friend_request(second_user_id)

        # Проверяем, что заявка есть
        requests_before = authenticated_client.get_pending_requests()
        assert any(req["user_id"] == second_user_id for req in requests_before["outgoing"])

        # Отменяем заявку
        authenticated_client.cancel_friend_request(second_user_id)

        # Проверяем, что заявка исчезла
        requests_after = authenticated_client.get_pending_requests()
        assert not any(req["user_id"] == second_user_id for req in requests_after["outgoing"])