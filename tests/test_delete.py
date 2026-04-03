"""Tests for session deletion functionality."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.session_manager import delete_session, delete_sessions_by_date_range

client = TestClient(app)

S1_UUID = "a0000000-0000-0000-0000-000000000001"
S2_UUID = "a0000000-0000-0000-0000-000000000002"
S3_UUID = "a0000000-0000-0000-0000-000000000003"
NONEXIST_UUID = "b0000000-0000-0000-0000-000000000099"


def _make_session(
    base: Path,
    session_id: str,
    updated_at: str = "2025-01-15T12:00:00.000Z",
    lock_pid: int | None = None,
) -> Path:
    session_dir = base / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    workspace = f"""\
id: {session_id}
cwd: /home/user/project
summary: Test session
created_at: 2025-01-01T10:00:00.000Z
updated_at: {updated_at}
"""
    (session_dir / "workspace.yaml").write_text(workspace)
    (session_dir / "events.jsonl").write_text('{"type":"test"}\n')
    if lock_pid is not None:
        (session_dir / f"inuse.{lock_pid}.lock").write_text(str(lock_pid))
    return session_dir


# ---------------------------------------------------------------------------
# Unit: delete_session
# ---------------------------------------------------------------------------


class TestDeleteSession:
    def test_deletes_inactive_session(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            result = delete_session(S1_UUID)
        assert result == "deleted"
        assert not (tmp_path / S1_UUID).exists()

    def test_returns_active_for_live_session(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, lock_pid=os.getpid())
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            result = delete_session(S1_UUID)
        assert result == "active"
        assert (tmp_path / S1_UUID).is_dir()

    def test_returns_not_found_for_missing(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            result = delete_session(NONEXIST_UUID)
        assert result == "not_found"

    def test_returns_not_found_for_invalid_uuid(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            result = delete_session("not-a-uuid")
        assert result == "not_found"


# ---------------------------------------------------------------------------
# Unit: delete_sessions_by_date_range
# ---------------------------------------------------------------------------


class TestDeleteSessionsByDateRange:
    def test_deletes_sessions_in_range(self, tmp_path: Path) -> None:
        from datetime import date

        _make_session(tmp_path, S1_UUID, updated_at="2025-01-10T12:00:00.000Z")
        _make_session(tmp_path, S2_UUID, updated_at="2025-01-20T12:00:00.000Z")
        _make_session(tmp_path, S3_UUID, updated_at="2025-02-15T12:00:00.000Z")

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            deleted, skipped, errors = delete_sessions_by_date_range(
                date(2025, 1, 1), date(2025, 1, 31)
            )

        assert set(deleted) == {S1_UUID, S2_UUID}
        assert S3_UUID not in deleted
        assert not skipped
        assert not errors
        assert (tmp_path / S3_UUID).is_dir()

    def test_skips_active_sessions(self, tmp_path: Path) -> None:
        from datetime import date

        _make_session(tmp_path, S1_UUID, updated_at="2025-01-15T12:00:00.000Z")
        _make_session(
            tmp_path,
            S2_UUID,
            updated_at="2025-01-15T12:00:00.000Z",
            lock_pid=os.getpid(),
        )

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            deleted, skipped, errors = delete_sessions_by_date_range(
                date(2025, 1, 1), date(2025, 1, 31)
            )

        assert deleted == [S1_UUID]
        assert skipped == [S2_UUID]
        assert (tmp_path / S2_UUID).is_dir()

    def test_inclusive_boundaries(self, tmp_path: Path) -> None:
        from datetime import date

        _make_session(tmp_path, S1_UUID, updated_at="2025-01-01T00:00:00.000Z")
        _make_session(tmp_path, S2_UUID, updated_at="2025-01-31T23:59:59.000Z")

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            deleted, _, _ = delete_sessions_by_date_range(
                date(2025, 1, 1), date(2025, 1, 31)
            )

        assert set(deleted) == {S1_UUID, S2_UUID}


# ---------------------------------------------------------------------------
# API: DELETE /api/sessions/{session_id}
# ---------------------------------------------------------------------------


class TestDeleteSingleEndpoint:
    def test_deletes_inactive_session(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.delete(f"/api/sessions/{S1_UUID}")
        assert resp.status_code == 200
        data = resp.json()
        assert S1_UUID in data["deleted"]
        assert not (tmp_path / S1_UUID).exists()

    def test_409_for_active_session(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, lock_pid=os.getpid())
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.delete(f"/api/sessions/{S1_UUID}")
        assert resp.status_code == 409
        assert (tmp_path / S1_UUID).is_dir()

    def test_404_for_missing_session(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.delete(f"/api/sessions/{NONEXIST_UUID}")
        assert resp.status_code == 404

    def test_400_for_malformed_uuid(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.delete("/api/sessions/not-a-uuid")
        assert resp.status_code == 400

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.delete("/api/sessions/../../etc/passwd")
        assert resp.status_code in (400, 404, 405, 422)


# ---------------------------------------------------------------------------
# API: DELETE /api/sessions (batch)
# ---------------------------------------------------------------------------


class TestDeleteBatchEndpoint:
    def test_batch_deletes_multiple_sessions(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID)
        _make_session(tmp_path, S2_UUID)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.request(
                "DELETE",
                "/api/sessions",
                json={"session_ids": [S1_UUID, S2_UUID]},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert set(data["deleted"]) == {S1_UUID, S2_UUID}

    def test_batch_empty_list_returns_empty_result(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.request(
                "DELETE",
                "/api/sessions",
                json={"session_ids": []},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] == []
        assert data["skipped_active"] == []
        assert data["not_found"] == []
        assert data["errors"] == {}

    def test_batch_categorizes_results(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID)
        _make_session(tmp_path, S2_UUID, lock_pid=os.getpid())
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.request(
                "DELETE",
                "/api/sessions",
                json={"session_ids": [S1_UUID, S2_UUID, NONEXIST_UUID, "bad-id"]},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert S1_UUID in data["deleted"]
        assert S2_UUID in data["skipped_active"]
        assert NONEXIST_UUID in data["not_found"]
        assert "bad-id" in data["not_found"]


# ---------------------------------------------------------------------------
# API: DELETE /api/sessions/by-date
# ---------------------------------------------------------------------------


class TestDeleteByDateEndpoint:
    def test_deletes_sessions_in_range(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, updated_at="2025-01-15T12:00:00.000Z")
        _make_session(tmp_path, S2_UUID, updated_at="2025-02-15T12:00:00.000Z")
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.request(
                "DELETE",
                "/api/sessions/by-date",
                json={"date_from": "2025-01-01", "date_to": "2025-01-31"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert S1_UUID in data["deleted"]
        assert S2_UUID not in data["deleted"]

    def test_400_when_date_from_after_date_to(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.request(
                "DELETE",
                "/api/sessions/by-date",
                json={"date_from": "2025-02-01", "date_to": "2025-01-01"},
            )
        assert resp.status_code == 400

    def test_400_for_invalid_date_format(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.request(
                "DELETE",
                "/api/sessions/by-date",
                json={"date_from": "not-a-date", "date_to": "2025-01-31"},
            )
        assert resp.status_code == 400

    def test_skips_active_sessions(self, tmp_path: Path) -> None:
        _make_session(
            tmp_path,
            S1_UUID,
            updated_at="2025-01-15T12:00:00.000Z",
            lock_pid=os.getpid(),
        )
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.request(
                "DELETE",
                "/api/sessions/by-date",
                json={"date_from": "2025-01-01", "date_to": "2025-01-31"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert S1_UUID in data["skipped_active"]
        assert not data["deleted"]


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class TestDeleteSecurity:
    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.delete("/api/sessions/../../etc/passwd")
        assert resp.status_code in (400, 404, 405, 422)

    def test_symlink_session_rejected(self, tmp_path: Path) -> None:
        # Create a real directory outside session-state
        real_dir = tmp_path / "outside"
        real_dir.mkdir()
        (real_dir / "workspace.yaml").write_text("id: fake\n")

        # Create a symlink inside session-state pointing to it
        symlink = tmp_path / S1_UUID
        symlink.symlink_to(real_dir)

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.delete(f"/api/sessions/{S1_UUID}")
        # Must NOT delete the real directory
        assert resp.status_code in (400, 404)
        assert real_dir.is_dir(), "Real directory must not be deleted via symlink"
