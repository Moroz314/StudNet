from fastapi import FastAPI

from .projects.championships.service import ChampionshipService
from .users.auth.controller import auth_router
from .users.profile.controller import profile_router
from .users.chat.controller import chat_router
from .users.feed.controller import user_feed_router
from .users.relationship.controller import relationship_router
from .projects.core.controller import project_router
from .projects.files.controller import project_files_router
from .projects.tasks.controller import tasks_router
from .projects.channel.controller import channel_router
from .projects.feed.controller import feed_router
from .projects.announcements.controller import announcement_router
from .files.controller import files_router
from .projects.championships.controller import championship_router


def register_routers(app: FastAPI):
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(chat_router)
    app.include_router(user_feed_router)
    app.include_router(project_router)
    app.include_router(project_files_router)
    app.include_router(tasks_router)
    app.include_router(relationship_router)
    app.include_router(channel_router)
    app.include_router(feed_router)
    app.include_router(announcement_router)
    app.include_router(files_router)
    app.include_router(championship_router)