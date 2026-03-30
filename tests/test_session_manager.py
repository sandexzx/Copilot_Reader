"""Tests for session_manager module."""

from __future__ import annotations

import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.models import Session, SessionSummary
from backend.session_manager import (
    discover_sessions,
    get_session,
    get_session_metadata,
    is_session_active,
)

SAMPLE_WORKSPACE_YAML = """\
id: aaa-bbb-ccc
cwd: /home/user/project
summary: My test session
created_at: 2026-03-15T10:00:00.000Z
updated_at: 2026-03-15T12:00:00.000Z
git_root: /home/user/project
branch: main
"""

MINIMAL_WORKSPACE_YAML = """\
id: ddd-eee-fff
cwd: /tmp/somewhere
created_at: 2026-03-10T08:00:00.000Z
updated_at: 2026-03-10T09:00:00.000Z
"""


def _make_session(
    tmp_path: Path,
    session_id: str,
    workspace_yaml: str | None = None,
    event_lines: int = 0,
    lock_pid: int | None = None,
) -> Path:
    """Helper to create a mock session directory."""
    session_dir = tmp_path / session_id
    session_dir.mkdir()
    if workspace_yaml is not None:
        (session_dir / "workspace.yaml").write_text(workspace_yaml)
    if event_lines > 0:
        lines = ['{"type":"test"}\n'] * event_lines
        (session_dir / "events.jsonl").write_text("".join(lines))
    if lock_pid is not None:
        (session_dir / f"inuse.{lock_pid}.lock").write_text(str(lock_pid))
    return session_dir


# --- AC6: get_session_metadata ---


class TestGetSessionMetadata:
    def test_parses_full_workspace_yaml(self, tmp_path: Path) -> None:
        session_dir = _make_session(tmp_path, "aaa-bbb-ccc", SAMPLE_WORKSPACE_YAML)
        meta = get_session_metadata(session_dir)
        assert meta["id"] == "aaa-bbb-ccc"
        assert meta["cwd"] == "/home/user/project"
        assert meta["summary"] == "My test session"
        assert meta["git_root"] == "/home/user/project"
        assert meta["branch"] == "main"
        assert isinstance(meta["created_at"], datetime)
        assert isinstance(meta["updated_at"], datetime)

    def test_parses_minimal_workspace_yaml(self, tmp_path: Path) -> None:
        session_dir = _make_session(tmp_path, "ddd-eee-fff", MINIMAL_WORKSPACE_YAML)
        meta = get_session_metadata(session_dir)
        assert meta["id"] == "ddd-eee-fff"
        assert meta["git_root"] is None
        assert meta["branch"] is None
        assert meta["summary"] is None or meta["summary"] == ""

    def test_missing_workspace_yaml_returns_fallback(self, tmp_path: Path) -> None:
        session_dir = _make_session(tmp_path, "no-yaml-here")
        meta = get_session_metadata(session_dir)
        assert meta["id"] == "no-yaml-here"
        assert meta["cwd"] == ""
        assert meta["summary"] is None

    def test_corrupted_workspace_yaml_returns_fallback(self, tmp_path: Path) -> None:
        session_dir = _make_session(tmp_path, "bad-yaml-id")
        (session_dir / "workspace.yaml").write_text(":::not valid yaml{{{}}}:::")
        meta = get_session_metadata(session_dir)
        assert meta["id"] == "bad-yaml-id"
        assert meta["cwd"] == ""


# --- AC2: is_session_active ---


class TestIsSessionActive:
    def test_no_lock_file_means_inactive(self, tmp_path: Path) -> None:
        session_dir = _make_session(tmp_path, "no-lock", SAMPLE_WORKSPACE_YAML)
        assert is_session_active(session_dir) == (False, None)

    def test_lock_with_running_pid_means_active(self, tmp_path: Path) -> None:
        my_pid = os.getpid()
        session_dir = _make_session(
            tmp_path, "active-sess", SAMPLE_WORKSPACE_YAML, lock_pid=my_pid
        )
        active, pid = is_session_active(session_dir)
        assert active is True
        assert pid == my_pid

    def test_lock_with_dead_pid_means_inactive(self, tmp_path: Path) -> None:
        dead_pid = 999999999  # Almost certainly not running
        session_dir = _make_session(
            tmp_path, "dead-sess", SAMPLE_WORKSPACE_YAML, lock_pid=dead_pid
        )
        active, pid = is_session_active(session_dir)
        assert active is False
        assert pid is None


# --- AC1, AC3, AC4: discover_sessions ---


