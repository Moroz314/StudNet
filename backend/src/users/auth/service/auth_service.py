import asyncio
from starlette.responses import JSONResponse
from ....database.repositories.user.auth import UserRepository
from ...auth.schemas import *
from .utils import *
from fastapi.exceptions import HTTPException
from fastapi import status
import httpx
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from ....database.core import get_db
from ....database.redis.redis_auth import RedisAuth
from fastapi_mail import FastMail, ConnectionConfig
from .email_service import EmailService

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_USERNAME"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

fast_mail = FastMail(conf)

client_id = os.getenv("GITHUB_APP_ID")
client_secret = os.getenv("GITHUB_APP_SECRET")

def get_user_auth_service(db: Session = Depends(get_db)):
    user_repo = UserRepository(session=db)
    return AuthUserService(user_repo=user_repo)

class AuthUserService:
    def __init__(self, user_repo: UserRepository,
                 redis_service: RedisAuth = RedisAuth(),
                 email_service: EmailService = EmailService()):

        self.user_repo = user_repo
        self.redis_service = redis_service
        self.email_service = email_service

    async def register_init(self, data: UserRegister):
        email = str(data.email)

        if self.user_repo.get_user_by_email(email):
            raise HTTPException(
                detail="Пользователь с данным email уже существует.",
                status_code=status.HTTP_409_CONFLICT
            )

        code = self.redis_service.generate_code()

        user_data = dict(data)
        user_data['password'] = get_password_hash(data.password)

        try:
            await self.redis_service.store_verification_data(email, user_data, code)
            asyncio.create_task(self.email_service.send_verification_email(email, code))

            return True

        except Exception as e:
            print(e)
            raise HTTPException(
                detail="Внутренняя ошибка сервера.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    async def verify_and_register(self, data: VerificationRequest):
        email = str(data.email)

        redis_data = await self.redis_service.get_verification_data(email)

        # Проверяем лимит попыток
        if await self.redis_service.is_rate_limited(str(data.email)):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много неверных попыток. Попробуйте позже."
            )

        if not redis_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Код устарел или недействителен. Запросите новый код."
            )

        if redis_data['code'] != data.code:
            await self.redis_service.increment_attempts(str(data.email))
            remaining_attempts = 5 - (redis_data.get('attempts', 0) + 1)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неверный код подтверждения. Осталось попыток: {remaining_attempts}"
            )

        # Код верный - создаем пользователя
        user_data = redis_data['user_data']
        user = self.user_repo.create(user_data)

        # Удаляем данные из Redis
        await self.redis_service.delete_verification_data(str(data.email))

        access_token = create_access_token(
            {
                "sub": str(user.id),
                "role": "user"
            }
        )

        return access_token

    def login(self, data: UserLogIn):
        email, password = str(data.email), data.password

        user = self.user_repo.get_user_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        user = User.model_validate(user, from_attributes=True)

        if verify_password(password, user.password):
            access_token = create_access_token({"sub": str(user.id), "role": "user"})

            return access_token

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wrong password."
            )

    async def get_github_access_token(self, code: str, user_id: int):
        url = "https://github.com/login/oauth/access_token"
        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code
        }
        headers = {
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url=url, params=params, headers=headers)

        response_json = response.json()
        access_token = response_json["access_token"]

        result = self.user_repo.update_github_access_token(access_token=access_token,
                                                  user_id=user_id)

        return result





