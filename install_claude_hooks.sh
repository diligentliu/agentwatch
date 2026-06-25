#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# AgentWatch — install Claude Code hooks
#
# Thin wrapper: resolves the Python interpreter (preferring the project .venv)
# and delegates all install logic to install_hooks_safe.py, the single source
# of truth for hook configuration (schema, matchers, idempotent de-duplication,
# and backup of the existing settings.json).
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Resolve Python path — prefer .venv, fall back to system python3.
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"
else
    PYTHON_BIN="$(which python3 2>/dev/null || which python 2>/dev/null || echo '')"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[AgentWatch] ERROR: Could not find python3. Please install Python 3.10+ and try again."
    exit 1
fi

echo "[AgentWatch] Using Python: $PYTHON_BIN"

# Delegate to the single source of truth. Run from SCRIPT_DIR so the installer
# resolves the project root correctly.
cd "$SCRIPT_DIR"
"$PYTHON_BIN" install_hooks_safe.py

echo ""
echo "[AgentWatch] Done!"
echo "[AgentWatch] To test, run:      agentwatch simulate danger"
echo "[AgentWatch] To uninstall, run: bash $SCRIPT_DIR/uninstall_claude_hooks.sh"
