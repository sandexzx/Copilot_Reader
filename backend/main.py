"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.sessions import router as sessions_router
from .api.websocket import router as websocket_router, shutdown_watcher_manager
from .api.ai import router as ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    yield
    await shutdown_watcher_manager()


app = FastAPI(title="Copilot Reader", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API and WebSocket routes (registered BEFORE static mount so they take priority) ---
app.include_router(sessions_router)
app.include_router(websocket_router)
app.include_router(ai_router)


@app.get("/api/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


# --- Static file serving (SvelteKit build output, SPA fallback) ---
_STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "build"

if _STATIC_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_STATIC_DIR), html=True),
        name="spa",
    )


PORT = int(os.environ.get("COPILOT_READER_PORT", "8000"))
