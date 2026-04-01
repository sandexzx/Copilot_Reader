"""Tests for GET /api/sessions/stats/daily endpoint."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.usage_aggregator import _read_shutdown_metrics

client = TestClient(app)

S1_UUID = "a0000000-0000-0000-0000-000000000001"
S2_UUID = "a0000000-0000-0000-0000-000000000002"
S3_UUID = "a0000000-0000-0000-0000-000000000003"


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _yesterday_iso() -> str:
    from datetime import timedelta

    dt = datetime.now(timezone.utc) - timedelta(days=1)
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _workspace_yaml(created_at: str) -> str:
    return (
        f"id: test\n"
        f"cwd: /home/user/project\n"
        f"summary: Test\n"
        f"created_at: {created_at}\n"
        f"updated_at: {created_at}\n"
    )


def _shutdown_event(model_metrics: dict) -> dict:
    return {
        "type": "session.shutdown",
        "data": {"modelMetrics": model_metrics},
        "id": "shutdown-1",
        "timestamp": _today_iso(),
        "parentId": None,
    }


def _make_session(
    base: Path,
    session_id: str,
    created_at: str,
    events: list[dict] | None = None,
) -> Path:
    session_dir = base / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "workspace.yaml").write_text(_workspace_yaml(created_at))
    if events is not None:
        lines = [json.dumps(e) for e in events]
        (session_dir / "events.jsonl").write_text("\n".join(lines) + "\n")
    return session_dir


# ---------------------------------------------------------------------------
# _read_shutdown_metrics unit tests
# ---------------------------------------------------------------------------


class TestReadShutdownMetrics:
    def test_extracts_metrics_from_last_line(self, tmp_path: Path) -> None:
        metrics = {"gpt-5.4": {"usage": {"inputTokens": 100}, "requests": {"count": 1}}}
        events = [
            json.dumps({"type": "session.start", "data": {}}),
            json.dumps({"type": "session.shutdown", "data": {"modelMetrics": metrics}}),
        ]
        p = tmp_path / "events.jsonl"
        p.write_text("\n".join(events) + "\n")
        result = _read_shutdown_metrics(p)
        assert result == metrics

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        p.write_text("")
        assert _read_shutdown_metrics(p) is None

    def test_returns_none_when_last_line_is_not_shutdown(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        p.write_text(json.dumps({"type": "user.message", "data": {}}) + "\n")
        assert _read_shutdown_metrics(p) is None

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert _read_shutdown_metrics(tmp_path / "nonexistent.jsonl") is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        p.write_text("not json at all\n")
        assert _read_shutdown_metrics(p) is None


# ---------------------------------------------------------------------------
# GET /api/sessions/stats/daily
# ---------------------------------------------------------------------------


class TestDailyUsageEndpoint:
    def test_empty_state_dir(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions/stats/daily")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sessions_count"] == 0
        assert data["models"] == {}
        assert data["totals"]["input_tokens"] == 0

    def test_filters_to_today_only(self, tmp_path: Path) -> None:
        metrics = {
            "claude-sonnet-4": {
                "usage": {"inputTokens": 500, "outputTokens": 50, "cacheReadTokens": 0, "cacheWriteTokens": 0},
                "requests": {"count": 5, "cost": 1},
            }
        }
        _make_session(tmp_path, S1_UUID, _today_iso(), [_shutdown_event(metrics)])
        _make_session(tmp_path, S2_UUID, _yesterday_iso(), [_shutdown_event(metrics)])

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions/stats/daily")

        data = resp.json()
        assert data["sessions_count"] == 1
        assert data["totals"]["input_tokens"] == 500

    def test_aggregates_multiple_sessions(self, tmp_path: Path) -> None:
        metrics1 = {
            "claude-opus-4.6": {
                "usage": {"inputTokens": 1000, "outputTokens": 100, "cacheReadTokens": 200, "cacheWriteTokens": 10},
                "requests": {"count": 5, "cost": 3},
            }
        }
        metrics2 = {
            "claude-opus-4.6": {
                "usage": {"inputTokens": 2000, "outputTokens": 200, "cacheReadTokens": 400, "cacheWriteTokens": 20},
                "requests": {"count": 10, "cost": 2},
            }
        }
        _make_session(tmp_path, S1_UUID, _today_iso(), [_shutdown_event(metrics1)])
        _make_session(tmp_path, S2_UUID, _today_iso(), [_shutdown_event(metrics2)])

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions/stats/daily")

        data = resp.json()
        assert data["sessions_count"] == 2
        model = data["models"]["claude-opus-4.6"]
        assert model["input_tokens"] == 3000
        assert model["output_tokens"] == 300
        assert model["cache_read_tokens"] == 600
        assert model["cache_write_tokens"] == 30
        assert model["premium_requests"] == 5
        assert model["requests_count"] == 15

    def test_aggregates_multiple_models(self, tmp_path: Path) -> None:
        metrics = {
            "claude-opus-4.6": {
                "usage": {"inputTokens": 1000, "outputTokens": 100, "cacheReadTokens": 0, "cacheWriteTokens": 0},
                "requests": {"count": 5, "cost": 3},
            },
            "claude-haiku-4.5": {
                "usage": {"inputTokens": 500, "outputTokens": 50, "cacheReadTokens": 0, "cacheWriteTokens": 0},
                "requests": {"count": 10, "cost": 0},
            },
        }
        _make_session(tmp_path, S1_UUID, _today_iso(), [_shutdown_event(metrics)])

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions/stats/daily")

        data = resp.json()
        assert len(data["models"]) == 2
        assert data["totals"]["input_tokens"] == 1500
        assert data["totals"]["output_tokens"] == 150
        assert data["totals"]["premium_requests"] == 3

    def test_session_without_shutdown_counted_but_no_metrics(self, tmp_path: Path) -> None:
        events = [{"type": "session.start", "data": {}, "id": "a", "timestamp": _today_iso(), "parentId": None}]
        _make_session(tmp_path, S1_UUID, _today_iso(), events)

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions/stats/daily")

        data = resp.json()
        assert data["sessions_count"] == 1
        assert data["models"] == {}
        assert data["totals"]["input_tokens"] == 0

    def test_session_without_events_file_counted(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, _today_iso(), events=None)

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions/stats/daily")

        data = resp.json()
        assert data["sessions_count"] == 1
        assert data["models"] == {}

    def test_date_field_is_today_utc(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions/stats/daily")
        today = datetime.now(timezone.utc).date().isoformat()
        assert resp.json()["date"] == today

    def test_route_not_captured_by_session_id(self, tmp_path: Path) -> None:
        """Ensure /stats/daily is not interpreted as /{session_id}."""
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions/stats/daily")
        # Should be 200, not 400 (invalid session ID) or 404
        assert resp.status_code == 200
