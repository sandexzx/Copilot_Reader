"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.sessions import router as sessions_router
from .api.websocket import router as websocket_router, shutdown_watcher_manager


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

app.include_router(sessions_router)
app.include_router(websocket_router)


@app.get("/api/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


PORT = int(os.environ.get("COPILOT_READER_PORT", "8000"))
