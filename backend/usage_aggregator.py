"""Daily usage aggregation from session shutdown metrics."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .models import DailyUsageResponse, DailyUsageTotals, ModelUsage
from .session_manager import _get_session_state_dir, get_session_metadata

logger = logging.getLogger(__name__)


def _read_shutdown_metrics(events_path: Path) -> dict | None:
    """Extract modelMetrics from the session.shutdown event.

    Reads from the end of the file for efficiency since the shutdown
    event is always the last line in events.jsonl.
    """
    try:
        with open(events_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size == 0:
                return None
            read_size = min(size, 65536)
            f.seek(-read_size, 2)
            chunk = f.read(read_size).decode("utf-8", errors="replace")
    except (OSError, IOError):
        return None

    last_line = chunk.rstrip("\n").rsplit("\n", 1)[-1]
    if not last_line:
        return None

    try:
        event = json.loads(last_line)
    except (json.JSONDecodeError, ValueError):
        return None

    if event.get("type") != "session.shutdown":
        return None

    return event.get("data", {}).get("modelMetrics")


async def get_daily_usage() -> DailyUsageResponse:
    """Aggregate token usage for today's sessions across all models."""
    today = datetime.now(timezone.utc).date()
    state_dir = _get_session_state_dir()

    models: dict[str, ModelUsage] = {}
    sessions_count = 0

    if not state_dir.is_dir():
        return DailyUsageResponse(date=today.isoformat())

    for entry in state_dir.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            continue

        meta = get_session_metadata(entry)
        created_at = meta["created_at"]
        if isinstance(created_at, datetime):
            session_date = created_at.date()
        else:
            try:
                session_date = datetime.fromisoformat(
                    str(created_at).replace("Z", "+00:00")
                ).date()
            except (ValueError, TypeError):
                continue

        if session_date != today:
            continue

        sessions_count += 1

        events_path = entry / "events.jsonl"
        if not events_path.is_file():
            continue

        model_metrics = _read_shutdown_metrics(events_path)
        if not model_metrics:
            continue

        for model_name, metrics in model_metrics.items():
            usage = metrics.get("usage", {})
            requests = metrics.get("requests", {})

            if model_name not in models:
                models[model_name] = ModelUsage()

            m = models[model_name]
            m.input_tokens += usage.get("inputTokens", 0)
            m.output_tokens += usage.get("outputTokens", 0)
            m.cache_read_tokens += usage.get("cacheReadTokens", 0)
            m.cache_write_tokens += usage.get("cacheWriteTokens", 0)
            m.premium_requests += requests.get("cost", 0)
            m.requests_count += requests.get("count", 0)

    totals = DailyUsageTotals()
    for m in models.values():
        totals.input_tokens += m.input_tokens
        totals.output_tokens += m.output_tokens
        totals.cache_read_tokens += m.cache_read_tokens
        totals.cache_write_tokens += m.cache_write_tokens
        totals.premium_requests += m.premium_requests

    return DailyUsageResponse(
        date=today.isoformat(),
        sessions_count=sessions_count,
        models=models,
        totals=totals,
    )
