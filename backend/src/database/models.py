from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (Column, String, Integer,
                        ForeignKey, DateTime,
                        BigInteger, Text, Date, UUID,
                        Boolean, func, Index, UniqueConstraint)
from datetime import datetime, UTC
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
import enum
import uuid

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String, unique=True)
    password = Column(String)
    github_access_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(UTC))

    profile = relationship("UserProfile",
                           back_populates="user",
                           cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = 'user_profiles'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name = Column(String)
    lastname = Column(String)
    username = Column(String)
    birth_date = Column(Date)
    avatar_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("file_metadata.id", ondelete="SET NULL"),
        nullable=True
    )
    university = Column(String)
    faculty = Column(String)
    course = Column(Integer)
    info = Column(Text)
    interests = Column(ARRAY(String), nullable=True)
    skills = Column(ARRAY(String), nullable=True)
    links = Column(ARRAY(String), nullable=True)

    user = relationship("User", back_populates="profile")
    avatar_file = relationship("FileMetadata", foreign_keys=[avatar_file_id])
    messages = relationship("Message", back_populates="user_profile", cascade="all, delete-orphan")
    participant_in_chats = relationship("ChatParticipant", back_populates="user_profile", cascade="all, delete-orphan")
    received_invitations = relationship(
        "ProjectInvitation",
        foreign_keys="[ProjectInvitation.invited_user_id]",
        back_populates="invited_user",
        cascade="all, delete-orphan"
    )
    sent_invitations = relationship(
        "ProjectInvitation",
        foreign_keys="[ProjectInvitation.invited_by]",
        back_populates="inviter",
        cascade="all, delete-orphan"
    )
    project_participations = relationship(
        "ProjectParticipant",
        back_populates="user_profile",
        cascade="all, delete-orphan"
    )
    project_likes = relationship(
        "ProjectLike",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")


class ChatRoomType(enum.Enum):
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"


class UserRole(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class MessageType(enum.Enum):
    TEXT = "text"
    MEDIA = "media"
    REPLY = "reply"
    FORWARD = "forward"


class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String, nullable=False)
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    description = Column(Text, nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)

    participants = relationship("ChatParticipant", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('project_id', name='uq_project_channel'),
    )


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    role = Column(String, default=UserRole.MEMBER.value)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="participants")
    user_profile = relationship("UserProfile", back_populates="participant_in_chats")
    workspace_participant = relationship(
        "WorkspaceParticipant",
        back_populates="workspace_chat_participant",
        foreign_keys="[WorkspaceParticipant.workspace_chat_participant_id]"
    )

    __table_args__ = (
        Index('idx_chat_participants_user_id', 'user_id'),
        Index('idx_chat_participants_chat_room', 'chat_id'),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, default=MessageType.TEXT.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_edited = Column(Boolean, default=False)
    read_by = Column(JSONB, default={})
    reply_to_message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    is_forwarded = Column(Boolean, default=False)
    original_message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    forwarded_at = Column(DateTime(timezone=True), nullable=True)
    likes_count = Column(Integer, default=0, nullable=False)
    likes = Column(JSONB, default={})

    chat = relationship("Chat", back_populates="messages")
    user_profile = relationship("UserProfile", back_populates="messages")
    replied_message = relationship("Message", remote_side=[id], backref="replies", foreign_keys=[reply_to_message_id])
    original_message = relationship("Message", remote_side=[id], backref="forwarded_copies",
                                    foreign_keys=[original_message_id])

    __table_args__ = (
        Index('idx_messages_chat_room_created', 'chat_id', 'created_at'),
        Index('idx_messages_user_id', 'user_id'),
        Index('idx_messages_reply_to', 'reply_to_message_id'),
        Index('idx_messages_original_message', 'original_message_id'),
        Index('idx_messages_likes_count', 'likes_count'),
    )


class ProjectStatus(enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    PUBLISHED = "published"


class ProjectParticipantStatus(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ProjectRole(enum.Enum):
    SEO = "seo"
    DEVELOPER = "developer"
    DESIGNER = "designer"
    PROJECT_MANAGER = "project_manager"
    CONTENT_MANAGER = "content_manager"
    MARKETER = "marketer"
    ANALYST = "analyst"
    TESTER = "tester"
    DEVOPS = "devops"
    OTHER = "other"


class ProjectCategory(enum.Enum):
    TECHNOLOGY = "technology"
    SCIENCE = "science"
    MATHEMATICS = "mathematics"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    MEDICINE = "medicine"
    ENGINEERING = "engineering"
    ART = "art"
    DESIGN = "design"
    MUSIC = "music"
    LITERATURE = "literature"
    LINGUISTICS = "linguistics"
    HISTORY = "history"
    PHILOSOPHY = "philosophy"
    ECONOMICS = "economics"
    BUSINESS = "business"
    MARKETING = "marketing"
    EDUCATION = "education"
    ENVIRONMENT = "environment"
    SOCIAL = "social"
    OTHER = "other"


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    created_by = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status = Column(String, default=ProjectStatus.ACTIVE.value)
    wallet_id = Column(String, nullable=True)

    avatar_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("file_metadata.id", ondelete="SET NULL"),
        nullable=True
    )

    tags = Column(ARRAY(String), nullable=True)
    links = Column(ARRAY(String), nullable=True)
    github_links = Column(ARRAY(String), nullable=True)

    creator = relationship("UserProfile", foreign_keys=[created_by])
    workspaces = relationship("ProjectWorkspace", back_populates="project", cascade="all, delete-orphan")
    project_participants = relationship(
        "ProjectParticipant",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    avatar_file = relationship("FileMetadata", foreign_keys=[avatar_file_id])
    invitations = relationship("ProjectInvitation", back_populates="project", cascade="all, delete-orphan")

    post = relationship("ProjectPost", back_populates="project", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_projects_created_by', 'created_by'),
        Index('idx_projects_status', 'status'),
        Index('idx_projects_category', 'category'),
    )

class ProjectPost(Base):
    __tablename__ = "project_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    description = Column(Text, nullable=True)
    github_links = Column(ARRAY(String), nullable=True)
    likes_count = Column(Integer, default=0, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Отношения
    project = relationship("Project", back_populates="post")
    files = relationship("ProjectPostFile", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("ProjectLike", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_project_posts_published_at', 'published_at'),
        Index('idx_project_posts_likes_count', 'likes_count'),
    )


class ProjectLike(Base):
    __tablename__ = "project_likes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("project_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("ProjectPost", back_populates="likes")
    user = relationship("UserProfile")

    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='uq_project_like'),
        Index('idx_project_likes_post', 'post_id'),
        Index('idx_project_likes_user', 'user_id'),
        Index('idx_project_likes_created', 'created_at'),
    )


class Comment(Base):
    __tablename__ = "project_comments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("project_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("project_comments.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)
    likes = Column(JSONB, default={})
    replies_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_edited = Column(Boolean, default=False)

    post = relationship("ProjectPost", back_populates="comments")
    user = relationship("UserProfile")
    parent = relationship("Comment", remote_side=[id], backref="replies")

    __table_args__ = (
        Index('idx_comments_post', 'post_id'),
        Index('idx_comments_user', 'user_id'),
        Index('idx_comments_parent', 'parent_id'),
        Index('idx_comments_created', 'created_at'),
        Index('idx_comments_post_created', 'post_id', 'created_at'),
    )


class ProjectInvitation(Base):
    __tablename__ = "project_invitations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    invited_user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    invited_by = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default=InvitationStatus.PENDING.value)
    role = Column(String, default=ProjectRole.OTHER.value)
    permission_level = Column(String, default=ProjectParticipantStatus.VIEWER.value)
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)
    message = Column(Text, nullable=True)

    project = relationship("Project", back_populates="invitations")
    invited_user = relationship("UserProfile", foreign_keys=[invited_user_id])
    inviter = relationship("UserProfile", foreign_keys=[invited_by])

    __table_args__ = (
        Index('idx_project_invitations_project', 'project_id'),
        Index('idx_project_invitations_user', 'invited_user_id'),
        Index('idx_project_invitations_status', 'status'),
        UniqueConstraint('project_id', 'invited_user_id', name='uq_project_invitation_user'),
    )


class ProjectWorkspace(Base):
    __tablename__ = "project_workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    links = Column(ARRAY(String), nullable=True)
    github_links = Column(ARRAY(String), nullable=True)
    is_main = Column(Boolean, default=False)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="workspaces")
    chat = relationship("Chat", foreign_keys=[chat_id])
    workspace_participants = relationship(
        "WorkspaceParticipant",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="workspace", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_project_workspaces_project', 'project_id'),
        Index('idx_project_workspaces_main', 'project_id', 'is_main'),
    )


class ProjectParticipant(Base):
    __tablename__ = "project_participants"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default=ProjectParticipantStatus.VIEWER.value)
    role = Column(String, default=ProjectRole.OTHER.value)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="project_participants")
    user_profile = relationship("UserProfile", back_populates="project_participations")
    workspace_participations = relationship(
        "WorkspaceParticipant",
        back_populates="project_participant",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_project_participants_user', 'user_id'),
        Index('idx_project_participants_project', 'project_id'),
        Index('idx_project_participants_status', 'status'),
        Index('idx_project_participants_role', 'role'),
        UniqueConstraint('project_id', 'user_id', name='uq_project_participant'),
    )


