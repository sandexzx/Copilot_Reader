"""File system watching via watchdog/inotify."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .models import Event

logger = logging.getLogger(__name__)

EventCallback = Callable[[Event], None]


class _EventFileHandler(FileSystemEventHandler):
    """Watchdog handler that detects modifications to events.jsonl."""

    def __init__(self, file_path: Path, on_lines: Callable[[list[str]], None]) -> None:
        super().__init__()
        self._file_path = file_path
        self._on_lines = on_lines

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if Path(event.src_path).name == self._file_path.name:
            self._on_lines([])  # signal to read new data


class FileWatcher:
    """Watches a single events.jsonl file and emits parsed Event objects.

    Uses watchdog Observer to watch the parent directory. On file modification,
    reads only new bytes from the tracked position, buffers incomplete lines,
    and parses complete lines into Event objects.
    """

    def __init__(self, file_path: Path, loop: asyncio.AbstractEventLoop) -> None:
        self._file_path = file_path
        self._loop = loop
        self._position: int = 0
        self._buffer: str = ""
        self._callbacks: set[EventCallback] = set()
        self._observer: Observer | None = None
        self._lock = threading.Lock()

        # Initialize position to end of file if it exists
        if self._file_path.exists():
            self._position = self._file_path.stat().st_size

    def add_callback(self, callback: EventCallback) -> None:
        with self._lock:
            self._callbacks.add(callback)

    def remove_callback(self, callback: EventCallback) -> None:
        with self._lock:
            self._callbacks.discard(callback)

    @property
    def callback_count(self) -> int:
        with self._lock:
            return len(self._callbacks)

    def start(self) -> None:
        """Start watching the file's parent directory."""
        handler = _EventFileHandler(self._file_path, self._on_file_signal)
        self._observer = Observer()
        self._observer.schedule(handler, str(self._file_path.parent), recursive=False)
        self._observer.daemon = True
        self._observer.start()
        logger.info("FileWatcher started for %s", self._file_path)

    def stop(self) -> None:
        """Stop the watchdog observer."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        logger.info("FileWatcher stopped for %s", self._file_path)

    def _on_file_signal(self, _lines: list[str]) -> None:
        """Called from watchdog thread when file is modified."""
        self._read_new_lines()

    def _read_new_lines(self) -> None:
        """Read new bytes from file, buffer partials, emit complete lines."""
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                f.seek(self._position)
                new_data = f.read()
                self._position = f.tell()
        except (OSError, IOError) as exc:
            logger.warning("Error reading %s: %s", self._file_path, exc)
            return

        if not new_data:
            return

        self._buffer += new_data
        # Split on newlines; last element is incomplete if doesn't end with \n
        parts = self._buffer.split("\n")
        # If buffer ended with \n, last part is empty string
        self._buffer = parts[-1]  # keep incomplete part
        complete_lines = parts[:-1]

        for line in complete_lines:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
                event = Event.model_validate(raw)
                self._emit_event(event)
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning("Skipping malformed line in %s: %s", self._file_path, exc)

    def _emit_event(self, event: Event) -> None:
        """Emit event to all registered callbacks via the asyncio loop."""
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                self._loop.call_soon_threadsafe(cb, event)
            except RuntimeError:
                # Loop is closed
                pass


class SessionWatcherManager:
    """Manages one FileWatcher per session with subscriber tracking.

    Lazily creates watchers when the first client subscribes and stops
    them when the last client unsubscribes.
    """

    def __init__(self, session_state_dir: Path, loop: asyncio.AbstractEventLoop) -> None:
        self._session_state_dir = session_state_dir
        self._loop = loop
        self._watchers: dict[str, FileWatcher] = {}
        self._lock = threading.Lock()

    def subscribe(self, session_id: str, callback: EventCallback) -> None:
        """Subscribe a callback to events from a session's events.jsonl."""
        with self._lock:
            if session_id not in self._watchers:
                file_path = self._session_state_dir / session_id / "events.jsonl"
                watcher = FileWatcher(file_path, self._loop)
                watcher.start()
                self._watchers[session_id] = watcher
            self._watchers[session_id].add_callback(callback)

    def unsubscribe(self, session_id: str, callback: EventCallback) -> None:
        """Unsubscribe a callback. Stops watcher if last subscriber."""
        with self._lock:
            watcher = self._watchers.get(session_id)
            if watcher is None:
                return
            watcher.remove_callback(callback)
            if watcher.callback_count == 0:
                watcher.stop()
                del self._watchers[session_id]

    def stop_all(self) -> None:
        """Stop all active watchers."""
        with self._lock:
            for watcher in self._watchers.values():
                watcher.stop()
            self._watchers.clear()