class TestDiscoverSessions:
    def test_returns_session_summaries(self, tmp_path: Path) -> None:
        _make_session(tmp_path, "sess-1", SAMPLE_WORKSPACE_YAML, event_lines=5)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            sessions = discover_sessions()
        assert len(sessions) == 1
        s = sessions[0]
        assert isinstance(s, SessionSummary)
        assert s.id == "aaa-bbb-ccc"
        assert s.cwd == "/home/user/project"
        assert s.summary == "My test session"
        assert s.event_count == 5
        assert s.is_active is False

    def test_event_count_zero_when_no_events_file(self, tmp_path: Path) -> None:
        _make_session(tmp_path, "no-events", SAMPLE_WORKSPACE_YAML)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            sessions = discover_sessions()
        assert sessions[0].event_count == 0

    def test_handles_missing_workspace_yaml(self, tmp_path: Path) -> None:
        _make_session(tmp_path, "no-yaml")
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            sessions = discover_sessions()
        assert len(sessions) == 1
        assert sessions[0].id == "no-yaml"
        assert sessions[0].cwd == ""

    def test_handles_corrupted_workspace_yaml(self, tmp_path: Path) -> None:
        session_dir = _make_session(tmp_path, "corrupt-yaml")
        (session_dir / "workspace.yaml").write_text("{{{{not yaml")
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            sessions = discover_sessions()
        assert len(sessions) == 1
        assert sessions[0].id == "corrupt-yaml"

    def test_sorting_active_first_then_by_date(self, tmp_path: Path) -> None:
        my_pid = os.getpid()
        # Older active session
        yaml_active_old = """\
id: active-old
cwd: /a
created_at: 2026-03-01T10:00:00.000Z
updated_at: 2026-03-01T12:00:00.000Z
"""
        # Newer active session
        yaml_active_new = """\
id: active-new
cwd: /b
created_at: 2026-03-10T10:00:00.000Z
updated_at: 2026-03-10T12:00:00.000Z
"""
        # Older inactive session
        yaml_inactive_old = """\
id: inactive-old
cwd: /c
created_at: 2026-02-01T10:00:00.000Z
updated_at: 2026-02-01T12:00:00.000Z
"""
        # Newer inactive session
        yaml_inactive_new = """\
id: inactive-new
cwd: /d
created_at: 2026-03-20T10:00:00.000Z
updated_at: 2026-03-20T12:00:00.000Z
"""
        _make_session(tmp_path, "s1", yaml_active_old, lock_pid=my_pid)
        _make_session(tmp_path, "s2", yaml_active_new, lock_pid=my_pid)
        _make_session(tmp_path, "s3", yaml_inactive_old)
        _make_session(tmp_path, "s4", yaml_inactive_new)

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            sessions = discover_sessions()

        ids = [s.id for s in sessions]
        # Active sessions first (newest first), then inactive (newest first)
        assert ids == ["active-new", "active-old", "inactive-new", "inactive-old"]

    def test_env_var_configures_path(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        _make_session(custom_dir, "env-test", SAMPLE_WORKSPACE_YAML)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(custom_dir)}):
            sessions = discover_sessions()
        assert len(sessions) == 1


# --- get_session ---


class TestGetSession:
    def test_returns_full_session_with_git_info(self, tmp_path: Path) -> None:
        _make_session(tmp_path, "full-sess", SAMPLE_WORKSPACE_YAML, event_lines=10)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            s = get_session("full-sess")
        assert isinstance(s, Session)
        assert s.id == "aaa-bbb-ccc"
        assert s.git_root == "/home/user/project"
        assert s.branch == "main"
        assert s.event_count == 10
        assert s.pid is None

    def test_returns_session_with_active_pid(self, tmp_path: Path) -> None:
        my_pid = os.getpid()
        _make_session(
            tmp_path, "active-full", SAMPLE_WORKSPACE_YAML, lock_pid=my_pid
        )
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            s = get_session("active-full")
        assert s.is_active is True
        assert s.pid == my_pid

    def test_raises_for_missing_session(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            with pytest.raises(FileNotFoundError):
                get_session("nonexistent")


# --- AC5: Performance against real data ---


class TestRealData:
    @pytest.mark.skipif(
        not Path(os.path.expanduser("~/.copilot/session-state")).is_dir(),
        reason="Real session-state directory not available",
    )
    def test_discover_real_sessions_performance(self) -> None:
        import time

        # Unset env var to use default path
        env = os.environ.copy()
        env.pop("COPILOT_SESSION_STATE_DIR", None)
        with patch.dict(os.environ, env, clear=True):
            start = time.monotonic()
            sessions = discover_sessions()
            elapsed = time.monotonic() - start

        assert len(sessions) >= 100, f"Expected ~136 sessions, got {len(sessions)}"
        assert elapsed < 3.0, f"Took {elapsed:.2f}s, expected < 3s"
        # Verify sorting: all active before inactive
        saw_inactive = False
        for s in sessions:
            if not s.is_active:
                saw_inactive = True
            elif saw_inactive:
                pytest.fail("Active session found after inactive session — bad sort")
