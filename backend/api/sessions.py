"""REST API endpoints for sessions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..event_parser import (
    build_event_tree,
    compute_stats,
    correlate_tool_names,
    parse_events_file,
)
from ..models import (
    CopilotUserInfo,
    DailyUsageResponse,
    DateRangeDeleteRequest,
    DeleteRequest,
    DeleteResult,
    Event,
    Session,
    SessionStats,
    SessionSummary,
    TreeNode,
)
from ..security import safe_session_dir, validate_session_id
from ..session_manager import (
    delete_session,
    delete_sessions_by_date_range,
    discover_sessions,
    get_copilot_user_info,
    get_session,
)
from ..usage_aggregator import get_daily_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _resolve_events_path(session_id: str):
    """Resolve the events.jsonl path for a session, raising 404 if missing."""
    session_dir = safe_session_dir(session_id)
    if not session_dir.is_dir():
        raise HTTPException(status_code=404, detail="Session not found")
    events_path = session_dir / "events.jsonl"
    return events_path


@router.get("", response_model=list[SessionSummary])
async def list_sessions() -> list[SessionSummary]:
    """List all discovered sessions, active-first by updated_at desc."""
    try:
        return discover_sessions()
    except Exception as exc:
        logger.exception("Failed to discover sessions")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/stats/daily", response_model=DailyUsageResponse)
async def get_daily_usage_stats() -> DailyUsageResponse:
    """Get aggregated token usage for today's sessions."""
    try:
        return await get_daily_usage()
    except Exception as exc:
        logger.exception("Failed to compute daily usage stats")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/copilot-user", response_model=CopilotUserInfo)
async def get_current_copilot_user() -> CopilotUserInfo:
    """Get the currently logged-in Copilot CLI user."""
    try:
        return get_copilot_user_info()
    except Exception as exc:
        logger.exception("Failed to read Copilot user info")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.delete("/by-date", response_model=DeleteResult)
async def delete_sessions_by_date(body: DateRangeDeleteRequest) -> DeleteResult:
    """Delete all inactive sessions within a date range (inclusive)."""
    from datetime import date as date_type

    try:
        d_from = date_type.fromisoformat(body.date_from)
        d_to = date_type.fromisoformat(body.date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    if d_from > d_to:
        raise HTTPException(status_code=400, detail="date_from must be <= date_to")

    try:
        deleted, skipped_active, errors = delete_sessions_by_date_range(d_from, d_to)
        return DeleteResult(
            deleted=deleted,
            skipped_active=skipped_active,
            errors=errors,
        )
    except Exception as exc:
        logger.exception("Failed to delete sessions by date range")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.delete("/{session_id}", response_model=DeleteResult)
async def delete_single_session(session_id: str) -> DeleteResult:
    """Delete a single session by ID."""
    validate_session_id(session_id)
    result = delete_session(session_id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Session not found")
    if result == "active":
        raise HTTPException(status_code=409, detail="Session is active")
    if result.startswith("error:"):
        raise HTTPException(status_code=500, detail=result)
    return DeleteResult(deleted=[session_id])


@router.delete("", response_model=DeleteResult)
async def delete_sessions_batch(body: DeleteRequest) -> DeleteResult:
    """Batch delete sessions by IDs."""
    delete_result = DeleteResult()
    for sid in body.session_ids:
        try:
            validate_session_id(sid)
        except HTTPException:
            delete_result.not_found.append(sid)
            continue

        result = delete_session(sid)
        if result == "deleted":
            delete_result.deleted.append(sid)
        elif result == "active":
            delete_result.skipped_active.append(sid)
        elif result == "not_found":
            delete_result.not_found.append(sid)
        else:
            delete_result.errors[sid] = result
    return delete_result


@router.get("/{session_id}", response_model=Session)
async def get_session_detail(session_id: str) -> Session:
    """Get full metadata for a single session."""
    validate_session_id(session_id)
    try:
        return get_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as exc:
        logger.exception("Failed to get session %s", session_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{session_id}/events", response_model=list[Event])
async def get_session_events(session_id: str) -> list[Event]:
    """Get parsed and correlated events for a session."""
    events_path = _resolve_events_path(session_id)
    if not events_path.is_file():
        return []
    try:
        events = parse_events_file(events_path)
        correlate_tool_names(events)
        return events
    except Exception as exc:
        logger.exception("Failed to parse events for session %s", session_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{session_id}/stats", response_model=SessionStats)
async def get_session_stats(session_id: str) -> SessionStats:
    """Get computed statistics for a session."""
    events_path = _resolve_events_path(session_id)
    if not events_path.is_file():
        return SessionStats()
    try:
        events = parse_events_file(events_path)
        return compute_stats(events)
    except Exception as exc:
        logger.exception("Failed to compute stats for session %s", session_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


def _tree_to_dict(node: TreeNode) -> dict:
    """Recursively convert a TreeNode to a dict, avoiding Pydantic depth limits."""
    return {
        "event": node.event.model_dump(mode="json", by_alias=True),
        "semantic_kind": node.semantic_kind,
        "event_count": node.event_count,
        "duration_ms": node.duration_ms,
        "brief_description": node.brief_description,
        "status": node.status,
        "agent_name": node.agent_name,
        "children": [_tree_to_dict(c) for c in node.children],
    }


@router.get("/{session_id}/tree")
async def get_session_tree(session_id: str) -> JSONResponse:
    """Get nested event tree for a session."""
    events_path = _resolve_events_path(session_id)
    if not events_path.is_file():
        return JSONResponse(content=[])
    try:
        events = parse_events_file(events_path)
        correlate_tool_names(events)
        roots = build_event_tree(events)
        return JSONResponse(content=[_tree_to_dict(r) for r in roots])
    except Exception as exc:
        logger.exception("Failed to build tree for session %s", session_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
