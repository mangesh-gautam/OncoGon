import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Roles a person may pick at sign-up. Platform administrator and auditor are assigned by an admin.
SelfServiceRole = Literal[
    "researcher",
    "principal_investigator",
    "scientific_reviewer",
    "ml_scientist",
    "tto_officer",
    "industry_user",
]


def _check_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number.")
    return value


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(max_length=128)
    role: SelfServiceRole = "researcher"
    institution: str | None = Field(default=None, max_length=160)

    @field_validator("full_name", "institution")
    @classmethod
    def strip(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    institution: str | None
    created_at: datetime
    last_login_at: datetime | None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    user: UserOut
    tokens: TokenPair


class ForgotPasswordResponse(BaseModel):
    message: str
    # Development only: there is no email service yet, so the code is returned for testing.
    debug_code: str | None = None


class ResetTokenResponse(BaseModel):
    reset_token: str
    expires_in: int


class MessageResponse(BaseModel):
    message: str
