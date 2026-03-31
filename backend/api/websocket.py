"""WebSocket handler for live updates."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..file_watcher import SessionWatcherManager
from ..models import Event
from ..security import safe_session_dir
from ..session_manager import _get_session_state_dir

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Module-level singleton, initialized lazily on first connection.
_manager: SessionWatcherManager | None = None
_manager_lock = asyncio.Lock()

# --- Connection limits ---
MAX_CONNECTIONS_PER_SESSION = 10
_connection_counts: dict[str, int] = {}
_counts_lock = asyncio.Lock()


def _count_events(session_dir: Path) -> int:
    """Count lines in events.jsonl without loading content."""
    events_file = session_dir / "events.jsonl"
    if not events_file.exists():
        return 0
    count = 0
    try:
        with open(events_file, "rb") as f:
            for _ in f:
                count += 1
    except (OSError, IOError):
        pass
    return count


async def _get_manager() -> SessionWatcherManager:
    """Get or create the singleton SessionWatcherManager."""
    global _manager
    if _manager is None:
        async with _manager_lock:
            if _manager is None:
                loop = asyncio.get_running_loop()
                state_dir = _get_session_state_dir()
                _manager = SessionWatcherManager(state_dir, loop)
    return _manager


async def shutdown_watcher_manager() -> None:
    """Shut down the global watcher manager. Called on app shutdown."""
    global _manager
    if _manager is not None:
        _manager.stop_all()
        _manager = None


@router.websocket("/ws/sessions/{session_id}/events")
async def session_events_ws(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for streaming session events in real-time."""
    # Validate session id format and resolve safely
    try:
        session_dir = safe_session_dir(session_id)
    except Exception:
        await websocket.close(code=4400, reason="Invalid session ID")
        return

    if not session_dir.is_dir():
        await websocket.close(code=4004, reason="Session not found")
        return

    # Connection limit check
    async with _counts_lock:
        current = _connection_counts.get(session_id, 0)
        if current >= MAX_CONNECTIONS_PER_SESSION:
            await websocket.close(code=4008, reason="Too many connections")
            return
        _connection_counts[session_id] = current + 1

    try:
        await websocket.accept()

        event_count = _count_events(session_dir)
        await websocket.send_json({
            "type": "connected",
            "data": {"session_id": session_id, "event_count": event_count},
        })

        manager = await _get_manager()
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=1000)
        disconnect_event = asyncio.Event()

        def on_event(event: Event) -> None:
            """Callback invoked from the event loop via call_soon_threadsafe."""
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Event queue full for session %s, dropping event", session_id)

        manager.subscribe(session_id, on_event)

        async def _send_events() -> None:
            """Drain queue and send events to client until disconnect."""
            try:
                while not disconnect_event.is_set():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=0.5)
                    except asyncio.TimeoutError:
                        continue
                    await websocket.send_json({
                        "type": "event",
                        "data": event.model_dump(mode="json", by_alias=True),
                    })
            except (WebSocketDisconnect, Exception):
                pass

        async def _receive_disconnect() -> None:
            """Wait for client to disconnect."""
            try:
                while True:
                    await websocket.receive_text()
            except (WebSocketDisconnect, Exception):
                pass
            finally:
                disconnect_event.set()

        try:
            send_task = asyncio.create_task(_send_events())
            recv_task = asyncio.create_task(_receive_disconnect())
            await asyncio.wait(
                [send_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            disconnect_event.set()
            send_task.cancel()
            recv_task.cancel()
            # Suppress CancelledError from tasks
            for t in (send_task, recv_task):
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
            manager.unsubscribe(session_id, on_event)
    finally:
        async with _counts_lock:
            _connection_counts[session_id] = max(
                0, _connection_counts.get(session_id, 1) - 1
            )