class WorkspaceParticipant(Base):
    __tablename__ = "workspace_participants"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("project_workspaces.id", ondelete="CASCADE"), nullable=False)
    project_participant_id = Column(BigInteger, ForeignKey("project_participants.id", ondelete="CASCADE"),
                                    nullable=False)
    workspace_chat_participant_id = Column(
        BigInteger,
        ForeignKey("chat_participants.id", ondelete="SET NULL"),
        nullable=True
    )
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("ProjectWorkspace", back_populates="workspace_participants")
    project_participant = relationship("ProjectParticipant", back_populates="workspace_participations")
    workspace_chat_participant = relationship("ChatParticipant", back_populates="workspace_participant")

    __table_args__ = (
        Index('idx_workspace_participants_workspace', 'workspace_id'),
        Index('idx_workspace_participants_project_participant', 'project_participant_id'),
        UniqueConstraint('workspace_id', 'project_participant_id', name='uq_workspace_participant'),
    )


class FileType(enum.Enum):
    AVATAR = "avatar"
    PROJECT_FILE = "project_file"
    MESSAGE_ATTACHMENT = "message_attachment"
    PROJECT_AVATAR = "project_avatar"
    USER_DOCUMENT = "user_document"
    ANNOUNCEMENT_FILE = "announcement_file"
    APPLICATION_FILE = "application_file"
    PROJECT_POST_FILE = "project_post_file"
    TASK_ATTACHMENT = "task_attachment"
    CHAMPIONSHIP_FILE = "championship_file"
    OTHER = "other"


