from src.database.models import *
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, text, delete
from sqlalchemy import and_, update
from src.database.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    def create(self, data: dict) -> User:
        user = User(**data)
        self.session.add(user)
        self.session.commit()

        return user

    def get_user_by_email(self, email: str) -> User:
        user = self.session.query(User).filter(User.email == email).first()
        return user

    def get_user_by_id(self, user_id: int) -> User:
        user = self.session.query(User).filter(User.id == user_id).first()

        return user

    def update_github_access_token(self, access_token: str, user_id: int):
        stmt = (
            update(User).values(github_access_token=access_token)
            .filter(User.id == user_id)
        )

        self.session.execute(stmt)
        self.session.commit()

        return True

    def delete_user(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        self.session.delete(user)
        self.session.commit()
        return True



