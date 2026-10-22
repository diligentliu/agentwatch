#!/usr/bin/env python3
"""Remove AgentWatch lifecycle hooks from ~/.codex/hooks.json safely."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

HOOKS_FILE = Path.home() / ".codex" / "hooks.json"


def main() -> None:
    if not HOOKS_FILE.exists():
        print("[AgentWatch] No Codex hooks.json found.")
        return

    backup = HOOKS_FILE.with_name(
        f"hooks.json.agentwatch.bak.uninstall.{time.strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copy2(HOOKS_FILE, backup)
    settings = json.loads(HOOKS_FILE.read_text(encoding="utf-8-sig"))
    hooks = settings.get("hooks", {})
    removed = []
    if isinstance(hooks, dict):
        for event, groups in list(hooks.items()):
            if not isinstance(groups, list):
                continue
            kept = []
            for group in groups:
                inner = group.get("hooks", []) if isinstance(group, dict) else []
                filtered = [
                    item for item in inner
                    if not (
                        isinstance(item, dict)
                        and isinstance(item.get("command"), str)
                        and "agentwatch" in item["command"].lower()
                    )
                ]
                if len(filtered) != len(inner):
                    removed.append(event)
                    if filtered:
                        group["hooks"] = filtered
                        kept.append(group)
                else:
                    kept.append(group)
            if kept or not any(name == event for name in removed):
                hooks[event] = kept
            else:
                del hooks[event]
        if not hooks:
            settings.pop("hooks", None)

    HOOKS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if removed:
        print(f"[AgentWatch] Removed hooks from: {', '.join(sorted(set(removed)))}")
    else:
        print("[AgentWatch] No AgentWatch hooks found.")
    print(f"[AgentWatch] Backup: {backup}")


if __name__ == "__main__":
    main()
