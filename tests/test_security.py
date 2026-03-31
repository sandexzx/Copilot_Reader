"""Tests for backend.security module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.security import UUID_PATTERN, safe_session_dir, validate_session_id


class TestValidateSessionId:
    def test_accepts_valid_uuid(self) -> None:
        result = validate_session_id("c753e394-40eb-4c8f-b40b-981316a7eeff")
        assert result == "c753e394-40eb-4c8f-b40b-981316a7eeff"

    def test_accepts_uppercase_uuid(self) -> None:
        result = validate_session_id("C753E394-40EB-4C8F-B40B-981316A7EEFF")
        assert result == "C753E394-40EB-4C8F-B40B-981316A7EEFF"

    def test_rejects_plain_string(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_session_id("not-a-uuid")
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid session ID format"

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_session_id("")
        assert exc_info.value.status_code == 400

    def test_rejects_path_traversal(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_session_id("../../../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_rejects_uuid_with_extra_chars(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_session_id("c753e394-40eb-4c8f-b40b-981316a7eeff; rm -rf /")
        assert exc_info.value.status_code == 400


class TestSafeSessionDir:
    def test_returns_path_for_valid_uuid(self, tmp_path: Path) -> None:
        session_id = "a0000000-0000-0000-0000-000000000001"
        (tmp_path / session_id).mkdir()
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            result = safe_session_dir(session_id)
        assert result.name == session_id

    def test_rejects_invalid_uuid(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            with pytest.raises(HTTPException) as exc_info:
                safe_session_dir("bad-id")
            assert exc_info.value.status_code == 400

    def test_rejects_symlink(self, tmp_path: Path) -> None:
        session_id = "a0000000-0000-0000-0000-000000000002"
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        symlink = tmp_path / session_id
        symlink.symlink_to(real_dir)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            with pytest.raises(HTTPException) as exc_info:
                safe_session_dir(session_id)
            assert exc_info.value.status_code == 404
