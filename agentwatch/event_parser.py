"""Parse Claude Code hook JSON into a structured internal event."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentwatch.utils import flatten_strings


def parse_event(raw: dict[str, Any] | None, event_name: str) -> dict[str, Any]:
    """Turn a raw Claude Code hook payload into an AgentWatch internal event dict.

    Parameters
    ----------
    raw : dict or None
        The JSON parsed from stdin.  May be None when stdin was empty.
    event_name : str
        One of PreToolUse, PostToolUse, Notification, Stop.

    Returns
    -------
    dict with keys:
        timestamp, event_name, raw_text, tool_name, tool_input,
        has_error, parsed, raw_event
    """
    parsed = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_name": event_name,
        "raw_text": "",
        "tool_name": "",
        "tool_input": {},
        "has_error": False,
        "parsed": True,
        "raw_event": raw or {},
    }

    if raw is None:
        return parsed

    # Flatten all strings for keyword matching.
    all_strings = flatten_strings(raw)
    parsed["raw_text"] = " ".join(all_strings)

    # Extract tool_name / tool_input for PreToolUse / PostToolUse.
    tool_name = raw.get("tool_name", "") or raw.get("tool", "") or ""
    if not tool_name and isinstance(raw.get("tool_use"), dict):
        tool_name = raw["tool_use"].get("name", "")
    parsed["tool_name"] = tool_name

    tool_input = raw.get("tool_input", {}) or raw.get("input", {})
    if isinstance(tool_input, str):
        try:
            import json as _json
            tool_input = _json.loads(tool_input)
        except Exception:
            tool_input = {"raw": tool_input}
    parsed["tool_input"] = tool_input if isinstance(tool_input, dict) else {}

    # Detect error indicators for PostToolUse.
    error_keywords = {"error", "failed", "exception", "traceback", "non-zero", "exit code", "traceback", "stack trace"}
    raw_lower = parsed["raw_text"].lower()
    if any(kw in raw_lower for kw in error_keywords):
        parsed["has_error"] = True

    return parsed


def extract_tool_identity(parsed: dict[str, Any]) -> str:
    """Extract a stable tool-call identity from a parsed event.

    Prefers tool_use_id from raw_event, falls back to empty string.
    """
    raw = parsed.get("raw_event", {}) or {}
    tuid = raw.get("tool_use_id", "") or ""
    if not tuid and isinstance(raw.get("tool_use"), dict):
        tuid = raw["tool_use"].get("id", "") or ""
    return tuid


def extract_tool_summary(parsed: dict[str, Any]) -> str:
    """Produce a short human-readable summary of the tool call."""
    tool_name = parsed.get("tool_name", "") or "Unknown"
    tool_input = parsed.get("tool_input", {}) or {}

    command = tool_input.get("command", "")
    file_path = tool_input.get("file_path", "")
    url = tool_input.get("url", "")
    notebook_path = tool_input.get("notebook_path", "")

    snippet = command or file_path or url or notebook_path or ""
    if snippet:
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        return f"{tool_name}: {snippet}"

    for k in ("command", "file_path", "content", "url", "description"):
        v = tool_input.get(k, "")
        if v and isinstance(v, str) and len(v) > 2:
            short = v[:120] + "..." if len(v) > 120 else v
            return f"{tool_name}: {short}"

    return f"{tool_name}"


def make_pending_action_id(parsed: dict[str, Any]) -> str:
    """Create a pending-action id, preferring tool_use_id from the hook JSON."""
    tuid = extract_tool_identity(parsed)
    if tuid:
        return tuid
    from agentwatch.store import new_action_id
    return new_action_id()


# Per-tool extraction: which tool_input field carries the "what is happening".
# Order within each tuple is priority — first non-empty wins.
_TOOL_DETAIL_FIELDS: dict[str, tuple[str, ...]] = {
    "Bash":        ("command",),
    "Edit":        ("file_path",),
    "MultiEdit":   ("file_path",),
    "Write":       ("file_path",),
    "NotebookEdit": ("notebook_path", "file_path"),
    "Read":        ("file_path",),
    "Glob":        ("pattern", "path"),
    "Grep":        ("pattern", "path"),
    "WebFetch":    ("url",),
    "WebSearch":   ("query",),
}

# Fallback field probe order for unknown tools.
_DETAIL_FALLBACK_FIELDS = ("command", "file_path", "notebook_path", "url", "query", "pattern", "path", "description")


def extract_tool_detail(parsed: dict[str, Any], max_len: int = 200) -> dict[str, str]:
    """Extract the raw 'what is happening' content of a tool call.

    Returns {"tool": <tool name>, "detail": <key field, truncated>}. The detail
    is the bare command / file path / url — no risk or suggestion framing. When
    no field matches, detail is "" and the caller shows just the tool name.
    """
    tool_name = parsed.get("tool_name", "") or "Unknown"
    tool_input = parsed.get("tool_input", {}) or {}

    fields = _TOOL_DETAIL_FIELDS.get(tool_name, _DETAIL_FALLBACK_FIELDS)
    detail = ""
    for key in fields:
        val = tool_input.get(key, "")
        if isinstance(val, str) and val.strip():
            detail = val.strip()
            break

    if not detail:
        for key in _DETAIL_FALLBACK_FIELDS:
            val = tool_input.get(key, "")
            if isinstance(val, str) and val.strip():
                detail = val.strip()
                break

    if len(detail) > max_len:
        detail = detail[: max_len - 1] + "…"

    return {"tool": tool_name, "detail": detail}


def extract_last_assistant_text(raw: dict[str, Any] | None, max_len: int = 400) -> str:
    """Read the transcript and return Claude's last assistant text block.

    Reads ``raw["transcript_path"]`` (a JSONL file), scans from the end for the
    most recent ``type == "assistant"`` message, and returns its last text
    block. Returns "" on any failure — this runs inside a hook, so it must
    never raise.
    """
    if not raw:
        return ""
    transcript_path = raw.get("transcript_path", "") or ""
    if not transcript_path:
        return ""

    try:
        import json as _json

        with open(transcript_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()

        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
            except Exception:
                continue
            if obj.get("type") != "assistant":
                continue
            msg = obj.get("message", {})
            if isinstance(msg, str):
                text = msg.strip()
            elif isinstance(msg, dict):
                content = msg.get("content", [])
                text = ""
                if isinstance(content, str):
                    text = content.strip()
                elif isinstance(content, list):
                    for block in reversed(content):
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = (block.get("text", "") or "").strip()
                            if text:
                                break
            else:
                text = ""
            if text:
                if len(text) > max_len:
                    text = text[: max_len - 1] + "…"
                return text
        return ""
    except Exception:
        return ""
