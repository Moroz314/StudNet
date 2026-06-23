from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from starlette.responses import JSONResponse
from .schemas import *
from .service.utils import verify_token
from .service.auth_service import get_user_auth_service, AuthUserService
#from ..utils import exception_handler

auth_router = APIRouter()
service = Depends(get_user_auth_service)
get_user_id = Depends(verify_token)


@auth_router.post('/user/register-init',
                  response_model=InitVerificationResponse,
                  description="Инициализация регистрации пользователя"
                  )
async def register_init(data: UserRegister, auth: AuthUserService = service):
    await auth.register_init(data)

    return InitVerificationResponse(
        message="Код подтверждения отправлен на ваш email",
        email=data.email
    )


@auth_router.post('/user/register',
                  response_model=RegisterResponse,
                  status_code=201,
                  description="Проверка кода и регистрация пользователя.")
async def register_user(data: VerificationRequest, auth: AuthUserService = service):
    access_token = await auth.verify_and_register(data)

    return RegisterResponse(
        access_token=access_token
    )


@auth_router.post('/user/login',
                  response_model=LoginResponse,
                  description='Аутентификация пользователя'
                  )
def login_user(data: UserLogIn, auth: AuthUserService = service):
    access_token = auth.login(data)

    return LoginResponse(
        access_token=access_token
    )


@auth_router.patch('/user/connect-github',
                 description='Подключение Github'
                 )
async def connect_github(code: str,
                         user_id: int = get_user_id,
                         auth: AuthUserService = service):

    await auth.get_github_access_token(code=code, user_id=user_id)

    return JSONResponse(content={
            "status": "Github был успешно подключён.",
        },
        status_code=status.HTTP_200_OK
    )


