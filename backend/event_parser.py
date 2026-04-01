"""JSONL event parsing logic."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from .models import Event, SessionStats, TreeNode

logger = logging.getLogger(__name__)

MAX_TREE_DEPTH = 50


def parse_events_file(path: Path | str) -> list[Event]:
    """Parse a JSONL file into a sorted list of Event objects.

    Reads line by line to avoid loading the entire file into memory.
    Malformed lines are skipped with a warning.
    Events are sorted by timestamp after parsing.
    """
    path = Path(path)
    events: list[Event] = []
    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
                events.append(Event.model_validate(raw))
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning("Skipping malformed line %d in %s: %s", line_num, path, exc)
    events.sort(key=lambda e: e.timestamp)
    return events


def correlate_tool_names(events: list[Event]) -> list[Event]:
    """Populate tool_name on tool.execution_complete events.

    Builds a lookup from toolCallId -> toolName using tool.execution_start
    events, then sets tool_name on matching tool.execution_complete events.
    """
    call_id_to_name: dict[str, str] = {}
    for ev in events:
        if ev.type == "tool.execution_start":
            tool_call_id = ev.data.get("toolCallId")
            tool_name = ev.data.get("toolName")
            if tool_call_id and tool_name:
                call_id_to_name[tool_call_id] = tool_name

    for ev in events:
        if ev.type == "tool.execution_complete":
            tool_call_id = ev.data.get("toolCallId")
            if tool_call_id:
                name = call_id_to_name.get(tool_call_id)
                if name:
                    ev.tool_name = name
    return events


def _coerce_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return " ".join(text.split())


def _truncate_text(text: str | None, limit: int = 72) -> str | None:
    if not text:
        return None
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _get_text(data: dict, *keys: str) -> str | None:
    for key in keys:
        text = _coerce_text(data.get(key))
        if text:
            return text
    return None


def _get_int(data: dict, *keys: str) -> int | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                continue
    return None


def _get_tool_call_id(event: Event) -> str | None:
    return _coerce_text(event.data.get("toolCallId"))


def _classify_semantic_kind(event_type: str) -> str:
    if event_type.startswith("session"):
        return "session"
    if event_type.startswith("turn") or ".turn_" in event_type:
        return "turn"
    if event_type.startswith("user"):
        return "user"
    if event_type.startswith("assistant"):
        return "assistant"
    if event_type.startswith("tool"):
        return "tool"
    if event_type.startswith("subagent"):
        return "subagent"
    return "event"


def _derive_status(event: Event) -> str | None:
    event_type = event.type
    if event_type.endswith("failed"):
        return "failed"
    if event_type.endswith("completed"):
        return "completed"

    success = event.data.get("success")
    if success is True:
        return "completed"
    if success is False:
        return "failed"

    if event_type.endswith("started"):
        return "running"
    return None


def _derive_agent_name(event: Event) -> str | None:
    data = event.data
    agent_name = _get_text(data, "agentName", "agent_name")
    if agent_name:
        return agent_name

    tool_telemetry = data.get("toolTelemetry")
    if isinstance(tool_telemetry, dict):
        properties = tool_telemetry.get("properties")
        if isinstance(properties, dict):
            agent_name = _get_text(
                properties,
                "agentName",
                "agent_name",
                "agent_type",
                "agentDisplayName",
            )
            if agent_name:
                return agent_name

    return _get_text(data, "agentDisplayName", "name")


def _derive_duration_ms(
    event: Event,
    tool_start_times: dict[str, Event],
    subagent_start_times: dict[str, Event],
) -> int | None:
    data = event.data

    duration_ms = _get_int(data, "duration_ms", "durationMs")
    if duration_ms is not None:
        return duration_ms

    result = data.get("result")
    if isinstance(result, dict):
        duration_ms = _get_int(result, "duration_ms", "durationMs")
        if duration_ms is not None:
            return duration_ms

    tool_telemetry = data.get("toolTelemetry")
    if isinstance(tool_telemetry, dict):
        metrics = tool_telemetry.get("metrics")
        if isinstance(metrics, dict):
            duration_seconds = metrics.get("duration_seconds")
            if isinstance(duration_seconds, (int, float)):
                return int(duration_seconds * 1000)

            elapsed_seconds = metrics.get("elapsed_seconds")
            if isinstance(elapsed_seconds, (int, float)):
                return int(elapsed_seconds * 1000)

    tool_call_id = _get_tool_call_id(event)
    if not tool_call_id:
        return None

    if event.type == "tool.execution_complete":
        start_event = tool_start_times.get(tool_call_id)
        if start_event is not None:
            delta = event.timestamp - start_event.timestamp
            return max(int(delta.total_seconds() * 1000), 0)

    if event.type.startswith("subagent."):
        start_event = subagent_start_times.get(tool_call_id)
        if start_event is not None:
            delta = event.timestamp - start_event.timestamp
            return max(int(delta.total_seconds() * 1000), 0)

    return None


def _format_session_description(event: Event) -> str | None:
    session_id = _get_text(event.data, "sessionId", "session_id")
    if not session_id:
        return None
    if len(session_id) <= 12:
        return session_id
    return session_id[:8]


def _format_turn_description(event: Event) -> str | None:
    turn_number = _get_int(event.data, "turn_number", "turnNumber", "turn_index", "turnIndex")
    if turn_number is None:
        return None
    return f"turn #{turn_number}"


def _derive_brief_description(event: Event, semantic_kind: str) -> str | None:
    if semantic_kind == "session":
        return _format_session_description(event)

    if semantic_kind == "turn":
        return _format_turn_description(event)

    if semantic_kind == "tool":
        tool_name = event.tool_name or _get_text(event.data, "toolName", "tool_name")
        args = event.data.get("arguments")
        if isinstance(args, dict):
            if tool_name == "bash":
                cmd = _get_text(args, "command")
                if cmd:
                    return f"$ {_truncate_text(cmd, 80)}"
            elif tool_name == "grep":
                pattern = _get_text(args, "pattern")
                if pattern:
                    path = _get_text(args, "path")
                    path_short = path.rsplit("/", 1)[-1] if path else None
                    desc = f"/{_truncate_text(pattern, 40)}/"
                    if path_short:
                        desc += f" in {path_short}"
                    return desc
            elif tool_name == "glob":
                pattern = _get_text(args, "pattern")
                if pattern:
                    return _truncate_text(pattern, 80)

    content = _get_text(event.data, "content", "message", "intent", "description")
    if content:
        return _truncate_text(content)

    tool_requests = event.data.get("toolRequests")
    if isinstance(tool_requests, list) and tool_requests:
        count = len(tool_requests)
        noun = "tool call" if count == 1 else "tool calls"
        return f"{count} {noun}"

    result = event.data.get("result")
    if isinstance(result, dict):
        content = _get_text(result, "content", "detailedContent")
        if content:
            return _truncate_text(content)

    return None


def _build_start_time_lookups(events: Iterable[Event]) -> tuple[dict[str, Event], dict[str, Event]]:
    tool_start_times: dict[str, Event] = {}
    subagent_start_times: dict[str, Event] = {}

    for event in events:
        tool_call_id = _get_tool_call_id(event)
        if not tool_call_id:
            continue

        if event.type == "tool.execution_start":
            tool_start_times.setdefault(tool_call_id, event)
        elif event.type == "subagent.started":
            subagent_start_times.setdefault(tool_call_id, event)

    return tool_start_times, subagent_start_times


def _enrich_tree_node(
    node: TreeNode,
    tool_start_times: dict[str, Event],
    subagent_start_times: dict[str, Event],
) -> int:
    event_count = 1
    for child in node.children:
        event_count += _enrich_tree_node(child, tool_start_times, subagent_start_times)

    semantic_kind = _classify_semantic_kind(node.event.type)
    node.semantic_kind = semantic_kind
    node.event_count = event_count
    node.status = _derive_status(node.event)
    node.duration_ms = _derive_duration_ms(node.event, tool_start_times, subagent_start_times)
    node.brief_description = _derive_brief_description(node.event, semantic_kind)
    node.agent_name = _derive_agent_name(node.event) if semantic_kind == "subagent" else None
    return event_count


def _enrich_tree_nodes(roots: list[TreeNode], events: list[Event]) -> None:
    tool_start_times, subagent_start_times = _build_start_time_lookups(events)
    for root in roots:
        _enrich_tree_node(root, tool_start_times, subagent_start_times)


def build_event_tree(events: list[Event], max_depth: int = MAX_TREE_DEPTH) -> list[TreeNode]:
    """Build a nested tree from parentId chains.

    Returns root nodes (events with missing or invalid parents). Parent cycles are
    broken deterministically, and trees deeper than max_depth are flattened.
    """
    nodes: dict[str, TreeNode] = {}
    for ev in events:
        nodes[ev.id] = TreeNode(event=ev)

    child_ids_by_parent: dict[str, list[str]] = defaultdict(list)
    ordered_ids = [ev.id for ev in events]
    root_ids: list[str] = []

    for ev in events:
        parent_id = ev.parent_id
        if parent_id is None or parent_id == ev.id or parent_id not in nodes:
            root_ids.append(ev.id)
        else:
            child_ids_by_parent[parent_id].append(ev.id)

    roots: list[TreeNode] = []
    visited: set[str] = set()

    def attach_subtree(root_id: str) -> None:
        if root_id in visited:
            return

        root = nodes[root_id]
        roots.append(root)
        visited.add(root_id)

        initial_cap_node = root if max_depth == 0 else None
        stack: list[tuple[str, TreeNode, int, set[str], TreeNode | None]] = [
            (root_id, root, 0, {root_id}, initial_cap_node)
        ]

        while stack:
            parent_id, parent_node, depth, path, cap_node = stack.pop()

            for child_id in reversed(child_ids_by_parent.get(parent_id, [])):
                if child_id in visited or child_id in path:
                    continue

                child_node = nodes[child_id]
                next_depth = depth + 1

                if next_depth > max_depth:
                    target_parent = cap_node or parent_node
                    next_cap_node = cap_node or parent_node
                    effective_depth = max_depth
                else:
                    target_parent = parent_node
                    next_cap_node = child_node if next_depth == max_depth else cap_node
                    effective_depth = next_depth

                target_parent.children.append(child_node)
                visited.add(child_id)
                stack.append(
                    (
                        child_id,
                        child_node,
                        effective_depth,
                        path | {child_id},
                        next_cap_node,
                    )
                )

    for root_id in root_ids:
        attach_subtree(root_id)

    for event_id in ordered_ids:
        attach_subtree(event_id)

    _enrich_tree_nodes(roots, events)
    return roots


def compute_stats(events: list[Event]) -> SessionStats:
    """Compute session statistics from events.

    Uses session.shutdown data when available, and counts event types.
    """
    total_events = len(events)
    duration_seconds = 0.0
    models_used: list[str] = []
    input_tokens = 0
    output_tokens = 0
    cache_read_tokens = 0
    cache_write_tokens = 0
    tool_calls = 0
    user_messages = 0
    assistant_turns = 0
    files_modified = 0
    lines_added = 0
    lines_removed = 0
    premium_requests = 0

    # Compute duration from first/last event timestamps
    if len(events) >= 2:
        dt = (events[-1].timestamp - events[0].timestamp).total_seconds()
        duration_seconds = max(dt, 0.0)

    # Count event types
    for ev in events:
        if ev.type == "tool.execution_start":
            tool_calls += 1
        elif ev.type == "user.message":
            user_messages += 1
        elif ev.type == "assistant.turn_start":
            assistant_turns += 1

    # Extract shutdown data if present
    for ev in events:
        if ev.type == "session.shutdown":
            data = ev.data
            premium_requests = data.get("totalPremiumRequests", 0)

            if "totalApiDurationMs" in data:
                duration_seconds = data["totalApiDurationMs"] / 1000.0

            code_changes = data.get("codeChanges", {})
            lines_added = code_changes.get("linesAdded", 0)
            lines_removed = code_changes.get("linesRemoved", 0)
            files_list = code_changes.get("filesModified", [])
            files_modified = len(files_list) if isinstance(files_list, list) else 0

            model_metrics = data.get("modelMetrics", {})
            for model_name, metrics in model_metrics.items():
                models_used.append(model_name)
                usage = metrics.get("usage", {})
                input_tokens += usage.get("inputTokens", 0)
                output_tokens += usage.get("outputTokens", 0)
                cache_read_tokens += usage.get("cacheReadTokens", 0)
                cache_write_tokens += usage.get("cacheWriteTokens", 0)

            current_model = data.get("currentModel")
            if current_model and current_model not in models_used:
                models_used.append(current_model)
            break

    return SessionStats(
        total_events=total_events,
        duration_seconds=duration_seconds,
        models_used=models_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
        tool_calls=tool_calls,
        user_messages=user_messages,
        assistant_turns=assistant_turns,
        files_modified=files_modified,
        lines_added=lines_added,
        lines_removed=lines_removed,
        premium_requests=premium_requests,
    )