class FileMetadata(Base):
    __tablename__ = "file_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    s3_key = Column(String, nullable=False, unique=True)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    uploaded_by = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Отношения через связующие таблицы
    project_files = relationship("ProjectFile", back_populates="file", cascade="all, delete-orphan")
    messages = relationship("MessageAttachment", back_populates="file", cascade="all, delete-orphan")
    task_comments = relationship("TaskAttachment", back_populates="file", cascade="all, delete-orphan")
    announcements = relationship("AnnouncementFile", back_populates="file", cascade="all, delete-orphan")
    applications = relationship("ApplicationFile", back_populates="file", cascade="all, delete-orphan")

    uploader = relationship("UserProfile", foreign_keys=[uploaded_by])

    __table_args__ = (
        Index('idx_file_metadata_s3_key', 's3_key'),
        Index('idx_file_metadata_uploaded_by', 'uploaded_by'),
        Index('idx_file_metadata_file_type', 'file_type'),
        Index('idx_file_metadata_uploaded_at', 'uploaded_at'),
        Index('idx_file_metadata_size', 'size_bytes'),
    )


class ProjectFile(Base):
    """Связь файлов с проектами (многие ко многим)"""
    __tablename__ = "project_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("project_workspaces.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True)

    # Отношения
    project = relationship("Project", foreign_keys=[project_id])
    workspace = relationship("ProjectWorkspace", foreign_keys=[workspace_id])
    file = relationship("FileMetadata", back_populates="project_files")
    uploader = relationship("UserProfile", foreign_keys=[uploaded_by])

    __table_args__ = (
        Index('idx_project_files_project', 'project_id'),
        Index('idx_project_files_file', 'file_id'),
        Index('idx_project_files_workspace', 'workspace_id'),
        Index('idx_project_files_uploaded_by', 'uploaded_by'),
        Index('idx_project_files_uploaded_at', 'uploaded_at'),
        UniqueConstraint('project_id', 'file_id', name='uq_project_file'),
    )


class ProjectPostFile(Base):
    """Связь файлов с постами проектов в ленте"""
    __tablename__ = "project_post_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("project_posts.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, default=0)
    attached_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("ProjectPost", foreign_keys=[post_id])
    file = relationship("FileMetadata", foreign_keys=[file_id])

    __table_args__ = (
        Index('idx_project_post_files_post', 'post_id'),
        Index('idx_project_post_files_file', 'file_id'),
        Index('idx_project_post_files_order', 'post_id', 'order'),
        UniqueConstraint('post_id', 'file_id', name='uq_project_post_file'),
    )


class MessageAttachment(Base):
    """Связь файлов с сообщениями"""
    __tablename__ = "message_attachments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False)
    attached_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", foreign_keys=[message_id])
    file = relationship("FileMetadata", foreign_keys=[file_id])

    __table_args__ = (
        Index('idx_message_attachments_message', 'message_id'),
        Index('idx_message_attachments_file', 'file_id'),
        UniqueConstraint('message_id', 'file_id', name='uq_message_attachment'),
    )


class TaskPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(enum.Enum):
    IDEA = "idea"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskType(enum.Enum):
    IDEA = "idea"
    TASK = "task"
    URGENT_TASK = "urgent_task"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("project_workspaces.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String, nullable=False)
    priority = Column(String, default=TaskPriority.MEDIUM.value)
    status = Column(String, default=TaskStatus.IDEA.value)
    deadline = Column(DateTime(timezone=True), nullable=True)
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    assignees = Column(ARRAY(BigInteger), nullable=True)

    workspace = relationship("ProjectWorkspace", back_populates="tasks")
    creator_profile = relationship("UserProfile", foreign_keys=[created_by])
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_tasks_workspace', 'workspace_id'),
        Index('idx_tasks_created_by', 'created_by'),
        Index('idx_tasks_status', 'status'),
        Index('idx_tasks_priority', 'priority'),
        Index('idx_tasks_type', 'task_type'),
        Index('idx_tasks_deadline', 'deadline'),
        Index('idx_tasks_created_at', 'created_at'),
        Index('idx_tasks_assignees', 'assignees', postgresql_using='gin'),
    )


class TaskComment(Base):
    __tablename__ = "task_comments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_edited = Column(Boolean, default=False)

    task = relationship("Task", back_populates="comments")
    user_profile = relationship("UserProfile")
    attachments = relationship("TaskAttachment", back_populates="comment", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_task_comments_task', 'task_id'),
        Index('idx_task_comments_user', 'user_id'),
        Index('idx_task_comments_created_at', 'created_at'),
    )


class TaskAttachment(Base):
    __tablename__ = "task_attachments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    comment_id = Column(BigInteger, ForeignKey("task_comments.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False)
    attached_at = Column(DateTime(timezone=True), server_default=func.now())

    comment = relationship("TaskComment", back_populates="attachments")
    file = relationship("FileMetadata", back_populates="task_comments")

    __table_args__ = (
        Index('idx_task_attachments_comment', 'comment_id'),
        Index('idx_task_attachments_file', 'file_id'),
        Index('idx_task_attachments_comment_file', 'comment_id', 'file_id', unique=True),
    )


class TaskStatistic(Base):
    __tablename__ = "task_statistics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("project_workspaces.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    total_tasks = Column(Integer, default=0)
    idea_count = Column(Integer, default=0)
    todo_count = Column(Integer, default=0)
    in_progress_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    done_count = Column(Integer, default=0)
    cancelled_count = Column(Integer, default=0)
    urgent_total = Column(Integer, default=0)
    urgent_overdue = Column(Integer, default=0)
    total_estimated_hours = Column(Integer, default=0)
    total_actual_hours = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_task_stats_workspace_date', 'workspace_id', 'date'),
        Index('idx_task_stats_date', 'date'),
    )


class RelationshipStatus(enum.Enum):
    PENDING = "pending"
    FRIEND = "friend"
    BLOCKED = "blocked"


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    related_user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default=RelationshipStatus.PENDING.value)
    action_user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("UserProfile", foreign_keys=[user_id], backref="sent_relationships")
    related_user = relationship("UserProfile", foreign_keys=[related_user_id], backref="received_relationships")
    action_user = relationship("UserProfile", foreign_keys=[action_user_id])

    __table_args__ = (
        Index('idx_relationships_user_id', 'user_id'),
        Index('idx_relationships_related_user_id', 'related_user_id'),
        Index('idx_relationships_status', 'status'),
        Index('idx_relationships_user_related', 'user_id', 'related_user_id'),
        Index('idx_relationships_related_user', 'related_user_id', 'user_id'),
        UniqueConstraint('user_id', 'related_user_id', name='uq_user_relationship'),
    )


