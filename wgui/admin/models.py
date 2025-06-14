from pydantic import BaseModel, EmailStr, field_validator, TypeAdapter


class AddUserData(BaseModel):
    username: str
    email: EmailStr
    password: str


class EmailSettingsData(BaseModel):
    from_email: EmailStr
    to_email: str
    smtp_server: str
    smtp_port: int
    smtp_user: str | None = None
    smtp_pass: str | None = None

    @property
    def recipients(self) -> list[str]:
        return [e.strip() for e in self.to_email.split(',') if e.strip()]

    @field_validator('to_email')
    @classmethod
    def validate_to_email(cls, v: str) -> str:
        emails = [e.strip() for e in v.split(',') if e.strip()]
        if not emails:
            raise ValueError('At least one recipient is required')
        adapter = TypeAdapter(EmailStr)
        for e in emails:
            adapter.validate_python(e)
        return ', '.join(emails)

