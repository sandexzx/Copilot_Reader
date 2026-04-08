"""Session discovery and management."""

from __future__ import annotations

import json
import os
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from .models import CopilotUserInfo, Session, SessionSummary

_DEFAULT_SESSION_STATE_DIR = "~/.copilot/session-state"


def _get_session_state_dir() -> Path:
    raw = os.environ.get("COPILOT_SESSION_STATE_DIR") or _DEFAULT_SESSION_STATE_DIR
    return Path(os.path.expanduser(raw))


def _get_copilot_home() -> Path:
    return Path(os.path.expanduser("~/.copilot"))


def get_copilot_user_info() -> CopilotUserInfo:
    """Read current user info from ~/.copilot/config.json."""
    config_path = _get_copilot_home() / "config.json"
    if not config_path.is_file():
        return CopilotUserInfo()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        last_user = data.get("last_logged_in_user", {})
        current = last_user.get("login") if isinstance(last_user, dict) else None
        all_users = [
            u.get("login", "")
            for u in data.get("logged_in_users", [])
            if isinstance(u, dict) and u.get("login")
        ]
        return CopilotUserInfo(current_user=current, all_users=all_users)
    except (json.JSONDecodeError, OSError):
        return CopilotUserInfo()

def _count_lines(filepath: Path) -> int:
    """Count lines in a file without reading all content into memory."""
    try:
        count = 0
        with open(filepath, "rb") as f:
            for _ in f:
                count += 1
        return count
    except (OSError, IOError):
        return 0


def _parse_datetime(value: object) -> datetime:
    """Parse a datetime from a YAML value, handling strings and datetime objects."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    s = str(value)
    # Handle ISO format with Z suffix
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def get_session_metadata(session_dir: Path) -> dict:
    """Parse workspace.yaml and return metadata dict.

    Returns fallback values when workspace.yaml is missing or corrupted.
    """
    dir_name = session_dir.name
    fallback = {
        "id": dir_name,
        "cwd": "",
        "summary": None,
        "created_at": datetime.fromtimestamp(
            session_dir.stat().st_ctime, tz=timezone.utc
        ),
        "updated_at": datetime.fromtimestamp(
            session_dir.stat().st_mtime, tz=timezone.utc
        ),
        "git_root": None,
        "branch": None,
    }

    yaml_path = session_dir / "workspace.yaml"
    if not yaml_path.is_file():
        return fallback

    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
        return fallback

    if not isinstance(data, dict):
        return fallback

    return {
        "id": data.get("id", dir_name),
        "cwd": data.get("cwd", ""),
        "summary": data.get("summary") or None,
        "created_at": _parse_datetime(data["created_at"])
        if "created_at" in data
        else fallback["created_at"],
        "updated_at": _parse_datetime(data["updated_at"])
        if "updated_at" in data
        else fallback["updated_at"],
        "git_root": data.get("git_root"),
        "branch": data.get("branch"),
    }


def is_session_active(session_dir: Path) -> tuple[bool, int | None]:
    """Check if a session is active via lock file + PID validation.

    Returns (is_active, pid) tuple. pid is None when inactive.
    """
    try:
        lock_files = list(session_dir.glob("inuse.*.lock"))
    except OSError:
        return False, None

    for lock_file in lock_files:
        try:
            pid_str = lock_file.read_text().strip()
            pid = int(pid_str)
        except (OSError, ValueError):
            continue

        try:
            os.kill(pid, 0)
            return True, pid
        except PermissionError:
            # Process exists but we lack permission — still alive
            return True, pid
        except ProcessLookupError:
            # PID does not exist
            continue
        except OSError:
            continue

    return False, None


def discover_sessions() -> list[SessionSummary]:
    """Discover all Copilot sessions on disk.

    Returns SessionSummary objects sorted: active first (by updated_at desc),
    then inactive (by updated_at desc).
    """
    state_dir = _get_session_state_dir()
    if not state_dir.is_dir():
        return []

    sessions: list[SessionSummary] = []

    for entry in state_dir.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            continue

        meta = get_session_metadata(entry)
        active, _pid = is_session_active(entry)
        event_count = _count_lines(entry / "events.jsonl")

        created_at = meta["created_at"]
        updated_at = meta["updated_at"]

        sessions.append(
            SessionSummary(
                id=str(meta["id"]),
                cwd=meta["cwd"] or "",
                summary=meta["summary"] or "",
                created_at=created_at.isoformat() if isinstance(created_at, datetime) else str(created_at),
                updated_at=updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at),
                is_active=active,
                event_count=event_count,
            )
        )

    # Sort: active first (updated_at desc), then inactive (updated_at desc)
    active = sorted(
        (s for s in sessions if s.is_active),
        key=lambda s: s.updated_at,
        reverse=True,
    )
    inactive = sorted(
        (s for s in sessions if not s.is_active),
        key=lambda s: s.updated_at,
        reverse=True,
    )
    return active + inactive


def delete_session(session_id: str) -> str:
    """Delete a single session directory.

    Returns: "deleted", "active", "not_found", or error message starting with "error:".
    """
    from .security import safe_session_dir

    try:
        session_dir = safe_session_dir(session_id)
    except Exception:
        return "not_found"

    if not session_dir.is_dir():
        return "not_found"

    active, _pid = is_session_active(session_dir)
    if active:
        return "active"

    try:
        shutil.rmtree(session_dir)
        return "deleted"
    except Exception as e:
        return f"error:{e}"


def delete_sessions_by_date_range(
    date_from: date, date_to: date
) -> tuple[list[str], list[str], dict[str, str]]:
    """Find and delete all inactive sessions within date range (inclusive).

    Filters by updated_at. Returns (deleted_ids, skipped_active_ids, errors_dict).
    """
    state_dir = _get_session_state_dir()
    deleted: list[str] = []
    skipped_active: list[str] = []
    errors: dict[str, str] = {}

    if not state_dir.is_dir():
        return deleted, skipped_active, errors

    for entry in state_dir.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            continue

        session_id = entry.name
        meta = get_session_metadata(entry)
        updated_at = meta["updated_at"]

        if isinstance(updated_at, datetime):
            updated_date = updated_at.date()
        else:
            continue

        if not (date_from <= updated_date <= date_to):
            continue

        active, _pid = is_session_active(entry)
        if active:
            skipped_active.append(session_id)
            continue

        try:
            shutil.rmtree(entry)
            deleted.append(session_id)
        except Exception as e:
            errors[session_id] = str(e)

    return deleted, skipped_active, errors


def get_session(session_id: str) -> Session:
    """Get full details for a single session."""
    state_dir = _get_session_state_dir()
    session_dir = state_dir / session_id

    if not session_dir.is_dir():
        raise FileNotFoundError(f"Session not found: {session_id}")

    meta = get_session_metadata(session_dir)
    active, pid = is_session_active(session_dir)
    event_count = _count_lines(session_dir / "events.jsonl")

    created_at = meta["created_at"]
    updated_at = meta["updated_at"]

    return Session(
        id=str(meta["id"]),
        cwd=meta["cwd"] or "",
        summary=meta["summary"] or "",
        created_at=created_at.isoformat() if isinstance(created_at, datetime) else str(created_at),
        updated_at=updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at),
        is_active=active,
        event_count=event_count,
        git_root=meta.get("git_root"),
        branch=meta.get("branch"),
        pid=pid,
    )
