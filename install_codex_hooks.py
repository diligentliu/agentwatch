#!/usr/bin/env python3
"""Safely merge AgentWatch lifecycle hooks into ~/.codex/hooks.json."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HOOKS_FILE = Path.home() / ".codex" / "hooks.json"
EVENTS = (
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PermissionRequest",
    "Stop",
)


def has_agentwatch(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    return any(
        isinstance(hook, dict)
        and isinstance(hook.get("command"), str)
        and "agentwatch" in hook["command"].lower()
        for hook in entry.get("hooks", [])
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Python interpreter used by Codex hooks")
    args = parser.parse_args()

    if HOOKS_FILE.exists():
        backup = HOOKS_FILE.with_name(
            f"hooks.json.agentwatch.bak.{time.strftime('%Y%m%d_%H%M%S')}"
        )
        shutil.copy2(HOOKS_FILE, backup)
        with HOOKS_FILE.open(encoding="utf-8-sig") as stream:
            settings = json.load(stream)
        print(f"[AgentWatch] Backed up Codex hooks to {backup}")
    else:
        HOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        settings = {}

    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"[AgentWatch] Invalid hooks.json: 'hooks' must be an object ({HOOKS_FILE})")

    command = f'"{Path(args.python).as_posix()}" -m agentwatch.cli hook --event '
    for event in EVENTS:
        groups = hooks.get(event, [])
        if not isinstance(groups, list):
            raise SystemExit(f"[AgentWatch] Invalid hook list for {event}; file left unchanged")
        kept = [group for group in groups if not has_agentwatch(group)]
        kept.append({
            "hooks": [{
                "type": "command",
                "command": command + event,
                "timeout": 15,
            }]
        })
        hooks[event] = kept

    temp = HOOKS_FILE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(HOOKS_FILE)
    print(f"[AgentWatch] Installed Codex hooks: {', '.join(EVENTS)}")
    print(f"[AgentWatch] Updated: {HOOKS_FILE}")
    print("[AgentWatch] In Codex, run /hooks and review/trust the new AgentWatch hooks.")


if __name__ == "__main__":
    main()
