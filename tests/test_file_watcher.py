"""Tests for backend.file_watcher module."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest

from backend.file_watcher import FileWatcher, SessionWatcherManager
from backend.models import Event


def _make_event_line(
    event_type: str = "test.event",
    event_id: str = "evt-1",
    ts: str = "2026-01-01T00:00:00.000Z",
) -> str:
    return json.dumps({
        "type": event_type,
        "data": {"key": "value"},
        "id": event_id,
        "timestamp": ts,
        "parentId": None,
    })


# ---------------------------------------------------------------------------
# AC1: FileWatcher watches events.jsonl and emits only new lines
# ---------------------------------------------------------------------------


class TestFileWatcherNewLines:
    def test_detects_appended_lines(self, tmp_path: Path) -> None:
        """FileWatcher calls callback when new lines are appended."""
        events_file = tmp_path / "events.jsonl"
        # Pre-existing content — watcher should skip this
        events_file.write_text(_make_event_line("old.event", "old-1") + "\n")

        loop = asyncio.new_event_loop()
        received: list[Event] = []

        def on_event(event: Event) -> None:
            received.append(event)

        watcher = FileWatcher(events_file, loop)
        watcher.add_callback(on_event)
        watcher.start()

        try:
            # Append a new line
            with open(events_file, "a") as f:
                f.write(_make_event_line("new.event", "new-1") + "\n")
                f.flush()

            # Wait for watchdog to detect the change
            deadline = time.monotonic() + 3.0
            while not received and time.monotonic() < deadline:
                loop.run_until_complete(asyncio.sleep(0.1))

            assert len(received) == 1
            assert received[0].type == "new.event"
            assert received[0].id == "new-1"
        finally:
            watcher.stop()
            loop.close()

    def test_tracks_position_only_new(self, tmp_path: Path) -> None:
        """FileWatcher does NOT re-emit events that existed before start."""
        events_file = tmp_path / "events.jsonl"
        events_file.write_text(
            _make_event_line("pre-existing", "pre-1") + "\n"
            + _make_event_line("pre-existing", "pre-2") + "\n"
        )

        loop = asyncio.new_event_loop()
        received: list[Event] = []

        watcher = FileWatcher(events_file, loop)
        watcher.add_callback(lambda e: received.append(e))
        watcher.start()

        try:
            with open(events_file, "a") as f:
                f.write(_make_event_line("new.event", "new-1") + "\n")
                f.flush()

            deadline = time.monotonic() + 3.0
            while not received and time.monotonic() < deadline:
                loop.run_until_complete(asyncio.sleep(0.1))

            # Only the new event, not the pre-existing ones
            assert len(received) == 1
            assert received[0].id == "new-1"
        finally:
            watcher.stop()
            loop.close()


# ---------------------------------------------------------------------------
# AC6: Partial JSON lines (burst writes) are buffered
# ---------------------------------------------------------------------------


class TestFileWatcherPartialLines:
    def test_buffers_partial_lines(self, tmp_path: Path) -> None:
        """Incomplete lines are buffered until completed with newline."""
        events_file = tmp_path / "events.jsonl"
        events_file.write_text("")

        loop = asyncio.new_event_loop()
        received: list[Event] = []

        watcher = FileWatcher(events_file, loop)
        watcher.add_callback(lambda e: received.append(e))
        watcher.start()

        try:
            line = _make_event_line("partial.test", "partial-1")
            half = len(line) // 2

            # Write first half (no newline)
            with open(events_file, "a") as f:
                f.write(line[:half])
                f.flush()

            loop.run_until_complete(asyncio.sleep(1.0))
            assert len(received) == 0, "Partial line should not emit an event"

            # Write second half + newline
            with open(events_file, "a") as f:
                f.write(line[half:] + "\n")
                f.flush()

            deadline = time.monotonic() + 3.0
            while not received and time.monotonic() < deadline:
                loop.run_until_complete(asyncio.sleep(0.1))

            assert len(received) == 1
            assert received[0].id == "partial-1"
        finally:
            watcher.stop()
            loop.close()


# ---------------------------------------------------------------------------
# AC5: Multiple callbacks all receive events
# ---------------------------------------------------------------------------


class TestFileWatcherMultipleCallbacks:
    def test_multiple_callbacks_receive_events(self, tmp_path: Path) -> None:
        events_file = tmp_path / "events.jsonl"
        events_file.write_text("")

        loop = asyncio.new_event_loop()
        received_a: list[Event] = []
        received_b: list[Event] = []

        watcher = FileWatcher(events_file, loop)
        watcher.add_callback(lambda e: received_a.append(e))
        watcher.add_callback(lambda e: received_b.append(e))
        watcher.start()

        try:
            with open(events_file, "a") as f:
                f.write(_make_event_line("multi.test", "multi-1") + "\n")
                f.flush()

            deadline = time.monotonic() + 3.0
            while (not received_a or not received_b) and time.monotonic() < deadline:
                loop.run_until_complete(asyncio.sleep(0.1))

            assert len(received_a) == 1
            assert len(received_b) == 1
        finally:
            watcher.stop()
            loop.close()


# ---------------------------------------------------------------------------
# SessionWatcherManager: subscribe/unsubscribe lifecycle
# ---------------------------------------------------------------------------


class TestSessionWatcherManager:
    def test_subscribe_creates_watcher(self, tmp_path: Path) -> None:
        session_dir = tmp_path / "test-session"
        session_dir.mkdir()
        (session_dir / "events.jsonl").write_text("")

        loop = asyncio.new_event_loop()
        mgr = SessionWatcherManager(tmp_path, loop)

        try:
            mgr.subscribe("test-session", lambda e: None)
            assert "test-session" in mgr._watchers
        finally:
            mgr.stop_all()
            loop.close()

    def test_unsubscribe_last_stops_watcher(self, tmp_path: Path) -> None:
        session_dir = tmp_path / "test-session"
        session_dir.mkdir()
        (session_dir / "events.jsonl").write_text("")

        loop = asyncio.new_event_loop()
        mgr = SessionWatcherManager(tmp_path, loop)
        cb = lambda e: None

        try:
            mgr.subscribe("test-session", cb)
            assert "test-session" in mgr._watchers
            mgr.unsubscribe("test-session", cb)
            assert "test-session" not in mgr._watchers
        finally:
            mgr.stop_all()
            loop.close()

    def test_multiple_subscribers_keeps_watcher(self, tmp_path: Path) -> None:
        session_dir = tmp_path / "test-session"
        session_dir.mkdir()
        (session_dir / "events.jsonl").write_text("")

        loop = asyncio.new_event_loop()
        mgr = SessionWatcherManager(tmp_path, loop)
        cb1 = lambda e: None
        cb2 = lambda e: None

        try:
            mgr.subscribe("test-session", cb1)
            mgr.subscribe("test-session", cb2)
            mgr.unsubscribe("test-session", cb1)
            # Watcher still alive because cb2 remains
            assert "test-session" in mgr._watchers
            mgr.unsubscribe("test-session", cb2)
            assert "test-session" not in mgr._watchers
        finally:
            mgr.stop_all()
            loop.close()
