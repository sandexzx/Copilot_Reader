"""Pydantic models for Copilot Reader."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Represents a single JSONL event."""

    type: str
    data: dict
    id: str
    timestamp: datetime
    parent_id: str | None = Field(None, alias="parentId")
    tool_name: str | None = None

    model_config = {"populate_by_name": True}


class SessionSummary(BaseModel):
    """Summary view for session list."""

    id: str
    summary: str
    cwd: str
    created_at: str
    updated_at: str
    is_active: bool
    event_count: int


class Session(SessionSummary):
    """Full session details."""

    git_root: str | None = None
    branch: str | None = None
    pid: int | None = None


class SessionStats(BaseModel):
    """Computed statistics for a session."""

    total_events: int = 0
    duration_seconds: float = 0.0
    models_used: list[str] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    tool_calls: int = 0
    user_messages: int = 0
    assistant_turns: int = 0
    files_modified: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    premium_requests: int = 0


class TreeNode(BaseModel):
    """Nested event tree node."""

    event: Event
    children: list[TreeNode] = Field(default_factory=list)
    semantic_kind: str = "event"
    event_count: int = 1
    duration_ms: int | None = None
    brief_description: str | None = None
    status: str | None = None
    agent_name: str | None = None


class ModelUsage(BaseModel):
    """Per-model token usage counters."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    premium_requests: int = 0
    requests_count: int = 0


class DailyUsageTotals(BaseModel):
    """Aggregated totals across all models."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    premium_requests: int = 0


class DailyUsageResponse(BaseModel):
    """Daily usage aggregation response."""

    date: str  # ISO date "2026-04-01"
    sessions_count: int = 0
    models: dict[str, ModelUsage] = Field(default_factory=dict)
    totals: DailyUsageTotals = Field(default_factory=DailyUsageTotals)


class WebSocketMessage(BaseModel):
    """Messages sent over WebSocket."""

    type: str
    data: dict
