from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends, status, UploadFile
from ..chat.schemas import *
from ...database.models import *
from ...database.core import get_db
from ...database.repositories.user.chat import ChatRepository
from ...database.repositories.files import FileRepository
from ...database.redis.redis_presence import RedisPresence, UserStatus
from ...files.service import FileService
from ...files.schemas import FileType as GlobalFileType
from typing import Dict, List, Optional, Set
from datetime import datetime, UTC
from uuid import UUID
from ...websockets.connection import connection_manager
from ...users.auth.service.utils import verify_token
from sqlalchemy.orm import Session

AVATAR_URL_EXPIRY = 86400  # 24 часа
MEDIA_URL_EXPIRY = 3600  # 1 час


def build_chat_service(db: Session, user_id: int) -> "ChatService":
    chat_repo = ChatRepository(db)
    file_repo = FileRepository(db)
    presence_service = RedisPresence()
    file_service = FileService(session=db)

    return ChatService(
        chat_repo=chat_repo,
        file_repo=file_repo,
        presence_service=presence_service,
        file_service=file_service,
        user_id=user_id,
    )


def get_chat_service(
        db: Session = Depends(get_db),
        user_id: int = Depends(verify_token),
):
    return build_chat_service(db, user_id)


class ChatService:
    def __init__(
            self,
            chat_repo: ChatRepository,
            file_repo: FileRepository,
            presence_service: RedisPresence,
            file_service: FileService,
            user_id: int
    ):
        self.file_service = file_service
        self.presence_service = presence_service
        self.chat_repo = chat_repo
        self.file_repo = file_repo
        self.user_id = user_id

    async def _get_avatar_url(self, avatar_file: Optional[FileMetadata]) -> Optional[str]:
        """Получение URL аватара через FileService"""
        if not avatar_file:
            return None
        try:
            return await self.file_service.get_file_url(
                file_id=avatar_file.id,
                user_id=self.user_id,
                expires_in=AVATAR_URL_EXPIRY
            )
        except Exception:
            return None

    async def _get_media_urls_batch(self, file_ids: List[UUID]) -> Dict[UUID, str]:
        """Получение URL для медиа-файлов batch-запросом"""
        if not file_ids:
            return {}
        return await self.file_service.get_file_urls_batch(
            file_ids=file_ids,
            user_id=self.user_id,
            expires_in=MEDIA_URL_EXPIRY
        )

    # ============ REST ENDPOINTS ДЛЯ ОТПРАВКИ СООБЩЕНИЙ ============

    async def send_text_message_rest(self, message_data: MessageSend, sender_id: int) -> MessageDTO:
        """
        REST эндпоинт для отправки текстового сообщения.
        Сохраняет сообщение в БД и отправляет уведомление через WebSocket.
        """
        chat_id = message_data.chat_id

        # Проверяем, что пользователь является участником чата
        if not self.chat_repo.is_user_in_chat(sender_id, chat_id):
            raise HTTPException(status_code=403, detail="Пользователь не является участником данного чата!")

        # Подготавливаем данные сообщения
        message_dict = {
            "chat_id": chat_id,
            "user_id": sender_id,
            "content": message_data.content,
            "message_type": message_data.message_type or MessageType.TEXT.value,
        }

        # Обработка ответов и пересылок
        await self._process_message_references(message_dict, message_data, sender_id, chat_id)

        # Сохраняем сообщение в БД
        saved_message = self.chat_repo.message.save_message(message_dict)

        # Создаем DTO для ответа
        message_dto = await self._create_message_dto(saved_message, sender_id)

        # Отправляем WebSocket уведомление
        await self._notify_new_message(message_dto, chat_id, sender_id)

        return message_dto

    async def send_media_message_rest(
            self,
            chat_id: UUID,
            sender_id: int,
            files: List[UploadFile],
            caption: Optional[str] = None,
            reply_to_message_id: Optional[int] = None
    ) -> MessageDTO:
        """
        REST эндпоинт для отправки медиа-сообщения (фото, видео, файлы).
        Загружает файлы через FileService, сохраняет метаданные в БД и отправляет уведомление через WebSocket.
        """
        # Проверяем, что пользователь является участником чата
        if not self.chat_repo.is_user_in_chat(sender_id, chat_id):
            raise HTTPException(status_code=403, detail="Пользователь не является участником данного чата!")

        # Загружаем файлы через FileService
        file_ids = []
        for file in files:
            upload_result = await self.file_service.upload_file(
                file=file,
                file_type=GlobalFileType.MESSAGE_ATTACHMENT,
                user_id=sender_id,
                metadata={
                    "chat_id": str(chat_id),
                    "sender_id": str(sender_id)
                },
                public=False
            )
            file_ids.append(upload_result.file_id)

        # Подготавливаем данные сообщения
        message_dict = {
            "chat_id": chat_id,
            "user_id": sender_id,
            "content": caption or "",
            "message_type": MessageType.MEDIA.value,
        }

        # Обработка ответа на сообщение
        if reply_to_message_id:
            await self._validate_reply_message(reply_to_message_id, chat_id, sender_id)
            message_dict.update({
                "reply_to_message_id": reply_to_message_id,
                "message_type": MessageType.REPLY.value
            })

        # Сохраняем сообщение с медиа-файлами
        saved_message = self.chat_repo.message.save_media_message(message_dict, file_ids)

        # Создаем DTO для ответа
        message_dto = await self._create_message_dto(saved_message, sender_id)

        # Отправляем WebSocket уведомление
        await self._notify_new_message(message_dto, chat_id, sender_id)

        return message_dto

    async def forward_messages_rest(
            self,
            forward_data: ForwardRequest,
            sender_id: int
    ) -> Dict:
        """
        REST эндпоинт для пересылки сообщений.
        """
        return await self.forward_messages(forward_data, sender_id)

    # ============ WEBSOCKET HANDLER ============

    async def handle_ws(self, websocket: WebSocket, user_id: int, device_info: dict = None):
        """
        WebSocket handler только для событий реального времени:
        - печать сообщения
        - прочтение
        - статус онлайн/оффлайн
        - лайки
        - получение новых сообщений (уведомления)
        """
        connection_id = await connection_manager.connect(websocket, user_id)

        # Обновляем статус присутствия
        await self.presence_service.user_connected(
            user_id=user_id,
            connection_id=str(connection_id),
            device_info=device_info
        )

        # Уведомляем контакты пользователя о его онлайн статусе
        await self._notify_presence_change(user_id, UserStatus.ONLINE)

        try:
            while True:
                # Ожидаем сообщения от клиента (только события)
                data = await websocket.receive_json()
                await self._handle_ws_event(user_id, data)

        except WebSocketDisconnect:
            print(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            print(f"Error for user {user_id}: {e}")
        finally:
            # Очищаем ресурсы
            await connection_manager.disconnect(user_id, connection_id)
            await self.presence_service.user_disconnected(connection_id)

            # Проверяем, есть ли еще активные соединения у пользователя
            remaining_connections = connection_manager.get_user_connections(user_id)
            if not remaining_connections:
                await self.presence_service.set_user_offline(user_id)
                await self._notify_presence_change(user_id, UserStatus.OFFLINE)

    async def _handle_ws_event(self, user_id: int, data: dict):
        """
        Обработка входящих WebSocket событий.
        """
        event_type = data.get("event")
        event_data = data.get("data", {})

        try:
            if event_type == "user_typing":
                chat_id = UUID(event_data.get("chat_id"))
                await self.handle_user_typing(user_id, chat_id, True)

            elif event_type == "user_stop_typing":
                chat_id = UUID(event_data.get("chat_id"))
                await self.handle_user_typing(user_id, chat_id, False)

            elif event_type == "message_read":
                message_id = int(event_data.get("message_id"))
                chat_id = UUID(event_data.get("chat_id"))
                await self.handle_message_read(user_id, message_id, chat_id)

            elif event_type == "messages_read":
                chat_id = UUID(event_data.get("chat_id"))
                messages_read = event_data.get("messages_read", [])
                mark_all = event_data.get("mark_all", False)
                await self.mark_chat_messages_as_read(user_id, chat_id, messages_read, mark_all)

            elif event_type == "like_message":
                message_id = int(event_data.get("message_id"))
                chat_id = UUID(event_data.get("chat_id"))
                await self.like_message(user_id, message_id, chat_id)

            elif event_type == "unlike_message":
                message_id = int(event_data.get("message_id"))
                chat_id = UUID(event_data.get("chat_id"))
                await self.unlike_message(user_id, message_id, chat_id)

            elif event_type == "get_presence":
                target_user_id = event_data.get("user_id")
                presence_data = await self.presence_service.get_user_presence_data(target_user_id)
                await connection_manager.send_to_user(user_id, {
                    "event": "user_presence",
                    "data": presence_data
                })

            elif event_type == "ping":
                await connection_manager.send_to_user(user_id, {
                    "event": "pong",
                    "data": event_data or {},
                })

            elif event_type == "subscribe_to_chats":
                pass

        except Exception as e:
            error_message = {
                "event": "error",
                "data": {"message": str(e)}
            }
            await connection_manager.send_to_user(user_id, error_message)

    # ============ МЕТОДЫ ДЛЯ ЛАЙКОВ ============

    async def like_message(self, user_id: int, message_id: int, chat_id: UUID) -> Dict:
        """Поставить лайк сообщению"""
        if not self.chat_repo.is_user_in_chat(user_id, chat_id):
            raise HTTPException(status_code=403, detail="Пользователь не является участником данного чата!")

        message = self.chat_repo.message.get_message_by_id(message_id)
        if not message or message.chat_id != chat_id:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")

        success = self.chat_repo.message.add_like(message_id, user_id)

        if success:
            updated_message = self.chat_repo.message.get_message_full(message_id)

            # Уведомляем участников чата
            chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(chat_id)
            ws_message = {
                "event": "message_liked",
                "data": {
                    "message_id": message_id,
                    "chat_id": str(chat_id),
                    "user_id": user_id,
                    "likes_count": updated_message.likes_count,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_chat(chat_participants_ids, ws_message, exclude_user_id=user_id)

            return {
                "message_id": message_id,
                "likes_count": updated_message.likes_count,
                "liked": True
            }

        raise HTTPException(status_code=400, detail="Already liked this message")

    async def unlike_message(self, user_id: int, message_id: int, chat_id: UUID) -> Dict:
        """Убрать лайк с сообщения"""
        message = self.chat_repo.message.get_message_by_id(message_id)
        if not message or message.chat_id != chat_id:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")

        success = self.chat_repo.message.remove_like(message_id, user_id)

        if success:
            updated_message = self.chat_repo.message.get_message_full(message_id)

            chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(chat_id)
            ws_message = {
                "event": "message_unliked",
                "data": {
                    "message_id": message_id,
                    "chat_id": str(chat_id),
                    "user_id": user_id,
                    "likes_count": updated_message.likes_count,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }
            await connection_manager.send_to_chat(chat_participants_ids, ws_message, exclude_user_id=user_id)

            return {
                "message_id": message_id,
                "likes_count": updated_message.likes_count,
                "liked": False
            }

        raise HTTPException(status_code=400, detail="Not liked this message")

    # ============ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============

    async def _process_message_references(self, message_dict: dict, message_data: MessageSend,
                                          sender_id: int, chat_id: UUID):
        """Обработка ссылок на другие сообщения (ответы, пересылки)"""
        if message_data.reply_to_message_id:
            original_message = self.chat_repo.message.get_message_by_id(message_data.reply_to_message_id)

            if not original_message:
                raise HTTPException(status_code=404, detail="Сообщение для ответа не найдено")

            if original_message.chat_id != chat_id:
                raise HTTPException(status_code=400, detail="Нельзя отвечать на сообщение из другого чата")

            if not self.chat_repo.is_user_in_chat(sender_id, original_message.chat_id):
                raise HTTPException(status_code=403, detail="Нет доступа к оригинальному сообщению")

            message_dict.update({
                "reply_to_message_id": original_message.id,
                "message_type": MessageType.REPLY.value
            })

        elif message_data.forward_message_id:
            original_message = self.chat_repo.message.get_message_by_id(message_data.forward_message_id)

            if not original_message:
                raise HTTPException(status_code=404, detail="Сообщение для пересылки не найдено")

            if original_message.chat.type != ChatRoomType.CHANNEL.value:
                if not self.chat_repo.is_user_in_chat(sender_id, original_message.chat_id):
                    raise HTTPException(status_code=403, detail="Нет доступа к оригинальному сообщению")

            message_dict.update({
                "is_forwarded": True,
                "original_message_id": original_message.id,
                "forwarded_at": datetime.now(UTC),
                "message_type": MessageType.FORWARD.value,
            })

    async def _validate_reply_message(self, reply_to_message_id: int, chat_id: UUID, user_id: int):
        """Проверить возможность ответа на сообщение"""
        original_message = self.chat_repo.message.get_message_by_id(reply_to_message_id)

        if not original_message:
            raise HTTPException(status_code=404, detail="Сообщение для ответа не найдено")

        if original_message.chat_id != chat_id:
            raise HTTPException(status_code=400, detail="Нельзя отвечать на сообщение из другого чата")

        if not self.chat_repo.is_user_in_chat(user_id, original_message.chat_id):
            raise HTTPException(status_code=403, detail="Нет доступа к оригинальному сообщению")

    async def _notify_new_message(self, message_dto: MessageDTO, chat_id: UUID, sender_id: int):
        """Отправить уведомление о новом сообщении через WebSocket"""
        chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(chat_id)
        ws_message = {
            "event": "new_message",
            "data": message_dto.model_dump(mode="json")
        }
        await connection_manager.send_to_chat(
            chat_participants_ids,
            ws_message,
            exclude_user_id=sender_id
        )

    # ============ СУЩЕСТВУЮЩИЕ МЕТОДЫ ============

    async def send_text_message(self, message_data: MessageSend, sender_id: int) -> MessageDTO:
        """Внутренний метод для отправки текстового сообщения"""
        return await self.send_text_message_rest(message_data, sender_id)

    async def forward_messages(self, forward_data: ForwardRequest, sender_id: int) -> Dict:
        """Пересылка нескольких сообщений"""
        messages_to_forward = self.chat_repo.message.get_messages_full(forward_data.message_ids)

        if not messages_to_forward:
            raise HTTPException(status_code=404, detail="Сообщения для пересылки не найдены")

        results = []
        forwarded_message_ids_by_chat: Dict[UUID, List[int]] = {}

        for target_chat_id in forward_data.target_chat_ids:
            if not self.chat_repo.is_user_in_chat(sender_id, target_chat_id):
                continue

            forwarded_message_ids_by_chat[target_chat_id] = []

            for original_message in messages_to_forward:
                if original_message.chat.type != ChatRoomType.CHANNEL.value:
                    if not self.chat_repo.is_user_in_chat(sender_id, original_message.chat_id):
                        continue

                message_dict = {
                    "chat_id": target_chat_id,
                    "user_id": sender_id,
                    "content": original_message.content,
                    "message_type": MessageType.FORWARD.value,
                    "is_forwarded": True,
                    "original_message_id": original_message.id,
                    "forwarded_at": datetime.now(UTC),
                }

                saved_message = self.chat_repo.message.save_message(message_dict)
                forwarded_message_ids_by_chat[target_chat_id].append(saved_message.id)

                results.append({
                    "original_message_id": original_message.id,
                    "target_chat_id": target_chat_id,
                    "forwarded_message_id": saved_message.id,
                    "status": "forwarded"
                })

        # Отправляем уведомления
        for target_chat_id, message_ids in forwarded_message_ids_by_chat.items():
            if not message_ids:
                continue

            full_messages = self.chat_repo.message.get_messages_full(message_ids)
            for message in full_messages:
                message_dto = await self._create_message_dto(message, sender_id)
                await self._notify_new_message(message_dto, target_chat_id, sender_id)

        return {
            "results": results,
            "total_forwarded": len(results)
        }

    async def edit_message(self, message_id: int, user_id: int, new_content: str) -> Optional[MessageDTO]:
        """Редактирование сообщения"""
        edited_message = self.chat_repo.message.edit_message(message_id, new_content, user_id)

        if not edited_message:
            raise HTTPException(status_code=404, detail="Сообщение не найдено или у вас нет прав для редактирования")

        full_message = self.chat_repo.message.get_message_full(edited_message.id)
        if not full_message:
            raise HTTPException(status_code=500, detail="Ошибка при получении данных сообщения")

        message_dto = await self._create_message_dto(full_message, user_id)

        chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(edited_message.chat_id)
        ws_message = {
            "event": "message_edited",
            "data": message_dto.model_dump(mode="json")
        }
        await connection_manager.send_to_chat(chat_participants_ids, ws_message)

        return message_dto

    async def delete_message(self, message_id: int, user_id: int) -> bool:
        """Удаление сообщения"""
        deleted_message = self.chat_repo.message.delete_message(message_id, user_id)

        if not deleted_message:
            raise HTTPException(status_code=404, detail="Сообщение не найдено или у вас нет прав для удаления")

        chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(deleted_message.chat_id)
        ws_message = {
            "event": "message_deleted",
            "data": {
                "message_id": message_id,
                "chat_id": str(deleted_message.chat_id),
                "user_id": user_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
        }
        await connection_manager.send_to_chat(
            chat_participants_ids,
            ws_message,
            exclude_user_id=user_id
        )

        return True

    async def handle_user_typing(self, user_id: int, chat_id: UUID, is_typing: bool):
        """Обработка события набора текста"""
        if not self.chat_repo.is_user_in_chat(user_id, chat_id):
            raise HTTPException(status_code=403, detail="Пользователь не является участником данного чата!")

        chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(chat_id)

        event_type = "user_typing" if is_typing else "user_stop_typing"
        ws_message = {
            "event": event_type,
            "data": {
                "user_id": user_id,
                "chat_id": str(chat_id),
                "timestamp": datetime.now(UTC).isoformat()
            }
        }

        await connection_manager.send_to_chat(
            chat_participants_ids,
            ws_message,
            exclude_user_id=user_id
        )

    async def handle_message_read(self, user_id: int, message_id: int, chat_id: UUID):
        """Обработка события прочтения сообщения"""
        if not self.chat_repo.is_user_in_chat(user_id, chat_id):
            raise HTTPException(status_code=403, detail="Пользователь не является участником данного чата!")

        success = self.chat_repo.message.mark_message_as_read(message_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")

        chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(chat_id)
        ws_message = {
            "event": "message_read",
            "data": {
                "user_id": user_id,
                "message_id": message_id,
                "chat_id": str(chat_id),
                "timestamp": datetime.now(UTC).isoformat()
            }
        }

        await connection_manager.send_to_chat(
            chat_participants_ids,
            ws_message,
            exclude_user_id=user_id
        )

    async def mark_message_as_read(self, user_id: int, message_id: int):
        """Отметить сообщение как прочитанное"""
        message = self.chat_repo.message.get_message_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")

        chat_id = message.chat_id
        if not self.chat_repo.is_user_in_chat(user_id, chat_id):
            raise HTTPException(status_code=403, detail="Пользователь не является участником данного чата!")

        success = self.chat_repo.message.mark_message_as_read(message_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")

        chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(chat_id)
        ws_message = {
            "event": "message_read",
            "data": {
                "user_id": user_id,
                "message_id": message_id,
                "chat_id": str(chat_id),
                "timestamp": datetime.now(UTC).isoformat()
            }
        }

        await connection_manager.send_to_chat(
            chat_participants_ids,
            ws_message,
            exclude_user_id=user_id
        )

    async def mark_chat_messages_as_read(
            self,
            user_id: int,
            chat_id: UUID,
            message_ids: list[int],
            mark_all: bool = False
    ):
        """Отметить все сообщения в чате как прочитанные"""
        if not self.chat_repo.is_user_in_chat(user_id, chat_id):
            raise HTTPException(status_code=403, detail="Пользователь не является участником данного чата!")

        if not mark_all and not message_ids:
            raise HTTPException(status_code=400, detail="message_ids is required when mark_all is false")

        success = self.chat_repo.message.mark_chat_messages_as_read(chat_id, user_id, message_ids, mark_all=mark_all)
        if not success:
            return

        chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(chat_id)
        ws_message = {
            "event": "messages_read",
            "data": {
                "user_id": user_id,
                "chat_id": str(chat_id),
                "timestamp": datetime.now(UTC).isoformat(),
                "read_messages": message_ids if not mark_all else "all"
            }
        }

        await connection_manager.send_to_chat(
            chat_participants_ids,
            ws_message,
            exclude_user_id=user_id
        )

    @staticmethod
    def _create_chat_dto(
            chat: Chat,
            user_id: int,
            last_message: Message,
            unread_count: int
    ):
        if chat.type == ChatRoomType.PRIVATE.value:
            participants = chat.participants

            for participant in participants:
                if participant.user_id != user_id:
                    chat.name = participant.user_profile.username

        chat_dto = ChatDTO(
            id=chat.id,
            name=chat.name,
            type=chat.type,
            created_by=chat.created_by,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            last_message=last_message.content[:100] + "..." if last_message and len(
                last_message.content) > 100 else last_message.content if last_message else None,
            last_message_time=last_message.created_at if last_message else None,
            unread_count=unread_count,
            participants_count=len(chat.participants)
        )

        return chat_dto

    async def get_chat(self, user_id: int, chat_id: UUID) -> ChatDTO:
        chat = self.chat_repo.get_chat_by_id(chat_id)

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found."
            )

        if not self.chat_repo.is_user_in_chat(user_id, chat_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a participant of this chat."
            )

        last_message = self.chat_repo.message.get_last_message(chat_id)
        unread_count = self.chat_repo.message.get_unread_messages_count(chat_id, user_id)

        chat_dto = self._create_chat_dto(chat, user_id, last_message, unread_count)

        return chat_dto

    async def get_user_chats(self, user_id: int) -> List[ChatDTO]:
        """Получить все чаты пользователя"""
        chats = self.chat_repo.get_user_chats(user_id)

        chat_dtos = []

        # Собираем ID всех чатов для пакетной обработки
        chat_ids = [chat.id for chat in chats]

        if chat_ids:
            # Получаем последние сообщения и непрочитанные счетчики одним запросом
            last_messages = self.chat_repo.message.get_last_messages_for_chats(chat_ids)
            unread_counts = self.chat_repo.message.get_unread_counts_for_chats(chat_ids, user_id)
        else:
            last_messages = {}
            unread_counts = {}

        for chat in chats:
            last_message = last_messages.get(chat.id)
            unread_count = unread_counts.get(chat.id, 0)

            chat_dto = self._create_chat_dto(chat, user_id, last_message, unread_count)
            chat_dtos.append(chat_dto)

        return chat_dtos

    async def get_chat_messages(self, chat_id: UUID, user_id: int, limit: int = 50, offset: int = 0) -> List[
        MessageDTO]:
        """Получить сообщения чата"""
        if not self.chat_repo.is_user_in_chat(user_id, chat_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a participant of this chat."
            )

        # Получаем сообщения со всеми связями
        messages = self.chat_repo.message.get_chat_messages(chat_id, limit, offset)

        # Конвертируем в DTO
        message_dtos = [await self._create_message_dto(message, user_id) for message in messages]

        return message_dtos

    async def get_message_replies(self, message_id: int, user_id: int, limit: int = 50, offset: int = 0) -> List[
        MessageDTO]:
        """Получить все ответы на конкретное сообщение"""
        # Получаем оригинальное сообщение с проверкой доступа
        original_message = self.chat_repo.message.get_message_by_id(message_id)
        if not original_message:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")

        # Проверяем доступ к чату
        if not self.chat_repo.is_user_in_chat(user_id, original_message.chat_id):
            raise HTTPException(status_code=403, detail="Нет доступа к чату")

        # Получаем ответы со всеми связями из репозитория
        replies = self.chat_repo.message.get_message_replies(message_id, limit, offset)

        # Конвертируем в DTO с медиа и лайками
        message_dtos = []
        for reply in replies:
            dto = await self._create_message_dto(reply, user_id)
            message_dtos.append(dto)

        return message_dtos

    async def search_messages(self, chat_id: UUID, user_id: int, search_query: str, limit: int = 50) -> List[
        MessageDTO]:
        """Поиск сообщений в чате"""
        if not self.chat_repo.is_user_in_chat(user_id, chat_id):
            raise HTTPException(status_code=403, detail="Пользователь не является участником данного чата!")

        # Получаем сообщения со всеми связями
        messages = self.chat_repo.message.search_messages(chat_id, search_query, limit)

        # Конвертируем в DTO
        message_dtos = [await self._create_message_dto(message, user_id) for message in messages]

        return message_dtos

    async def create_chat(self,
                          chat_data: ChatCreate,
                          user_id: int) -> ChatDTO:

        if chat_data.data.type == ChatRoomType.PRIVATE.value:
            if not chat_data.members or len(chat_data.members) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Создать приватный чат можно только с одним пользователем."
                )
            companion_id = chat_data.members[0]
            if user_id == companion_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Нельзя передавать свой id в поле members"
                )

            if not self.chat_repo.user.get_profile_by_user_id(companion_id):
                raise HTTPException(404, "Собеседник не найден!")

            if self.chat_repo.check_private_chat_exists(user_id, companion_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Приватный чат между данными пользователями уже существует."
                )

        chat_data_dict = chat_data.model_dump(mode="json")
        chat_data_dict["data"]["created_by"] = user_id

        chat = self.chat_repo.create_chat(chat_data_dict["data"])

        participant_data = [
            {
                "chat_id": chat.id,
                "user_id": user_id,
                "role": UserRole.OWNER.value
            }
        ]

        if chat_data.members:
            for member_id in chat_data.members:
                participant_data.append(
                    {
                        "chat_id": chat.id,
                        "user_id": member_id,
                        "role": UserRole.MEMBER.value
                    }
                )

        self.chat_repo.add_to_chat(participant_data)

        chat_dto = ChatDTO(
            id=chat.id,
            name=chat.name,
            type=chat.type,
            created_by=chat.created_by,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            participants_count=len(participant_data)
        )

        return chat_dto

    async def add_users_to_chat(self, chat_id: UUID, user_id: int, new_user_ids: Set[int]):
        """Добавить пользователей в чат"""
        # Проверяем права пользователя (только владелец/админ могут добавлять)
        participant = self.chat_repo.get_participant_info(user_id, chat_id)

        if participant.chat.type == ChatRoomType.PRIVATE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя добавить пользователя/ей в уже созданный приватный чат."
            )

        if not participant or participant.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для добавления пользователей"
            )

        users_with_existing_profiles = self.chat_repo.user.get_existing_users_ids(new_user_ids)
        non_existing = [user_id for user_id in new_user_ids if user_id not in users_with_existing_profiles]

        if non_existing:
            raise HTTPException(
                detail={
                    "message": "Не у всех добавляемых пользователей есть профиль!",
                    "non_existing": non_existing,
                    "valid_users": users_with_existing_profiles
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        chat_participants_ids = self.chat_repo.get_chat_participant_user_ids(chat_id)
        already_in_chat = [uid for uid in chat_participants_ids if uid in new_user_ids]

        if already_in_chat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Некоторые пользователи уже есть в чате!",
                    "users_already_in_chat": already_in_chat
                }
            )

        participant_data = []
        for new_user_id in new_user_ids:
            participant_data.append({
                "chat_id": chat_id,
                "user_id": new_user_id,
                "role": UserRole.MEMBER.value
            })

        self.chat_repo.add_to_chat(participant_data)

        ws_message = {
            "event": "users_added_to_chat",
            "data": {
                "chat_id": str(chat_id),
                "added_user_ids": list(new_user_ids),
                "added_by": user_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
        }
        await connection_manager.send_to_chat(chat_participants_ids, ws_message)

    async def get_chat_participants(self, user_id: int, chat_id: UUID) -> list[ChatParticipantDTO]:
        if not self.chat_repo.is_user_in_chat(user_id, chat_id):
            raise HTTPException(status_code=403, detail="Пользователь не является участником данного чата!")

        participants = self.chat_repo.get_chat_participants(chat_id)
        participants_dto = []

        for participant in participants:
            participant_dto = ChatParticipantDTO.model_validate(participant, from_attributes=True)
            participant_dto.username = participant.user_profile.username

            avatar_url = await self._get_avatar_url(participant.user_profile.avatar_file)
            participant_dto.avatar_url = avatar_url

            participants_dto.append(participant_dto)

        return participants_dto

    async def _notify_presence_change(self, user_id: int, status: UserStatus):
        """Уведомление контактов об изменении статуса присутствия"""
        # Получаем все чаты пользователя
        participants = self.chat_repo.get_user_chats_participant(user_id)
        chat_ids = [p.chat_id for p in participants]

        # Для каждого чата получаем участников и уведомляем их
        for chat_id in chat_ids:
            participant_ids = self.chat_repo.get_chat_participant_user_ids(chat_id)

            presence_message = {
                "event": "user_presence",
                "data": {
                    "user_id": user_id,
                    "status": status.value,
                    "chat_id": str(chat_id),
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }

            await connection_manager.send_to_chat(
                participant_ids,
                presence_message,
                exclude_user_id=user_id
            )

    async def _create_message_dto(self, message: Message, current_user_id: int) -> MessageDTO:
        """Создать DTO из модели сообщения с медиа-файлами и лайками"""
        if not message:
            raise ValueError("Message is None")

        # Получаем медиа-файлы для сообщения
        media_files = self.chat_repo.message.get_message_media(message.id)

        # Получаем URL для всех медиа-файлов batch-запросом
        file_ids = [media.id for media in media_files]
        media_urls_map = await self._get_media_urls_batch(file_ids)

        media_urls = []
        for media in media_files:
            url = media_urls_map.get(media.id, "")
            media_urls.append({
                'url': url,
                'type': media.mime_type,
                'filename': media.original_filename,
                'size': media.size_bytes
            })

        # Проверяем, лайкнул ли текущий пользователь
        is_liked = False
        if message.likes and str(current_user_id) in message.likes:
            is_liked = True

        username = None
        name = None
        lastname = None
        avatar_url = None
        if message.user_profile:
            username = message.user_profile.username
            name = message.user_profile.name
            lastname = message.user_profile.lastname
            if message.user_profile.avatar_file:
                avatar_url = await self._get_avatar_url(message.user_profile.avatar_file)

        # Базовая информация
        message_dto = MessageDTO(
            id=message.id,
            chat_id=message.chat_id,
            user_id=message.user_id,
            username=username,
            name=name,
            lastname=lastname,
            avatar_url=avatar_url,
            content=message.content,
            message_type=message.message_type,
            created_at=message.created_at,
            is_edited=message.is_edited,
            reply_to_message_id=message.reply_to_message_id,
            is_forwarded=message.is_forwarded,
            original_message_id=message.original_message_id,
            forwarded_at=message.forwarded_at,
            media_urls=media_urls,
            likes_count=message.likes_count or 0,
            is_liked_by_user=is_liked
        )

        # Добавляем информацию о прочитавших
        if message.read_by:
            current_user_key = str(current_user_id)

            if current_user_id == message.user_id:
                # Автор сообщения видит всех, кто прочитал
                message_dto.read_by = {}
                for user_key, read_data in message.read_by.items():
                    processed_data = read_data.copy()
                    if read_data.get('avatar'):
                        try:
                            # Здесь avatar - это s3_key, нужно получить URL
                            # Но так как это сложно в batch, оставляем как есть или обрабатываем отдельно
                            processed_data['avatar_url'] = None
                        except Exception:
                            processed_data['avatar_url'] = None
                    message_dto.read_by[user_key] = processed_data
            else:
                # Не автор видит только себя в списке прочитавших
                if current_user_key in message.read_by:
                    read_data = message.read_by[current_user_key]
                    processed_data = read_data.copy()
                    message_dto.read_by = {current_user_key: processed_data}

        # Добавляем превью для ответов
        if message.reply_to_message_id and hasattr(message, 'replied_message') and message.replied_message:
            replied_message = message.replied_message
            message_dto.reply_to = MessagePreview(
                id=replied_message.id,
                chat_id=replied_message.chat_id,
                user_id=replied_message.user_id,
                content=replied_message.content,
                message_type=replied_message.message_type,
                created_at=replied_message.created_at,
                is_edited=replied_message.is_edited
            )

            if hasattr(replied_message, 'user_profile') and replied_message.user_profile:
                avatar_url = await self._get_avatar_url(replied_message.user_profile.avatar_file)

                message_dto.reply_to.sender = UserShortInfo(
                    user_id=replied_message.user_id,
                    username=replied_message.user_profile.username,
                    name=replied_message.user_profile.name,
                    lastname=replied_message.user_profile.lastname,
                    avatar_url=avatar_url
                )

        # Добавляем информацию о пересланном сообщении
        if message.is_forwarded and hasattr(message, 'original_message') and message.original_message:
            original_msg = message.original_message

            message_dto.original_message_preview = MessagePreview(
                id=original_msg.id,
                chat_id=original_msg.chat_id,
                user_id=original_msg.user_id,
                content=original_msg.content,
                message_type=original_msg.message_type,
                created_at=original_msg.created_at,
                is_edited=original_msg.is_edited
            )

            if hasattr(original_msg, 'user_profile') and original_msg.user_profile:
                avatar_url = await self._get_avatar_url(original_msg.user_profile.avatar_file)

                message_dto.original_message_preview.sender = UserShortInfo(
                    user_id=original_msg.user_id,
                    username=original_msg.user_profile.username,
                    name=original_msg.user_profile.name,
                    lastname=original_msg.user_profile.lastname,
                    avatar_url=avatar_url
                )

            if hasattr(original_msg, 'chat') and original_msg.chat:
                message_dto.original_message_preview.chat = ChatShortInfo(
                    chat_id=original_msg.chat_id,
                    type=original_msg.chat.type,
                    name=original_msg.chat.name
                )

        return message_dto