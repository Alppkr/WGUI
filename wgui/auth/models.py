from pydantic import BaseModel, EmailStr


class LoginData(BaseModel):
    username: str
    password: str


class ChangeEmailData(BaseModel):
    email: EmailStr


class ChangePasswordData(BaseModel):
    password: str
