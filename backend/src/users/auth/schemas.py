from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class VerificationRequest(BaseModel):
    email: EmailStr
    code: str

class InitVerificationResponse(BaseModel):
    message: str
    email: EmailStr

class UserLogIn(UserRegister):
    pass

class User(UserRegister):
    id: int
    github_access_token: Optional[str] = None


class RegisterResponse(BaseModel):
    access_token: str

class LoginResponse(RegisterResponse):
    pass