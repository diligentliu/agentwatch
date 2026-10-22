"""Classify parsed events into AgentWatch event types."""

from __future__ import annotations

from typing import Any

# ── Notification hook keyword sets ────────────────────────────────────────
# Strong keywords → permission_required (user MUST act).
_PERMISSION_KEYWORDS_EN = {
    "permission", "permissions", "allow", "approve", "approval",
    "confirm", "confirmation", "needs your attention",
    "waiting for input", "waiting for user", "requires user",
    "user action required",
}
_PERMISSION_KEYWORDS_ZH = {
    "权限", "允许", "批准", "确认", "等待用户",
    "需要你", "需要用户", "需要操作", "是否继续", "请确认",
}
# Softer keywords → attention_required (user SHOULD check).
_ATTENTION_KEYWORDS_EN = {
    "continue?", "proceed?", "notice", "warning",
    "requires attention", "user input", "intervention",
}
_ATTENTION_KEYWORDS_ZH = {
    "注意", "提醒", "需要处理", "需要介入",
}

# Structured routing for the Notification hook's `notification_type` field
# (current Claude Code always sends it). Only types that need the user to act
# AND would be missed while away get pushed; the rest are logged as `info`.
# `permission_prompt` maps to info because PermissionRequest already covers it
# with richer payload — routing it here would duplicate that push.
_NOTIFICATION_TYPE_MAP = {
    "permission_prompt": "info",
    "idle_prompt": "attention_required",
    "elicitation_dialog": "attention_required",
    "auth_success": "info",
    "elicitation_complete": "info",
    "elicitation_response": "info",
}


def _scan_notification_text(raw_text: str) -> str:
    """Scan Notification hook text for permission / attention keywords.

    Returns 'permission_required', 'attention_required', or 'attention_required'
    (default fallback for Notification events).
    """
    text_lower = raw_text.lower()

    # Check strong permission keywords first.
    for kw in _PERMISSION_KEYWORDS_EN:
        if kw in text_lower:
            return "permission_required"
    for kw in _PERMISSION_KEYWORDS_ZH:
        if kw in text_lower:
            return "permission_required"

    # Check softer attention keywords.
    for kw in _ATTENTION_KEYWORDS_EN:
        if kw in text_lower:
            return "attention_required"
    for kw in _ATTENTION_KEYWORDS_ZH:
        if kw in text_lower:
            return "attention_required"

    # Notification hook fired but no strong keyword → still attention_required.
    return "attention_required"


def classify(parsed: dict[str, Any]) -> str:
    """Return an event-type label for the parsed event.

    Possible return values:
        permission_required  — Notification hook with permission/approval keywords.
        attention_required   — Notification hook without strong permission keywords.
        task_done            — Stop hook fired.
        danger               — High-risk tool usage detected (policy.py upgrades).
        drift                — Suspected task-boundary violation (policy.py upgrades).
        failure              — Consecutive failures reached threshold (policy.py upgrades).
        pretooluse           — PreToolUse, pending policy evaluation.
        posttooluse          — PostToolUse (success).
        posttooluse_error    — PostToolUse with error indicators.
        info                 — Informational, no notification needed.
    """
    event_name = parsed.get("event_name", "")

    if event_name == "PermissionRequest":
        return "permission_required"

    if event_name == "PermissionDenied":
        return "permission_denied"

    if event_name == "Notification":
        raw = parsed.get("raw_event", {}) or {}
        ntype = raw.get("notification_type", "")
        if ntype:
            # Known field → structured routing. Unknown value stays actionable
            # rather than being silently dropped.
            return _NOTIFICATION_TYPE_MAP.get(ntype, "attention_required")
        # Field absent (older Claude Code / non-standard payload) → fall back to
        # the keyword scan, the only signal available without the typed field.
        raw_text = parsed.get("raw_text", "")
        return _scan_notification_text(raw_text)

    if event_name == "Stop":
        return "task_done"

    if event_name == "PreToolUse":
        return "pretooluse"

    if event_name == "PostToolUse":
        if parsed.get("has_error"):
            return "posttooluse_error"
        return "posttooluse"

    return "info"


def classify_simulated(scenario: str) -> str:
    """Map a simulate subcommand to an event type."""
    mapping = {
        "danger": "danger",
        "done": "task_done",
        "drift": "drift",
        "failure": "failure",
        "permission": "permission_required",
        "permission-request": "permission_required",
        "permission-denied": "permission_denied",
    }
    return mapping.get(scenario, "info")
