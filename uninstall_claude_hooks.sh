#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# AgentWatch — uninstall Claude Code hooks
#
# Removes AgentWatch hook entries from ~/.claude/settings.json.
# Does NOT destroy any other user hooks.
# ---------------------------------------------------------------------------
set -euo pipefail

SETTINGS_FILE="$HOME/.claude/settings.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --no-backup: skip this script's own backup. Used when install_claude_hooks.sh
# calls us as a pre-clean step — the installer makes its own backup right after,
# so a second one here is just noise.
NO_BACKUP=0
for arg in "$@"; do
    case "$arg" in
        --no-backup) NO_BACKUP=1 ;;
    esac
done

# Resolve Python.
PYTHON_BIN=""
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"
else
    PYTHON_BIN="$(which python3 2>/dev/null || which python 2>/dev/null || echo '')"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[AgentWatch] ERROR: Could not find python3."
    exit 1
fi

if [ ! -f "$SETTINGS_FILE" ]; then
    echo "[AgentWatch] No settings.json found. Nothing to uninstall."
    exit 0
fi

if [ "$NO_BACKUP" -eq 1 ]; then
    echo "[AgentWatch] Skipping backup (--no-backup; caller will back up)."
else
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$HOME/.claude/settings.json.agentwatch.bak.uninstall.$TIMESTAMP"
    cp "$SETTINGS_FILE" "$BACKUP_FILE"
    echo "[AgentWatch] Backed up current settings to: $BACKUP_FILE"
fi

$PYTHON_BIN << PYEOF
import json, sys
from pathlib import Path

settings_file = Path("$SETTINGS_FILE")

with open(settings_file, "r", encoding="utf-8") as fh:
    settings = json.load(fh)

hooks = settings.get("hooks", {}) or {}
removed = []

for event_name in list(hooks.keys()):
    entries = hooks[event_name]
    if not isinstance(entries, list):
        continue

    kept = []
    for entry in entries:
        if not isinstance(entry, dict):
            kept.append(entry)
            continue

        # Nested schema: {"hooks": [{type: "command", command: "..."}], ...}.
        # Only treat as nested when the "hooks" key is actually present — a flat
        # entry has no such key, and entry.get("hooks", []) would otherwise
        # masquerade as an empty nested group and get dropped.
        if "hooks" in entry and isinstance(entry["hooks"], list):
            inner_hooks = entry["hooks"]
            filtered = [h for h in inner_hooks if not (isinstance(h, dict) and "agentwatch" in h.get("command", ""))]
            if len(filtered) < len(inner_hooks):
                removed.append(f"{event_name} (nested)")
            if filtered:
                entry["hooks"] = filtered
                kept.append(entry)
            # else: the group held only agentwatch hooks → drop it entirely.
            continue

        # Legacy flat format: {"command": "...agentwatch..."}.
        if "agentwatch" in entry.get("command", ""):
            removed.append(f"{event_name} (legacy)")
            continue

        kept.append(entry)

    if kept:
        hooks[event_name] = kept
    elif any(r.startswith(f"{event_name} ") for r in removed):
        # Only drop the event key when we actually removed an agentwatch hook
        # from it and nothing else remained — never touch an event we left alone.
        del hooks[event_name]

if removed:
    settings["hooks"] = hooks
    with open(settings_file, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, ensure_ascii=False, indent=2)
    print(f"[AgentWatch] Removed hooks for: {', '.join(removed)}")
    print(f"[AgentWatch] Updated: {settings_file}")
else:
    print("[AgentWatch] No AgentWatch hooks found — nothing removed.")

# If hooks dict is now empty, remove it.
if not hooks:
    settings.pop("hooks", None)
    with open(settings_file, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, ensure_ascii=False, indent=2)

PYEOF

if [ "$NO_BACKUP" -eq 1 ]; then
    # Pre-clean step for the installer — stay quiet so it doesn't look like a
    # standalone uninstall finished mid-install.
    echo "[AgentWatch] Pre-clean done (removed any stale AgentWatch hooks)."
else
    echo ""
    echo "[AgentWatch] Uninstall complete."
    echo "[AgentWatch] To restore from an earlier backup: cp <backup_file> $SETTINGS_FILE"
    echo "[AgentWatch] Backups available:"
    ls -la "$HOME/.claude/settings.json.agentwatch.bak."* 2>/dev/null || echo "  (none found)"
fi
