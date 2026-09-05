"""Session (identity) endpoints.

``POST /auth/session`` mints a server-generated anonymous identity and signs it
for later requests via the ``Authorization: Bearer`` header.  A client cannot
choose another user's id. ``GET /auth/me`` echoes the verified identity.

Production authentication (passwords, OAuth, cookie-only sessions over TLS) is
explicitly out of scope.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.api.deps import get_user_id
from app.api.security import sign_session, token_expiry

router = APIRouter(prefix="/auth", tags=["auth"])


class SessionOut(BaseModel):
    token: str
    user_id: str
    expires_at: int


class MeOut(BaseModel):
    user_id: str
    exp: int | None = None


@router.post("/session", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session() -> SessionOut:
    """Mint a fresh, opaque demo identity without accepting a user id."""
    user_id = f"anon_{secrets.token_urlsafe(18)}"
    token = sign_session(user_id)
    exp = token_expiry(token)
    assert exp is not None  # freshly minted token must carry an expiry
    return SessionOut(token=token, user_id=user_id, expires_at=exp)


@router.get("/me", response_model=MeOut, tags=["auth"])
def me(user_id: str = Depends(get_user_id)) -> MeOut:
    """Echo the identity verified for this request."""
    return MeOut(user_id=user_id, exp=None)
