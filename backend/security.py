"""Shared security utilities for input validation and path safety."""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import HTTPException

from .session_manager import _get_session_state_dir

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def validate_session_id(session_id: str) -> str:
    """Validate that *session_id* matches UUID v4 hex format.

    Returns the validated id unchanged; raises 400 on mismatch.
    """
    if not UUID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    return session_id


def safe_session_dir(session_id: str) -> Path:
    """Return a validated, resolved session directory path.

    Guarantees:
    * *session_id* is a valid UUID string.
    * The resolved path lives inside the session-state directory.
    * The path is not a symlink.

    Raises ``HTTPException`` on any violation.
    """
    validate_session_id(session_id)

    state_dir = _get_session_state_dir().resolve()
    raw_session_dir = state_dir / session_id

    # Symlink guard (check before resolve, which follows symlinks)
    if raw_session_dir.is_symlink():
        raise HTTPException(status_code=404, detail="Session not found")

    session_dir = raw_session_dir.resolve()

    # Path-traversal guard
    if not str(session_dir).startswith(str(state_dir) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    return session_dir
