"""Session (identity) endpoints.

The product is single-user; this is a DEMO-GRADE auth seam. ``POST /auth/session``
mints a signed token for a user id (server-verified on later requests via the
``Authorization: Bearer`` header). ``GET /auth/me`` echoes the verified identity.

Production authentication (passwords, OAuth, cookie-only sessions over TLS) is
explicitly out of scope.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import DEFAULT_USER_ID, get_user_id
from app.api.security import sign_session, token_expiry
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class SessionRequest(BaseModel):
    # Default to the legacy single-user identity so a bare client still works.
    user_id: str = Field(default=DEFAULT_USER_ID, min_length=1, max_length=64)


class SessionOut(BaseModel):
    token: str
    user_id: str
    expires_at: int


class MeOut(BaseModel):
    user_id: str
    exp: int | None = None


@router.post("/session", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(body: SessionRequest) -> SessionOut:
    """Mint a signed session token for ``user_id``."""
    user_id = body.user_id.strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_id must not be blank",
        )
    token = sign_session(user_id)
    exp = token_expiry(token)
    assert exp is not None  # freshly minted token must carry an expiry
    return SessionOut(token=token, user_id=user_id, expires_at=exp)


@router.get("/me", response_model=MeOut, tags=["auth"])
def me(user_id: str = Depends(get_user_id)) -> MeOut:
    """Echo the identity verified for this request."""
    return MeOut(user_id=user_id, exp=None)