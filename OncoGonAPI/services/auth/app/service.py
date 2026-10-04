"""Authentication use-cases. Routes stay thin; all rules live here."""

import uuid
from datetime import timedelta

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from . import security
from .config import get_settings
from .models import PasswordResetCode, RefreshToken, User
from .schemas import AuthResponse, RegisterRequest, TokenPair, UserOut

settings = get_settings()

INVALID_CREDENTIALS = HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
INVALID_REFRESH = HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please sign in again.")


async def _issue_tokens(db: AsyncSession, user: User, user_agent: str | None, family_id: uuid.UUID | None = None) -> TokenPair:
    access = security.create_jwt(
        user.id,
        "access",
        timedelta(minutes=settings.access_token_ttl_minutes),
        {"role": user.role, "email": user.email},
    )
    raw, digest = security.new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            token_hash=digest,
            user_agent=(user_agent or "")[:255] or None,
            expires_at=security.now() + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    return TokenPair(access_token=access, refresh_token=raw, expires_in=settings.access_token_ttl_minutes * 60)


async def register(db: AsyncSession, data: RegisterRequest, user_agent: str | None) -> AuthResponse:
    user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        password_hash=security.hash_password(data.password),
        role=data.role,
        institution=data.institution or None,
        last_login_at=security.now(),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    tokens = await _issue_tokens(db, user, user_agent)
    await db.commit()
    await db.refresh(user)
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


async def login(db: AsyncSession, email: str, password: str, user_agent: str | None) -> AuthResponse:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        security.verify_password(password, security.DUMMY_HASH)
        raise INVALID_CREDENTIALS

    if user.locked_until and user.locked_until > security.now():
        minutes = max(1, int((user.locked_until - security.now()).total_seconds() // 60) + 1)
        raise HTTPException(status.HTTP_423_LOCKED, f"Too many failed attempts. Try again in {minutes} minute(s).")

    if not security.verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.locked_until = security.now() + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
        await db.commit()
        raise INVALID_CREDENTIALS

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")

    if security.needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = security.now()
    tokens = await _issue_tokens(db, user, user_agent)
    await db.commit()
    await db.refresh(user)
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


async def refresh(db: AsyncSession, raw_token: str, user_agent: str | None) -> TokenPair:
    stored = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == security.sha256(raw_token)))
    if stored is None:
        raise INVALID_REFRESH
    if stored.revoked_at is not None:
        # A rotated token was replayed: assume theft and end every session in this login family.
        await _revoke_family(db, stored.family_id)
        await db.commit()
        raise INVALID_REFRESH
    if stored.expires_at <= security.now():
        raise INVALID_REFRESH

    user = await db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise INVALID_REFRESH

    stored.revoked_at = security.now()
    tokens = await _issue_tokens(db, user, user_agent, family_id=stored.family_id)
    await db.commit()
    return tokens


async def logout(db: AsyncSession, raw_token: str) -> None:
    stored = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == security.sha256(raw_token)))
    if stored is not None:
        await _revoke_family(db, stored.family_id)
        await db.commit()


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=security.now())
    )


async def current_user(db: AsyncSession, access_token: str) -> User:
    try:
        payload = security.decode_jwt(access_token, "access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token.", {"WWW-Authenticate": "Bearer"})
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found.", {"WWW-Authenticate": "Bearer"})
    return user


async def request_password_reset(db: AsyncSession, email: str) -> str | None:
    """Creates a 6-digit code. Returns it (for dev delivery) or None when the email is unknown."""
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        return None
    # Only the newest code is valid.
    await db.execute(
        update(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.id, PasswordResetCode.consumed_at.is_(None))
        .values(consumed_at=security.now())
    )
    code = security.new_reset_code()
    db.add(
        PasswordResetCode(
            user_id=user.id,
            code_hash=security.hash_password(code),
            expires_at=security.now() + timedelta(minutes=settings.reset_code_ttl_minutes),
        )
    )
    await db.commit()
    return code


async def verify_reset_code(db: AsyncSession, email: str, code: str) -> str:
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "The code is invalid or has expired.")
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        raise invalid
    entry = await db.scalar(
        select(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.id, PasswordResetCode.consumed_at.is_(None))
        .order_by(PasswordResetCode.created_at.desc())
        .limit(1)
    )
    if entry is None or entry.expires_at <= security.now() or entry.attempts >= settings.reset_code_max_attempts:
        raise invalid
    if not security.verify_password(code, entry.code_hash):
        entry.attempts += 1
        await db.commit()
        raise invalid
    entry.consumed_at = security.now()
    await db.commit()
    return security.create_jwt(user.id, "password_reset", timedelta(minutes=settings.reset_token_ttl_minutes))


async def reset_password(db: AsyncSession, reset_token: str, new_password: str) -> None:
    try:
        payload = security.decode_jwt(reset_token, "password_reset")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reset link expired. Request a new code.")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reset link expired. Request a new code.")
    user.password_hash = security.hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    # Sign out everywhere after a password change.
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=security.now())
    )
    await db.commit()
