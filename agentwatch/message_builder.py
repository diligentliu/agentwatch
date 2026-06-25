"""Build Watch notification titles and bodies.

Design: the body is the raw "what is happening" — the actual command, file
path, url, or Claude's last reply — with no risk level or suggestion framing.
The title names the event type (and the tool, when known) so a glance is
enough to decide whether to act. Risk/drift/failure detection still decides
*whether* to push (see policy.py); it just no longer dictates the wording.
"""

from __future__ import annotations

from typing import Any

from agentwatch.event_parser import extract_tool_detail, extract_last_assistant_text


# Base title per event_type. build_message may append " · <tool>" or other
# context to make the title self-explanatory at a glance.
TITLE_MAP = {
    "permission_required": "权限请求",
    "attention_required": "需要处理",
    "task_done": "任务完成",
    "guard_blocked": "已拦截",
    "danger": "高风险",
    "drift": "可能跑偏",
    "failure": "连续失败",
    "possible_permission_wait": "疑似等待",
    "permission_denied": "已拒绝",
}


def build_message(
    event_type: str,
    parsed: dict[str, Any] | None = None,
    danger_info: dict[str, Any] | None = None,
    drift_info: dict[str, Any] | None = None,
    failure_info: dict[str, Any] | None = None,
    extra_summary: str = "",
    config: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Generate a Watch notification {title, body}.

    The body carries the bare event content (command / path / url / reply).
    extra_summary is a pre-rendered "Tool: snippet" fallback used by the
    simulate path, where no real tool_input is available.
    """
    title = TITLE_MAP.get(event_type, "AgentWatch")
    suffix = _title_suffix(event_type, parsed, drift_info, failure_info)
    if suffix:
        title = f"{title} · {suffix}"

    body = _build_body(event_type, parsed, danger_info, drift_info, failure_info, extra_summary)
    return {"title": title, "body": body}


def _title_suffix(
    event_type: str,
    parsed: dict[str, Any] | None,
    drift_info: dict[str, Any] | None,
    failure_info: dict[str, Any] | None,
) -> str:
    """Context appended to the title so the user knows what kind of event it is."""
    if event_type in ("permission_required", "guard_blocked", "danger", "possible_permission_wait", "permission_denied"):
        tool = (parsed or {}).get("tool_name", "")
        return tool or ""
    if event_type == "drift" and drift_info:
        return f"原任务 {drift_info.get('task_name', '')}".strip()
    if event_type == "failure" and failure_info:
        count = failure_info.get("consecutive_failures", "")
        return f"{count} 次" if count else ""
    return ""


def _build_body(
    event_type: str,
    parsed: dict[str, Any] | None,
    danger_info: dict[str, Any] | None,
    drift_info: dict[str, Any] | None,
    failure_info: dict[str, Any] | None,
    extra_summary: str = "",
) -> str:
    if event_type == "permission_required":
        return _body_tool_content(parsed, extra_summary, fallback="等待用户允许操作")
    if event_type == "attention_required":
        return _body_attention(parsed)
    if event_type == "task_done":
        return _body_done(parsed)
    if event_type == "guard_blocked":
        return _body_tool_content(parsed, extra_summary, danger_info=danger_info, fallback="高风险操作已拦截")
    if event_type == "danger":
        return _body_tool_content(parsed, extra_summary, danger_info=danger_info, fallback="检测到高风险操作")
    if event_type == "drift":
        return _body_drift(drift_info)
    if event_type == "failure":
        return _body_failure(parsed, failure_info)
    if event_type == "possible_permission_wait":
        return _body_tool_content(parsed, extra_summary, fallback="工具调用尚未返回")
    if event_type == "permission_denied":
        return _body_permission_denied(parsed)
    return "AgentWatch 事件"


def _body_tool_content(
    parsed: dict[str, Any] | None,
    extra_summary: str = "",
    danger_info: dict[str, Any] | None = None,
    fallback: str = "",
) -> str:
    """Body = the raw tool content (command / file path / url).

    Prefers the real tool_input from *parsed*. Falls back to the pre-rendered
    extra_summary (simulate path), then to matched danger keywords, then to a
    plain fallback string. No risk/suggestion lines.
    """
    detail = ""
    if parsed:
        detail = extract_tool_detail(parsed).get("detail", "")
    if not detail and extra_summary:
        detail = extra_summary
    if not detail and danger_info:
        kws = ", ".join(danger_info.get("matched_keywords", [])[:3])
        if kws:
            detail = f"涉及 {kws}"
    return detail or fallback


def _body_attention(parsed: dict[str, Any] | None) -> str:
    raw_event = (parsed or {}).get("raw_event", {}) or {}
    # Current Claude Code puts `message` at the top level of the Notification
    # payload; the nested `notification` object is a back-compat fallback.
    nested = raw_event.get("notification", {}) or {}
    msg = (
        raw_event.get("message", "")
        or nested.get("message", "")
        or nested.get("body", "")
        or nested.get("title", "")
        or "Agent 需要你处理"
    )
    if len(msg) > 200:
        msg = msg[:199] + "…"
    return msg


def _body_done(parsed: dict[str, Any] | None) -> str:
    """Body for task_done — Claude's last reply, read from the transcript."""
    raw = (parsed or {}).get("raw_event", {}) or {}
    text = extract_last_assistant_text(raw)
    if text:
        return text
    # Fallback: stop reason, then a plain string.
    return raw.get("reason", "") or "任务已完成"


def _body_drift(drift_info: dict[str, Any] | None) -> str:
    if not drift_info:
        return "可能偏离了原任务"
    violations = drift_info.get("matched_boundary_violations", [])
    v_str = ", ".join(violations[:3])
    return f"触碰 {v_str}" if v_str else "可能偏离了原任务"


def _body_permission_denied(parsed: dict[str, Any] | None) -> str:
    detail = ""
    if parsed:
        detail = extract_tool_detail(parsed).get("detail", "")
    return detail or "用户已拒绝本次操作"


def _body_failure(parsed: dict[str, Any] | None, failure_info: dict[str, Any] | None) -> str:
    """Body for failure — the tool content that failed, if available."""
    detail = ""
    if parsed:
        detail = extract_tool_detail(parsed).get("detail", "")
    if detail:
        return detail
    if failure_info:
        count = failure_info.get("consecutive_failures", "?")
        return f"已连续失败 {count} 次"
    return "连续操作失败"
