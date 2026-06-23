from .base import BaseAPIClient
from .project import ProjectClientMixin
from .workspace import WorkspaceClientMixin
from .task import TaskClientMixin
from .comment import CommentClientMixin
from .statistics import StatisticsClientMixin
from .file import FileClientMixin
from .avatar import AvatarClientMixin
from .profile import ProfileClientMixin
from .relationships import RelationshipsClientMixin
from .chat import ChatClientMixin
from .channel import ChannelClientMixin
from .project_feed import ProjectFeedClientMixin
from .user_feed import UserFeedClientMixin
from .announcements import AnnouncementClientMixin
from ..config import BASE_URL


class ExtendedAPIClient(
    BaseAPIClient,
    ProjectClientMixin,
    WorkspaceClientMixin,
    TaskClientMixin,
    CommentClientMixin,
    StatisticsClientMixin,
    FileClientMixin,
    AvatarClientMixin,
    ProfileClientMixin,
    RelationshipsClientMixin,
    ChatClientMixin,
    ChannelClientMixin,
    ProjectFeedClientMixin,
    UserFeedClientMixin,
    AnnouncementClientMixin,
):
    """Расширенный клиент API со всеми методами"""

    def __init__(self, base_url: str = BASE_URL):
        super().__init__(base_url)
        self.login()  # Автоматическая аутентификация при создании