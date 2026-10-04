"""Shared FastAPI dependencies: the signed-in user and the data repository."""

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings
from .repositories import MockResearchRepository, ResearchRepository

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: str
    email: str | None


def require_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> CurrentUser:
    """Verifies an access token issued by the auth service (no database round trip)."""
    settings = get_settings()
    try:
        if creds is None:
            raise jwt.InvalidTokenError("Missing token")
        payload = jwt.decode(
            creds.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "typ"]},
        )
        if payload.get("typ") != "access":
            raise jwt.InvalidTokenError("Wrong token type")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token.", {"WWW-Authenticate": "Bearer"})
    return CurrentUser(id=payload["sub"], role=payload.get("role", "researcher"), email=payload.get("email"))


_mock_repository = MockResearchRepository()


def get_repository() -> ResearchRepository:
    """The single switch point: return the real repository here once it exists."""
    return _mock_repository
