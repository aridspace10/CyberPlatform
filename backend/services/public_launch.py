"""Feature boundary for the initial public Sandbox release."""

import os

from fastapi import HTTPException
from services.session_service import is_sandbox_session


def public_sandbox_only() -> bool:
    value = os.environ.get("CYBERPLATFORM_PUBLIC_SANDBOX_ONLY", "")
    return value.strip().lower() == "true"


def require_multiplayer_enabled() -> None:
    if public_sandbox_only():
        raise HTTPException(status_code=404, detail="This feature is unavailable")


def require_public_sandbox_owner(db, session, user_id: int) -> None:
    if public_sandbox_only() and (
        session.creatorID != user_id or not is_sandbox_session(db, session.id)
    ):
        raise HTTPException(status_code=404, detail="Session not found")
