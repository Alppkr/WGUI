from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginData(BaseModel):
    username: str
    password: str


class UpdateAccountData(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
