"""Database-backed fixed windows for the public account endpoints."""

import hashlib
import json
import math
import time

from db.modals import AuthRateLimit
from fastapi import HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

WINDOW_SECONDS = 300
LOGIN_ACCOUNT_CLIENT_LIMIT = 5
LOGIN_ACCOUNT_LIMIT = 30
LOGIN_CLIENT_LIMIT = 60
SIGNUP_CLIENT_LIMIT = 10
CONTACT_CLIENT_LIMIT = 5


def enforce_auth_rate_limit(
    db: Session, request: Request, action: str, username: str = ""
) -> None:
    """Count attempts before password hashing or verification.

    Uvicorn resolves trusted proxy headers into request.client. Reading raw
    forwarded headers here would let callers choose their own rate-limit key.
    """
    now = time.time()
    window_start = int(now // WINDOW_SECONDS) * WINDOW_SECONDS
    client = request.client.host if request.client else "unknown"
    if action == "login":
        account = username.strip().casefold()
        buckets = (
            (("login-account-client", account, client), LOGIN_ACCOUNT_CLIENT_LIMIT),
            (("login-account", account), LOGIN_ACCOUNT_LIMIT),
            (("login-client", client), LOGIN_CLIENT_LIMIT),
        )
    elif action == "signup":
        buckets = ((("signup-client", client), SIGNUP_CLIENT_LIMIT),)
    elif action == "contact":
        buckets = ((("contact-client", client), CONTACT_CLIENT_LIMIT),)
    else:
        raise ValueError(f"Unsupported auth action: {action}")

    limited = False
    # SQLite serializes these writes, including when several workers race to
    # increment the same window. The database is the backend's shared store.
    for identity, limit in buckets:
        key = hashlib.sha256(
            json.dumps((window_start, *identity), separators=(",", ":")).encode()
        ).hexdigest()
        statement = insert(AuthRateLimit).values(
            key=key, window_start=window_start, hits=1
        )
        db.execute(
            statement.on_conflict_do_update(
                index_elements=[AuthRateLimit.key],
                set_={"hits": AuthRateLimit.hits + 1},
            )
        )
        hits = db.scalar(select(AuthRateLimit.hits).where(AuthRateLimit.key == key))
        limited |= hits > limit

    # Retain the current and previous windows for a bounded table size.
    db.execute(
        delete(AuthRateLimit).where(
            AuthRateLimit.window_start < window_start - WINDOW_SECONDS
        )
    )
    db.commit()
    if limited:
        retry_after = max(1, math.ceil(window_start + WINDOW_SECONDS - now))
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
