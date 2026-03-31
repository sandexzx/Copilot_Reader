"""Tests for REST API session endpoints."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import SessionSummary

client = TestClient(app)

# Valid UUID used as directory names for test sessions
S1_UUID = "a0000000-0000-0000-0000-000000000001"
NONEXIST_UUID = "b0000000-0000-0000-0000-000000000099"

SAMPLE_WORKSPACE_YAML = """\
id: test-session-1
cwd: /home/user/project
summary: Test session
created_at: 2026-03-15T10:00:00.000Z
updated_at: 2026-03-15T12:00:00.000Z
git_root: /home/user/project
branch: main
"""


def _make_session(
    base: Path,
    session_id: str,
    workspace_yaml: str | None = None,
    events: list[dict] | None = None,
) -> Path:
    session_dir = base / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    if workspace_yaml is not None:
        (session_dir / "workspace.yaml").write_text(workspace_yaml)
    if events is not None:
        lines = [json.dumps(e) for e in events]
        (session_dir / "events.jsonl").write_text("\n".join(lines) + "\n")
    return session_dir


SAMPLE_EVENTS = [
    {
        "type": "session.start",
        "data": {"sessionId": "test"},
        "id": "aaa",
        "timestamp": "2026-01-01T00:00:00.000Z",
        "parentId": None,
    },
    {
        "type": "user.message",
        "data": {"content": "hello"},
        "id": "bbb",
        "timestamp": "2026-01-01T00:00:01.000Z",
        "parentId": "aaa",
    },
    {
        "type": "tool.execution_start",
        "data": {"toolCallId": "tc1", "toolName": "bash"},
        "id": "ccc",
        "timestamp": "2026-01-01T00:00:02.000Z",
        "parentId": "bbb",
    },
    {
        "type": "tool.execution_complete",
        "data": {"toolCallId": "tc1", "success": True},
        "id": "ddd",
        "timestamp": "2026-01-01T00:00:03.000Z",
        "parentId": "ccc",
    },
]


def _find_tree_node(node: dict, event_id: str) -> dict | None:
    if node["event"]["id"] == event_id:
        return node
    for child in node["children"]:
        found = _find_tree_node(child, event_id)
        if found is not None:
            return found
    return None


# ---------------------------------------------------------------------------
# GET /api/sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    def test_returns_json_array(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, SAMPLE_WORKSPACE_YAML, SAMPLE_EVENTS)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_session_summary_fields(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, SAMPLE_WORKSPACE_YAML, SAMPLE_EVENTS)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions")
        item = resp.json()[0]
        assert item["id"] == "test-session-1"
        assert item["summary"] == "Test session"
        assert item["cwd"] == "/home/user/project"
        assert "created_at" in item
        assert "updated_at" in item
        assert item["is_active"] is False
        assert item["event_count"] == 4

    def test_empty_state_dir(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/sessions/{id}
# ---------------------------------------------------------------------------


class TestGetSession:
    def test_returns_session_detail(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, SAMPLE_WORKSPACE_YAML, SAMPLE_EVENTS)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{S1_UUID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "test-session-1"
        assert data["git_root"] == "/home/user/project"
        assert data["branch"] == "main"

    def test_404_for_unknown_id(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{NONEXIST_UUID}")
        assert resp.status_code == 404
        assert resp.json() == {"detail": "Session not found"}

    def test_400_for_invalid_uuid(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get("/api/sessions/not-a-uuid")
        assert resp.status_code == 400
        assert resp.json() == {"detail": "Invalid session ID format"}


# ---------------------------------------------------------------------------
# GET /api/sessions/{id}/events
# ---------------------------------------------------------------------------


class TestGetEvents:
    def test_returns_events_array(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, SAMPLE_WORKSPACE_YAML, SAMPLE_EVENTS)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{S1_UUID}/events")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 4

    def test_events_have_tool_name_correlated(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, SAMPLE_WORKSPACE_YAML, SAMPLE_EVENTS)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{S1_UUID}/events")
        data = resp.json()
        complete = [e for e in data if e["type"] == "tool.execution_complete"]
        assert len(complete) == 1
        assert complete[0]["tool_name"] == "bash"

    def test_404_for_unknown_session(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{NONEXIST_UUID}/events")
        assert resp.status_code == 404
        assert resp.json() == {"detail": "Session not found"}


# ---------------------------------------------------------------------------
# GET /api/sessions/{id}/stats
# ---------------------------------------------------------------------------


class TestGetStats:
    def test_returns_session_stats(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, SAMPLE_WORKSPACE_YAML, SAMPLE_EVENTS)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{S1_UUID}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 4
        assert data["user_messages"] == 1
        assert data["tool_calls"] == 1
        assert data["duration_seconds"] >= 0

    def test_returns_cache_write_tokens(self, tmp_path: Path) -> None:
        events = [
            *SAMPLE_EVENTS,
            {
                "type": "session.shutdown",
                "data": {
                    "modelMetrics": {
                        "gpt-5.4": {
                            "usage": {
                                "inputTokens": 120,
                                "outputTokens": 30,
                                "cacheReadTokens": 45,
                                "cacheWriteTokens": 15,
                            }
                        }
                    },
                    "currentModel": "gpt-5.4",
                },
                "id": "eee",
                "timestamp": "2026-01-01T00:00:04.000Z",
                "parentId": "ddd",
            },
        ]
        _make_session(tmp_path, S1_UUID, SAMPLE_WORKSPACE_YAML, events)

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{S1_UUID}/stats")

        assert resp.status_code == 200
        assert resp.json()["cache_write_tokens"] == 15

    def test_404_for_unknown_session(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{NONEXIST_UUID}/stats")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/sessions/{id}/tree
# ---------------------------------------------------------------------------


class TestGetTree:
    def test_returns_tree_nodes(self, tmp_path: Path) -> None:
        _make_session(tmp_path, S1_UUID, SAMPLE_WORKSPACE_YAML, SAMPLE_EVENTS)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{S1_UUID}/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1  # one root
        root = data[0]
        assert root["event"]["id"] == "aaa"
        assert len(root["children"]) == 1

    def test_404_for_unknown_session(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{NONEXIST_UUID}/tree")
        assert resp.status_code == 404

    def test_returns_enriched_tree_metadata(self, tmp_path: Path) -> None:
        events = [
            {
                "type": "session.start",
                "data": {"sessionId": "test-session"},
                "id": "aaa",
                "timestamp": "2026-01-01T00:00:00.000Z",
                "parentId": None,
            },
            {
                "type": "user.message",
                "data": {"content": "hello from api tree"},
                "id": "bbb",
                "timestamp": "2026-01-01T00:00:01.000Z",
                "parentId": "aaa",
            },
            {
                "type": "tool.execution_start",
                "data": {"toolCallId": "tc1", "toolName": "bash"},
                "id": "ccc",
                "timestamp": "2026-01-01T00:00:02.000Z",
                "parentId": "bbb",
            },
            {
                "type": "tool.execution_complete",
                "data": {"toolCallId": "tc1", "success": True},
                "id": "ddd",
                "timestamp": "2026-01-01T00:00:03.000Z",
                "parentId": "ccc",
            },
            {
                "type": "subagent.started",
                "data": {"toolCallId": "agent-1", "agentName": "explore"},
                "id": "eee",
                "timestamp": "2026-01-01T00:00:04.000Z",
                "parentId": "bbb",
            },
            {
                "type": "subagent.completed",
                "data": {"toolCallId": "agent-1", "agentName": "explore"},
                "id": "fff",
                "timestamp": "2026-01-01T00:00:06.000Z",
                "parentId": "eee",
            },
        ]
        _make_session(tmp_path, S1_UUID, SAMPLE_WORKSPACE_YAML, events)

        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            resp = client.get(f"/api/sessions/{S1_UUID}/tree")

        assert resp.status_code == 200
        root = resp.json()[0]
        assert root["event_count"] == 6
        assert root["semantic_kind"] == "session"

        user_node = _find_tree_node(root, "bbb")
        assert user_node is not None
        assert user_node["semantic_kind"] == "user"
        assert user_node["brief_description"] == "hello from api tree"

        tool_node = _find_tree_node(root, "ddd")
        assert tool_node is not None
        assert tool_node["semantic_kind"] == "tool"
        assert tool_node["status"] == "completed"
        assert tool_node["duration_ms"] == 1000
        assert tool_node["event"]["tool_name"] == "bash"

        subagent_node = _find_tree_node(root, "fff")
        assert subagent_node is not None
        assert subagent_node["semantic_kind"] == "subagent"
        assert subagent_node["agent_name"] == "explore"
        assert subagent_node["status"] == "completed"


# ---------------------------------------------------------------------------
# Real data integration tests
# ---------------------------------------------------------------------------

REAL_SESSION_DIR = Path.home() / ".copilot" / "session-state"
TEST_SESSION = "c753e394-40eb-4c8f-b40b-981316a7eeff"


class TestRealDataIntegration:
    @pytest.mark.skipif(
        not REAL_SESSION_DIR.is_dir(),
        reason="Real session-state directory not available",
    )
    def test_list_sessions_count(self) -> None:
        env = os.environ.copy()
        env.pop("COPILOT_SESSION_STATE_DIR", None)
        with patch.dict(os.environ, env, clear=True):
            resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 100, f"Expected ~136 sessions, got {len(data)}"

    @pytest.mark.skipif(
        not (REAL_SESSION_DIR / TEST_SESSION).is_dir(),
        reason="Test session not available",
    )
    def test_get_real_session_events(self) -> None:
        env = os.environ.copy()
        env.pop("COPILOT_SESSION_STATE_DIR", None)
        with patch.dict(os.environ, env, clear=True):
            resp = client.get(f"/api/sessions/{TEST_SESSION}/events")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 100

    @pytest.mark.skipif(
        not (REAL_SESSION_DIR / TEST_SESSION).is_dir(),
        reason="Test session not available",
    )
    def test_get_real_session_stats(self) -> None:
        env = os.environ.copy()
        env.pop("COPILOT_SESSION_STATE_DIR", None)
        with patch.dict(os.environ, env, clear=True):
            resp = client.get(f"/api/sessions/{TEST_SESSION}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] > 0