class AnnouncementStatus(enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ApplicationStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class VoteType(enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    questions = Column(ARRAY(Text), nullable=False, default=[])
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("project_workspaces.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default=AnnouncementStatus.ACTIVE.value)
    created_by = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", foreign_keys=[project_id])
    workspace = relationship("ProjectWorkspace", foreign_keys=[workspace_id])
    creator = relationship("UserProfile", foreign_keys=[created_by])
    applications = relationship("Application", back_populates="announcement", cascade="all, delete-orphan")
    files = relationship("AnnouncementFile", back_populates="announcement", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_announcements_project', 'project_id'),
        Index('idx_announcements_workspace', 'workspace_id'),
        Index('idx_announcements_status', 'status'),
        Index('idx_announcements_created_at', 'created_at'),
        Index('idx_announcements_created_by', 'created_by'),
    )


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    announcement_id = Column(UUID(as_uuid=True), ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    links = Column(ARRAY(String), nullable=False, default=[])
    likes = Column(JSONB, default={})
    dislikes = Column(JSONB, default={})
    status = Column(String, default=ApplicationStatus.PENDING.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    announcement = relationship("Announcement", back_populates="applications")
    user = relationship("UserProfile", foreign_keys=[user_id])
    files = relationship("ApplicationFile", back_populates="application", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_applications_announcement', 'announcement_id'),
        Index('idx_applications_user', 'user_id'),
        Index('idx_applications_status', 'status'),
        Index('idx_applications_created_at', 'created_at'),
        Index('idx_applications_announcement_status', 'announcement_id', 'status'),
        UniqueConstraint('announcement_id', 'user_id', name='uq_announcement_user'),
    )


class AnnouncementFile(Base):
    __tablename__ = "announcement_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    announcement_id = Column(UUID(as_uuid=True), ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False)
    attached_at = Column(DateTime(timezone=True), server_default=func.now())

    announcement = relationship("Announcement", foreign_keys=[announcement_id])
    file = relationship("FileMetadata", foreign_keys=[file_id])

    __table_args__ = (
        Index('idx_announcement_files_announcement', 'announcement_id'),
        Index('idx_announcement_files_file', 'file_id'),
        UniqueConstraint('announcement_id', 'file_id', name='uq_announcement_file'),
    )


class ApplicationFile(Base):
    __tablename__ = "application_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False)
    attached_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", foreign_keys=[application_id])
    file = relationship("FileMetadata", foreign_keys=[file_id])

    __table_args__ = (
        Index('idx_application_files_application', 'application_id'),
        Index('idx_application_files_file', 'file_id'),
        UniqueConstraint('application_id', 'file_id', name='uq_application_file'),
    )


class Championship(Base):
    """Модель для кейс-чемпионатов"""
    __tablename__ = "championships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="inactive")  # inactive, active, completed

    # Настройки чемпионата
    max_winners = Column(Integer, nullable=False, default=1)
    max_participants = Column(Integer, nullable=False)  # максимум решений-проектов
    prize_amount = Column(BigInteger, nullable=False, default=0)  # общий приз в нанотонах
    prize_distribution = Column(ARRAY(BigInteger), nullable=True)  # распределение приза по местам

    # Связь с проектом-организатором и пользователем
    created_by = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    organizer_project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # Временные рамки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deadline = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Отношения
    creator = relationship("UserProfile", foreign_keys=[created_by])
    organizer_project = relationship("Project", foreign_keys=[organizer_project_id])
    championship_files = relationship("ChampionshipFile", back_populates="championship", cascade="all, delete-orphan")
    solutions = relationship("ChampionshipSolution", back_populates="championship", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_championships_status', 'status'),
        Index('idx_championships_created_by', 'created_by'),
        Index('idx_championships_deadline', 'deadline'),
        Index('idx_championships_created_at', 'created_at'),
    )


class ChampionshipSolution(Base):
    """Модель для решений (проектов) чемпионата"""
    __tablename__ = "championship_solutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    championship_id = Column(UUID(as_uuid=True), ForeignKey("championships.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Информация о решении
    submitted_by = Column(BigInteger, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="submitted")  # submitted, winner, etc.

    # Место в чемпионате (0 - не определено)
    place = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Отношения
    championship = relationship("Championship", back_populates="solutions")
    project = relationship("Project", foreign_keys=[project_id])
    submitter = relationship("UserProfile", foreign_keys=[submitted_by])

    __table_args__ = (
        Index('idx_solutions_championship', 'championship_id'),
        Index('idx_solutions_project', 'project_id'),
        UniqueConstraint('championship_id', 'project_id', name='uq_championship_solution'),
        UniqueConstraint('championship_id', 'submitted_by', name='uq_user_solution_per_championship'),
    )


class ChampionshipFile(Base):
    """Связь файлов с чемпионатами"""
    __tablename__ = "championship_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    championship_id = Column(UUID(as_uuid=True), ForeignKey("championships.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("file_metadata.id", ondelete="CASCADE"), nullable=False)
    attached_at = Column(DateTime(timezone=True), server_default=func.now())

    championship = relationship("Championship", foreign_keys=[championship_id])
    file = relationship("FileMetadata", foreign_keys=[file_id])

    __table_args__ = (
        Index('idx_championship_files_championship', 'championship_id'),
        Index('idx_championship_files_file', 'file_id'),
        UniqueConstraint('championship_id', 'file_id', name='uq_championship_file'),
    )