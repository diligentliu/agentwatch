"""Configuration management for AgentWatch.

Paths are auto-detected from the project root (where pyproject.toml lives).
No hardcoded home-directory assumptions — works anywhere the user clones.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any

# ── Project root detection ──────────────────────────────────────────────

def _find_project_root() -> Path:
    """Return the directory containing pyproject.toml.

    Detection order:
    1. Walk up from this file (agentwatch/config.py -> agentwatch/ -> root)
    2. AGENTWATCH_HOME environment variable
    3. Current working directory
    4. ~/Projects/agentwatch (legacy compatibility)
    """
    # 1. Walk up from this config module.
    here = Path(__file__).resolve().parent.parent
    if (here / "pyproject.toml").exists():
        return here

    # 2. Environment variable.
    env = os.environ.get("AGENTWATCH_HOME", "")
    if env:
        p = Path(env)
        if (p / "pyproject.toml").exists():
            return p

    # 3. Current working directory.
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists():
        return cwd

    # 4. Legacy default.
    legacy = Path.home() / "Projects" / "agentwatch"
    if legacy.exists():
        return legacy

    # Last resort: return cwd so the user sees a clear error.
    return cwd


_PROJECT_ROOT: Path | None = None


def project_root() -> Path:
    """Return the cached project root directory."""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = _find_project_root()
    return _PROJECT_ROOT


# ── Paths ───────────────────────────────────────────────────────────────

def _config_file_path() -> Path:
    return project_root() / "config.json"


def _example_config_path() -> Path:
    return project_root() / "config.example.json"


def _logs_dir_path() -> Path:
    return project_root() / "logs"


def _state_file_path() -> Path:
    return project_root() / "logs" / "state.json"


# Module-level aliases — updated each time project_root() is evaluated.
# (Safe because these are immutable Path objects; callers that store
#  these at import time will have the correct value if root is fixed.)

DEFAULT_CONFIG_DIR = project_root()
CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
EXAMPLE_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.example.json"
LOGS_DIR = DEFAULT_CONFIG_DIR / "logs"
STATE_FILE = LOGS_DIR / "state.json"


# ── Public API ──────────────────────────────────────────────────────────

def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load configuration from config.json.  Exit with a clear message if missing."""
    target = Path(path) if path else CONFIG_FILE
    if not target.exists():
        print(f"[AgentWatch] Config file not found: {target}")
        print("[AgentWatch] Run 'agentwatch init' to create one.")
        raise SystemExit(1)
    try:
        with open(target, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"[AgentWatch] Failed to parse config: {exc}")
        raise SystemExit(1)


def init_config() -> Path:
    """Copy config.example.json -> config.json if the latter does not exist."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_FILE.exists():
        print(f"[AgentWatch] {CONFIG_FILE} already exists -- skipping init.")
        return CONFIG_FILE

    if not EXAMPLE_CONFIG_FILE.exists():
        print(f"[AgentWatch] {EXAMPLE_CONFIG_FILE} not found. Cannot initialise.")
        print(f"[AgentWatch] Project root: {project_root()}")
        print("[AgentWatch] Make sure config.example.json is in the project directory.")
        raise SystemExit(1)

    shutil.copy(EXAMPLE_CONFIG_FILE, CONFIG_FILE)
    print(f"[AgentWatch] Created {CONFIG_FILE}")
    print("[AgentWatch]   -> Edit it and fill in your notifier.bark_key.")
    return CONFIG_FILE


def get_notifier_config(config: dict[str, Any]) -> dict[str, Any]:
    """Extract and validate notifier section."""
    nc = config.get("notifier", {})
    if nc.get("type") == "bark" and not nc.get("bark_key"):
        print("[AgentWatch] WARNING: bark_key is empty in config.json")
    return nc


def get_risk_policy(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("risk_policy", {})


def get_task_boundary(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("task_boundary", {})


def get_failure_policy(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("failure_policy", {})


def get_notification_rules(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("notification_rules", {})


# ── Guard mode ──────────────────────────────────────────────────────────

# Risk levels from most to least severe, as produced by policy.evaluate_danger.
# Index 0 = most severe.
RISK_ORDER: list[str] = ["极高", "高", "中", "低"]


def risk_rank(risk: str) -> int:
    """Return the severity rank of *risk* (0 = most severe).

    Unknown values rank as least severe so they never trip a guard threshold.
    """
    try:
        return RISK_ORDER.index(risk)
    except ValueError:
        return len(RISK_ORDER)


def risk_at_least(risk: str, threshold: str) -> bool:
    """True when *risk* is at least as severe as *threshold*.

    Severity is ranked by RISK_ORDER, so a lower rank index means higher
    severity — hence the ``<=`` comparison.
    """
    return risk_rank(risk) <= risk_rank(threshold)


def get_guard_mode(config: dict[str, Any]) -> dict[str, Any]:
    """Return the guard_mode block with safe defaults.

    Guard mode is OFF by default.  When enabled, the PreToolUse hook can DENY a
    dangerous operation before it runs (see cli.cmd_hook).  ``action`` is one of
    "deny" (hard block, reason fed to Claude), "ask" (prompt the user), or
    "warn" (notify only, do not block).  ``min_risk`` gates which operations are
    guarded — only those at/above this risk level (default 极高, the most severe).
    """
    gm = dict(config.get("guard_mode", {}) or {})
    gm.setdefault("enabled", False)
    gm.setdefault("action", "deny")
    gm.setdefault("min_risk", "极高")
    return gm
