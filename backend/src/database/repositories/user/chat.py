from ....database.repositories.base_repository import BaseRepository
from ....database.models import *
from sqlalchemy import and_, exists, func, update
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import List, Optional, Dict
from datetime import datetime, UTC
from ....database.repositories.user.profile import ProfileRepository
import json


class ChatRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)
        self.message = MessageRepository(session)
        self.user = ProfileRepository(session)

    def create_chat(self, chat_data: dict) -> Chat:
        chat = Chat(**chat_data)
        self.session.add(chat)
        self.session.flush()
        self.session.commit()
        return chat

    def add_to_chat(self, participant_data: list[dict]):
        participants = list(map(lambda data: ChatParticipant(**data), participant_data))
        self.session.add_all(participants)
        self.session.commit()
        return True

    def get_participant_info(self, user_id: int, chat_id: str | UUID) -> Optional[ChatParticipant]:
        participant = (
            self.session.query(ChatParticipant)
            .filter(
                and_(
                    ChatParticipant.chat_id == chat_id,
                    ChatParticipant.user_id == user_id)
            )
            .options(joinedload(ChatParticipant.chat))
        ).first()
        return participant

    def get_chat_participant_user_ids(self, chat_id: str | UUID) -> List[int]:
        user_ids = (
            self.session
            .query(ChatParticipant.user_id)
            .filter(ChatParticipant.chat_id == chat_id)
            .all()
        )
        return [user_id[0] for user_id in user_ids]

    def get_user_chats_participant(self, user_id: int) -> List[ChatParticipant]:
        participants = (
            self.session
            .query(ChatParticipant)
            .filter(ChatParticipant.user_id == user_id)
            .all()
        )
        return participants

    def get_user_chats(self, user_id: int) -> List[Chat]:
        """Получить все чаты пользователя с основной информацией"""
        chats = (
            self.session.query(Chat)
            .join(ChatParticipant, Chat.id == ChatParticipant.chat_id)
            .filter(ChatParticipant.user_id == user_id)
            .options(joinedload(Chat.participants).joinedload(ChatParticipant.user_profile))
            .order_by(Chat.updated_at.desc())
            .all()
        )
        return chats

    def get_chat_by_id(self, chat_id: str | UUID) -> Optional[Chat]:
        """Получить чат по ID"""
        chat = (
            self.session.query(Chat)
            .filter(Chat.id == chat_id)
            .options(
                joinedload(Chat.participants).joinedload(ChatParticipant.user_profile),
                joinedload(Chat.messages)
            )
            .first()
        )
        return chat

    def update_chat(self, chat_id: str | UUID, update_data: dict) -> Optional[Chat]:
        """Обновить информацию о чате"""
        result = (
            self.session.query(Chat)
            .filter(Chat.id == chat_id)
            .update(update_data)
        )
        self.session.commit()

        if result:
            return self.get_chat_by_id(chat_id)
        return None

    def delete_chat(self, chat_id: str | UUID) -> bool:
        """Удалить чат (мягкое удаление)"""
        chat = self.get_chat_by_id(chat_id)
        if chat:
            self.session.delete(chat)
            self.session.commit()
            return True
        return False

    def check_private_chat_exists(self, user_a: int, user_b: int):
        return self.session.query(
            exists().where(
                and_(
                    Chat.type == ChatRoomType.PRIVATE.value,
                    Chat.id.in_(
                        self.session.query(ChatParticipant.chat_id)
                        .filter(ChatParticipant.user_id.in_([user_a, user_b]))
                        .group_by(ChatParticipant.chat_id)
                        .having(func.count(ChatParticipant.user_id) == 2)
                    )
                )
            )
        ).scalar()

    def remove_user_from_chat(self, chat_id: str | UUID, user_id: int) -> bool:
        """Удалить пользователя из чата"""
        participant = self.get_participant_info(user_id, chat_id)
        if participant:
            self.session.delete(participant)
            self.session.commit()
            return True
        return False

    def get_chat_participants(self, chat_id: str | UUID) -> List[ChatParticipant]:
        participants = (
            self.session.query(ChatParticipant)
            .filter(ChatParticipant.chat_id == chat_id)
            .options(
                joinedload(ChatParticipant.user_profile)
                .joinedload(UserProfile.avatar_file)
            )
            .all()
        )
        return participants

    def update_participant_role(self, chat_id: str | UUID, user_id: int, new_role: UserRole) -> bool:
        """Обновить роль участника чата"""
        participant = self.get_participant_info(user_id, chat_id)
        if participant:
            participant.role = new_role
            self.session.commit()
            return True
        return False

    def is_user_in_chat(self, user_id: int, chat_id: str | UUID) -> bool:
        """Проверить, является ли пользователь участником чата"""
        participant = self.get_participant_info(user_id, chat_id)
        return participant is not None

    def get_project_channel(self, project_id: UUID) -> Optional[Chat]:
        """Получить канал проекта"""
        return (
            self.session.query(Chat)
            .filter(
                and_(
                    Chat.project_id == project_id,
                    Chat.type == ChatRoomType.CHANNEL.value,
                )
            )
            .options(
                joinedload(Chat.participants)
                .joinedload(ChatParticipant.user_profile)
                .joinedload(UserProfile.avatar_file)
            )
            .first()
        )

    def get_channel_subscribers(self, channel_id: UUID) -> List[ChatParticipant]:
        """Получить подписчиков канала с профилями"""
        return (
            self.session.query(ChatParticipant)
            .filter(
                and_(
                    ChatParticipant.chat_id == channel_id,
                    ChatParticipant.role == UserRole.MEMBER.value
                )
            )
            .options(
                joinedload(ChatParticipant.user_profile)
                .joinedload(UserProfile.avatar_file)
            )
            .all()
        )

    def get_channel_subscribers_count(self, channel_id: UUID) -> int:
        """Получить количество подписчиков канала"""
        return (
            self.session.query(ChatParticipant)
            .filter(
                and_(
                    ChatParticipant.chat_id == channel_id,
                    ChatParticipant.role == UserRole.MEMBER.value
                )
            )
            .count()
        )

    def is_channel_subscriber(self, channel_id: UUID, user_id: int) -> bool:
        """Проверить, подписан ли пользователь на канал"""
        return (
            self.session.query(
                exists().where(
                    and_(
                        ChatParticipant.chat_id == channel_id,
                        ChatParticipant.user_id == user_id,
                        ChatParticipant.role == UserRole.MEMBER.value
                    )
                )
            )
        ).scalar()

    def subscribe_to_channel(self, channel_id: UUID, user_id: int) -> bool:
        """Подписаться на канал"""
        if self.is_channel_subscriber(channel_id, user_id):
            return False

        participant = ChatParticipant(
            chat_id=channel_id,
            user_id=user_id,
            role=UserRole.MEMBER.value
        )
        self.session.add(participant)
        self.session.commit()
        return True

    def unsubscribe_from_channel(self, channel_id: UUID, user_id: int) -> bool:
        """Отписаться от канала"""
        # Нельзя отписать владельца канала
        participant = self.get_participant_info(user_id, channel_id)
        if participant and participant.role == UserRole.OWNER.value:
            return False

        result = (
            self.session.query(ChatParticipant)
            .filter(
                and_(
                    ChatParticipant.chat_id == channel_id,
                    ChatParticipant.user_id == user_id,
                    ChatParticipant.role == UserRole.MEMBER.value
                )
            )
            .delete(synchronize_session=False)
        )
        self.session.commit()
        return result > 0

    def create_project_channel(self, project_id: UUID, name: str, description: Optional[str], created_by: int) -> Chat:
        """Создать канал для проекта"""
        channel = Chat(
            name=name,
            type=ChatRoomType.CHANNEL.value,
            created_by=created_by,
            project_id=project_id,
            description=description,
        )
        self.session.add(channel)
        self.session.flush()

        # Создатель автоматически становится владельцем канала
        participant = ChatParticipant(
            chat_id=channel.id,
            user_id=created_by,
            role=UserRole.OWNER.value
        )
        self.session.add(participant)
        self.session.commit()

        return channel

    def update_channel(self, channel_id: UUID, update_data: dict) -> Optional[Chat]:
        """Обновить канал"""
        self.session.query(Chat).filter(Chat.id == channel_id).update(update_data)
        self.session.commit()
        return self.get_chat_by_id(channel_id)

    def delete_channel(self, channel_id: UUID) -> bool:
        """Удалить канал (мягкое удаление)"""
        channel = self.get_chat_by_id(channel_id)
        if channel and channel.type == ChatRoomType.CHANNEL.value:
            self.session.delete(channel)
            self.session.commit()
            return True
        return False

    def get_user_subscribed_channels(self, user_id: int, limit: int, offset: int) -> List[Chat]:
        """Получить все каналы, на которые подписан пользователь"""
        return (
            self.session.query(Chat)
            .join(ChatParticipant, Chat.id == ChatParticipant.chat_id)
            .filter(
                and_(
                    ChatParticipant.user_id == user_id,
                    Chat.type == ChatRoomType.CHANNEL.value,
                    ChatParticipant.role == UserRole.MEMBER.value
                )
            )
            .options(
                joinedload(Chat.participants).joinedload(ChatParticipant.user_profile)
            )
            .order_by(Chat.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_user_admin_channels(self, user_id: int, limit: int = 100, offset: int = 0):
        # каналы проектов, где пользователь admin/owner
        query = (
            self.session.query(Chat)
            .join(
                ProjectParticipant,
                and_(
                    ProjectParticipant.project_id == Chat.project_id,
                    ProjectParticipant.user_id == user_id,
                    ProjectParticipant.status.in_(
                        [ProjectParticipantStatus.OWNER.value, ProjectParticipantStatus.ADMIN.value])
                )
            )
            .filter(Chat.type == ChatRoomType.CHANNEL.value)
            .order_by(Chat.created_at.desc())
        )

        total = query.count()
        channels = query.offset(offset).limit(limit).all()

        return channels, total

    def get_channel_owner_id(self, channel_id: UUID) -> Optional[int]:
        """Получить ID владельца канала"""
        participant = (
            self.session.query(ChatParticipant)
            .filter(
                and_(
                    ChatParticipant.chat_id == channel_id,
                    ChatParticipant.role == UserRole.OWNER.value
                )
            )
            .first()
        )
        return participant.user_id if participant else None


class MessageRepository(BaseRepository):
    def save_message(self, data: dict) -> Message:
        """Сохранить сообщение (создать новое)"""
        message = Message(**data)
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def get_message_by_id(self, message_id: int) -> Optional[Message]:
        """Получить сообщение по ID с базовыми связями"""
        return (
            self.session.query(Message)
            .filter(Message.id == message_id)
            .options(
                joinedload(Message.user_profile),
                joinedload(Message.chat)
            )
            .first()
        )

    message_options = [
        # Основной пользователь сообщения с аватаркой
        selectinload(Message.user_profile).selectinload(UserProfile.avatar_file),

        # Ответное сообщение: пользователь + его аватарка + чат
        selectinload(Message.replied_message)
        .selectinload(Message.user_profile)
        .selectinload(UserProfile.avatar_file),
        selectinload(Message.replied_message).selectinload(Message.chat),

        # Оригинальное сообщение (для пересланных): пользователь + аватарка + чат
        selectinload(Message.original_message)
        .selectinload(Message.user_profile)
        .selectinload(UserProfile.avatar_file),
        selectinload(Message.original_message).selectinload(Message.chat),

        # Ответы на сообщение: пользователь + аватарка
        selectinload(Message.replies)
        .selectinload(Message.user_profile)
        .selectinload(UserProfile.avatar_file),
    ]

    def get_message_full(self, message_id: int) -> Optional[Message]:
        """Получить сообщение со всеми связями"""
        return (
            self.session.query(Message)
            .filter(Message.id == message_id)
            .options(
                *self.message_options
            )
            .first()
        )

    def get_messages_full(self, message_ids: List[int]) -> List[Message]:
        """Получить несколько сообщений со всеми связями"""
        if not message_ids:
            return []

        return (
            self.session.query(Message)
            .filter(Message.id.in_(message_ids))
            .options(
                *self.message_options
            )
            .all()
        )

    def get_chat_messages(self, chat_id: UUID, limit: int = 50, offset: int = 0) -> List[Message]:
        """Получить сообщения чата со всеми связями"""
        return (
            self.session.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(limit)
            .options(
                *self.message_options
            )
            .all()
        )

    def get_message_replies(self, message_id: int, limit: int = 50, offset: int = 0) -> List[Message]:
        """Получить ответы на сообщение со всеми связями"""
        return (
            self.session.query(Message)
            .filter(Message.reply_to_message_id == message_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
            .options(
                *self.message_options
            )
            .all()
        )

    def search_messages(self, chat_id: UUID, search_query: str, limit: int = 50) -> List[Message]:
        """Поиск сообщений в чате со всеми связями"""
        return (
            self.session.query(Message)
            .filter(
                and_(
                    Message.chat_id == chat_id,
                    Message.content.ilike(f"%{search_query}%")
                )
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
            .options(
                *self.message_options
            )
            .all()
        )

    def get_unread_counts_for_chats(self, chat_ids: List[UUID], user_id: int) -> Dict[UUID, int]:
        """Получить количество непрочитанных сообщений для нескольких чатов"""
        if not chat_ids:
            return {}

        result = (
            self.session.query(
                Message.chat_id,
                func.count(Message.id).label('unread_count')
            )
            .filter(
                and_(
                    Message.chat_id.in_(chat_ids),
                    Message.user_id != user_id,
                    ~Message.read_by.has_key(str(user_id))
                )
            )
            .group_by(Message.chat_id)
            .all()
        )

        return {chat_id: count for chat_id, count in result}

    def mark_message_as_read(self, message_id: int, user_id: int) -> bool:
        # Используем update с возвратом данных для атомарности
        user_key = str(user_id)
        current_time = datetime.now()

        # Получаем текущее значение read_by и обновляем его
        message = self.session.query(Message).filter(Message.id == message_id).first()
        if not message:
            return False

        # Инициализируем read_by если None
        if message.read_by is None:
            message.read_by = {}

        # Проверяем, не отмечено ли уже как прочитанное
        if user_key in message.read_by:
            return True

        # Получаем информацию о пользователе одним запросом
        user_info = (
            self.session.query(UserProfile.username, FileMetadata.s3_key)
            .outerjoin(FileMetadata, UserProfile.avatar_file_id == FileMetadata.id)
            .filter(UserProfile.user_id == user_id)
            .first()
        )

        if not user_info:
            return False

        username, avatar_key = user_info

        # Обновляем read_by
        read_by_copy = dict(message.read_by)
        read_by_copy[user_key] = {
            'username': username,
            'avatar': avatar_key,
            'read_at': current_time.isoformat()
        }

        # Атомарное обновление
        stmt = (
            update(Message)
            .where(Message.id == message_id)
            .values(
                read_by=read_by_copy,
                updated_at=current_time
            )
        )

        self.session.execute(stmt)
        self.session.commit()

        return True

    def mark_chat_messages_as_read(
            self,
            chat_id: UUID,
            user_id: int,
            message_ids: Optional[List[int]] = None,
            mark_all: bool = False
    ) -> bool:

        if not mark_all and not message_ids:
            return False

        user_key = str(user_id)
        current_time = datetime.now()
        current_time_iso = current_time.isoformat()

        # Сначала получаем информацию о пользователе
        user_info = (
            self.session.query(UserProfile.username, FileMetadata.s3_key)
            .outerjoin(FileMetadata, UserProfile.avatar_file_id == FileMetadata.id)
            .filter(UserProfile.user_id == user_id)
            .first()
        )

        if not user_info:
            return False

        username, avatar_key = user_info

        # Строим базовый запрос для сообщений, которые нужно обновить
        query = self.session.query(Message).filter(
            Message.chat_id == chat_id,
            Message.user_id != user_id  # Не отмечаем свои сообщения
        )

        if not mark_all and message_ids:
            # Проверяем, что все указанные сообщения принадлежат этому чату
            subquery = query.filter(Message.id.in_(message_ids)).subquery()
            actual_count = self.session.query(subquery).count()
            if actual_count != len(message_ids):
                # Некоторые сообщения не найдены или не принадлежат чату
                return False

        # Cоздаем JSON объект для добавления
        new_read_entry = json.dumps({
            user_key: {
                'username': username,
                'avatar': avatar_key,
                'read_at': current_time_iso
            }
        })

        # Атомарное обновление с использованием JSONB функций PostgreSQL
        stmt = (
            update(Message)
            .where(
                and_(
                    Message.chat_id == chat_id,
                    Message.user_id != user_id,
                    ~Message.read_by.has_key(user_key)  # Только непрочитанные
                )
            )
            .values(
                # Используем оператор || для объединения JSONB объектов
                read_by=func.coalesce(Message.read_by, '{}').op('||')(new_read_entry),
                updated_at=current_time
            )
        )

        if not mark_all and message_ids:
            stmt = stmt.where(Message.id.in_(message_ids))

        result = self.session.execute(stmt)
        self.session.commit()

        return result.rowcount > 0

    def edit_message(self, message_id: int, new_content: str, user_id: int) -> Optional[Message]:
        """Редактировать сообщение"""
        message = self.get_message_by_id(message_id)

        if message and message.user_id == user_id:
            message.content = new_content
            message.is_edited = True
            message.updated_at = datetime.now()
            self.session.commit()
            return message
        return None

    def delete_message(self, message_id: int, user_id: int) -> Message | bool:
        """Удалить сообщение"""
        message = self.get_message_by_id(message_id)

        if message and message.user_id == user_id:
            self.session.delete(message)
            self.session.commit()
            return message
        return False

    def get_unread_messages_count(self, chat_id: UUID, user_id: int) -> int:
        """Получить количество непрочитанных сообщений в чате"""
        count = (
            self.session.query(Message)
            .filter(
                and_(
                    Message.chat_id == chat_id,
                    Message.user_id != user_id,
                    ~Message.read_by.has_key(str(user_id))
                )
            )
            .count()
        )
        return count

    def get_last_message(self, chat_id: UUID) -> Optional[Message]:
        """Получить последнее сообщение в чате со всеми связями"""
        return (
            self.session.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .options(
                *self.message_options
            )
            .first()
        )

    def get_last_messages_for_chats(self, chat_ids: List[UUID]) -> Dict[UUID, Optional[Message]]:
        """Получить последние сообщения для нескольких чатов"""
        if not chat_ids:
            return {}

        # Подзапрос для получения последнего сообщения в каждом чате
        subquery = (
            self.session.query(
                Message.chat_id,
                func.max(Message.created_at).label('max_created_at')
            )
            .filter(Message.chat_id.in_(chat_ids))
            .group_by(Message.chat_id)
            .subquery()
        )

        # Основной запрос
        messages = (
            self.session.query(Message)
            .join(
                subquery,
                and_(
                    Message.chat_id == subquery.c.chat_id,
                    Message.created_at == subquery.c.max_created_at
                )
            )
            .options(
                *self.message_options
            )
            .all()
        )

        return {msg.chat_id: msg for msg in messages}

    def get_messages_by_user(self, chat_id: UUID, user_id: int, limit: int = 50) -> List[Message]:
        """Получить сообщения конкретного пользователя в чате"""
        messages = (
            self.session.query(Message)
            .filter(
                and_(
                    Message.chat_id == chat_id,
                    Message.user_id == user_id
                )
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
            .options(
                *self.message_options
            )
            .all()
        )
        return messages

    def get_chat_messages_count(self, chat_id: UUID) -> int:
        """Получить общее количество сообщений в чате"""
        return (
            self.session.query(Message)
            .filter(Message.chat_id == chat_id)
            .count()
        )

    def save_media_message(self, data: dict, file_ids: List[UUID]) -> Message:
        """
        Сохранить сообщение с медиа-файлами.
        Файлы привязываются через связующую таблицу message_attachments.
        """
        message = Message(**data)
        self.session.add(message)
        self.session.flush()  # Получаем ID сообщения

        # Привязываем файлы к сообщению через связующую таблицу
        for file_id in file_ids:
            attachment = MessageAttachment(
                message_id=message.id,
                file_id=file_id
            )
            self.session.add(attachment)

        self.session.commit()
        self.session.refresh(message)
        return message

    def get_message_media(self, message_id: int) -> List[FileMetadata]:
        """
        Получить медиа-файлы сообщения через связующую таблицу message_attachments.
        """
        return (
            self.session.query(FileMetadata)
            .join(MessageAttachment, MessageAttachment.file_id == FileMetadata.id)
            .filter(MessageAttachment.message_id == message_id)
            .all()
        )

    def add_like(self, message_id: int, user_id: int) -> bool:
        """Добавить лайк сообщению"""
        message = self.get_message_by_id(message_id)
        if not message:
            return False

        if not message.likes:
            message.likes = {}

        user_key = str(user_id)
        if user_key not in message.likes:
            message.likes[user_key] = {
                'user_id': user_id,
                'liked_at': datetime.now(UTC).isoformat()
            }
            message.likes_count = len(message.likes)
            self.session.commit()
            return True
        return False

    def remove_like(self, message_id: int, user_id: int) -> bool:
        """Убрать лайк с сообщения"""
        message = self.get_message_by_id(message_id)
        if not message or not message.likes:
            return False

        user_key = str(user_id)

        if user_key in message.likes:
            likes_dict = dict(message.likes)
            del likes_dict[user_key]
            message.likes = likes_dict
            message.likes_count = len(message.likes)
            self.session.commit()
            return True
        return False