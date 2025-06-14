from pydantic import BaseModel, EmailStr


class AddUserData(BaseModel):
    username: str
    email: EmailStr
    password: str


class EmailSettingsData(BaseModel):
    from_email: EmailStr
    to_email: EmailStr
    smtp_server: str
    smtp_port: int
    smtp_user: str | None = None
    smtp_pass: str | None = None
