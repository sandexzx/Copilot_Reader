"""Tests for backend.event_parser module."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.event_parser import (
    build_event_tree,
    compute_stats,
    correlate_tool_names,
    parse_events_file,
)
from backend.models import Event, SessionStats, TreeNode


def _find_tree_node(node: TreeNode, event_id: str) -> TreeNode | None:
    if node.event.id == event_id:
        return node
    for child in node.children:
        found = _find_tree_node(child, event_id)
        if found is not None:
            return found
    return None


def _walk_tree_ids(nodes: list[TreeNode]) -> list[str]:
    seen: list[str] = []

    def visit(node: TreeNode) -> None:
        seen.append(node.event.id)
        for child in node.children:
            visit(child)

    for node in nodes:
        visit(node)
    return seen

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_SESSION = "c753e394-40eb-4c8f-b40b-981316a7eeff"
SESSION_DIR = Path.home() / ".copilot" / "session-state"
TEST_FILE = SESSION_DIR / TEST_SESSION / "events.jsonl"

# A session known to contain session.shutdown
SHUTDOWN_SESSION = "8b3a1e3c-7075-4d4f-b5b6-679a719eb471"
SHUTDOWN_FILE = SESSION_DIR / SHUTDOWN_SESSION / "events.jsonl"


@pytest.fixture
def sample_events_file(tmp_path: Path) -> Path:
    """Create a minimal JSONL file for unit tests."""
    events = [
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
    p = tmp_path / "events.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return p


@pytest.fixture
def malformed_file(tmp_path: Path) -> Path:
    """JSONL file with some malformed lines."""
    lines = [
        json.dumps({
            "type": "session.start",
            "data": {},
            "id": "aaa",
            "timestamp": "2026-01-01T00:00:00.000Z",
            "parentId": None,
        }),
        "",  # empty line
        "not json at all",
        '{"truncated": true',  # truncated
        json.dumps({
            "type": "user.message",
            "data": {"content": "hi"},
            "id": "bbb",
            "timestamp": "2026-01-01T00:00:01.000Z",
            "parentId": "aaa",
        }),
    ]
    p = tmp_path / "events.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p


# ---------------------------------------------------------------------------
# AC1: parse_events_file
# ---------------------------------------------------------------------------


class TestParseEventsFile:
    def test_returns_event_objects(self, sample_events_file: Path) -> None:
        events = parse_events_file(sample_events_file)
        assert len(events) == 4
        assert all(isinstance(e, Event) for e in events)

    def test_event_fields(self, sample_events_file: Path) -> None:
        events = parse_events_file(sample_events_file)
        first = events[0]
        assert first.type == "session.start"
        assert isinstance(first.data, dict)
        assert isinstance(first.id, str)
        assert isinstance(first.timestamp, datetime)
        assert first.parent_id is None

    def test_parent_id_populated(self, sample_events_file: Path) -> None:
        events = parse_events_file(sample_events_file)
        assert events[1].parent_id == "aaa"

    def test_sorted_by_timestamp(self, sample_events_file: Path) -> None:
        events = parse_events_file(sample_events_file)
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

    @pytest.mark.skipif(not TEST_FILE.exists(), reason="Real session data not available")
    def test_real_session(self) -> None:
        events = parse_events_file(TEST_FILE)
        assert len(events) > 100
        assert all(isinstance(e, Event) for e in events)
        assert events[0].type == "session.start"


# ---------------------------------------------------------------------------
# AC2: correlate_tool_names
# ---------------------------------------------------------------------------


class TestCorrelateToolNames:
    def test_populates_tool_name(self, sample_events_file: Path) -> None:
        events = parse_events_file(sample_events_file)
        correlate_tool_names(events)
        complete = [e for e in events if e.type == "tool.execution_complete"]
        assert len(complete) == 1
        assert complete[0].tool_name == "bash"

    @pytest.mark.skipif(not TEST_FILE.exists(), reason="Real session data not available")
    def test_real_session_90_percent(self) -> None:
        events = parse_events_file(TEST_FILE)
        correlate_tool_names(events)
        completes = [e for e in events if e.type == "tool.execution_complete"]
        with_name = [e for e in completes if e.tool_name is not None]
        assert len(completes) > 0
        ratio = len(with_name) / len(completes)
        assert ratio >= 0.9, f"Only {ratio:.1%} of complete events have tool_name"


# ---------------------------------------------------------------------------
# AC3: build_event_tree
# ---------------------------------------------------------------------------


class TestBuildEventTree:
    def test_tree_structure(self, sample_events_file: Path) -> None:
        events = parse_events_file(sample_events_file)
        roots = build_event_tree(events)
        assert len(roots) == 1
        root = roots[0]
        assert isinstance(root, TreeNode)
        assert root.event.id == "aaa"
        assert len(root.children) == 1
        assert root.children[0].event.id == "bbb"

    def test_root_nodes_have_no_parent(self, sample_events_file: Path) -> None:
        events = parse_events_file(sample_events_file)
        roots = build_event_tree(events)
        for root in roots:
            assert root.event.parent_id is None or root.event.parent_id not in {e.id for e in events}

    def test_depth(self, sample_events_file: Path) -> None:
        events = parse_events_file(sample_events_file)
        roots = build_event_tree(events)
        # aaa -> bbb -> ccc -> ddd
        assert roots[0].children[0].children[0].children[0].event.id == "ddd"

    def test_enriches_tree_nodes_with_metadata(self) -> None:
        events = [
            Event(
                type="session.start",
                data={"sessionId": "session-12345678"},
                id="aaa",
                timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                parentId=None,
            ),
            Event(
                type="user.message",
                data={"content": "Hello from the user message body"},
                id="bbb",
                timestamp=datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
                parentId="aaa",
            ),
            Event(
                type="tool.execution_start",
                data={"toolCallId": "tc1", "toolName": "bash"},
                id="ccc",
                timestamp=datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
                parentId="bbb",
            ),
            Event(
                type="tool.execution_complete",
                data={"toolCallId": "tc1", "success": True},
                id="ddd",
                timestamp=datetime(2026, 1, 1, 0, 0, 3, tzinfo=timezone.utc),
                parentId="ccc",
            ),
            Event(
                type="subagent.started",
                data={"toolCallId": "agent-1", "agentName": "explore"},
                id="eee",
                timestamp=datetime(2026, 1, 1, 0, 0, 4, tzinfo=timezone.utc),
                parentId="bbb",
            ),
            Event(
                type="subagent.completed",
                data={"toolCallId": "agent-1", "agentName": "explore"},
                id="fff",
                timestamp=datetime(2026, 1, 1, 0, 0, 6, tzinfo=timezone.utc),
                parentId="eee",
            ),
        ]

        correlate_tool_names(events)
        roots = build_event_tree(events)

        assert roots[0].event_count == 6

        user_node = _find_tree_node(roots[0], "bbb")
        assert user_node is not None
        assert user_node.semantic_kind == "user"
        assert user_node.brief_description == "Hello from the user message body"

        tool_complete = _find_tree_node(roots[0], "ddd")
        assert tool_complete is not None
        assert tool_complete.semantic_kind == "tool"
        assert tool_complete.status == "completed"
        assert tool_complete.duration_ms == 1000
        assert tool_complete.event.tool_name == "bash"

        subagent_complete = _find_tree_node(roots[0], "fff")
        assert subagent_complete is not None
        assert subagent_complete.semantic_kind == "subagent"
        assert subagent_complete.agent_name == "explore"
        assert subagent_complete.status == "completed"
        assert subagent_complete.duration_ms == 2000

    def test_caps_tree_depth_at_50_levels(self) -> None:
        events: list[Event] = []
        base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        for index in range(55):
            events.append(
                Event(
                    type="user.message",
                    data={"content": f"message {index}"},
                    id=f"node-{index}",
                    timestamp=base_time + timedelta(seconds=index),
                    parentId=f"node-{index - 1}" if index > 0 else None,
                )
            )

        roots = build_event_tree(events)

        cap_node = roots[0]
        for _ in range(50):
            assert len(cap_node.children) == 1
            cap_node = cap_node.children[0]

        assert cap_node.event.id == "node-50"
        assert [child.event.id for child in cap_node.children] == [
            "node-51",
            "node-52",
            "node-53",
            "node-54",
        ]
        assert all(not child.children for child in cap_node.children)

    def test_breaks_parent_cycles_without_repeating_nodes(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        events = [
            Event(
                type="session.start",
                data={},
                id="aaa",
                timestamp=base_time,
                parentId="ccc",
            ),
            Event(
                type="user.message",
                data={"content": "hello"},
                id="bbb",
                timestamp=base_time + timedelta(seconds=1),
                parentId="aaa",
            ),
            Event(
                type="assistant.message",
                data={"message": "world"},
                id="ccc",
                timestamp=base_time + timedelta(seconds=2),
                parentId="bbb",
            ),
        ]

        roots = build_event_tree(events)

        assert [root.event.id for root in roots] == ["aaa"]
        assert roots[0].children[0].event.id == "bbb"
        assert roots[0].children[0].children[0].event.id == "ccc"
        assert roots[0].children[0].children[0].children == []
        assert _walk_tree_ids(roots) == ["aaa", "bbb", "ccc"]


# ---------------------------------------------------------------------------
# AC4: compute_stats
# ---------------------------------------------------------------------------


class TestComputeStats:
    def test_basic_counts(self, sample_events_file: Path) -> None:
        events = parse_events_file(sample_events_file)
        stats = compute_stats(events)
        assert isinstance(stats, SessionStats)
        assert stats.total_events == 4
        assert stats.user_messages == 1
        assert stats.tool_calls == 1

    def test_collects_cache_write_tokens_from_shutdown(self) -> None:
        events = [
            Event(
                type="session.start",
                data={},
                id="aaa",
                timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                parentId=None,
            ),
            Event(
                type="session.shutdown",
                data={
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
                id="bbb",
                timestamp=datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc),
                parentId="aaa",
            ),
        ]

        stats = compute_stats(events)

        assert stats.cache_write_tokens == 15

    @pytest.mark.skipif(not SHUTDOWN_FILE.exists(), reason="Shutdown session not available")
    def test_shutdown_data(self) -> None:
        events = parse_events_file(SHUTDOWN_FILE)
        stats = compute_stats(events)
        assert stats.total_events > 0
        assert stats.lines_added >= 0
        assert stats.lines_removed >= 0
        assert len(stats.models_used) > 0
        assert stats.input_tokens > 0


# ---------------------------------------------------------------------------
# AC5: malformed lines
# ---------------------------------------------------------------------------


class TestMalformedLines:
    def test_skips_malformed_without_exception(self, malformed_file: Path) -> None:
        events = parse_events_file(malformed_file)
        assert len(events) == 2

    def test_logs_warnings(self, malformed_file: Path, caplog: pytest.LogCaptureFixture) -> None:
        import logging
        with caplog.at_level(logging.WARNING):
            parse_events_file(malformed_file)
        assert len(caplog.records) >= 2  # "not json at all" and truncated


# ---------------------------------------------------------------------------
# AC6: performance
# ---------------------------------------------------------------------------


class TestPerformance:
    @pytest.mark.skipif(not TEST_FILE.exists(), reason="Real session data not available")
    def test_parse_under_5_seconds(self) -> None:
        start = time.monotonic()
        events = parse_events_file(TEST_FILE)
        correlate_tool_names(events)
        build_event_tree(events)
        compute_stats(events)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"Took {elapsed:.2f}s"
