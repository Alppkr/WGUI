from pydantic import BaseModel, EmailStr


class AddUserData(BaseModel):
    username: str
    email: EmailStr
    password: str
