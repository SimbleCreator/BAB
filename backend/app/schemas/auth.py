from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import normalize_email

PASSWORD_MIN = 10
PASSWORD_MAX = 128


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    is_adult: bool = Field(description="User confirms they are 18 or older. Must be true.")
    accepts_privacy: bool = Field(description="User accepts the privacy policy. Must be true.")

    _email = field_validator("email")(normalize_email)

    @field_validator("is_adult")
    @classmethod
    def _adult(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must be 18 or older to use B.A.B.")
        return v

    @field_validator("accepts_privacy")
    @classmethod
    def _consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Please accept the privacy policy to continue.")
        return v


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX)
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class UserOut(BaseModel):
    id: int
    email: str
    is_admin: bool
    created_at: datetime
    has_profile: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int = Field(description="Access token lifetime in seconds.")
    user: UserOut
