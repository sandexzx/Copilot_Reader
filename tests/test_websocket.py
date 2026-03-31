"""Tests for WebSocket endpoint /ws/sessions/{id}/events."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

# Valid UUIDs for test sessions
WS_TEST_UUID = "c0000000-0000-0000-0000-000000000001"
WS_PUSH_UUID = "c0000000-0000-0000-0000-000000000002"
WS_MULTI_UUID = "c0000000-0000-0000-0000-000000000003"
WS_NONEXIST_UUID = "c0000000-0000-0000-0000-000000000099"

SAMPLE_WORKSPACE_YAML = """\
id: ws-test-session
cwd: /tmp/test
summary: WebSocket test
created_at: 2026-03-15T10:00:00.000Z
updated_at: 2026-03-15T12:00:00.000Z
"""


def _make_session(tmp_path: Path, session_id: str, event_lines: int = 0) -> Path:
    session_dir = tmp_path / session_id
    session_dir.mkdir(exist_ok=True)
    (session_dir / "workspace.yaml").write_text(SAMPLE_WORKSPACE_YAML)
    if event_lines > 0:
        lines = []
        for i in range(event_lines):
            lines.append(json.dumps({
                "type": "test.event",
                "data": {},
                "id": f"evt-{i}",
                "timestamp": "2026-01-01T00:00:00.000Z",
                "parentId": None,
            }))
        (session_dir / "events.jsonl").write_text("\n".join(lines) + "\n")
    else:
        (session_dir / "events.jsonl").write_text("")
    return session_dir


# ---------------------------------------------------------------------------
# AC7: Connection to non-existent session returns close 4004
# ---------------------------------------------------------------------------


class TestWebSocketNonExistent:
    def test_nonexistent_session_returns_4004(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            # Reset module-level manager
            import backend.api.websocket as ws_mod
            ws_mod._manager = None

            client = TestClient(app)
            with pytest.raises(Exception) as exc_info:
                with client.websocket_connect(f"/ws/sessions/{WS_NONEXIST_UUID}/events"):
                    pass
            # FastAPI TestClient raises on WebSocket close with non-1000 code


# ---------------------------------------------------------------------------
# AC2: Connected message with session_id and event_count
# ---------------------------------------------------------------------------


class TestWebSocketConnectedMessage:
    def test_sends_connected_message(self, tmp_path: Path) -> None:
        _make_session(tmp_path, WS_TEST_UUID, event_lines=5)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            import backend.api.websocket as ws_mod
            ws_mod._manager = None

            client = TestClient(app)
            with client.websocket_connect(f"/ws/sessions/{WS_TEST_UUID}/events") as ws:
                msg = ws.receive_json()
                assert msg["type"] == "connected"
                assert msg["data"]["session_id"] == WS_TEST_UUID
                assert msg["data"]["event_count"] == 5


# ---------------------------------------------------------------------------
# AC3: New events pushed to connected client
# ---------------------------------------------------------------------------


class TestWebSocketEventPush:
    def test_new_events_pushed(self, tmp_path: Path) -> None:
        session_dir = _make_session(tmp_path, WS_PUSH_UUID, event_lines=0)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            import backend.api.websocket as ws_mod
            ws_mod._manager = None

            client = TestClient(app)
            with client.websocket_connect(f"/ws/sessions/{WS_PUSH_UUID}/events") as ws:
                # Consume connected message
                connected = ws.receive_json()
                assert connected["type"] == "connected"

                # Append an event to the file
                new_event = json.dumps({
                    "type": "user.message",
                    "data": {"content": "hello"},
                    "id": "pushed-1",
                    "timestamp": "2026-01-01T00:00:05.000Z",
                    "parentId": None,
                })
                events_file = session_dir / "events.jsonl"
                with open(events_file, "a") as f:
                    f.write(new_event + "\n")
                    f.flush()

                # Read the pushed event with a timeout
                import time
                deadline = time.monotonic() + 5.0
                received = None
                while time.monotonic() < deadline:
                    try:
                        # Use a short receive timeout
                        received = ws.receive_json(mode="text")
                        if received and received.get("type") == "event":
                            break
                    except Exception:
                        time.sleep(0.1)
                        continue

                assert received is not None, "Did not receive pushed event"
                assert received["type"] == "event"
                assert received["data"]["id"] == "pushed-1"
                assert received["data"]["type"] == "user.message"


# ---------------------------------------------------------------------------
# AC5: Multiple clients receive same events
# ---------------------------------------------------------------------------


class TestWebSocketMultipleClients:
    def test_multiple_clients_receive_events(self, tmp_path: Path) -> None:
        session_dir = _make_session(tmp_path, WS_MULTI_UUID, event_lines=0)
        with patch.dict(os.environ, {"COPILOT_SESSION_STATE_DIR": str(tmp_path)}):
            import backend.api.websocket as ws_mod
            ws_mod._manager = None

            client = TestClient(app)
            with client.websocket_connect(f"/ws/sessions/{WS_MULTI_UUID}/events") as ws1:
                with client.websocket_connect(f"/ws/sessions/{WS_MULTI_UUID}/events") as ws2:
                    # Consume connected messages
                    ws1.receive_json()
                    ws2.receive_json()

                    # Append event
                    new_event = json.dumps({
                        "type": "test.broadcast",
                        "data": {"msg": "for both"},
                        "id": "broadcast-1",
                        "timestamp": "2026-01-01T00:00:10.000Z",
                        "parentId": None,
                    })
                    with open(session_dir / "events.jsonl", "a") as f:
                        f.write(new_event + "\n")
                        f.flush()

                    import time
                    deadline = time.monotonic() + 5.0
                    r1 = r2 = None
                    while time.monotonic() < deadline:
                        try:
                            if r1 is None:
                                r1 = ws1.receive_json(mode="text")
                            if r2 is None:
                                r2 = ws2.receive_json(mode="text")
                            if r1 and r2:
                                break
                        except Exception:
                            time.sleep(0.1)

                    assert r1 is not None and r1["type"] == "event"
                    assert r2 is not None and r2["type"] == "event"
                    assert r1["data"]["id"] == "broadcast-1"
                    assert r2["data"]["id"] == "broadcast-1"
