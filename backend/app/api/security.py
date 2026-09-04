"""Signed session tokens.

Demo-grade identity: every response-bearing request carries a compact token the
server can verify without any per-user server state.

Format: ``v1.<base64url(json{user_id, iat, exp})>.<base64url(hmac-sha256)>``

* ``user_id`` is verified on every request.
* ``exp`` makes tokens expire (TTL configurable via ``SESSION_TTL_SECONDS``).
* The HMAC signature binds the payload to ``SESSION_SECRET``, so a token cannot
  be forged or tampered with by a client.

Production-grade authentication (passwords, OAuth, secure-cookie-only sessions)
is deliberately out of scope; this module is the seam where it would slot in.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from app.config import get_settings

_PREFIX = "v1"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _signature(body: str) -> str:
    secret = get_settings().SESSION_SECRET.encode("utf-8")
    digest = hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()
    return _b64(digest)


def _payload(user_id: str, now: float, ttl_seconds: int) -> dict:
    return {
        "user_id": user_id,
        "iat": int(now),
        "exp": int(now) + ttl_seconds,
    }


def sign_session(
    user_id: str,
    *,
    now: float | None = None,
    ttl_seconds: int | None = None,
) -> str:
    """Mint a signed session token for ``user_id``."""
    now = now if now is not None else time.time()
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.SESSION_TTL_SECONDS
    body = _b64(
        json.dumps(_payload(user_id, now, ttl), separators=(",", ":")).encode("utf-8")
    )
    return f"{_PREFIX}.{body}.{_signature(body)}"


def verify_session(token: str | None, *, now: float | None = None) -> str | None:
    """Return the verified ``user_id``, or ``None`` for bad/expired tokens."""
    token = (token or "").strip()
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != _PREFIX:
        return None
    _, body, signature = parts
    if not hmac.compare_digest(_signature(body), signature):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    user_id = payload.get("user_id")
    exp = payload.get("exp")
    if not isinstance(user_id, str) or not user_id or not isinstance(exp, int):
        return None
    now = now if now is not None else time.time()
    if now >= exp:
        return None
    return user_id


def token_expiry(token: str) -> int | None:
    """The token's ``exp`` unix timestamp, or ``None`` if the signature is bad.

    Unlike :func:`verify_session`, this does NOT require the token to still be
    fresh — callers (e.g. the mint endpoint) want the declared expiry even for
    a just-created token.
    """
    token = (token or "").strip()
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != _PREFIX:
        return None
    _, body, signature = parts
    if not hmac.compare_digest(_signature(body), signature):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    exp = payload.get("exp")
    return exp if isinstance(exp, int) else None