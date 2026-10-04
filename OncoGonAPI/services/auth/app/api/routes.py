import logging

from fastapi import APIRouter, Depends, Header, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .. import service
from ..config import get_settings
from ..db import get_session
from ..models import User
from ..schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResetTokenResponse,
    TokenPair,
    UserOut,
    VerifyCodeRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=True)
settings = get_settings()
log = logging.getLogger("oncogon.auth")


async def require_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_session),
) -> User:
    return await service.current_user(db, creds.credentials)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_session), user_agent: str | None = Header(None)):
    return await service.register(db, body, user_agent)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_session), user_agent: str | None = Header(None)):
    return await service.login(db, body.email, body.password, user_agent)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_session), user_agent: str | None = Header(None)):
    return await service.refresh(db, body.refresh_token, user_agent)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_session)):
    await service.logout(db, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(require_user)):
    return user


@router.post("/password/forgot", response_model=ForgotPasswordResponse, status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_session)):
    code = await service.request_password_reset(db, body.email)
    message = "If an account exists for this email, a 6-digit code has been sent."
    if code and settings.is_development:
        # No email provider is configured yet. Never enabled outside development.
        log.warning("Password reset code for %s: %s (development only)", body.email, code)
        return ForgotPasswordResponse(message=message, debug_code=code)
    return ForgotPasswordResponse(message=message)


@router.post("/password/verify", response_model=ResetTokenResponse)
async def verify_code(body: VerifyCodeRequest, db: AsyncSession = Depends(get_session)):
    token = await service.verify_reset_code(db, body.email, body.code)
    return ResetTokenResponse(reset_token=token, expires_in=settings.reset_token_ttl_minutes * 60)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_session)):
    await service.reset_password(db, body.reset_token, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
