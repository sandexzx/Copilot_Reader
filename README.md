# Copilot Reader

Real-time monitoring tool for GitHub Copilot CLI sessions. Parses `events.jsonl` from `~/.copilot/session-state/` and displays all operations in a beautiful IDE-style dark web interface.

[Screenshot placeholder]

## Features

- **Real-time streaming** — WebSocket-powered live event feed (tail -f style)
- **Session browser** — List, search, and filter all Copilot CLI sessions
- **Nested event tree** — Visualize agent → tool → sub-agent call hierarchies
- **Session statistics** — Token usage, models, cost, files modified
- **IDE-style dark theme** — VS Code / GitHub Dark inspired interface with monospace log viewer
- **Active session detection** — Lock-file based detection of running sessions
- **Zero configuration** — Reads directly from `~/.copilot/session-state/`

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-username/Copilot_Reader.git
cd Copilot_Reader

# 2. Launch (installs dependencies automatically)
./start.sh

# 3. Open in your browser
open http://localhost:8000
```

> **Prerequisites:** Python 3.12+ and [Bun](https://bun.sh) must be installed.

The start script automatically installs Python and frontend dependencies, builds the SvelteKit frontend, and starts the FastAPI server.

## Development

Run in dev mode for hot-reload on both frontend and backend:

```bash
./start.sh dev
```

This starts:
- **Vite dev server** on `http://localhost:5173` (HMR for Svelte)
- **uvicorn** on `http://localhost:8000` with `--reload` (auto-restart on Python changes)

### Running Tests

```bash
python -m pytest tests/
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `COPILOT_READER_PORT` | `8000` | Port for the FastAPI server |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Browser                            │
│              (SvelteKit + Svelte 5)                      │
└──────────┬──────────────────────┬───────────────────────┘
           │ REST (HTTP)          │ WebSocket
           ▼                      ▼
┌──────────────────────────────────────────────────────────┐
│                  FastAPI Backend                         │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Sessions API │  │ WebSocket    │  │ Health Check  │  │
│  │  /api/sessions│  │ /ws/sessions │  │ /api/health   │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────┘  │
│         │                  │                              │
│         ▼                  ▼                              │
│  ┌──────────────┐  ┌───────────────┐                     │
│  │ Session      │  │ File Watcher  │                     │
│  │ Manager      │  │ (watchdog)    │                     │
│  └──────┬───────┘  └──────┬────────┘                     │
│         │                  │                              │
└─────────┼──────────────────┼─────────────────────────────┘
          │                  │
          ▼                  ▼
┌──────────────────────────────────────────────────────────┐
│            ~/.copilot/session-state/                      │
│                                                          │
│  <session-uuid>/                                         │
│  ├── events.jsonl    ← main event log (append-only)      │
│  ├── workspace.yaml  ← session metadata                  │
│  └── inuse.PID.lock  ← active session indicator          │
└──────────────────────────────────────────────────────────┘
```

**Data flow:**
1. Copilot CLI writes events to `events.jsonl` in real time
2. File Watcher (watchdog/inotify) detects file changes and emits new events
3. WebSocket pushes new events to connected browser clients instantly
4. REST API provides session listing, event history, stats, and tree views on demand

## API Reference

### Health Check

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Server health check |

```json
{ "status": "ok" }
```

### Sessions

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sessions` | List all sessions (active-first, sorted by updated_at) |
| `GET` | `/api/sessions/{session_id}` | Get full details for a single session |
| `GET` | `/api/sessions/{session_id}/events` | Get all parsed events (with tool name correlation) |
| `GET` | `/api/sessions/{session_id}/stats` | Get computed session statistics |
| `GET` | `/api/sessions/{session_id}/tree` | Get nested event tree |

#### `GET /api/sessions`

Returns a list of session summaries.

```json
[
  {
    "id": "a1b2c3d4-...",
    "summary": "Implement auth module",
    "cwd": "/home/user/project",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T11:45:00Z",
    "is_active": true,
    "event_count": 342
  }
]
```

#### `GET /api/sessions/{session_id}`

Returns full session details including git metadata.

```json
{
  "id": "a1b2c3d4-...",
  "summary": "Implement auth module",
  "cwd": "/home/user/project",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T11:45:00Z",
  "is_active": true,
  "event_count": 342,
  "git_root": "/home/user/project",
  "branch": "main",
  "pid": 12345
}
```

#### `GET /api/sessions/{session_id}/events`

Returns all events for a session with correlated tool names.

```json
[
  {
    "type": "user.message",
    "data": { "content": "Fix the login bug" },
    "id": "evt-uuid",
    "timestamp": "2025-01-15T10:31:00Z",
    "parentId": null,
    "tool_name": null
  }
]
```

#### `GET /api/sessions/{session_id}/stats`

Returns computed statistics for a session.

```json
{
  "total_events": 342,
  "duration_seconds": 4500.0,
  "models_used": ["claude-sonnet-4", "claude-haiku-4"],
  "input_tokens": 125000,
  "output_tokens": 45000,
  "cache_read_tokens": 80000,
  "cache_write_tokens": 10000,
  "tool_calls": 87,
  "user_messages": 12,
  "assistant_turns": 12,
  "files_modified": 8,
  "lines_added": 340,
  "lines_removed": 120,
  "premium_requests": 5
}
```

#### `GET /api/sessions/{session_id}/tree`

Returns a nested tree of events grouped by semantic relationships.

```json
[
  {
    "event": { "type": "user.message", "..." : "..." },
    "semantic_kind": "user_turn",
    "event_count": 15,
    "duration_ms": 3200,
    "brief_description": "Fix the login bug",
    "status": "completed",
    "agent_name": null,
    "children": []
  }
]
```

### WebSocket

| Protocol | Path | Description |
|---|---|---|
| `WS` | `/ws/sessions/{session_id}/events` | Stream new events in real time |

On connection, the server sends a `connected` message:

```json
{ "type": "connected", "data": { "session_id": "a1b2c3d4-...", "event_count": 342 } }
```

New events are pushed as they arrive:

```json
{ "type": "event", "data": { "type": "tool.execution_complete", "..." : "..." } }
```

## Project Structure

```
Copilot_Reader/
├── start.sh                  # Launch script (prod & dev modes)
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── models.py             # Pydantic data models
│   ├── session_manager.py    # Session discovery & metadata
│   ├── event_parser.py       # JSONL parsing, tree building, stats
│   ├── file_watcher.py       # Watchdog-based file change detection
│   ├── requirements.txt      # Python dependencies
│   └── api/
│       ├── sessions.py       # REST API endpoints
│       └── websocket.py      # WebSocket endpoint
├── frontend/
│   ├── package.json          # Bun/Node dependencies
│   ├── svelte.config.js      # SvelteKit configuration
│   ├── vite.config.ts        # Vite build configuration
│   └── src/
│       ├── app.html          # HTML shell
│       ├── app.css           # Global styles
│       ├── lib/              # Shared components & utilities
│       └── routes/           # SvelteKit pages
├── tests/
│   ├── test_api_sessions.py  # REST API tests
│   ├── test_event_parser.py  # Event parser tests
│   ├── test_file_watcher.py  # File watcher tests
│   ├── test_session_manager.py
│   └── test_websocket.py     # WebSocket tests
└── demos/                    # Design prototypes
```

## License

This project is for personal use.
